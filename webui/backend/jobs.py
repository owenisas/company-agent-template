"""Process-local chat jobs. One host, one process — enough."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .config import (
    JOBS_DIR,
    hermes_bin,
    hermes_model,
    hermes_provider,
    hermes_reasoning,
)

try:
    import fcntl
except Exception:  # pragma: no cover — Windows / missing fcntl
    fcntl = None  # type: ignore[assignment]

_LOCK = threading.Lock()
_JOBS: dict[str, "Job"] = {}
_JOB_TIMEOUT_SEC = int(os.environ.get("WEBUI_JOB_TIMEOUT", "600"))
_CRED_THREAD_LOCKS: dict[str, threading.Lock] = {}
_CRED_THREAD_GUARD = threading.Lock()


def _credential_lock_key() -> str:
    """Jobs that share a provider share one rotating OAuth grant on this host."""
    return hermes_provider() or "default"


def _thread_lock_for(key: str) -> threading.Lock:
    with _CRED_THREAD_GUARD:
        lock = _CRED_THREAD_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _CRED_THREAD_LOCKS[key] = lock
        return lock


@contextmanager
def _credential_job_lock(key: str) -> Iterator[None]:
    """Serialize hermes launches that share a credential.

    Threading lock covers one webui process. File flock covers a second
    webui/worker on the same host. Held for the whole job so the second
    chat queues until the first hermes process exits.
    """
    safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in key)
    lock_path = JOBS_DIR / f".cred-{safe}.lock"
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    thread_lock = _thread_lock_for(key)
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


@dataclass
class Job:
    job_id: str
    profile: str
    message: str
    status: str = "running"
    partial: str = ""
    result: str | None = None
    error: str | None = None
    started_at: float = field(default_factory=time.time)
    proc: subprocess.Popen[str] | None = field(default=None, repr=False)

    def elapsed(self) -> float:
        return round(time.time() - self.started_at, 3)

    def public(self) -> dict:
        return {
            "job_id": self.job_id,
            "profile": self.profile,
            "status": self.status,
            "partial": self.partial,
            "result": self.result,
            "error": self.error,
            "started_at": datetime.fromtimestamp(
                self.started_at, tz=timezone.utc
            ).isoformat(),
            "elapsed": self.elapsed(),
        }


def _ensure_jobs_dir() -> Path:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    return JOBS_DIR


def _persist(job: Job) -> None:
    target = _ensure_jobs_dir() / f"{job.job_id}.json"
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(job.public(), indent=2) + "\n", encoding="utf-8")
    tmp.replace(target)


def _append_log(job_id: str, text: str) -> None:
    path = _ensure_jobs_dir() / f"{job_id}.log"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text)


def _run_job(job: Job) -> None:
    binary = shutil.which(hermes_bin()) or hermes_bin()
    cmd = [
        binary,
        "-p",
        job.profile,
        "--provider",
        hermes_provider(),
        "-m",
        hermes_model(),
        "--reasoning",
        hermes_reasoning(),
        "--cli",
        "-z",
        job.message,
    ]
    _append_log(job.job_id, "$ " + " ".join(cmd) + "\n")
    try:
        with _credential_job_lock(_credential_lock_key()):
            _exec_hermes(job, cmd)
    except Exception as exc:  # noqa: BLE001 — surface to the poller
        job.status = "error"
        job.error = str(exc)
        if job.partial and not job.result:
            job.result = job.partial
    finally:
        _persist(job)


def _exec_hermes(job: Job, cmd: list[str]) -> None:
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    job.proc = proc
    chunks: list[str] = []
    assert proc.stdout is not None
    deadline = job.started_at + _JOB_TIMEOUT_SEC
    while True:
        if time.time() > deadline:
            proc.kill()
            job.status = "error"
            job.error = f"timed out after {_JOB_TIMEOUT_SEC}s"
            job.result = "".join(chunks).strip() or None
            break
        line = proc.stdout.readline()
        if line == "" and proc.poll() is not None:
            break
        if line:
            chunks.append(line)
            job.partial = "".join(chunks)
            _append_log(job.job_id, line)
    rc = proc.wait()
    text = "".join(chunks).strip()
    if job.status != "error":
        if rc == 0:
            job.status = "done"
            job.result = text
        else:
            job.status = "error"
            job.error = f"exit {rc}"
            job.result = text or None


def start_job(profile: str, message: str) -> Job:
    job = Job(job_id=uuid.uuid4().hex[:12], profile=profile, message=message)
    _ensure_jobs_dir()
    _persist(job)
    with _LOCK:
        _JOBS[job.job_id] = job
    thread = threading.Thread(target=_run_job, args=(job,), name=f"job-{job.job_id}", daemon=True)
    thread.start()
    return job


def get_job(job_id: str) -> Job | None:
    with _LOCK:
        job = _JOBS.get(job_id)
    if job:
        return job
    path = JOBS_DIR / f"{job_id}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    restored = Job(
        job_id=data.get("job_id") or job_id,
        profile=data.get("profile") or "",
        message="",
        status=data.get("status") or "error",
        partial=data.get("partial") or "",
        result=data.get("result"),
        error=data.get("error"),
    )
    try:
        restored.started_at = datetime.fromisoformat(data["started_at"]).timestamp()
    except (KeyError, TypeError, ValueError):
        pass
    return restored
