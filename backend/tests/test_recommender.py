from app.models import Scheme, UserProfile
from app.services.recommender import recommend


def test_recommendations_return_every_rule_match_without_text_ranking() -> None:
    schemes = [
        Scheme(
            scheme_id="z-scheme",
            name="Zeta",
            category="Housing",
            description="Unrelated to the profile need.",
            eligibility={"min_age": 18},
            benefits="Housing support",
            official_url="https://example.gov.in",
            source="Test source",
        ),
        Scheme(
            scheme_id="a-scheme",
            name="Alpha",
            category="Education",
            description="This matches the profile's stated need.",
            eligibility={"min_age": 18},
            benefits="Education support",
            official_url="https://example.gov.in",
            source="Test source",
        ),
    ]

    results, excluded_count = recommend(UserProfile(age=20, need="education"), schemes, 1)

    assert [result.scheme.scheme_id for result in results] == ["a-scheme", "z-scheme"]
    assert all(result.match_score == 100 for result in results)
    assert excluded_count == 0


def test_ineligible_schemes_are_excluded() -> None:
    scheme = Scheme(
        scheme_id="income-limit",
        name="Income-based assistance",
        category="Financial support",
        description="Financial assistance",
        eligibility={"max_income": 1000},
        benefits="Support",
        official_url="https://example.gov.in",
        source="Test source",
    )

    results, excluded_count = recommend(
        UserProfile(annual_income=5000, need="financial assistance"),
        [scheme],
        5,
    )

    assert results == []
    assert excluded_count == 1
