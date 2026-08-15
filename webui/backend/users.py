"""Load users from runtime/users.json and verify passwords."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path

from .config import PBKDF2_ITERATIONS, USERS_PATH


def hash_password(
    password: str,
    salt: bytes | None = None,
    iterations: int = PBKDF2_ITERATIONS,
) -> dict[str, str | int]:
    if salt is None:
        salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return {
        "algo": "pbkdf2_sha256",
        "iterations": iterations,
        "salt": salt.hex(),
        "password_hash": digest.hex(),
    }


def verify_password(password: str, record: dict) -> bool:
    try:
        salt = bytes.fromhex(record["salt"])
        expected = bytes.fromhex(record["password_hash"])
        iterations = int(record.get("iterations") or PBKDF2_ITERATIONS)
    except (KeyError, ValueError, TypeError):
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(digest, expected)


def load_users(path: Path | None = None) -> list[dict]:
    target = path or USERS_PATH
    if not target.is_file():
        return []
    raw = target.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    data = json.loads(raw)
    if isinstance(data, dict):
        users = data.get("users", [])
    elif isinstance(data, list):
        users = data
    else:
        return []
    return [u for u in users if isinstance(u, dict) and u.get("username")]


def find_user(username: str, path: Path | None = None) -> dict | None:
    wanted = (username or "").strip()
    if not wanted:
        return None
    for user in load_users(path):
        if user.get("username") == wanted:
            return user
    return None


def public_user(user: dict) -> dict:
    return {
        "username": user.get("username"),
        "role": user.get("role") or "viewer",
        "profile": user.get("profile") or "",
    }
