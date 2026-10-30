"""Evidence-based catalogue trust indicators, not eligibility or approval scores."""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

from app.models import Scheme


def calculate_trust_score(
    scheme: Scheme,
    now: datetime | None = None,
) -> dict:
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    evidence: list[dict[str, int | str]] = []
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

    verified_points = 0
    verified_detail = "No verification date is recorded."
    if scheme.last_verified:
        try:
            verified_at = datetime.fromisoformat(scheme.last_verified.replace("Z", "+00:00"))
            if verified_at.tzinfo is None:
                verified_at = verified_at.replace(tzinfo=timezone.utc)
            age_days = (current_time - verified_at).days
            if 0 <= age_days <= 365:
                verified_points = 20
                verified_detail = "Verified within the past year."
            elif 0 <= age_days <= 730:
                verified_points = 15
                verified_detail = "Verified within the past two years."
            elif 0 <= age_days <= 1095:
                verified_points = 8
                verified_detail = "Verification is more than two years old."
            elif age_days > 1095:
                verified_points = 2
                verified_detail = "Verification is more than three years old."
            else:
                verified_detail = "Verification date is in the future."
        except ValueError:
            verified_detail = "Verification date could not be parsed."
    score += verified_points
    evidence.append({"factor": "Recent verification", "points": verified_points, "detail": verified_detail})

    content_checks = (
        ("Scheme description", bool(scheme.description.strip()), 5),
        ("Benefits", bool(scheme.benefits.strip()), 5),
        ("Eligibility rules", bool(scheme.eligibility), 10),
        ("Required documents", bool(scheme.documents), 5),
        ("Application instructions", bool(scheme.application_process), 5),
    )
    for label, present, points in content_checks:
        awarded = points if present else 0
        score += awarded
        evidence.append({
            "factor": label,
            "points": awarded,
            "detail": "Present in the catalogue." if present else "Not recorded in the catalogue.",
        })

    return {
        "score": score,
        "level": "high" if score >= 75 else "moderate" if score >= 50 else "low",
        "evidence": evidence,
        "disclaimer": "This score reflects recorded source provenance and catalogue completeness; it does not verify accuracy, eligibility, or approval.",
    }
