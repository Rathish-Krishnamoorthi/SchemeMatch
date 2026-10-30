"""
Admin API router — mounted at /admin-api in main.py.
All routes except /admin-api/login require a valid admin JWT.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.models import Scheme
from app.services.llm_service import (
    LLMProviderSettings,
    LLMServiceError,
    get_safe_settings,
    save_provider_settings,
    test_provider_connection,
)
from app.services.admin import (
    AdminAuthError,
    add_scheme,
    count_schemes,
    count_users,
    create_admin_token,
    delete_scheme,
    list_schemes_admin,
    list_users,
    update_scheme,
    verify_admin_credentials,
    verify_admin_token,
)
from app.services.scheme_store import SchemeStoreUnavailable

router = APIRouter(prefix="/admin-api", tags=["admin"])
_bearer = HTTPBearer()


# ── Auth dependency ───────────────────────────────────────────────────────────

def require_admin(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> None:
    try:
        verify_admin_token(credentials.credentials)
    except AdminAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


# ── Request / response models ─────────────────────────────────────────────────

class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    token: str


class UsersResponse(BaseModel):
    users: list[dict]
    total: int
    skip: int
    limit: int


class SchemesResponse(BaseModel):
    schemes: list[dict]
    total: int
    skip: int
    limit: int


class SchemeCreateRequest(BaseModel):
    scheme_id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1)
    eligibility: dict = Field(default_factory=dict)
    benefits: str = Field(min_length=1)
    documents: list[str] = Field(default_factory=list)
    application_process: list[str] = Field(default_factory=list)
    official_url: str = Field(min_length=5)
    source: str = Field(min_length=1)
    last_verified: str | None = None
    verification_note: str | None = None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=AdminLoginResponse)
def admin_login(body: AdminLoginRequest) -> AdminLoginResponse:
    try:
        verify_admin_credentials(body.username, body.password)
    except AdminAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    return AdminLoginResponse(token=create_admin_token())


@router.get("/stats", dependencies=[Depends(require_admin)])
def stats() -> dict:
    return {
        "users": count_users(),
        "schemes": count_schemes(),
    }


@router.get("/settings/llm", dependencies=[Depends(require_admin)])
def get_llm_settings() -> dict:
    try:
        return get_safe_settings()
    except LLMServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SchemeStoreUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.put("/settings/llm", dependencies=[Depends(require_admin)])
def update_llm_settings(body: LLMProviderSettings) -> dict:
    try:
        return save_provider_settings(body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SchemeStoreUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/settings/llm/test", dependencies=[Depends(require_admin)])
def test_llm_settings() -> dict:
    try:
        return test_provider_connection()
    except LLMServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except SchemeStoreUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/users", response_model=UsersResponse, dependencies=[Depends(require_admin)])
def get_users(skip: int = 0, limit: int = 50) -> UsersResponse:
    users = list_users(skip=skip, limit=limit)
    return UsersResponse(users=users, total=count_users(), skip=skip, limit=limit)


@router.get("/schemes", response_model=SchemesResponse, dependencies=[Depends(require_admin)])
def get_schemes(skip: int = 0, limit: int = 100) -> SchemesResponse:
    schemes = list_schemes_admin(skip=skip, limit=limit)
    return SchemesResponse(schemes=schemes, total=count_schemes(), skip=skip, limit=limit)


@router.post("/schemes", status_code=201, dependencies=[Depends(require_admin)])
def create_scheme(body: SchemeCreateRequest) -> dict:
    try:
        scheme_id = add_scheme(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"status": "created", "scheme_id": scheme_id}


@router.put("/schemes/{scheme_id}", dependencies=[Depends(require_admin)])
def edit_scheme(scheme_id: str, body: SchemeCreateRequest) -> dict:
    updated = update_scheme(scheme_id, body.model_dump())
    if not updated:
        raise HTTPException(status_code=404, detail="Scheme not found.")
    return {"status": "updated", "scheme_id": scheme_id}


@router.delete("/schemes/{scheme_id}", dependencies=[Depends(require_admin)])
def remove_scheme(scheme_id: str) -> dict:
    deleted = delete_scheme(scheme_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Scheme not found.")
    return {"status": "deleted", "scheme_id": scheme_id}
