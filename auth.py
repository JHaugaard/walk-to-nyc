import hashlib

from fastapi import Request, HTTPException
from itsdangerous import URLSafeSerializer, BadSignature

from config import COOKIE_SECRET, COOKIE_NAME
from db import get_db


signer = URLSafeSerializer(COOKIE_SECRET)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def get_current_user(request: Request) -> dict | None:
    """Read the signed session cookie and return user dict, or None."""
    cookie_val = request.cookies.get(COOKIE_NAME)
    if not cookie_val:
        return None
    try:
        user_id = signer.loads(cookie_val)
    except BadSignature:
        return None
    db = get_db()
    row = db.execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
    db.close()
    if not row:
        return None
    return dict(row)


def require_user(request: Request) -> dict:
    """Dependency: returns user or raises 401."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_walker(request: Request) -> dict:
    """Dependency: returns walker user or raises 403."""
    user = require_user(request)
    if user["role"] != "walker":
        raise HTTPException(status_code=403, detail="Walker access required")
    return user


def require_setup_complete(request: Request) -> dict:
    """Dependency: returns walker who has completed setup, or raises."""
    user = require_walker(request)
    if not user["setup_complete"]:
        raise HTTPException(status_code=302, detail="Setup required")
    return user


def require_admin(request: Request) -> dict:
    """Dependency: returns admin user or raises 403."""
    user = require_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def validate_token(raw_token: str) -> dict | None:
    """Hash a raw token and look up the user. Returns user dict or None."""
    token_hash = hash_token(raw_token)
    db = get_db()
    row = db.execute("SELECT * FROM user WHERE token_hash = ?", (token_hash,)).fetchone()
    db.close()
    if not row:
        return None
    return dict(row)


def make_cookie_value(user_id: int) -> str:
    """Sign a user ID for cookie storage."""
    return signer.dumps(user_id)
