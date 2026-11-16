import hashlib
import hmac
import os
import secrets
import time
from datetime import datetime, timezone

import jwt
from fastapi import HTTPException, Request
from pymongo import MongoClient

MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGO_DB", "remote_robot_cell_identity")
JWT_SECRET = os.getenv("JWT_SECRET", "local-development-secret-change-me")
JWT_ALGORITHM = "HS256"


def _password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 240_000)
    return f"pbkdf2_sha256$240000${salt.hex()}${digest.hex()}"


def _password_matches(password: str, encoded: str) -> bool:
    try:
        scheme, rounds, salt_hex, digest_hex = encoded.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds)).hex()
        return hmac.compare_digest(candidate, digest_hex)
    except (ValueError, TypeError):
        return False


class UserStore:
    def __init__(self):
        self.client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000)
        self.users = self.client[MONGO_DB]["users"]
        try:
            self.users.create_index("username", unique=True)
        except Exception:
            # API health and deterministic non-auth tests can start before Mongo.
            pass

    def seed_user(self, username: str, password: str, role: str = "operator"):
        self.users.update_one(
            {"username": username},
            {"$setOnInsert": {"username": username, "password_hash": _password_hash(password), "role": role, "active": True, "created_at": datetime.now(timezone.utc)}},
            upsert=True,
        )

    def authenticate(self, username: str, password: str):
        try:
            user = self.users.find_one({"username": username})
        except Exception as exc:
            raise HTTPException(503, "identity database unavailable") from exc
        if not user or not user.get("active") or not _password_matches(password, user.get("password_hash", "")):
            return None
        return {"username": user["username"], "role": user.get("role", "operator")}


user_store = UserStore()


def issue_token(user: dict) -> str:
    return jwt.encode({"sub": user["username"], "role": user["role"], "exp": int(time.time()) + 8 * 3600}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(401, "authentication required")
    try:
        claims = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(401, "invalid or expired session") from exc
    try:
        user = user_store.users.find_one({"username": claims.get("sub"), "active": True})
    except Exception as exc:
        raise HTTPException(503, "identity database unavailable") from exc
    if not user:
        raise HTTPException(401, "user is inactive")
    return {"username": user["username"], "role": user.get("role", "operator")}
