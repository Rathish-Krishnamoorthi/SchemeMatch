"""Rule-based recommendations and shared profile-context text for the finder."""
from __future__ import annotations

from app.models import Recommendation, Scheme, UserProfile
from app.services.eligibility import evaluate_eligibility

OCCUPATION_EXPANSION: dict[str, set[str]] = {
    "farmer": {"agriculture", "crop", "kisan", "farm", "agri", "horticulture", "fisheries", "irrigation", "soil", "livestock", "dairy"},
    "student": {"scholarship", "college", "university", "study", "tuition", "fellowship", "education", "hostel", "coaching"},
    "salaried": {"employment", "worker", "salary", "sector", "service"},
    "self-employed": {"enterprise", "business", "loan", "credit", "mudra", "msme"},
    "artisan / craftsperson": {"craft", "artisan", "khadi", "vishwakarma", "skill", "handloom"},
    "homemaker": {"women", "self-help", "shg", "livelihood"},
    "unemployed": {"employment", "job", "training", "skill", "apprentice"},
}

CATEGORY_EXPANSION: dict[str, set[str]] = {
    "sc": {"scheduled caste", "dalit", "ambedkar", "sc", "backward"},
    "st": {"scheduled tribe", "tribal", "adivasi", "forest", "eklavya"},
    "obc": {"obc", "other backward", "backward class"},
    "ews": {"ews", "economically weaker", "bpl", "poor"},
    "general": {"general", "open category"},
}

DISABILITY_EXPANSION = {"disability", "disabled", "divyang", "pwd", "saksham", "handicap"}


def _profile_context(profile: UserProfile) -> str:
    parts: list[str] = []
    if profile.occupation:
        occupation = profile.occupation.casefold()
        parts.append(profile.occupation)
        for key, terms in OCCUPATION_EXPANSION.items():
            if key in occupation:
                parts.extend(terms)
                break
    if profile.farmer_status is True:
        parts.extend(OCCUPATION_EXPANSION["farmer"])
    if profile.student_status is True:
        parts.extend(OCCUPATION_EXPANSION["student"])
    if profile.category:
        category = profile.category.casefold()
        parts.append(profile.category)
        for key, terms in CATEGORY_EXPANSION.items():
            if key in category:
                parts.extend(terms)
                break
    for field in (
        profile.education_level,
        profile.employment_status,
        profile.state,
        profile.gender,
    ):
        if field:
            parts.append(field)
    if profile.disability_status is True:
        parts.extend(DISABILITY_EXPANSION)
    if profile.age is not None:
        if profile.age < 18:
            parts.append("child minor school")
        elif profile.age < 25:
            parts.append("youth young student")
        elif profile.age >= 60:
            parts.append("senior elderly pension")
    if profile.annual_income is not None:
        if profile.annual_income < 100000:
            parts.append("bpl poor low income subsidy")
        elif profile.annual_income < 300000:
            parts.append("low income ews")
        elif profile.annual_income < 800000:
            parts.append("middle income")
    if profile.need:
        parts.append(profile.need)
    return " ".join(parts)


def recommend(
    profile: UserProfile,
    schemes: list[Scheme],
    limit: int,
) -> tuple[list[Recommendation], int]:
    """Return all schemes whose recorded rules match; ``limit`` is legacy-only."""
    eligible: list[Recommendation] = []
    excluded_count = 0
    for scheme in schemes:
        result = evaluate_eligibility(profile, scheme)
        if result.status == "NOT_ELIGIBLE":
            excluded_count += 1
            continue
        if result.status != "LIKELY_ELIGIBLE":
            continue
        eligible.append(Recommendation(
            scheme=scheme,
            eligibility=result,
            match_score=100,
            explanation="All recorded mandatory eligibility rules match your profile.",
        ))
    eligible.sort(key=lambda result: (result.scheme.category.casefold(), result.scheme.name.casefold()))
    return eligible, excluded_count
