import pytest

from app.models import Scheme
from app.services import semantic_finder


def make_scheme(scheme_id: str, eligibility: dict, category: str = "Education") -> Scheme:
    return Scheme(
        scheme_id=scheme_id,
        name=f"Scheme {scheme_id}",
        category=category,
        description="Education support for students",
        eligibility=eligibility,
        benefits="Tuition support and stipend",
        documents=["Identity proof"],
        application_process=["Apply online"],
        official_url="https://education.gov.in",
        source="Education department",
    )


def test_finder_semantically_ranks_only_known_eligible_schemes(monkeypatch) -> None:
    eligible = make_scheme("eligible", {"min_age": 18, "max_income": 100000})
    unknown = make_scheme("unknown", {"genders": ["Female"]})
    unverified = make_scheme("unverified", {})
    ineligible = make_scheme("ineligible", {"min_age": 40})
    monkeypatch.setattr(semantic_finder, "load_schemes", lambda: [eligible, unknown, unverified, ineligible])
    monkeypatch.setattr(semantic_finder, "_get_collection", lambda: object())
    monkeypatch.setattr(semantic_finder, "_sync_catalogue", lambda collection, schemes: None)
    monkeypatch.setattr(semantic_finder, "_embed", lambda texts: [[1.0, 0.0]])
    monkeypatch.setattr(
        semantic_finder,
        "generate_grounded_finder_explanations",
        lambda results, **_kwargs: results,
    )
    searched: list[str] = []

    def semantic_scores(collection, query_embedding, schemes):
        searched.extend(scheme.scheme_id for scheme in schemes)
        return {"eligible": 0.9}

    monkeypatch.setattr(semantic_finder, "_query_semantic_scores", semantic_scores)

    result = semantic_finder.find_schemes(
        {"age": "25", "annual_income": "50000"},
        {"category": "Education", "objective": "tuition support"},
    )

    assert [item["scheme"].scheme_id for item in result["results"]] == ["eligible"]
    assert [item["scheme"].scheme_id for item in result["unknown"]] == ["unknown", "unverified"]
    assert result["excluded_count"] == 1
    assert result["total_candidates"] == 1
    assert searched == ["eligible"]
    assert result["weights"] == {"semantic": 0.60, "category": 0.25, "benefit": 0.15}


def test_custom_weights_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="sum to 1"):
        semantic_finder._validated_weights({
            "semantic": 0.7,
            "category": 0.2,
            "benefit": 0.2,
        })


def test_finder_limits_llm_explanations_to_displayed_results(monkeypatch) -> None:
    schemes = [make_scheme(f"eligible-{index}", {"min_age": 18}) for index in range(51)]
    monkeypatch.setattr(semantic_finder, "load_schemes", lambda: schemes)
    monkeypatch.setattr(semantic_finder, "_get_collection", lambda: object())
    monkeypatch.setattr(semantic_finder, "_sync_catalogue", lambda collection, records: None)
    monkeypatch.setattr(semantic_finder, "_embed", lambda texts: [[1.0, 0.0]])
    monkeypatch.setattr(
        semantic_finder,
        "_query_semantic_scores",
        lambda collection, embedding, records: {scheme.scheme_id: 0.9 for scheme in records},
    )
    explanation_batch_sizes = []
    explanation_contexts = []

    def capture_explanations(results, **kwargs):
        explanation_batch_sizes.append(len(results))
        explanation_contexts.append(kwargs["context"])
        return results

    monkeypatch.setattr(
        semantic_finder,
        "generate_grounded_finder_explanations",
        capture_explanations,
    )

    result = semantic_finder.find_schemes(
        {"age": 25},
        {"category": "Education", "objective": "tuition support"},
    )

    assert result["total_candidates"] == 51
    assert len(result["results"]) == 5
    assert explanation_batch_sizes == [5]
    assert explanation_contexts[0]["selected_category"] == "Education"
    assert explanation_contexts[0]["objective"] == "tuition support"
    assert explanation_contexts[0]["profile"]["age"] == 25


def test_finder_filters_by_selected_category_before_eligibility_and_ranking(monkeypatch) -> None:
    selected = make_scheme("selected", {"min_age": 18}, "Education")
    other = make_scheme("other", {"min_age": 18}, "Agriculture")
    monkeypatch.setattr(semantic_finder, "load_schemes", lambda: [selected, other])
    monkeypatch.setattr(semantic_finder, "_get_collection", lambda: object())
    monkeypatch.setattr(semantic_finder, "_sync_catalogue", lambda collection, records: None)
    monkeypatch.setattr(semantic_finder, "_embed", lambda texts: [[1.0, 0.0]])
    searched: list[str] = []
    monkeypatch.setattr(
        semantic_finder,
        "_query_semantic_scores",
        lambda collection, embedding, records: (
            searched.extend(scheme.scheme_id for scheme in records) or {"selected": 0.9}
        ),
    )
    monkeypatch.setattr(
        semantic_finder,
        "generate_grounded_finder_explanations",
        lambda results, **_kwargs: results,
    )

    result = semantic_finder.find_schemes(
        {"age": 25},
        {"category": "Education", "objective": "tuition support"},
    )

    assert [item["scheme"].scheme_id for item in result["results"]] == ["selected"]
    assert result["total_candidates"] == 1
    assert result["excluded_count"] == 0
    assert searched == ["selected"]


def test_chroma_catalogue_sync_updates_changed_records(monkeypatch) -> None:
    scheme = make_scheme("scheme-a", {"min_age": 18})

    class FakeCollection:
        records = {
            "stale": {"content_hash": "old"},
            "scheme-a": {"content_hash": "old"},
        }
        deleted: list[str] = []
        upserted: list[str] = []

        def get(self, include):
            return {"ids": list(self.records), "metadatas": list(self.records.values())}

        def delete(self, ids):
            self.deleted.extend(ids)
            for scheme_id in ids:
                self.records.pop(scheme_id, None)

        def upsert(self, ids, documents, embeddings, metadatas):
            self.upserted.extend(ids)
            self.records.update(zip(ids, metadatas))

    collection = FakeCollection()
    monkeypatch.setattr(semantic_finder, "_synced_catalogue_hash", None)
    monkeypatch.setattr(semantic_finder, "_embed", lambda texts: [[1.0, 0.0] for _ in texts])

    semantic_finder._sync_catalogue(collection, [scheme])

    assert collection.deleted == ["stale"]
    assert collection.upserted == ["scheme-a"]


def test_persistent_chroma_search_returns_only_requested_candidates(monkeypatch, tmp_path) -> None:
    pytest.importorskip("chromadb")
    eligible = make_scheme("eligible", {"min_age": 18})
    ineligible = make_scheme("ineligible", {"min_age": 60})
    monkeypatch.setattr(semantic_finder, "_CHROMA_PATH", tmp_path)
    monkeypatch.setattr(semantic_finder, "_chroma_client", None)
    monkeypatch.setattr(semantic_finder, "_synced_catalogue_hash", None)
    monkeypatch.setattr(semantic_finder, "_embed", lambda texts: [[1.0, 0.0] for _ in texts])

    collection = semantic_finder._get_collection()
    semantic_finder._sync_catalogue(collection, [eligible, ineligible])
    results = semantic_finder._query_semantic_scores(collection, [1.0, 0.0], [eligible])

    assert results == {"eligible": pytest.approx(1.0)}
