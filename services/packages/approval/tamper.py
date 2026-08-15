"""Approval request fingerprint (spec 12.5: invalidate on material change).

Algorithm (scaffold default; production choice is D060):
  sha256 hex of canonical JSON over the material field set.

The fingerprint is a hash, never a secret. Secret-like keys are dropped
before hashing so they cannot enter the approval object.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

SECRET_LIKE_KEYS = frozenset(
    {
        "password",
        "passwd",
        "token",
        "api_key",
        "api-key",
        "apikey",
        "secret",
        "credential",
        "private_key",
        "access_token",
        "refresh_token",
    }
)


def strip_secret_like(value: Any) -> Any:
    """Drop secret-like keys from mappings. Used by preview and fingerprint."""
    if isinstance(value, dict):
        return {
            str(k): strip_secret_like(v)
            for k, v in value.items()
            if str(k).lower() not in SECRET_LIKE_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [strip_secret_like(v) for v in value]
    return value


def _canonicalize(value: Any) -> Any:
    value = strip_secret_like(value)
    if isinstance(value, dict):
        return {str(k): _canonicalize(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def request_fingerprint(material: dict[str, Any]) -> str:
    """Stable fingerprint over material approval parameters."""
    canonical = json.dumps(
        _canonicalize(material),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def fingerprints_match(left: str, right: str) -> bool:
    return bool(left) and left == right
