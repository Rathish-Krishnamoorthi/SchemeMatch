"""
Rule-based eligibility evaluator.

Supported eligibility dict keys:
  Numeric: min_age, max_age, min_income, max_income, min/max_land_acres,
           min/max_dependants
  List:    states, districts, occupations, education_levels,
           employment_statuses, professions, institution_types, categories,
           genders, marital_statuses, disability_types
  Boolean: student_status, farmer_status, disability_status
"""
from __future__ import annotations

import math

from app.models import EligibilityResult, Scheme, UserProfile


def evaluate_eligibility(profile: UserProfile, scheme: Scheme) -> EligibilityResult:
    rules = scheme.eligibility

    # No rules defined — cannot make any determination
    if not rules:
        note = scheme.verification_note or "Official eligibility rules need verification."
        return EligibilityResult(
            scheme_id=scheme.scheme_id,
            status="NEEDS_VERIFICATION",
            reasons=[note],
        )

    mismatches: list[str] = []
    missing: list[str] = []

    # ── Numeric range checks ──────────────────────────────────────────────────
    numeric_rules: list[tuple[str, float | int | None, str, str, bool]] = [
        ("min_age", profile.age, "age", "at least", True),
        ("max_age", profile.age, "age", "no more than", False),
        ("min_income", profile.annual_income, "annual income", "at least ₹", True),
        ("max_income", profile.annual_income, "annual income", "no more than ₹", False),
        ("min_land_acres", profile.land_holding_acres, "land holding", "at least", True),
        ("max_land_acres", profile.land_holding_acres, "land holding", "no more than", False),
        ("min_dependants", profile.dependants, "number of dependants", "at least", True),
        ("max_dependants", profile.dependants, "number of dependants", "no more than", False),
    ]
    for rule_key, value, label, comparison, is_minimum in numeric_rules:
        if rule_key not in rules:
            continue
        if value is None:
            missing.append(f"Your {label} is needed to check this requirement.")
            continue
        try:
            threshold = float(rules[rule_key])
        except (TypeError, ValueError) as error:
            raise ValueError(f"Eligibility rule {rule_key} must be a number.") from error
        if not math.isfinite(threshold):
            raise ValueError(f"Eligibility rule {rule_key} must be finite.")
        failed = value < threshold if is_minimum else value > threshold
        if failed:
            mismatches.append(f"The scheme requires {label} {comparison}{threshold}.")

    # ── List / allowlist checks ───────────────────────────────────────────────
    profile_fields: list[tuple[str, str | None, str]] = [
        ("states",              profile.state,              "state"),
        ("districts",           profile.district,           "district"),
        ("occupations",         profile.occupation,         "occupation"),
        ("professions",         profile.profession,         "profession"),
        ("education_levels",    profile.education_level,    "education level"),
        ("employment_statuses", profile.employment_status,  "employment status"),
        ("institution_types",   profile.institution_type,  "institution type"),
        ("categories",          profile.category,           "social category"),
        ("genders",             profile.gender,             "gender"),
        ("marital_statuses",    profile.marital_status,     "marital status"),
        ("disability_types",    profile.disability_type,    "disability type"),
    ]
    for rule_key, value, label in profile_fields:
        if rule_key not in rules:
            continue
        raw_allowed = rules[rule_key]
        if isinstance(raw_allowed, str):
            allowed = [raw_allowed]
        elif isinstance(raw_allowed, list) and all(isinstance(option, str) for option in raw_allowed):
            allowed = raw_allowed
        else:
            raise ValueError(f"Eligibility rule {rule_key} must be a string or list of strings.")
        if not allowed:
            raise ValueError(f"Eligibility rule {rule_key} cannot be empty.")
        if not value:
            missing.append(f"Your {label} is needed to check this requirement.")
        elif value.casefold() not in {str(opt).casefold() for opt in allowed}:
            mismatches.append(
                f"Your {label} ({value}) does not match the requirement: "
                f"{', '.join(str(o) for o in allowed)}."
            )

    # ── Boolean checks ────────────────────────────────────────────────────────
    boolean_fields: dict[str, bool | None] = {
        "student_status":    profile.student_status,
        "farmer_status":     profile.farmer_status,
        "disability_status": profile.disability_status,
    }
    for rule_key, value in boolean_fields.items():
        if rule_key not in rules:
            continue
        raw_expected = rules[rule_key]
        if isinstance(raw_expected, bool):
            expected = raw_expected
        elif isinstance(raw_expected, str) and raw_expected.casefold() in ("true", "false"):
            expected = raw_expected.casefold() == "true"
        else:
            raise ValueError(f"Eligibility rule {rule_key} must be a boolean.")
        label = rule_key.replace("_", " ")
        if value is None:
            missing.append(f"Your {label} is needed to check this requirement.")
        elif value != expected:                         # use == not `is` for safety
            qualifier = "be" if expected else "not be"
            mismatches.append(f"This scheme requires {label} to {qualifier} confirmed.")

    supported_rules = {
        rule_key for rule_key, *_ in numeric_rules
    } | {rule_key for rule_key, *_ in profile_fields} | set(boolean_fields)
    for rule_key in rules.keys() - supported_rules:
        missing.append(
            f"The eligibility condition '{rule_key}' cannot be checked with the current profile fields."
        )

    # ── Decision ──────────────────────────────────────────────────────────────
    if mismatches:
        return EligibilityResult(
            scheme_id=scheme.scheme_id,
            status="NOT_ELIGIBLE",
            reasons=mismatches,
        )
    if missing:
        return EligibilityResult(
            scheme_id=scheme.scheme_id,
            status="NEEDS_VERIFICATION",
            reasons=missing,
        )
    return EligibilityResult(
        scheme_id=scheme.scheme_id,
        status="LIKELY_ELIGIBLE",
        reasons=["All known eligibility criteria match your profile."],
    )
