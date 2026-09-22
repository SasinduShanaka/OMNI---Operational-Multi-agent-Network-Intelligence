"""User registration and signed bearer-token authentication for OMNI."""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from contextvars import ContextVar

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from database.connection import db


router = APIRouter(prefix="/auth", tags=["Authentication"])
users = db["users"]
settings = db["system_config"]

TOKEN_TTL_HOURS = int(os.getenv("AUTH_TOKEN_TTL_HOURS", "12"))
PASSWORD_ITERATIONS = 600_000
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
principal: ContextVar[dict | None] = ContextVar("omni_principal", default=None)


def current_user_name() -> str:
    user = principal.get()
    return user.get("name", "Human Manager") if user else "Human Manager"


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Enter your full name.")
        return value

    @field_validator("email")
    @classmethod
    def clean_email(cls, value):
        value = value.strip().lower()
        if not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("Enter a valid email address.")
        return value

    @field_validator("password")
    @classmethod
    def strong_password(cls, value):
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError("Password must contain at least one letter and one number.")
        return value


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class RoleChangeRequest(BaseModel):
    role: Literal["manager", "viewer"]


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _auth_secret() -> bytes:
    configured = os.getenv("AUTH_SECRET", "").strip()
    if configured:
        return configured.encode("utf-8")

    record = settings.find_one_and_update(
        {"_id": "authentication"},
        {"$setOnInsert": {"secret": secrets.token_urlsafe(48), "created_at": datetime.now(timezone.utc)}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return record["secret"].encode("utf-8")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), _b64decode(salt), int(iterations)
        )
        return hmac.compare_digest(_b64encode(digest), expected)
    except (TypeError, ValueError):
        return False


def public_user(user: dict) -> dict:
    return {
        "id": user["user_id"],
        "name": user["name"],
        "email": user["email"],
        "role": user.get("role", "viewer"),
    }


def create_token(user: dict) -> str:
    now = datetime.now(timezone.utc)
    header = _b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64encode(json.dumps({
        "sub": user["user_id"],
        "ver": user.get("token_version", 0),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=TOKEN_TTL_HOURS)).timestamp()),
    }, separators=(",", ":")).encode())
    signature = _b64encode(hmac.new(_auth_secret(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def authenticate_token(token: str) -> dict | None:
    try:
        header, payload, signature = token.split(".")
        expected = _b64encode(hmac.new(_auth_secret(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            return None
        claims = json.loads(_b64decode(payload))
        if int(claims["exp"]) <= int(datetime.now(timezone.utc).timestamp()):
            return None
        user = users.find_one({"user_id": claims["sub"], "active": True})
        if not user or user.get("token_version", 0) != claims.get("ver", 0):
            return None
        return user
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _auth_response(user: dict) -> dict:
    return {
        "access_token": create_token(user),
        "token_type": "bearer",
        "expires_in": TOKEN_TTL_HOURS * 3600,
        "user": public_user(user),
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, response: Response = None):
    now = datetime.now(timezone.utc)
    user = {
        "user_id": str(uuid.uuid4()),
        "name": request.name,
        "email": request.email,
        "password_hash": hash_password(request.password),
        "role": "manager" if users.count_documents({}) == 0 else "viewer",
        "active": True,
        "token_version": 0,
        "created_at": now,
        "last_login_at": now,
    }
    try:
        users.create_index("email", unique=True)
        users.create_index("user_id", unique=True)
        users.insert_one(user)
    except DuplicateKeyError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.") from error
    result = _auth_response(user)
    if response is not None:
        response.set_cookie("omni_session", result["access_token"], httponly=True,
                            secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
                            samesite="lax", max_age=TOKEN_TTL_HOURS * 3600)
    return {"token_type": result["token_type"], "expires_in": result["expires_in"], "user": result["user"]} if response is not None else result


@router.post("/login")
def login(request: LoginRequest, response: Response = None):
    email = request.email.strip().lower()
    user = users.find_one({"email": email})
    if not user or not user.get("active") or not verify_password(request.password, user.get("password_hash", "")):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email or password is incorrect.")
    users.update_one({"user_id": user["user_id"]}, {"$set": {"last_login_at": datetime.now(timezone.utc)}})
    result = _auth_response(user)
    if response is not None:
        response.set_cookie("omni_session", result["access_token"], httponly=True,
                            secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
                            samesite="lax", max_age=TOKEN_TTL_HOURS * 3600)
    return {"token_type": result["token_type"], "expires_in": result["expires_in"], "user": result["user"]} if response is not None else result


@router.get("/me")
def me(request: Request):
    return {"user": public_user(request.state.user)}


@router.post("/logout")
def logout(request: Request, response: Response = None):
    users.update_one(
        {"user_id": request.state.user["user_id"]},
        {"$inc": {"token_version": 1}, "$set": {"logged_out_at": datetime.now(timezone.utc)}},
    )
    if response is not None:
        response.delete_cookie("omni_session", samesite="lax")
    return {"status": "signed_out"}


@router.put("/users/{user_id}/role")
def change_user_role(user_id: str, change: RoleChangeRequest, request: Request):
    if request.state.user.get("role") not in {"manager", "user"}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Manager access is required.")
    if user_id == request.state.user["user_id"] and change.role != "manager":
        raise HTTPException(status.HTTP_409_CONFLICT, "A manager cannot remove their own manager role.")
    updated = users.find_one_and_update(
        {"user_id": user_id, "active": True},
        {"$set": {"role": change.role}, "$inc": {"token_version": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    return {"user": public_user(updated)}


@router.delete("/me")
def delete_account(request: Request, response: Response):
    """Remove account credentials and activity associated with this user ID."""
    user_id = request.state.user["user_id"]
    users.delete_one({"user_id": user_id})
    db["agent_activity"].delete_many({"user_id": user_id})
    response.delete_cookie("omni_session", samesite="lax")
    return {"status": "account_deleted"}
