"""Read-only per-profile token totals from Hermes state.db."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import hermes_home

_USAGE_SQL = """
SELECT
    COALESCE(NULLIF(s.profile_name, ''), ?) AS profile,
    COALESCE(SUM(u.input_tokens), 0) AS input_tokens,
    COALESCE(SUM(u.output_tokens), 0) AS output_tokens,
    COALESCE(SUM(u.cache_read_tokens), 0) AS cache_read_tokens,
    COALESCE(SUM(u.cache_write_tokens), 0) AS cache_write_tokens,
    COALESCE(SUM(u.reasoning_tokens), 0) AS reasoning_tokens,
    COALESCE(SUM(u.api_call_count), 0) AS api_call_count,
    COALESCE(SUM(u.estimated_cost_usd), 0) AS estimated_cost_usd
FROM session_model_usage u
LEFT JOIN sessions s ON s.id = u.session_id
GROUP BY 1
"""


def _db_path_for(profile: str) -> Path:
    root = hermes_home()
    if profile == "default":
        return root / "state.db"
    return root / "profiles" / profile / "state.db"


def _read_db(path: Path, fallback_profile: str) -> dict[str, dict]:
    if not path.is_file():
        return {}
    uri = f"file:{path}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error:
        return {}
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(_USAGE_SQL, (fallback_profile,)).fetchall()
    except sqlite3.Error:
        return {}
    finally:
        conn.close()
    out: dict[str, dict] = {}
    for row in rows:
        name = row["profile"] or fallback_profile
        out[name] = {
            "profile": name,
            "input_tokens": int(row["input_tokens"]),
            "output_tokens": int(row["output_tokens"]),
            "cache_read_tokens": int(row["cache_read_tokens"]),
            "cache_write_tokens": int(row["cache_write_tokens"]),
            "reasoning_tokens": int(row["reasoning_tokens"]),
            "api_call_count": int(row["api_call_count"]),
            "estimated_cost_usd": float(row["estimated_cost_usd"]),
        }
    return out


def empty_usage(profile: str) -> dict:
    return {
        "profile": profile,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "reasoning_tokens": 0,
        "api_call_count": 0,
        "estimated_cost_usd": 0.0,
    }


def usage_for_profiles(profiles: list[str]) -> list[dict]:
    """Totals for the caller's accessible profiles only."""
    combined: dict[str, dict] = {}
    default_db = hermes_home() / "state.db"
    combined.update(_read_db(default_db, "default"))
    for name in profiles:
        if name == "default":
            continue
        for key, row in _read_db(_db_path_for(name), name).items():
            if key in combined:
                for field in (
                    "input_tokens",
                    "output_tokens",
                    "cache_read_tokens",
                    "cache_write_tokens",
                    "reasoning_tokens",
                    "api_call_count",
                    "estimated_cost_usd",
                ):
                    combined[key][field] += row[field]
            else:
                combined[key] = row
    result = []
    for name in profiles:
        row = combined.get(name) or empty_usage(name)
        row = dict(row)
        row["total_tokens"] = (
            int(row["input_tokens"])
            + int(row["output_tokens"])
            + int(row["reasoning_tokens"])
        )
        result.append(row)
    return result
