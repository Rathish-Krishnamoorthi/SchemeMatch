from app.models import Scheme, UserProfile
from app.services.eligibility import evaluate_eligibility


def make_scheme(eligibility: dict) -> Scheme:
    return Scheme(
        scheme_id="test",
        name="Test scheme",
        category="Education",
        description="A test scheme",
        eligibility=eligibility,
        benefits="Support",
        official_url="https://example.gov.in",
        source="Test source",
    )


def test_all_known_conditions_match() -> None:
    profile = UserProfile(
        age=20,
        annual_income=100000,
        state="Tamil Nadu",
        occupation="Student",
        student_status=True,
    )
    scheme = make_scheme(
        {
            "min_age": 18,
            "max_age": 25,
            "max_income": 200000,
            "states": ["Tamil Nadu"],
            "occupations": ["Student"],
            "student_status": True,
        }
    )

    result = evaluate_eligibility(profile, scheme)

    assert result.status == "LIKELY_ELIGIBLE"


def test_clear_income_mismatch_is_not_eligible() -> None:
    result = evaluate_eligibility(
        UserProfile(age=20, annual_income=300000),
        make_scheme({"max_income": 200000}),
    )

    assert result.status == "NOT_ELIGIBLE"
    assert "annual income" in result.reasons[0]


def test_missing_required_information_needs_verification() -> None:
    result = evaluate_eligibility(
        UserProfile(age=20),
        make_scheme({"states": ["Tamil Nadu"]}),
    )

    assert result.status == "NEEDS_VERIFICATION"


def test_rule_boundaries_are_inclusive() -> None:
    result = evaluate_eligibility(
        UserProfile(age=18, annual_income=200000),
        make_scheme({"min_age": 18, "max_income": 200000}),
    )

    assert result.status == "LIKELY_ELIGIBLE"


def test_empty_catalogue_rules_need_verification() -> None:
    result = evaluate_eligibility(UserProfile(), make_scheme({}))

    assert result.status == "NEEDS_VERIFICATION"


def test_state_mismatch_is_not_eligible() -> None:
    result = evaluate_eligibility(
        UserProfile(state="Kerala"),
        make_scheme({"states": ["Tamil Nadu"]}),
    )

    assert result.status == "NOT_ELIGIBLE"


def test_additional_profile_conditions_are_enforced() -> None:
    profile = UserProfile(
        land_holding_acres=1.5,
        dependants=2,
        profession="Tailor",
        institution_type="Private",
        disability_type="Visual",
    )
    scheme = make_scheme({
        "min_land_acres": 2,
        "min_dependants": 3,
        "professions": ["Artisan"],
        "institution_types": ["Government"],
        "disability_types": ["Hearing"],
    })

    result = evaluate_eligibility(profile, scheme)

    assert result.status == "NOT_ELIGIBLE"
    assert len(result.reasons) == 5


def test_missing_additional_profile_condition_is_unknown() -> None:
    result = evaluate_eligibility(
        UserProfile(),
        make_scheme({"institution_types": ["Government"]}),
    )

    assert result.status == "NEEDS_VERIFICATION"
    assert "institution type" in result.reasons[0]


def test_unsupported_eligibility_conditions_are_not_treated_as_matches() -> None:
    result = evaluate_eligibility(
        UserProfile(age=20),
        make_scheme({"household_type": "single parent"}),
    )

    assert result.status == "NEEDS_VERIFICATION"
    assert "household_type" in result.reasons[0]
