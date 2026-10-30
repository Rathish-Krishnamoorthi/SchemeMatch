from datetime import datetime, timezone

from app.models import Scheme
from app.services.trust_score import calculate_trust_score


def test_complete_recent_official_scheme_has_maximum_trust_evidence_score() -> None:
    now = datetime(2026, 10, 30, tzinfo=timezone.utc)
    scheme = Scheme(
        scheme_id="verified-scheme",
        name="Verified scheme",
        category="Education",
        description="A detailed scheme description.",
        eligibility={"min_age": 18},
        benefits="Tuition support.",
        documents=["Identity proof"],
        application_process=["Apply online"],
        official_url="https://education.gov.in/scheme",
        source="Education department",
        last_verified="2026-10-30",
    )

    result = calculate_trust_score(scheme, now)

    assert result["score"] == 100
    assert result["level"] == "high"
    assert sum(item["points"] for item in result["evidence"]) == 100


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
