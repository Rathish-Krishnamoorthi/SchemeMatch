"""Provider-neutral, environment-secret-backed structured LLM access."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import quote

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pymongo.errors import PyMongoError

from app.services.scheme_store import SchemeStoreUnavailable, _get_mongo_client

SUPPORTED_PROVIDERS = {"openai", "google", "anthropic", "openai_compatible", "ollama"}
PROVIDER_DEFAULTS = {
    "openai": "gpt-4o-mini",
    "google": "gemini-2.5-flash",
    "anthropic": "claude-3-5-haiku-latest",
    "openai_compatible": "openai/gpt-oss-120b",
    "ollama": "llama3.2",
}
_DATABASE_SETTINGS_ID = "active_llm_provider"
_REQUEST_TIMEOUT_SECONDS = 30.0
_MAX_ATTEMPTS = 3


class LLMServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


class ProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str
    base_url: str | None = None


class LLMProviderSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1, max_length=40)
    model: str = Field(min_length=1, max_length=160)


class EvidenceQuote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str = Field(pattern=r"^(name|category|description|benefits|documents|application_process)$")
    quote: str = Field(min_length=1, max_length=500)


class SchemeGrounding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scheme_id: str = Field(min_length=1, max_length=100)
    reasoning: str = Field(min_length=1, max_length=500)
    evidence: list[EvidenceQuote] = Field(min_length=1, max_length=3)

    @field_validator("reasoning")
    @classmethod
    def reasoning_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("LLM reasoning must not be blank.")
        return value.strip()


class GroundedFinderOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matches: list[SchemeGrounding] = Field(max_length=5)


class ConnectionTestOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connection: str = Field(pattern=r"^ok$")


class LLMClient(Protocol):
    def complete_json(self, system_prompt: str, user_prompt: str) -> str: ...


@dataclass(frozen=True)
class RuntimeLLMConfig:
    provider: str
    model: str
    base_url: str | None
    api_key: str | None


def _environment_provider() -> str:
    return os.getenv("LLM_PROVIDER", "ollama").strip().casefold()


def _environment_model(provider: str) -> str:
    return os.getenv("LLM_MODEL", PROVIDER_DEFAULTS.get(provider, "")).strip()


def _stored_selection() -> dict[str, str] | None:
    try:
        client = _get_mongo_client()
        document = client[os.getenv("DATABASE_NAME", "schemematch")]["app_settings"].find_one(
            {"_id": _DATABASE_SETTINGS_ID},
            {"provider": 1, "model": 1},
        )
    except PyMongoError as exc:
        raise SchemeStoreUnavailable("Database error loading LLM provider settings.") from exc
    if not document:
        return None
    return {"provider": str(document.get("provider", "")), "model": str(document.get("model", ""))}


def resolve_provider_selection() -> tuple[str, str]:
    stored = _stored_selection()
    provider = (stored or {}).get("provider") or _environment_provider()
    model = (stored or {}).get("model") or _environment_model(provider)
    if provider not in SUPPORTED_PROVIDERS:
        raise LLMServiceError(
            f"Unsupported LLM_PROVIDER '{provider}'. Select one of: {', '.join(sorted(SUPPORTED_PROVIDERS))}."
        )
    if not model:
        raise LLMServiceError(f"Set LLM_MODEL for the selected '{provider}' provider.")
    return provider, model


def _selected_api_key(provider: str) -> tuple[str | None, str | None]:
    key_variable = {
        "openai": "OPENAI_API_KEY",
        "openai_compatible": "OPENAI_API_KEY",
        "google": "GOOGLE_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }.get(provider)
    if not key_variable:
        return None, None
    key = os.getenv(key_variable, "").strip()
    if not key:
        return None, key_variable
    return key, key_variable


def get_runtime_config() -> RuntimeLLMConfig:
    provider, model = resolve_provider_selection()
    api_key, key_variable = _selected_api_key(provider)
    if key_variable and not api_key:
        raise LLMServiceError(
            f"LLM provider '{provider}' is selected, but {key_variable} is not configured in the backend environment."
        )
    base_url = os.getenv("LLM_BASE_URL", "").strip() or None
    if provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "").strip() or "http://127.0.0.1:11434"
    elif provider == "openai" and not base_url:
        base_url = "https://api.openai.com/v1"
    elif provider == "openai_compatible" and not base_url:
        raise LLMServiceError(
            "LLM_BASE_URL is required for the openai_compatible provider."
        )
    return RuntimeLLMConfig(provider, model, base_url, api_key)


def get_safe_settings() -> dict[str, Any]:
    provider, model = resolve_provider_selection()
    key, key_variable = _selected_api_key(provider)
    endpoint_variable = (
        "OLLAMA_BASE_URL" if provider == "ollama"
        else "LLM_BASE_URL" if provider in {"openai", "openai_compatible"}
        else None
    )
    credential_status = (
        "not_required"
        if provider == "ollama"
        else "configured" if key
        else "missing"
    )
    return {
        "provider": provider,
        "model": model,
        "base_url_configured": bool(endpoint_variable and os.getenv(endpoint_variable, "").strip()),
        "credential_status": credential_status,
        "credential_variable": key_variable,
        "supported_providers": sorted(SUPPORTED_PROVIDERS),
        "secrets_stored_in_database": False,
    }


def save_provider_settings(settings: LLMProviderSettings) -> dict[str, Any]:
    provider = settings.provider.strip().casefold()
    model = settings.model.strip()
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Choose a supported provider: {', '.join(sorted(SUPPORTED_PROVIDERS))}.")
    if not model or len(model) > 160:
        raise ValueError("Provide a model name between 1 and 160 characters.")
    try:
        client = _get_mongo_client()
        client[os.getenv("DATABASE_NAME", "schemematch")]["app_settings"].update_one(
            {"_id": _DATABASE_SETTINGS_ID},
            {"$set": {"provider": provider, "model": model}},
            upsert=True,
        )
    except PyMongoError as exc:
        raise SchemeStoreUnavailable("Database error saving LLM provider settings.") from exc
    return get_safe_settings()


def _openai_messages(system_prompt: str, user_prompt: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


class ProviderAdapter(Protocol):
    def build_request(
        self,
        config: RuntimeLLMConfig,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[str, str, dict, dict[str, str]]: ...

    def extract_text(self, response_data: dict[str, Any]) -> str: ...


class OpenAICompatibleAdapter:
    def build_request(self, config: RuntimeLLMConfig, system_prompt: str, user_prompt: str):
        return (
            "POST",
            f"{(config.base_url or '').rstrip('/')}/chat/completions",
            {
                "model": config.model,
                "messages": _openai_messages(system_prompt, user_prompt),
                "response_format": {"type": "json_object"},
                "temperature": 0,
            },
            {"Authorization": f"Bearer {config.api_key}"},
        )

    def extract_text(self, response_data: dict[str, Any]) -> str:
        return _extract_openai_text(response_data)


class GoogleGeminiAdapter:
    def build_request(self, config: RuntimeLLMConfig, system_prompt: str, user_prompt: str):
        base = "https://generativelanguage.googleapis.com/v1beta"
        return (
            "POST",
            f"{base.rstrip('/')}/models/{quote(config.model, safe='')}:generateContent",
            {
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0},
            },
            {"x-goog-api-key": str(config.api_key)},
        )

    def extract_text(self, response_data: dict[str, Any]) -> str:
        try:
            return "".join(
                part.get("text", "")
                for part in response_data["candidates"][0]["content"]["parts"]
            )
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMServiceError(
                "The google provider returned an unsupported response format.",
                status_code=502,
            ) from exc


class AnthropicAdapter:
    def build_request(self, config: RuntimeLLMConfig, system_prompt: str, user_prompt: str):
        base = "https://api.anthropic.com"
        return (
            "POST",
            f"{base.rstrip('/')}/v1/messages",
            {
                "model": config.model,
                "max_tokens": 4096,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
                "temperature": 0,
            },
            {
                "x-api-key": str(config.api_key),
                "anthropic-version": "2023-06-01",
            },
        )

    def extract_text(self, response_data: dict[str, Any]) -> str:
        try:
            return "".join(
                part.get("text", "")
                for part in response_data["content"]
                if part.get("type") == "text"
            )
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMServiceError(
                "The anthropic provider returned an unsupported response format.",
                status_code=502,
            ) from exc


class OllamaAdapter:
    def build_request(self, config: RuntimeLLMConfig, system_prompt: str, user_prompt: str):
        base = (config.base_url or "").rstrip("/")
        if base.endswith("/v1"):
            return (
                "POST",
                f"{base}/chat/completions",
                {
                    "model": config.model,
                    "messages": _openai_messages(system_prompt, user_prompt),
                    "response_format": {"type": "json_object"},
                    "temperature": 0,
                },
                {},
            )
        return (
            "POST",
            f"{base}/api/chat",
            {
                "model": config.model,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
            {},
        )

    def extract_text(self, response_data: dict[str, Any]) -> str:
        try:
            if "choices" in response_data:
                return _extract_openai_text(response_data)
            return response_data["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMServiceError(
                "The ollama provider returned an unsupported response format.",
                status_code=502,
            ) from exc


def _extract_openai_text(response_data: dict[str, Any]) -> str:
    try:
        return response_data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMServiceError(
            "The openai-compatible provider returned an unsupported response format.",
            status_code=502,
        ) from exc


_ADAPTERS: dict[str, ProviderAdapter] = {
    "openai": OpenAICompatibleAdapter(),
    "openai_compatible": OpenAICompatibleAdapter(),
    "google": GoogleGeminiAdapter(),
    "anthropic": AnthropicAdapter(),
    "ollama": OllamaAdapter(),
}


def _provider_error(response: httpx.Response, provider: str) -> LLMServiceError:
    try:
        error_body = response.json().get("error", {})
        if isinstance(error_body, dict):
            provider_code = " ".join(
                str(error_body.get(key, ""))
                for key in ("code", "status", "type")
            ).casefold()
            provider_message = str(error_body.get("message", "")).casefold()
        else:
            provider_code = ""
            provider_message = str(error_body).casefold()
    except (ValueError, AttributeError):
        provider_code = ""
        provider_message = ""

    if response.status_code == 401 or any(
        phrase in provider_message
        for phrase in ("invalid api key", "api key is not valid", "api key not valid")
    ):
        message = f"The {provider} API key is invalid, expired, or not accepted."
    elif response.status_code == 403:
        message = f"The {provider} credential lacks permission to use this model or endpoint."
    elif response.status_code == 429 or "resource_exhausted" in provider_code:
        if any(
            indicator in provider_code or indicator in provider_message
            for indicator in ("quota", "billing", "insufficient_quota", "resource_exhausted")
        ):
            message = f"The {provider} account has insufficient quota or billing credit."
        else:
            message = f"The {provider} rate limit was reached; retry after a short wait."
    elif response.status_code == 404:
        message = f"The {provider} model or endpoint was not found. Check the configured model and base URL."
    elif response.status_code >= 500:
        message = f"The {provider} service is temporarily unavailable."
    else:
        message = f"The {provider} request was rejected (HTTP {response.status_code}). Check provider, model, and request configuration."
    return LLMServiceError(message, status_code=502 if response.status_code != 429 else 503)


class HTTPJSONLLMClient:
    def __init__(
        self,
        config: RuntimeLLMConfig,
        transport: httpx.BaseTransport | None = None,
    ):
        self.config = config
        self.transport = transport

    def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        adapter = _ADAPTERS.get(self.config.provider)
        if adapter is None:
            raise LLMServiceError(f"Unsupported LLM provider '{self.config.provider}'.")
        method, url, payload, headers = adapter.build_request(
            self.config, system_prompt, user_prompt,
        )
        for attempt in range(_MAX_ATTEMPTS):
            try:
                with httpx.Client(
                    timeout=_REQUEST_TIMEOUT_SECONDS,
                    transport=self.transport,
                ) as client:
                    response = client.request(method, url, json=payload, headers=headers)
            except httpx.TimeoutException as exc:
                if attempt + 1 == _MAX_ATTEMPTS:
                    raise LLMServiceError(
                        f"The {self.config.provider} request timed out. Check provider availability and retry.",
                        status_code=504,
                    ) from exc
                time.sleep(0.25 * (2 ** attempt))
                continue
            except httpx.RequestError as exc:
                if attempt + 1 == _MAX_ATTEMPTS:
                    raise LLMServiceError(
                        f"Could not connect to the configured {self.config.provider} endpoint.",
                        status_code=503,
                    ) from exc
                time.sleep(0.25 * (2 ** attempt))
                continue

            if response.status_code == 429 and _is_quota_error(response):
                raise _provider_error(response, self.config.provider)
            if (
                response.status_code == 429 or response.status_code >= 500
            ) and attempt + 1 < _MAX_ATTEMPTS:
                try:
                    retry_after = min(2.0, max(0.0, float(response.headers.get("Retry-After", "0"))))
                except ValueError:
                    retry_after = 0.0
                time.sleep(retry_after or (0.25 * (2 ** attempt)))
                continue
            if not response.is_success:
                raise _provider_error(response, self.config.provider)
            try:
                response_data = response.json()
            except ValueError as exc:
                raise LLMServiceError(
                    f"The {self.config.provider} provider returned invalid JSON.",
                    status_code=502,
                ) from exc
            return adapter.extract_text(response_data)
        raise LLMServiceError(
            f"The {self.config.provider} service could not complete the request.",
            status_code=503,
        )


def _is_quota_error(response: httpx.Response) -> bool:
    try:
        error_body = response.json().get("error", {})
        if isinstance(error_body, dict):
            text = " ".join(
                str(error_body.get(key, ""))
                for key in ("code", "status", "type", "message")
            ).casefold()
        else:
            text = str(error_body).casefold()
    except (ValueError, AttributeError):
        return False
    return any(
        indicator in text
        for indicator in ("quota", "billing", "insufficient_quota", "resource_exhausted")
    )


def _scheme_field_values(scheme: dict[str, Any]) -> dict[str, list[str]]:
    return {
        "name": [str(scheme.get("name", ""))],
        "category": [str(scheme.get("category", ""))],
        "description": [str(scheme.get("description", ""))],
        "benefits": [str(scheme.get("benefits", ""))],
        "documents": [str(item) for item in scheme.get("documents", [])],
        "application_process": [str(item) for item in scheme.get("application_process", [])],
    }


def generate_grounded_finder_explanations(
    results: list[dict[str, Any]],
    provider: LLMClient | None = None,
    *,
    context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not results:
        return []

    sources = []
    for result in results:
        scheme = result["scheme"]
        scheme_data = scheme.model_dump() if hasattr(scheme, "model_dump") else scheme
        sources.append({
            "scheme_id": scheme_data["scheme_id"],
            "name": scheme_data["name"],
            "category": scheme_data["category"],
            "description": scheme_data["description"],
            "benefits": scheme_data["benefits"],
            "documents": scheme_data.get("documents", []),
            "application_process": scheme_data.get("application_process", []),
            "eligibility_reasons": result.get("eligibility").reasons
            if result.get("eligibility") else [],
            "relevance_scores": {
                key: result[key]
                for key in ("semantic_score", "category_score", "benefit_score", "weighted_score")
                if key in result
            },
        })

    system_prompt = (
        "You explain ranked government scheme matches using ONLY the supplied profile, "
        "search request, and scheme records. These results have already passed recorded "
        "rule-based eligibility checks. Do not infer eligibility or make a new "
        "eligibility determination, "
        "promise approval, or add outside facts. Write a concise, user-specific reason "
        "of 1 or 2 sentences explaining how the scheme's recorded purpose or benefits "
        "relate to the selected category, objective, and relevant profile details. "
        "Do not mention a profile detail unless it is supplied. Return valid JSON exactly "
        "matching "
        '{"matches":[{"scheme_id":"...","reasoning":"...","evidence":'
        '[{"field":"benefits","quote":"exact source excerpt"}]}]}. '
        "Return exactly one match for every supplied scheme_id and 1 to 3 exact, "
        "contiguous quotes copied verbatim from that scheme's fields. The field must "
        "be one of name, category, description, benefits, documents, application_process."
    )
    user_prompt = json.dumps({
        "search_context": context or {},
        "retrieved_schemes": sources,
    }, ensure_ascii=False)
    client = provider or HTTPJSONLLMClient(get_runtime_config())
    try:
        output = GroundedFinderOutput.model_validate_json(
            client.complete_json(system_prompt, user_prompt)
        )
    except LLMServiceError:
        raise
    except (ValueError, TypeError) as exc:
        raise LLMServiceError(
            "The LLM response was not valid structured JSON. Retry the search or test the configured model.",
            status_code=502,
        ) from exc

    expected_ids = {source["scheme_id"] for source in sources}
    returned_ids = [match.scheme_id for match in output.matches]
    if len(returned_ids) != len(set(returned_ids)) or set(returned_ids) != expected_ids:
        raise LLMServiceError(
            "The LLM response did not cover exactly the retrieved schemes. Retry the search.",
            status_code=502,
        )

    source_by_id = {source["scheme_id"]: source for source in sources}
    grounded_by_id: dict[str, dict[str, Any]] = {}
    for match in output.matches:
        fields = _scheme_field_values(source_by_id[match.scheme_id])
        for item in match.evidence:
            if not any(item.quote in value for value in fields[item.field]):
                raise LLMServiceError(
                    "The LLM returned evidence that was not present in the retrieved scheme data. Retry the search.",
                    status_code=502,
                )
        grounded_by_id[match.scheme_id] = {
            "evidence": [item.model_dump() for item in match.evidence],
            "explanation": match.reasoning.strip(),
        }

    annotated = []
    for result in results:
        scheme = result["scheme"]
        scheme_id = scheme.scheme_id if hasattr(scheme, "scheme_id") else scheme["scheme_id"]
        annotated.append({**result, **grounded_by_id[scheme_id]})
    return annotated


def test_provider_connection() -> dict[str, str]:
    config = get_runtime_config()
    client = HTTPJSONLLMClient(config)
    try:
        response = ConnectionTestOutput.model_validate_json(client.complete_json(
            "Return a JSON object with exactly one property named connection and value ok.",
            '{"connection":"ok"}',
        ))
    except LLMServiceError:
        raise
    except (ValueError, TypeError) as exc:
        raise LLMServiceError(
            "The provider connection succeeded, but its test response was not valid JSON.",
            status_code=502,
        ) from exc
    if response.connection != "ok":
        raise LLMServiceError(
            "The provider connection test returned an unexpected response.",
            status_code=502,
        )
    return {"status": "connected", "provider": config.provider, "model": config.model}
