from datetime import datetime, timezone

from app.models import Scheme
from app.services.trust_score import calculate_trust_score


def test_complete_recent_official_scheme_has_maximum_trust_evidence_score() -> None:
    now = datetime(2026, 10, 30, tzinfo=timezone.utc)
    scheme = Scheme(
        scheme_id="verified-scheme",
        name="Verified scheme",
        category="Education",
        description=" ".join(["description"] * 100),
        eligibility={f"criterion_{index}": True for index in range(8)},
        benefits=" ".join(["benefit"] * 60),
        documents=[f"Document {index}" for index in range(8)],
        application_process=[f"Step {index}" for index in range(6)],
        official_url="https://education.gov.in/scheme",
        source="Education department",
        last_verified="2026-10-30",
    )

    result = calculate_trust_score(scheme, now)

    assert result["score"] == 100
    assert result["level"] == "high"
    assert sum(item["points"] for item in result["evidence"]) == 100


def test_score_reflects_recorded_content_depth_and_verification_recency() -> None:
    now = datetime(2026, 10, 30, tzinfo=timezone.utc)
    concise = Scheme(
        scheme_id="concise",
        name="Concise scheme",
        category="Education",
        description="Education support",
        eligibility={"min_age": 18},
        benefits="Tuition support",
        documents=["Identity proof"],
        application_process=["Apply online"],
        official_url="https://education.gov.in/scheme",
        source="Education department",
        last_verified="2026-10-30",
    )
    detailed = concise.model_copy(update={
        "description": " ".join(["description"] * 100),
        "eligibility": {f"criterion_{index}": True for index in range(8)},
        "benefits": " ".join(["benefit"] * 60),
        "documents": [f"Document {index}" for index in range(8)],
        "application_process": [f"Step {index}" for index in range(6)],
    })

    concise_score = calculate_trust_score(concise, now)["score"]
    detailed_score = calculate_trust_score(detailed, now)["score"]
    older_score = calculate_trust_score(
        detailed.model_copy(update={"last_verified": "2025-10-30"}),
        now,
    )["score"]

    assert detailed_score > concise_score
    assert detailed_score - concise_score < 50
    assert 0 < detailed_score - older_score < 20


def test_catalogue_samples_produce_fine_grained_scores() -> None:
    now = datetime(2026, 10, 30, tzinfo=timezone.utc)
    schemes = [
        Scheme(
            scheme_id="short",
            name="Short record",
            category="Education",
            description="Education help",
            eligibility={},
            benefits="Tuition support",
            documents=["Identity proof"],
            application_process=["Apply online"],
            official_url="https://education.gov.in/scheme",
            source="Education department",
        ),
        Scheme(
            scheme_id="medium",
            name="Medium record",
            category="Education",
            description=" ".join(["education"] * 35),
            eligibility={"min_age": 18, "state": "Karnataka"},
            benefits=" ".join(["tuition"] * 20),
            documents=["Identity proof", "Income certificate", "Bank details"],
            application_process=["Register online", "Submit documents"],
            official_url="https://education.gov.in/scheme",
            source="Education department",
        ),
        Scheme(
            scheme_id="detailed",
            name="Detailed record",
            category="Education",
            description=" ".join(["education"] * 72),
            eligibility={f"criterion_{index}": True for index in range(6)},
            benefits=" ".join(["tuition"] * 43),
            documents=["Identity proof", "Income certificate", "Bank details", "Marksheets", "Photo"],
            application_process=["Register online", "Submit documents", "Track status", "Complete verification"],
            official_url="https://education.gov.in/scheme",
            source="Education department",
        ),
    ]

    scores = [calculate_trust_score(scheme, now)["score"] for scheme in schemes]

    assert len(set(scores)) == len(schemes)
    assert max(scores) - min(scores) >= 10
    assert any(score % 10 != 0 for score in scores)


def test_missing_or_untrusted_evidence_reduces_score() -> None:
    scheme = Scheme(
        scheme_id="incomplete",
        name="Incomplete scheme",
        category="Education",
        description="Some description",
        benefits="Support",
        official_url="http://example.com/scheme",
        source="",
    )

    result = calculate_trust_score(scheme, datetime(2026, 10, 30, tzinfo=timezone.utc))

    assert result["score"] < 50
    assert result["level"] == "low"
    assert any("not a recognised" in str(item["detail"]) for item in result["evidence"])
