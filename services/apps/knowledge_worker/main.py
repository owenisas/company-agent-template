"""knowledge-worker process (spec 13.2, 23).

Extraction, chunking, embeddings, entity/claim jobs.
Phase 2 scaffold: ingestion job loop stub. No live queue, no model key.
"""

from __future__ import annotations

from typing import Any

from packages.config import load_config
from packages.knowledge.ingestion import IngestionPlan, run_ingestion
from packages.knowledge.models import IngestionJob, IngestionState


def claim_next_job() -> IngestionJob | None:
    """PostgreSQL FOR UPDATE SKIP LOCKED is not configured (spec 6 job queue)."""
    return None


def process_job(job: IngestionJob, text: str = "") -> IngestionPlan:
    owner = job.notes[0] if job.notes else "company-system"
    return run_ingestion(
        owner_principal_id=owner,
        text=text or "",
        dry_run=job.dry_run,
    )


def run_loop_once() -> dict[str, Any]:
    cfg = load_config()
    job = claim_next_job()
    return {
        "status": "not_configured",
        "queue": "none",
        "job": None if job is None else job.model_dump(),
        "database_configured": cfg.database_configured,
        "embeddings_configured": cfg.embeddings_configured,
        "detail": "TODO: D055 postgres job table; D040 embedding key — worker will not start a live loop",
        "idle_state": IngestionState.RECEIVED.value,
    }


def main() -> None:
    result = run_loop_once()
    print(result)


if __name__ == "__main__":
    main()
