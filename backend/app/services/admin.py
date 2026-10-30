"""
Admin service — credentials from .env only (not from the users collection).
Admin JWT is signed with a separate secret so user tokens can never grant admin access.
"""
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
from dotenv import load_dotenv
from jose import JWTError, jwt
from pymongo.errors import PyMongoError
from bson import ObjectId

from app.services.scheme_store import _get_mongo_client, SchemeStoreUnavailable

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

_ADMIN_SECRET = os.getenv("ADMIN_JWT_SECRET", "admin-secret-change-before-deploy")
_ALGORITHM = "HS256"
_EXPIRE_MINUTES = 120


class AdminAuthError(ValueError):
    pass


# ── Token ────────────────────────────────────────────────────────────────────

def create_admin_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=_EXPIRE_MINUTES)
    return jwt.encode({"sub": "admin", "exp": expire}, _ADMIN_SECRET, algorithm=_ALGORITHM)


def verify_admin_token(token: str) -> None:
    try:
        payload = jwt.decode(token, _ADMIN_SECRET, algorithms=[_ALGORITHM])
        if payload.get("sub") != "admin":
            raise AdminAuthError("Not an admin token.")
    except JWTError as exc:
        raise AdminAuthError("Invalid or expired admin token.") from exc


def verify_admin_credentials(username: str, password: str) -> None:
    expected_user = os.getenv("ADMIN_USERNAME", "admin")
    expected_pass = os.getenv("ADMIN_PASSWORD", "")
    if username != expected_user or password != expected_pass:
        raise AdminAuthError("Incorrect admin credentials.")


# ── DB helpers ───────────────────────────────────────────────────────────────

def _db():
    client = _get_mongo_client()
    db_name = os.getenv("DATABASE_NAME", "schemematch")
    return client[db_name]


# ── Users ────────────────────────────────────────────────────────────────────

def list_users(skip: int = 0, limit: int = 50) -> list[dict]:
    try:
        docs = list(
            _db()["users"]
            .find({}, {"hashed_password": 0})   # never expose the hash
            .sort("_id", -1)
            .skip(skip)
            .limit(limit)
        )
    except PyMongoError as exc:
        raise SchemeStoreUnavailable("DB error listing users.") from exc
    for doc in docs:
        doc["id"] = str(doc.pop("_id"))
    return docs


def count_users() -> int:
    try:
        return _db()["users"].count_documents({})
    except PyMongoError as exc:
        raise SchemeStoreUnavailable("DB error counting users.") from exc


# ── Schemes ──────────────────────────────────────────────────────────────────

def list_schemes_admin(skip: int = 0, limit: int = 100) -> list[dict]:
    try:
        docs = list(
            _db()["schemes"]
            .find({}, {"_id": 0})
            .sort("scheme_id", 1)
            .skip(skip)
            .limit(limit)
        )
    except PyMongoError as exc:
        raise SchemeStoreUnavailable("DB error listing schemes.") from exc
    return docs


def count_schemes() -> int:
    try:
        return _db()["schemes"].count_documents({})
    except PyMongoError as exc:
        raise SchemeStoreUnavailable("DB error counting schemes.") from exc


def add_scheme(scheme: dict) -> str:
    """Insert a new scheme. Returns scheme_id. Raises ValueError on duplicate."""
    try:
        existing = _db()["schemes"].find_one({"scheme_id": scheme["scheme_id"]})
        if existing:
            raise ValueError(f"scheme_id '{scheme['scheme_id']}' already exists.")
        _db()["schemes"].insert_one({**scheme})
    except PyMongoError as exc:
        raise SchemeStoreUnavailable("DB error adding scheme.") from exc
    return scheme["scheme_id"]


def update_scheme(scheme_id: str, updates: dict) -> bool:
    """Replace scheme document. Returns True if found and updated."""
    updates.pop("_id", None)                    # never let caller set _id
    updates["scheme_id"] = scheme_id            # keep scheme_id consistent
    try:
        result = _db()["schemes"].replace_one(
            {"scheme_id": scheme_id}, updates, upsert=False
        )
    except PyMongoError as exc:
        raise SchemeStoreUnavailable("DB error updating scheme.") from exc
    return result.matched_count > 0


def delete_scheme(scheme_id: str) -> bool:
    """Delete a scheme. Returns True if found and deleted."""
    try:
        result = _db()["schemes"].delete_one({"scheme_id": scheme_id})
    except PyMongoError as exc:
        raise SchemeStoreUnavailable("DB error deleting scheme.") from exc
    return result.deleted_count > 0
