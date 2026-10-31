from fastapi.testclient import TestClient

from app import main
from app.main import app
from app.models import EligibilityResult, Scheme
from app.services import eligibility_scan


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_recommendations_return_all_rule_eligible_schemes(monkeypatch) -> None:
    schemes = [
        Scheme(
            scheme_id="eligible-a",
            name="Eligible A",
            category="Education",
            description="Education support",
            eligibility={"min_age": 18, "max_age": 30},
            benefits="Tuition support",
            official_url="https://education.gov.in",
            source="Education department",
        ),
        Scheme(
            scheme_id="eligible-b",
            name="Eligible B",
            category="Housing",
            description="Housing support",
            eligibility={"min_age": 18},
            benefits="Housing support",
            official_url="https://housing.gov.in",
            source="Housing department",
        ),
        Scheme(
            scheme_id="excluded",
            name="Excluded scheme",
            category="Education",
            description="Not for this age",
            eligibility={"max_age": 18},
            benefits="Support",
            official_url="https://excluded.gov.in",
            source="Department",
        ),
    ]
    monkeypatch.setattr(main, "load_schemes", lambda: schemes)

    with TestClient(app) as client:
        response = client.post(
            "/api/recommendations",
            json={
                "profile": {
                    "age": 20,
                    "state": "Tamil Nadu",
                    "need": "I need financial assistance for my engineering education.",
                },
                "limit": 1,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert [item["scheme"]["scheme_id"] for item in body["recommendations"]] == [
        "eligible-a", "eligible-b",
    ]
    assert all(item["eligibility"]["status"] == "LIKELY_ELIGIBLE" for item in body["recommendations"])
    assert body["excluded_count"] == 1


def test_profile_validation_rejects_out_of_range_age() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/eligibility/check",
            json={"profile": {"age": 121}},
        )

    assert response.status_code == 422


def test_saved_profile_endpoint_returns_only_eligible_schemes(monkeypatch) -> None:
    schemes = [
        Scheme(
            scheme_id="eligible",
            name="Eligible",
            category="Education",
            description="Education support",
            eligibility={"min_age": 18, "max_income": 100000},
            benefits="Tuition support",
            official_url="https://education.gov.in",
            source="Education department",
        ),
        Scheme(
            scheme_id="unknown",
            name="Unknown",
            category="Education",
            description="Gender-specific support",
            eligibility={"genders": ["Female"]},
            benefits="Education support",
            official_url="https://education.gov.in",
            source="Education department",
        ),
        Scheme(
            scheme_id="ineligible",
            name="Ineligible",
            category="Education",
            description="Age-limited support",
            eligibility={"min_age": 40},
            benefits="Education support",
            official_url="https://education.gov.in",
            source="Education department",
        ),
    ]
    monkeypatch.setattr(main, "get_user_profile", lambda _user_id: {
        "age": 25,
        "annual_income": 50000,
        "state": "Tamil Nadu",
    })
    monkeypatch.setattr(eligibility_scan, "load_schemes", lambda: schemes)
    app.dependency_overrides[main.current_user_id] = lambda: "test-user"
    try:
        with TestClient(app) as client:
            response = client.get("/api/users/me/eligible-schemes")
    finally:
        app.dependency_overrides.pop(main.current_user_id, None)

    assert response.status_code == 200
    body = response.json()
    assert body["eligible_count"] == 1
    assert body["total_schemes"] == 3
    assert body["schemes"][0]["scheme"]["scheme_id"] == "eligible"
    assert body["schemes"][0]["eligibility"]["status"] == "LIKELY_ELIGIBLE"
    assert body["schemes"][0]["trust"]["score"] > 0


def test_finder_endpoint_keeps_unknown_schemes_unranked(monkeypatch) -> None:
    eligible_scheme = Scheme(
        scheme_id="eligible",
        name="Eligible",
        category="Education",
        description="Education support",
        eligibility={"min_age": 18},
        benefits="Tuition support",
        official_url="https://education.gov.in",
        source="Education department",
    )
    unknown_scheme = Scheme(
        scheme_id="unknown",
        name="Unknown",
        category="Education",
        description="Education support",
        eligibility={},
        benefits="Tuition support",
        official_url="https://education.gov.in",
        source="Education department",
    )
    monkeypatch.setattr(main, "get_user_profile", lambda _user_id: {"age": 25})
    monkeypatch.setattr(main, "find_schemes", lambda *_args: {
        "results": [{
            "scheme": eligible_scheme,
            "eligibility": EligibilityResult(
                scheme_id="eligible",
                status="LIKELY_ELIGIBLE",
                reasons=["All known eligibility criteria match your profile."],
            ),
            "semantic_score": 90,
            "category_score": 80,
            "benefit_score": 70,
            "weighted_score": 84.5,
            "explanation": "Eligibility rules match.",
            "evidence": [{"field": "benefits", "quote": "Tuition support"}],
        }],
        "unknown": [{
            "scheme": unknown_scheme,
            "eligibility": EligibilityResult(
                scheme_id="unknown",
                status="NEEDS_VERIFICATION",
                reasons=["Official eligibility rules need verification."],
            ),
        }],
        "excluded_count": 1,
        "total_candidates": 1,
        "query_text": "education",
        "weights": {"semantic": 0.6, "category": 0.25, "benefit": 0.15},
        "disclaimer": "Verify official information.",
    })
    app.dependency_overrides[main.current_user_id] = lambda: "test-user"
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/users/me/scheme-finder",
                json={"questionnaire": {"category": "Education", "objective": "tuition support"}},
            )
    finally:
        app.dependency_overrides.pop(main.current_user_id, None)

    assert response.status_code == 200
    body = response.json()
    assert [item["scheme"]["scheme_id"] for item in body["results"]] == ["eligible"]
    assert [item["scheme"]["scheme_id"] for item in body["unknown"]] == ["unknown"]
    assert body["results"][0]["evidence"][0]["quote"] == "Tuition support"
    assert "trust" in body["unknown"][0]


def test_trust_score_endpoint_returns_every_catalogue_record(monkeypatch) -> None:
    scheme = Scheme(
        scheme_id="catalogue-scheme",
        name="Catalogue scheme",
        category="Housing",
        description="Housing support",
        eligibility={"min_age": 18},
        benefits="Housing support",
        documents=["Identity proof"],
        application_process=["Apply online"],
        official_url="https://housing.gov.in",
        source="Housing department",
    )
    monkeypatch.setattr(main, "load_schemes", lambda: [scheme])

    with TestClient(app) as client:
        response = client.get("/api/trust-scores")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["schemes"][0]["scheme"]["scheme_id"] == "catalogue-scheme"
    assert body["schemes"][0]["trust"]["score"] == 53
