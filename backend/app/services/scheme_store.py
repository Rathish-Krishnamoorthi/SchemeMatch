import os
from threading import Lock
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.models import Scheme


load_dotenv(Path(__file__).resolve().parents[2] / ".env")

_mongo_client: MongoClient | None = None
_mongo_client_lock = Lock()


class SchemeStoreUnavailable(RuntimeError):
    pass


def _get_mongo_client() -> MongoClient:
    global _mongo_client

    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        raise SchemeStoreUnavailable(
            "MONGODB_URI is not set. Add it to backend/.env to connect to MongoDB."
        )
    with _mongo_client_lock:
        if _mongo_client is None:
            _mongo_client = MongoClient(mongo_uri)
        return _mongo_client


def close_mongo_client() -> None:
    global _mongo_client

    with _mongo_client_lock:
        if _mongo_client is not None:
            _mongo_client.close()
            _mongo_client = None


def load_schemes() -> list[Scheme]:
    client = _get_mongo_client()
    database_name = os.getenv("DATABASE_NAME", "schemematch")
    try:
        documents = list(client[database_name]["schemes"].find({}, {"_id": 0}))
    except PyMongoError as error:
        raise SchemeStoreUnavailable(
            "MongoDB is unavailable. Check MONGODB_URI, Atlas network access, and database credentials."
        ) from error
    return [Scheme.model_validate(record) for record in documents]
