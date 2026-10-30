"""Eligibility-first scheme retrieval with BGE-M3 embeddings in persistent ChromaDB."""
from __future__ import annotations

import hashlib
import math
import os
import re
from pathlib import Path
from threading import Lock
from typing import Any

from app.models import EligibilityResult, Scheme, UserProfile
from app.services.eligibility import evaluate_eligibility
from app.services.eligibility_scan import _coerce_profile
from app.services.llm_service import generate_grounded_finder_explanations
from app.services.recommender import _profile_context
from app.services.scheme_store import load_schemes

DEFAULT_WEIGHTS = {"semantic": 0.60, "category": 0.25, "benefit": 0.15}
MAX_RESULTS = 5
_MODEL_NAME = "BAAI/bge-m3"
_CHROMA_PATH = Path(os.getenv(
    "CHROMA_PERSIST_DIRECTORY",
    str(Path(__file__).resolve().parents[2] / ".chroma"),
))

_model: Any | None = None
_model_lock = Lock()
_chroma_client: Any | None = None
_chroma_lock = Lock()
_sync_lock = Lock()
_synced_catalogue_hash: str | None = None


class SemanticSearchUnavailable(RuntimeError):
    """Raised when the required BGE-M3 or ChromaDB backend cannot be used."""


def _get_model() -> Any:
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(_MODEL_NAME)
        except Exception as exc:
            raise SemanticSearchUnavailable(
                f"Unable to load embedding model {_MODEL_NAME}. Check model access and dependencies."
            ) from exc
    return _model


def _embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = _get_model()
    try:
        vectors = model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=32,
        )
    except Exception as exc:
        raise SemanticSearchUnavailable("BGE-M3 could not encode the scheme search text.") from exc
    return vectors.tolist()


def _get_collection() -> Any:
    global _chroma_client
    if _chroma_client is None:
        with _chroma_lock:
            if _chroma_client is None:
                try:
                    import chromadb
                    _chroma_client = chromadb.PersistentClient(path=str(_CHROMA_PATH))
                except Exception as exc:
                    raise SemanticSearchUnavailable(
                        "ChromaDB is unavailable. Install the backend requirements and check its storage path."
                    ) from exc
    try:
        return _chroma_client.get_or_create_collection(
            name="schemes-bge-m3",
            metadata={"hnsw:space": "cosine", "embedding_model": _MODEL_NAME},
        )
    except Exception as exc:
        raise SemanticSearchUnavailable("Unable to open the ChromaDB scheme collection.") from exc


def _scheme_text(scheme: Scheme) -> str:
    return " ".join(
        part for part in (
            scheme.name,
            scheme.category,
            scheme.description,
            scheme.benefits,
            " ".join(scheme.documents),
            " ".join(scheme.application_process),
        ) if part
    )


def _record_hash(scheme: Scheme) -> str:
    return hashlib.sha256(_scheme_text(scheme).encode("utf-8")).hexdigest()


def _sync_catalogue(collection: Any, schemes: list[Scheme]) -> None:
    global _synced_catalogue_hash
    catalogue_hash = hashlib.sha256(
        "\n".join(f"{s.scheme_id}:{_record_hash(s)}" for s in sorted(schemes, key=lambda x: x.scheme_id)).encode()
    ).hexdigest()
    with _sync_lock:
        if catalogue_hash == _synced_catalogue_hash:
            return
        try:
            existing = collection.get(include=["metadatas"])
        except Exception as exc:
            raise SemanticSearchUnavailable("Unable to inspect the ChromaDB scheme index.") from exc

        existing_ids = existing.get("ids", [])
        existing_metadata = existing.get("metadatas", [])
        existing_hashes = {
            scheme_id: (metadata or {}).get("content_hash")
            for scheme_id, metadata in zip(existing_ids, existing_metadata)
        }
        current_ids = {scheme.scheme_id for scheme in schemes}
        stale_ids = [scheme_id for scheme_id in existing_ids if scheme_id not in current_ids]
        if stale_ids:
            try:
                collection.delete(ids=stale_ids)
            except Exception as exc:
                raise SemanticSearchUnavailable("Unable to remove stale schemes from ChromaDB.") from exc

        changed = [
            scheme for scheme in schemes
            if existing_hashes.get(scheme.scheme_id) != _record_hash(scheme)
        ]
        for start in range(0, len(changed), 128):
            batch = changed[start:start + 128]
            try:
                embeddings = _embed([_scheme_text(scheme) for scheme in batch])
                collection.upsert(
                    ids=[scheme.scheme_id for scheme in batch],
                    documents=[_scheme_text(scheme) for scheme in batch],
                    embeddings=embeddings,
                    metadatas=[
                        {"scheme_id": scheme.scheme_id, "content_hash": _record_hash(scheme)}
                        for scheme in batch
                    ],
                )
            except SemanticSearchUnavailable:
                raise
            except Exception as exc:
                raise SemanticSearchUnavailable("Unable to update the ChromaDB scheme index.") from exc
        _synced_catalogue_hash = catalogue_hash


_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "in", "is", "it", "its", "of", "on", "or", "that", "the",
    "to", "was", "were", "will", "with", "i", "me", "my", "we", "our",
    "you", "your",
}


def _tokens(text: str) -> set[str]:
    return {
        word.casefold()
        for word in re.findall(r"[a-zA-Z0-9]+", text)
        if word.casefold() not in _STOP_WORDS
    }


def _keyword_overlap(query: str, target: str) -> float:
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0
    return len(query_tokens & _tokens(target)) / len(query_tokens)


def _cosine(left: list[float], right: list[float]) -> float:
    dot_product = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return dot_product / (left_norm * right_norm) if left_norm and right_norm else 0.0


def _validated_weights(weights: dict | None) -> dict[str, float]:
    if weights is None:
        return DEFAULT_WEIGHTS.copy()
    if set(weights) != set(DEFAULT_WEIGHTS):
        raise ValueError("weights must contain semantic, category, and benefit values.")
    normalized = {key: float(value) for key, value in weights.items()}
    if any(not math.isfinite(value) or value < 0 or value > 1 for value in normalized.values()):
        raise ValueError("weight values must be finite numbers between 0 and 1.")
    if not math.isclose(sum(normalized.values()), 1.0, abs_tol=0.001):
        raise ValueError("weight values must sum to 1.")
    return normalized


def _query_semantic_scores(collection: Any, query_embedding: list[float], schemes: list[Scheme]) -> dict[str, float]:
    scores: dict[str, float] = {}
    for start in range(0, len(schemes), 250):
        batch = schemes[start:start + 250]
        try:
            result = collection.query(
                query_embeddings=[query_embedding],
                n_results=len(batch),
                where={"scheme_id": {"$in": [scheme.scheme_id for scheme in batch]}},
                include=["distances"],
            )
        except Exception as exc:
            raise SemanticSearchUnavailable("ChromaDB semantic search failed.") from exc
        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        for scheme_id, distance in zip(ids, distances):
            scores[scheme_id] = max(0.0, min(1.0, 1.0 - float(distance)))
    return scores


DISCLAIMER = (
    "Only schemes whose recorded rules match your profile are semantically ranked. "
    "Unknown eligibility remains separate; always verify details with the official authority."
)


def find_schemes(
    raw_profile: dict,
    questionnaire: dict,
    weights: dict | None = None,
) -> dict:
    weight_values = _validated_weights(weights)
    profile: UserProfile = _coerce_profile(raw_profile)
    all_schemes = load_schemes()

    category = str(questionnaire.get("category") or "").strip()
    selected_schemes = (
        all_schemes
        if not category or category.casefold() == "all"
        else [
            scheme for scheme in all_schemes
            if scheme.category.strip().casefold() == category.casefold()
        ]
    )

    eligible: list[tuple[Scheme, EligibilityResult]] = []
    unknown: list[tuple[Scheme, EligibilityResult]] = []
    excluded_count = 0
    for scheme in selected_schemes:
        eligibility = evaluate_eligibility(profile, scheme)
        if eligibility.status == "NOT_ELIGIBLE":
            excluded_count += 1
        elif eligibility.status == "LIKELY_ELIGIBLE":
            eligible.append((scheme, eligibility))
        else:
            unknown.append((scheme, eligibility))

    objective = str(questionnaire.get("objective") or "").strip()
    benefit_needs = str(questionnaire.get("benefit_needs") or "").strip()
    location = str(questionnaire.get("location_preference") or "").strip()
    additional = questionnaire.get("additional") or {}
    additional_values = [value.strip() for value in additional.values() if isinstance(value, str) and value.strip()]

    profile_context = _profile_context(profile)
    query_text = " ".join(
        part for part in [profile_context, category, objective, benefit_needs, location, *additional_values] if part
    )
    relevance_query = " ".join(part for part in [category, objective, *additional_values] if part)
    benefit_query = " ".join(part for part in [benefit_needs, objective, *additional_values] if part)

    scored: list[dict] = []
    if eligible:
        collection = _get_collection()
        _sync_catalogue(collection, all_schemes)
        query_embedding = _embed([query_text])[0]
        eligible_schemes = [scheme for scheme, _ in eligible]
        semantic_scores = _query_semantic_scores(collection, query_embedding, eligible_schemes)

        for scheme, eligibility in eligible:
            semantic_score = semantic_scores.get(scheme.scheme_id, 0.0)
            category_score = _keyword_overlap(
                relevance_query,
                f"{scheme.category} {scheme.name} {scheme.description}",
            )
            benefit_score = _keyword_overlap(benefit_query, scheme.benefits)
            weighted_score = (
                weight_values["semantic"] * semantic_score
                + weight_values["category"] * category_score
                + weight_values["benefit"] * benefit_score
            )
            scored.append({
                "scheme": scheme,
                "eligibility": eligibility,
                "semantic_score": round(semantic_score * 100, 1),
                "category_score": round(category_score * 100, 1),
                "benefit_score": round(benefit_score * 100, 1),
                "weighted_score": round(weighted_score * 100, 1),
            })

    scored.sort(key=lambda result: (-result["weighted_score"], result["scheme"].name.casefold()))
    if scored:
        profile_context = {
            key: value
            for key, value in profile.model_dump(exclude_none=True).items()
            if value != ""
        }
        scored = generate_grounded_finder_explanations(
            scored[:MAX_RESULTS],
            context={
                "selected_category": category or "All",
                "objective": objective,
                "benefit_needs": benefit_needs,
                "location_preference": location,
                "additional_answers": additional_values,
                "profile": profile_context,
            },
        )
    unknown.sort(key=lambda item: (item[0].category.casefold(), item[0].name.casefold()))
    return {
        "results": scored,
        "unknown": [
            {"scheme": scheme, "eligibility": eligibility}
            for scheme, eligibility in unknown
        ],
        "excluded_count": excluded_count,
        "total_candidates": len(eligible),
        "query_text": query_text,
        "weights": weight_values,
        "disclaimer": DISCLAIMER,
    }
