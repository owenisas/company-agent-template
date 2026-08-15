"""Load Notion public-connection settings from env / .env-style files."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

from packages.config import parse_env_file
from packages.notion.models import NotionConfig
from packages.notion.tokens import default_token_path

ENV_KEYS = (
    "NOTION_CLIENT_ID",
    "NOTION_CLIENT_SECRET",
    "NOTION_REDIRECT_URI",
    "NOTION_TOKEN_PATH",
)

DEFAULT_REDIRECT_URI = "http://127.0.0.1:8080/auth/notion/callback"


def load_notion_config(
    *,
    file_path: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> NotionConfig:
    merged: dict[str, str] = {}
    if file_path is not None and Path(file_path).is_file():
        merged.update(parse_env_file(file_path))
    env_map = env if env is not None else os.environ
    for key in ENV_KEYS:
        if key in env_map and env_map[key] != "":
            merged[key] = env_map[key]
    token_path = merged.get("NOTION_TOKEN_PATH") or str(default_token_path())
    return NotionConfig(
        client_id=merged.get("NOTION_CLIENT_ID", "").strip(),
        client_secret=merged.get("NOTION_CLIENT_SECRET", "").strip(),
        redirect_uri=(merged.get("NOTION_REDIRECT_URI") or DEFAULT_REDIRECT_URI).strip(),
        token_path=token_path,
    )
