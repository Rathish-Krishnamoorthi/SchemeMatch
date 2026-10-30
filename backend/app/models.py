import math
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


EligibilityStatus = Literal[
    "LIKELY_ELIGIBLE", "NEEDS_VERIFICATION", "NOT_ELIGIBLE"
]


class UserProfile(BaseModel):
    age: int | None = Field(default=None, ge=0, le=120)
    state: str | None = None
    district: str | None = None
    annual_income: float | None = Field(default=None, ge=0)
    occupation: str | None = None
    profession: str | None = None          # sub-type when employed/self-employed
    education_level: str | None = None
    employment_status: str | None = None
    farmer_status: bool | None = None
    land_holding_acres: float | None = Field(default=None, ge=0)  # for farmers
    student_status: bool | None = None
    institution_type: str | None = None    # for students
    category: str | None = None
    disability_status: bool | None = None
    disability_type: str | None = None     # sub-type when disability = True
    gender: str | None = None
    marital_status: str | None = None
    dependants: int | None = Field(default=None, ge=0)  # family size for income schemes
    need: str = Field(default="", max_length=1000)


class Scheme(BaseModel):
    scheme_id: str
    name: str
    category: str
    description: str
    eligibility: dict = Field(default_factory=dict)
    benefits: str
    documents: list[str] = Field(default_factory=list)
    application_process: list[str] = Field(default_factory=list)
    official_url: str
    source: str
    last_verified: str | None = None
    verification_note: str | None = None


class EligibilityResult(BaseModel):
    scheme_id: str
    status: EligibilityStatus
    reasons: list[str]


class EligibilityCheckRequest(BaseModel):
    profile: UserProfile
    scheme_ids: list[str] | None = None


class RecommendationRequest(BaseModel):
    profile: UserProfile
    limit: int = Field(default=5, ge=1, le=20)


class Recommendation(BaseModel):
    scheme: Scheme
    eligibility: EligibilityResult
    match_score: int = Field(ge=0, le=100)
    explanation: str


class RecommendationResponse(BaseModel):
    recommendations: list[Recommendation]
    excluded_count: int
    disclaimer: str


# ── Auth models ──────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuthResponse(BaseModel):
    token: str
    user: dict


# ── New module models ─────────────────────────────────────────────────────────

class FinderQuestionnaire(BaseModel):
    category: str = Field(default="All", max_length=80)
    objective: str = Field(min_length=1, max_length=500)
    benefit_needs: str = Field(default="", max_length=500)
    location_preference: str = Field(default="", max_length=120)
    additional: dict[str, str] = Field(default_factory=dict)

    @field_validator("objective")
    @classmethod
    def objective_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Provide an objective to search for schemes.")
        return value.strip()

    @field_validator("additional")
    @classmethod
    def limit_additional_answers(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > 25 or any(len(key) > 80 or len(answer) > 300 for key, answer in value.items()):
            raise ValueError("Questionnaire contains an answer that exceeds the allowed size.")
        return value


class FinderRequest(BaseModel):
    """Request body for the Required Scheme Finder (Module 2)."""
    questionnaire: FinderQuestionnaire
    weights: dict[str, float] | None = None

    @field_validator("weights")
    @classmethod
    def validate_weights(cls, weights: dict[str, float] | None) -> dict[str, float] | None:
        if weights is None:
            return None
        expected = {"semantic", "category", "benefit"}
        if set(weights) != expected:
            raise ValueError("weights must contain semantic, category, and benefit values.")
        if any(not math.isfinite(value) or value < 0 or value > 1 for value in weights.values()):
            raise ValueError("weight values must be finite numbers between 0 and 1.")
        if not math.isclose(sum(weights.values()), 1.0, abs_tol=0.001):
            raise ValueError("weight values must sum to 1.")
        return weights
