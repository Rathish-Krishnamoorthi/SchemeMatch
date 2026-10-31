import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
from dotenv import load_dotenv
from jose import JWTError, jwt
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.services.scheme_store import _get_mongo_client, SchemeStoreUnavailable

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


class AuthError(ValueError):
    """Raised for expected auth failures (duplicate email, bad credentials)."""


def _users_collection():
    client = _get_mongo_client()
    if client is None:
        raise SchemeStoreUnavailable(
            "MongoDB is unavailable. Check MONGODB_URI and database credentials."
        )
    database_name = os.getenv("DATABASE_NAME", "schemematch")
    collection = client[database_name]["users"]
    # Ensure the email index exists (idempotent on re-runs)
    try:
        collection.create_index("email", unique=True)
    except PyMongoError as error:
        raise SchemeStoreUnavailable("Database error preparing authentication.") from error
    return collection


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: str, email: str, name: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "exp": expire,
    }
    return jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
    except JWTError as error:
        raise AuthError("Invalid or expired token.") from error


def register_user(name: str, email: str, password: str) -> dict:
    """Create a new user in MongoDB. Returns the public user dict."""
    collection = _users_collection()
    hashed = hash_password(password)
    doc = {"name": name, "email": email, "hashed_password": hashed}
    try:
        result = collection.insert_one(doc)
    except DuplicateKeyError:
        raise AuthError("An account with that email already exists.")
    except PyMongoError as error:
        raise SchemeStoreUnavailable("Database error during registration.") from error

    user_id = str(result.inserted_id)
    return {"id": user_id, "name": name, "email": email}


def authenticate_user(email: str, password: str) -> dict:
    """Verify credentials. Returns the public user dict on success."""
    collection = _users_collection()
    try:
        doc = collection.find_one({"email": email})
    except PyMongoError as error:
        raise SchemeStoreUnavailable("Database error during login.") from error

    stored_hash = doc.get("hashed_password") if doc else None
    try:
        password_matches = (
            isinstance(stored_hash, str)
            and verify_password(password, stored_hash)
        )
    except (ValueError, TypeError):
        password_matches = False

    if not password_matches:
        raise AuthError("Incorrect email or password.")

    return {"id": str(doc["_id"]), "name": doc["name"], "email": doc["email"]}


def get_user_profile(user_id: str) -> dict | None:
    """Return the saved demographic profile for a user, or None if not yet set."""
    from bson import ObjectId

    collection = _users_collection()
    try:
        doc = collection.find_one({"_id": ObjectId(user_id)}, {"profile": 1})
    except PyMongoError as error:
        raise SchemeStoreUnavailable("Database error fetching profile.") from error
    if doc is None:
        return None
    return doc.get("profile")  # may be None if never set


def save_user_profile(user_id: str, profile: dict) -> None:
    """Upsert the demographic profile sub-document on the user record."""
    from bson import ObjectId

    collection = _users_collection()
    try:
        collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"profile": profile}},
        )
    except PyMongoError as error:
        raise SchemeStoreUnavailable("Database error saving profile.") from error
