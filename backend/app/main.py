from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.admin_routes import router as admin_router

from app.models import (
    AuthResponse,
    EligibilityCheckRequest,
    EligibilityResult,
    FinderRequest,
    LoginRequest,
    RecommendationRequest,
    RecommendationResponse,
    Scheme,
    SignupRequest,
    UserProfile,
)
from app.services.auth import (
    AuthError,
    authenticate_user,
    create_access_token,
    decode_access_token,
    get_user_profile,
    register_user,
    save_user_profile,
)
from app.services.eligibility import evaluate_eligibility
from app.services.recommender import recommend
from app.services.scheme_store import (
    SchemeStoreUnavailable,
    close_mongo_client,
    load_schemes,
)
from app.services.eligibility_scan import run_eligibility_scan
from app.services.llm_service import LLMServiceError
from app.services.semantic_finder import SemanticSearchUnavailable, find_schemes
from app.services.trust_score import calculate_trust_score


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    close_mongo_client()


app = FastAPI(title="SchemeMatch API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount admin API router
app.include_router(admin_router)

_ADMIN_UI = Path(__file__).resolve().parent / "admin_ui.html"


@app.get("/admin", include_in_schema=False)
def admin_ui() -> FileResponse:
    """Serve the standalone admin panel."""
    return FileResponse(_ADMIN_UI, media_type="text/html")

_bearer = HTTPBearer()


def current_user_id(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> str:
    """Extract and validate the JWT; return the user_id (sub claim)."""
    try:
        payload = decode_access_token(credentials.credentials)
    except AuthError as error:
        raise HTTPException(status_code=401, detail=str(error))
    return payload["sub"]


@app.exception_handler(SchemeStoreUnavailable)
async def scheme_store_error(_: Request, error: SchemeStoreUnavailable) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(error)})


DISCLAIMER = (
    "Eligibility is indicative and should be verified with the official government "
    "scheme authority before applying."
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/categories")
def categories() -> list[str]:
    return sorted({scheme.category for scheme in load_schemes()})


@app.get("/api/schemes", response_model=list[Scheme])
def schemes() -> list[Scheme]:
    return load_schemes()


@app.get("/api/schemes/{scheme_id}", response_model=Scheme)
def scheme_detail(scheme_id: str) -> Scheme:
    for scheme in load_schemes():
        if scheme.scheme_id == scheme_id:
            return scheme
    raise HTTPException(status_code=404, detail="Scheme not found")


@app.post("/api/eligibility/check", response_model=list[EligibilityResult])
def check_eligibility(request: EligibilityCheckRequest) -> list[EligibilityResult]:
    records = load_schemes()
    if request.scheme_ids is not None:
        requested = set(request.scheme_ids)
        records = [record for record in records if record.scheme_id in requested]
    return [evaluate_eligibility(request.profile, record) for record in records]


@app.post("/api/recommendations", response_model=RecommendationResponse)
def recommendations(request: RecommendationRequest) -> RecommendationResponse:
    ranked, excluded_count = recommend(request.profile, load_schemes(), request.limit)
    return RecommendationResponse(
        recommendations=ranked,
        excluded_count=excluded_count,
        disclaimer=DISCLAIMER,
    )


# ── Auth endpoints ────────────────────────────────────────────────────────────

@app.post("/api/auth/signup", response_model=AuthResponse, status_code=201)
def signup(request: SignupRequest) -> AuthResponse:
    try:
        user = register_user(request.name, request.email, request.password)
    except AuthError as error:
        raise HTTPException(status_code=409, detail=str(error))
    token = create_access_token(user["id"], user["email"], user["name"])
    return AuthResponse(token=token, user=user)


@app.post("/api/auth/login", response_model=AuthResponse)
def login(request: LoginRequest) -> AuthResponse:
    try:
        user = authenticate_user(request.email, request.password)
    except AuthError as error:
        raise HTTPException(status_code=401, detail=str(error))
    token = create_access_token(user["id"], user["email"], user["name"])
    # Include whether this user has completed their profile
    profile = get_user_profile(user["id"])
    return AuthResponse(token=token, user={**user, "has_profile": profile is not None})


# ── User profile endpoints (require JWT) ─────────────────────────────────────

@app.get("/api/users/me/profile")
def get_my_profile(user_id: str = Depends(current_user_id)) -> dict:
    profile = get_user_profile(user_id)
    return profile if profile is not None else {}


@app.put("/api/users/me/profile", status_code=200)
def save_my_profile(
    profile: dict,
    user_id: str = Depends(current_user_id),
) -> dict[str, str]:
    save_user_profile(user_id, profile)
    return {"status": "saved"}


# ── Module 1: Eligibility Scanner ─────────────────────────────────────────────

@app.get("/api/users/me/eligibility-scan")
def eligibility_scan(user_id: str = Depends(current_user_id)) -> dict:
    """
    Load the user's saved profile and check it against ALL schemes.
    Returns four groups: eligible, unknown, unverified, ineligible.
    """
    raw_profile = get_user_profile(user_id)
    if not raw_profile:
        raise HTTPException(status_code=400, detail="Profile not set. Complete your profile first.")
    result = run_eligibility_scan(raw_profile)

    def serialise(scan_results: list) -> list[dict]:
        out = []
        for sr in scan_results:
            out.append({
                "scheme": sr.scheme.model_dump(),
                "eligibility": sr.eligibility.model_dump(),
                "group": sr.group,
                "trust": calculate_trust_score(sr.scheme),
            })
        return out

    return {
        "eligible": serialise(result["eligible"]),
        "unknown": serialise(result["unknown"]),
        "unverified": serialise(result["unverified"]),
        "ineligible": serialise(result["ineligible"]),
        "totals": result["totals"],
        "profile_summary": result["profile_summary"],
    }


@app.get("/api/users/me/eligible-schemes")
def eligible_schemes(user_id: str = Depends(current_user_id)) -> dict:
    """Return every scheme whose recorded mandatory rules match the saved profile."""
    raw_profile = get_user_profile(user_id)
    if not raw_profile:
        raise HTTPException(status_code=400, detail="Profile not set. Complete your profile first.")
    result = run_eligibility_scan(raw_profile)
    schemes = [
        {
            "scheme": scan.scheme.model_dump(),
            "eligibility": scan.eligibility.model_dump(),
            "trust": calculate_trust_score(scan.scheme),
        }
        for scan in result["eligible"]
    ]
    return {
        "schemes": schemes,
        "eligible_count": len(schemes),
        "total_schemes": result["totals"]["total"],
        "profile_summary": result["profile_summary"],
        "disclaimer": DISCLAIMER,
    }


@app.get("/api/trust-scores")
def trust_scores() -> dict:
    """Show provenance and catalogue-completeness evidence for every scheme."""
    scored = [
        {"scheme": scheme.model_dump(), "trust": calculate_trust_score(scheme)}
        for scheme in load_schemes()
    ]
    scored.sort(key=lambda item: (-item["trust"]["score"], item["scheme"]["name"].casefold()))
    return {
        "schemes": scored,
        "total": len(scored),
        "disclaimer": (
            "Trust scores describe source provenance and catalogue completeness only. "
            "They do not certify scheme accuracy, eligibility, or approval."
        ),
    }


# ── Module 2: Semantic Scheme Finder ─────────────────────────────────────────

@app.post("/api/users/me/scheme-finder")
def scheme_finder(
    request: FinderRequest,
    user_id: str = Depends(current_user_id),
) -> dict:
    """
    Combine questionnaire answers with the user's saved profile,
    apply eligibility rules, then rank remaining schemes by semantic similarity.
    """
    raw_profile = get_user_profile(user_id)
    if not raw_profile:
        raise HTTPException(status_code=400, detail="Profile not set. Complete your profile first.")

    try:
        result = find_schemes(raw_profile, request.questionnaire.model_dump(), request.weights)
    except SemanticSearchUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except LLMServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error

    serialised = []
    for item in result["results"]:
        serialised.append({
            "scheme": item["scheme"].model_dump(),
            "eligibility": item["eligibility"].model_dump(),
            "semantic_score": item["semantic_score"],
            "category_score": item["category_score"],
            "benefit_score": item["benefit_score"],
            "weighted_score": item["weighted_score"],
            "explanation": item["explanation"],
            "evidence": item["evidence"],
            "trust": calculate_trust_score(item["scheme"]),
        })
    unknown = [
        {
            "scheme": item["scheme"].model_dump(),
            "eligibility": item["eligibility"].model_dump(),
            "group": "unknown",
            "trust": calculate_trust_score(item["scheme"]),
        }
        for item in result["unknown"]
    ]

    return {
        "results": serialised,
        "unknown": unknown,
        "excluded_count": result["excluded_count"],
        "total_candidates": result["total_candidates"],
        "query_text": result.get("query_text", ""),
        "weights": result["weights"],
        "disclaimer": result["disclaimer"],
    }
