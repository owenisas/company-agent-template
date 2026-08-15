"""Server-side Notion token store.

JSON file, mode 0600, default path ``~/.hermes/notion-tokens.json``.
Token values are never logged or included in public status payloads.
Writes take an exclusive file lock so refresh-token rotation is atomic.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from packages.notion.models import NotionConnectionStatus, NotionTokens

try:
    import fcntl
except Exception:  # pragma: no cover — Windows / missing fcntl
    fcntl = None  # type: ignore[assignment]

log = logging.getLogger("packages.notion.tokens")

_THREAD_GUARD = threading.Lock()
_THREAD_LOCKS: dict[str, threading.Lock] = {}

DEFAULT_TOKEN_RELATIVE = Path(".hermes") / "notion-tokens.json"


def default_token_path() -> Path:
    override = os.environ.get("NOTION_TOKEN_PATH", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / DEFAULT_TOKEN_RELATIVE


def _thread_lock_for(path: Path) -> threading.Lock:
    key = str(path.resolve()) if path.exists() or path.parent.exists() else str(path)
    with _THREAD_GUARD:
        lock = _THREAD_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _THREAD_LOCKS[key] = lock
        return lock


def _chmod_private(path: Path) -> None:
    try:
        os.chmod(path, 0o600)
    except OSError:
        log.warning("could not chmod 0600 on token file path")


@contextmanager
def rotation_lock(path: Path) -> Iterator[None]:
    """Exclusive lock for token read-modify-write (mirrors webui credential flock)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    thread_lock = _thread_lock_for(path)
    with thread_lock:
        if fcntl is None:
            yield
            return
        with lock_path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class TokenStore:
    """JSON file store. Public APIs never return access or refresh tokens."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path is not None else default_token_path()

    def load(self) -> NotionTokens | None:
        if not self.path.is_file():
            return None
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            log.warning("notion token file unreadable")
            return None
        if not isinstance(raw, dict):
            return None
        tokens = NotionTokens.from_disk(raw)
        if not tokens.has_access_token():
            return None
        return tokens

    def save(self, tokens: NotionTokens) -> None:
        payload = tokens.to_disk()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        _chmod_private(tmp)
        os.replace(tmp, self.path)
        _chmod_private(self.path)

    def clear(self) -> None:
        if self.path.is_file():
            try:
                self.path.unlink()
            except OSError:
                log.warning("could not remove notion token file")

    def status(self) -> NotionConnectionStatus:
        tokens = self.load()
        if tokens is None:
            return NotionConnectionStatus(
                connected=False,
                configured=False,
                detail="not_configured",
            )
        public = tokens.public_status()
        return NotionConnectionStatus(
            connected=True,
            configured=True,
            workspace_name=public["workspace_name"] or None,
            workspace_id=public["workspace_id"] or None,
            bot_id=public["bot_id"] or None,
            owner_name=public["owner_name"] or None,
            detail="connected",
        )

    def save_locked(self, tokens: NotionTokens) -> None:
        with rotation_lock(self.path):
            self.save(tokens)

    def load_locked(self) -> NotionTokens | None:
        with rotation_lock(self.path):
            return self.load()

    def clear_locked(self) -> None:
        with rotation_lock(self.path):
            self.clear()
