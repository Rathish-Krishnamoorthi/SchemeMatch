import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app import admin_routes
from app.main import app
from app.models import Scheme
from app.services import llm_service


_SECRET = "unit-test-credential-never-return-this"


@pytest.mark.parametrize(
    ("provider", "base_url", "expected_path", "response_data", "header", "header_value"),
    [
        (
            "openai",
            "https://api.openai.com/v1",
            "/v1/chat/completions",
            {"choices": [{"message": {"content": '{"connection":"ok"}'}}]},
            "authorization",
            f"Bearer {_SECRET}",
        ),
        (
            "openai_compatible",
            "https://llm.example/v1",
            "/v1/chat/completions",
            {"choices": [{"message": {"content": '{"connection":"ok"}'}}]},
            "authorization",
            f"Bearer {_SECRET}",
        ),
        (
            "google",
            "https://ignored.example",
            "/v1beta/models/model-name:generateContent",
            {"candidates": [{"content": {"parts": [{"text": '{"connection":"ok"}'}]}}]},
            "x-goog-api-key",
            _SECRET,
        ),
        (
            "anthropic",
            "https://ignored.example",
            "/v1/messages",
            {"content": [{"type": "text", "text": '{"connection":"ok"}'}]},
            "x-api-key",
            _SECRET,
        ),
        (
            "ollama",
            "http://ollama:11434",
            "/api/chat",
            {"message": {"content": '{"connection":"ok"}'}},
            None,
            None,
        ),
    ],
)
def test_provider_adapters_make_supported_requests(
    provider, base_url, expected_path, response_data, header, header_value
) -> None:
    config = llm_service.RuntimeLLMConfig(
        provider=provider,
        model="model-name",
        base_url=base_url,
        api_key=None if provider == "ollama" else _SECRET,
    )
    observed = {}

    def respond(request: httpx.Request) -> httpx.Response:
        observed["request"] = request
        return httpx.Response(200, json=response_data)

    client = llm_service.HTTPJSONLLMClient(config, httpx.MockTransport(respond))
    assert client.complete_json("system", "prompt") == '{"connection":"ok"}'
    request = observed["request"]
    assert request.url.path == expected_path
    if header:
        assert request.headers[header] == header_value
    else:
        assert "authorization" not in request.headers


def test_runtime_config_loads_only_the_selected_provider_credential(monkeypatch) -> None:
    monkeypatch.setattr(
        llm_service,
        "_stored_selection",
        lambda: {"provider": "google", "model": "gemini-test"},
    )
    monkeypatch.setenv("OPENAI_API_KEY", "unused-openai-credential")
    monkeypatch.setenv("GOOGLE_API_KEY", _SECRET)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "unused-anthropic-credential")

    config = llm_service.get_runtime_config()
    safe_settings = llm_service.get_safe_settings()

    assert config.provider == "google"
    assert config.api_key == _SECRET
    assert safe_settings["credential_status"] == "configured"
    assert safe_settings["credential_variable"] == "GOOGLE_API_KEY"
    assert _SECRET not in json.dumps(safe_settings)


def test_openai_compatible_default_uses_current_groq_model(monkeypatch) -> None:
    monkeypatch.setattr(llm_service, "_stored_selection", lambda: None)
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.setenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("OPENAI_API_KEY", _SECRET)

    config = llm_service.get_runtime_config()

    assert config.model == "openai/gpt-oss-120b"


def test_runtime_config_reports_missing_selected_key_without_echoing_other_keys(monkeypatch) -> None:
    monkeypatch.setattr(
        llm_service,
        "_stored_selection",
        lambda: {"provider": "anthropic", "model": "claude-test"},
    )
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", _SECRET)

    with pytest.raises(llm_service.LLMServiceError, match="ANTHROPIC_API_KEY") as exc:
        llm_service.get_runtime_config()

    assert _SECRET not in str(exc.value)


def test_rate_limit_retries_but_quota_error_does_not(monkeypatch) -> None:
    monkeypatch.setattr(llm_service.time, "sleep", lambda _seconds: None)
    config = llm_service.RuntimeLLMConfig("openai", "model", "https://api.openai.com/v1", _SECRET)
    calls = 0

    def recover_after_rate_limit(_request):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, json={"error": {"message": "rate limit"}})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"ok":true}'}}]},
        )

    response = llm_service.HTTPJSONLLMClient(
        config, httpx.MockTransport(recover_after_rate_limit),
    ).complete_json("system", "prompt")
    assert response == '{"ok":true}'
    assert calls == 2

    calls = 0

    def quota_error(_request):
        nonlocal calls
        calls += 1
        return httpx.Response(
            429,
            json={"error": {"code": "insufficient_quota", "message": "quota exhausted"}},
        )

    with pytest.raises(llm_service.LLMServiceError, match="insufficient quota"):
        llm_service.HTTPJSONLLMClient(
            config, httpx.MockTransport(quota_error),
        ).complete_json("system", "prompt")
    assert calls == 1


def test_timeout_is_retried_and_then_reported(monkeypatch) -> None:
    monkeypatch.setattr(llm_service.time, "sleep", lambda _seconds: None)
    calls = 0

    def timeout(_request):
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("provider timed out")

    config = llm_service.RuntimeLLMConfig("ollama", "local-model", "http://ollama:11434", None)
    with pytest.raises(llm_service.LLMServiceError, match="timed out") as exc:
        llm_service.HTTPJSONLLMClient(
            config, httpx.MockTransport(timeout),
        ).complete_json("system", "prompt")
    assert exc.value.status_code == 504
    assert calls == llm_service._MAX_ATTEMPTS


@pytest.mark.parametrize(
    ("status_code", "error_body"),
    [
        (401, {"error": {"message": "unauthorized"}}),
        (400, {"error": {"message": "API key not valid. Please pass a valid API key."}}),
        (429, {"error": {"code": "insufficient_quota", "message": "quota exceeded"}}),
    ],
)
def test_provider_credential_errors_are_clear_and_never_echo_secrets(
    status_code, error_body
) -> None:
    config = llm_service.RuntimeLLMConfig(
        "google", "gemini-test", None, _SECRET,
    )
    client = llm_service.HTTPJSONLLMClient(
        config,
        httpx.MockTransport(lambda _request: httpx.Response(status_code, json=error_body)),
    )

    with pytest.raises(llm_service.LLMServiceError) as exc:
        client.complete_json("system", "prompt")

    assert _SECRET not in str(exc.value)
    if status_code in (400, 401):
        assert "API key is invalid" in str(exc.value)
    else:
        assert "insufficient quota" in str(exc.value)


def test_finder_explanations_accept_only_exact_source_quotes() -> None:
    scheme = Scheme(
        scheme_id="scheme-1",
        name="Student support",
        category="Education",
        description="A grant for tuition costs.",
        eligibility={"min_age": 18},
        benefits="Tuition reimbursement up to 10000.",
        documents=["Identity proof"],
        application_process=["Apply online"],
        official_url="https://education.gov.in",
        source="Education department",
    )
    results = [{"scheme": scheme, "weighted_score": 90}]

    class FakeProvider:
        response = json.dumps({
            "matches": [{
                "scheme_id": "scheme-1",
                "reasoning": "Its tuition support aligns with your education funding goal.",
                "evidence": [{"field": "benefits", "quote": "Tuition reimbursement up to 10000."}],
            }],
        })

        def complete_json(self, system_prompt, user_prompt):
            assert "Do not infer eligibility" in system_prompt
            assert "scheme-1" in user_prompt
            assert "search_context" in user_prompt
            return self.response

    annotated = llm_service.generate_grounded_finder_explanations(
        results,
        FakeProvider(),
        context={"objective": "fund my education"},
    )
    assert annotated[0]["evidence"][0]["quote"] == "Tuition reimbursement up to 10000."
    assert annotated[0]["explanation"] == "Its tuition support aligns with your education funding goal."

    FakeProvider.response = json.dumps({
        "matches": [{
            "scheme_id": "scheme-1",
            "reasoning": "This scheme provides guaranteed free tuition.",
            "evidence": [{"field": "benefits", "quote": "Guaranteed free tuition."}],
        }],
    })
    with pytest.raises(llm_service.LLMServiceError, match="not present"):
        llm_service.generate_grounded_finder_explanations(results, FakeProvider())


def test_finder_explanations_reject_unretrieved_scheme_ids() -> None:
    class FakeProvider:
        def complete_json(self, _system_prompt, _user_prompt):
            return json.dumps({
                "matches": [{
                    "scheme_id": "not-retrieved",
                    "reasoning": "A reason.",
                    "evidence": [{"field": "benefits", "quote": "A quote"}],
                }],
            })

    scheme = Scheme(
        scheme_id="scheme-1",
        name="Support",
        category="Education",
        description="Education grant.",
        eligibility={"min_age": 18},
        benefits="Tuition support.",
        official_url="https://education.gov.in",
        source="Education department",
    )
    with pytest.raises(llm_service.LLMServiceError, match="exactly the retrieved schemes"):
        llm_service.generate_grounded_finder_explanations([{"scheme": scheme}], FakeProvider())


def test_admin_llm_settings_require_auth_and_never_return_credentials(monkeypatch) -> None:
    monkeypatch.setattr(
        llm_service,
        "_stored_selection",
        lambda: {"provider": "openai", "model": "gpt-test"},
    )
    monkeypatch.setenv("OPENAI_API_KEY", _SECRET)

    with TestClient(app) as client:
        response = client.get("/admin-api/settings/llm")
        assert response.status_code == 403

        app.dependency_overrides[admin_routes.require_admin] = lambda: None
        try:
            response = client.get("/admin-api/settings/llm")
        finally:
            app.dependency_overrides.pop(admin_routes.require_admin, None)

    assert response.status_code == 200
    assert response.json()["credential_status"] == "configured"
    assert _SECRET not in response.text


def test_admin_can_save_provider_and_test_connection(monkeypatch) -> None:
    monkeypatch.setattr(
        admin_routes,
        "save_provider_settings",
        lambda settings: {
            "provider": settings.provider,
            "model": settings.model,
            "credential_status": "configured",
        },
    )
    monkeypatch.setattr(
        admin_routes,
        "test_provider_connection",
        lambda: {"provider": "openai_compatible", "model": "llama-test"},
    )
    app.dependency_overrides[admin_routes.require_admin] = lambda: None
    try:
        with TestClient(app) as client:
            saved = client.put(
                "/admin-api/settings/llm",
                json={"provider": "openai_compatible", "model": "llama-test"},
            )
            tested = client.post("/admin-api/settings/llm/test")
    finally:
        app.dependency_overrides.pop(admin_routes.require_admin, None)

    assert saved.status_code == 200
    assert saved.json() == {
        "provider": "openai_compatible",
        "model": "llama-test",
        "credential_status": "configured",
    }
    assert tested.status_code == 200
    assert tested.json() == {"provider": "openai_compatible", "model": "llama-test"}


def test_admin_panel_serves_provider_configuration_controls() -> None:
    with TestClient(app) as client:
        response = client.get("/admin")

    assert response.status_code == 200
    assert 'id="page-llm-settings"' in response.text
    assert 'id="llm-provider"' in response.text
    assert 'id="llm-credential-mask"' in response.text
    assert "testLLMConnection()" in response.text
