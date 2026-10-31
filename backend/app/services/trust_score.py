"""Evidence-based catalogue trust indicators, not eligibility or approval scores."""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

from app.models import Scheme


def _rule_count(value: object) -> int:
    if isinstance(value, dict):
        return sum(_rule_count(item) for item in value.values())
    if isinstance(value, list):
        return sum(_rule_count(item) for item in value)
    return int(value is not None)


def _depth_points(actual: int, maximum: int, cap: int) -> float:
    return round(cap * min(actual / maximum, 1), 1)


def calculate_trust_score(
    scheme: Scheme,
    now: datetime | None = None,
) -> dict:
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    evidence: list[dict[str, int | float | str]] = []
    score = 0

    parsed_url = urlparse(scheme.official_url)
    hostname = (parsed_url.hostname or "").casefold().rstrip(".")
    is_government_domain = hostname.endswith((".gov.in", ".nic.in"))

    if is_government_domain:
        score += 25
        evidence.append({"factor": "Government domain", "points": 25, "detail": hostname})
    else:
        evidence.append({"factor": "Government domain", "points": 0, "detail": "Domain is not a recognised .gov.in or .nic.in host."})

    if parsed_url.scheme.casefold() == "https":
        score += 10
        evidence.append({"factor": "Secure source URL", "points": 10, "detail": "HTTPS"})
    else:
        evidence.append({"factor": "Secure source URL", "points": 0, "detail": "HTTPS is not recorded."})

    if scheme.source.strip():
        score += 15
        evidence.append({"factor": "Source attribution", "points": 15, "detail": scheme.source.strip()})
    else:
        evidence.append({"factor": "Source attribution", "points": 0, "detail": "Source attribution is missing."})

    verified_points = 0.0
    verified_detail = "No verification date is recorded."
    if scheme.last_verified:
        try:
            verified_at = datetime.fromisoformat(scheme.last_verified.replace("Z", "+00:00"))
            if verified_at.tzinfo is None:
                verified_at = verified_at.replace(tzinfo=timezone.utc)
            age_days = (current_time - verified_at).total_seconds() / 86400
            if age_days >= 0:
                verified_points = round(20 * max(0, 1 - age_days / 1825), 1)
                verified_detail = (
                    f"Verified {int(age_days)} days ago; recency credit declines "
                    "gradually to zero over five years."
                )
            else:
                verified_detail = "Verification date is in the future."
        except ValueError:
            verified_detail = "Verification date could not be parsed."
    score += verified_points
    evidence.append({"factor": "Recent verification", "points": verified_points, "detail": verified_detail})

    content_checks = (
        (
            "Scheme description",
            len(scheme.description.split()),
            100,
            5,
            "words",
        ),
        (
            "Benefits",
            len(scheme.benefits.split()),
            60,
            5,
            "words",
        ),
        (
            "Eligibility rules",
            _rule_count(scheme.eligibility),
            8,
            10,
            "recorded criteria",
        ),
        ("Required documents", len(scheme.documents), 8, 5, "items"),
        ("Application instructions", len(scheme.application_process), 6, 5, "steps"),
    )
    for label, actual, full_credit_at, cap, unit in content_checks:
        awarded = _depth_points(actual, full_credit_at, cap)
        score += awarded
        evidence.append({
            "factor": label,
            "points": awarded,
            "detail": (
                f"{actual} {unit} recorded; full credit at {full_credit_at}."
                if actual
                else f"No {unit} recorded."
            ),
        })

    displayed_score = round(score)
    return {
        "score": displayed_score,
        "level": "high" if displayed_score >= 75 else "moderate" if displayed_score >= 50 else "low",
        "evidence": evidence,
        "disclaimer": "This score reflects recorded source provenance and catalogue completeness; it does not verify accuracy, eligibility, or approval.",
    }
