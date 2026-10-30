"""
Module 1: Profile Eligibility Scanner
--------------------------------------
Loads the user's stored profile, converts raw form strings to typed values,
then runs every scheme in the database through the rule engine.

Returns three groups:
  - eligible:   LIKELY_ELIGIBLE
  - unknown:    NEEDS_VERIFICATION (eligibility dict present but data missing)
  - unverified: NEEDS_VERIFICATION (empty eligibility dict — no rules defined yet)
  - ineligible: NOT_ELIGIBLE (explicitly ruled out)
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models import EligibilityResult, Scheme, UserProfile
from app.services.eligibility import evaluate_eligibility
from app.services.scheme_store import load_schemes


def _coerce_profile(raw: dict) -> UserProfile:
    """Convert the raw form-string profile dict stored in MongoDB into a typed UserProfile."""

    def to_int(v: object) -> int | None:
        try:
            number = float(str(v)) if v not in (None, "") else None
            return int(number) if number is not None and number.is_integer() else None
        except (ValueError, TypeError):
            return None

    def to_float(v: object) -> float | None:
        try:
            return float(str(v)) if v not in (None, "") else None
        except (ValueError, TypeError):
            return None

    def to_bool(v: object) -> bool | None:
        if v in (None, ""):
            return None
        if isinstance(v, bool):
            return v
        normalized = str(v).strip().casefold()
        if normalized in ("yes", "true", "1"):
            return True
        if normalized in ("no", "false", "0"):
            return False
        return None

    def to_str(v: object) -> str | None:
        s = str(v).strip() if v not in (None, "") else None
        return s if s else None

    return UserProfile(
        age=to_int(raw.get("age")),
        state=to_str(raw.get("state")),
        district=to_str(raw.get("district")),
        annual_income=to_float(raw.get("annual_income")),
        occupation=to_str(raw.get("occupation")),
        profession=to_str(raw.get("profession")),
        education_level=to_str(raw.get("education_level")),
        employment_status=to_str(raw.get("employment_status")),
        farmer_status=to_bool(raw.get("farmer_status"))
            if raw.get("farmer_status") not in (None, "")
            else (True if (to_str(raw.get("occupation")) or "").casefold() == "farmer" else None),
        land_holding_acres=to_float(raw.get("land_holding_acres")),
        student_status=to_bool(raw.get("student_status"))
            if raw.get("student_status") not in (None, "")
            else (True if (to_str(raw.get("occupation")) or "").casefold() == "student" else None),
        institution_type=to_str(raw.get("institution_type")),
        category=to_str(raw.get("category")),
        disability_status=to_bool(raw.get("disability_status")),
        disability_type=to_str(raw.get("disability_type")),
        gender=to_str(raw.get("gender")),
        marital_status=to_str(raw.get("marital_status")),
        dependants=to_int(raw.get("dependants")),
        need=str(raw.get("need", "")),
    )


@dataclass
class ScanResult:
    scheme: Scheme
    eligibility: EligibilityResult
    group: str  # "eligible" | "unknown" | "unverified" | "ineligible"


def run_eligibility_scan(raw_profile: dict) -> dict:
    """
    Run every scheme through the rule engine.
    Returns a dict with four groups of ScanResult, plus profile snapshot.
    """
    profile = _coerce_profile(raw_profile)
    schemes = load_schemes()

    eligible: list[ScanResult] = []
    unknown: list[ScanResult] = []
    unverified: list[ScanResult] = []
    ineligible: list[ScanResult] = []

    for scheme in schemes:
        result = evaluate_eligibility(profile, scheme)

        if result.status == "NOT_ELIGIBLE":
            ineligible.append(ScanResult(scheme=scheme, eligibility=result, group="ineligible"))
        elif result.status == "LIKELY_ELIGIBLE":
            eligible.append(ScanResult(scheme=scheme, eligibility=result, group="eligible"))
        else:
            # NEEDS_VERIFICATION — distinguish between "no rules" vs "rules but data missing"
            if scheme.eligibility:
                unknown.append(ScanResult(scheme=scheme, eligibility=result, group="unknown"))
            else:
                unverified.append(ScanResult(scheme=scheme, eligibility=result, group="unverified"))

    # Sort each group alphabetically within category
    def sort_key(r: ScanResult) -> tuple[str, str]:
        return (r.scheme.category, r.scheme.name.casefold())

    return {
        "eligible": sorted(eligible, key=sort_key),
        "unknown": sorted(unknown, key=sort_key),
        "unverified": sorted(unverified, key=sort_key),
        "ineligible": sorted(ineligible, key=sort_key),
        "totals": {
            "eligible": len(eligible),
            "unknown": len(unknown),
            "unverified": len(unverified),
            "ineligible": len(ineligible),
            "total": len(schemes),
        },
        "profile_summary": {
            "age": profile.age,
            "state": profile.state,
            "occupation": profile.occupation,
            "category": profile.category,
            "gender": profile.gender,
            "education_level": profile.education_level,
            "annual_income": profile.annual_income,
            "farmer_status": profile.farmer_status,
            "student_status": profile.student_status,
            "disability_status": profile.disability_status,
        },
    }
