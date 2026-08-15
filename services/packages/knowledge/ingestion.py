"""Ingestion pipeline skeleton.

Normative: spec 6 (untrusted-content boundary), 14.5, 22.6, 23, 29.2 poisoning.

Stages: raw-store → normalize → chunk → embed.

Phase 2 deliverable: bulk import dry-run reports counts, types, size,
duplicates, and proposed ACLs without writing indexes or embeddings.

Stubs return explicit not-configured / TODO outcomes. They MUST NOT pretend
to persist, embed, or call a network.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from packages.knowledge.models import (
    Chunk,
    Classification,
    IngestionJob,
    IngestionState,
    RawObject,
    Source,
    SourceStatus,
    new_chunk_id,
    new_source_id,
)


CONTENT_ADDRESSED_PREFIX = "sha256"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def object_key_for(digest: str) -> str:
    """Spec 14.5: sha256/ab/cd/<full-sha256>."""
    return f"{CONTENT_ADDRESSED_PREFIX}/{digest[0:2]}/{digest[2:4]}/{digest}"


_INSTRUCTION_MARKERS = (
    "ignore previous",
    "ignore all instructions",
    "system prompt",
    "you are now",
    "disregard your",
)


def quarantine_flags(text: str) -> list[str]:
    """Spec 6 / 29.3: retrieved content is data, never control-plane instruction."""
    flags: list[str] = []
    lowered = text.lower()
    for marker in _INSTRUCTION_MARKERS:
        if marker in lowered:
            flags.append(f"untrusted_instruction:{marker}")
    if re.search(r"(api[_-]?key|password|secret|begin .+ private key)", lowered):
        flags.append("possible_secret_payload")
    return flags


@dataclass
class StageResult:
    name: str
    ok: bool
    configured: bool
    detail: str
    artifacts: dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestionPlan:
    """Dry-run or live plan. Live persist is not configured in Phase 2 scaffold."""

    job: IngestionJob
    stages: list[StageResult]
    source: Source | None = None
    raw: RawObject | None = None
    chunks: list[Chunk] = field(default_factory=list)
    proposed_acl: dict[str, Any] = field(default_factory=dict)
    flags: list[str] = field(default_factory=list)

    @property
    def configured(self) -> bool:
        return False


def _store_raw(payload: bytes, mime_type: str | None) -> tuple[RawObject, StageResult]:
    digest = sha256_hex(payload)
    raw = RawObject(
        raw_object_id=f"raw_{digest[:16]}",
        content_sha256=digest,
        object_key=object_key_for(digest),
        mime_type=mime_type,
        byte_length=len(payload),
        payload_ref="not_configured://raw-object-store",
    )
    return raw, StageResult(
        name="raw_store",
        ok=True,
        configured=False,
        detail="computed content-addressed key; object store not configured (D032/D055)",
        artifacts={"raw_object_id": raw.raw_object_id, "sha256": digest, "bytes": len(payload)},
    )


def _normalize(text: str) -> tuple[str, StageResult]:
    normalized = text.replace("\r\n", "\n").strip()
    return normalized, StageResult(
        name="normalize",
        ok=True,
        configured=True,
        detail="whitespace-normalized; parsers for pdf/html are TODO (Phase 3)",
        artifacts={"chars": len(normalized)},
    )


def _chunk(source_id: str, raw_object_id: str, text: str) -> tuple[list[Chunk], StageResult]:
    # Spec 23.3 step 7: short notes stay whole; otherwise paragraph groups.
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        paragraphs = [text] if text else []
    chunks: list[Chunk] = []
    cursor = 0
    for i, para in enumerate(paragraphs):
        start = text.find(para, cursor)
        end = start + len(para) if start >= 0 else cursor + len(para)
        chunks.append(
            Chunk(
                chunk_id=new_chunk_id(),
                source_id=source_id,
                raw_object_id=raw_object_id,
                ordinal=i,
                content=para,
                char_start=max(start, 0),
                char_end=end,
            )
        )
        cursor = end
    return chunks, StageResult(
        name="chunk",
        ok=True,
        configured=True,
        detail=f"{len(chunks)} chunk(s); offsets stored; no index write",
        artifacts={"chunk_count": len(chunks)},
    )


def _embed(chunks: list[Chunk]) -> StageResult:
    return StageResult(
        name="embed",
        ok=False,
        configured=False,
        detail="TODO: D040 embedding provider/model/dimensions — no vectors computed",
        artifacts={"chunk_count": len(chunks), "vectors": 0},
    )


def run_ingestion(
    *,
    owner_principal_id: str,
    text: str,
    source_type: str = "user_paste",
    visibility: str = "private",
    classification: Classification = Classification.INTERNAL,
    mime_type: str = "text/plain",
    dry_run: bool = False,
    title: str | None = None,
) -> IngestionPlan:
    """Run the pipeline in-memory. Never writes a database or object store."""
    job = IngestionJob(
        job_type="bulk_import" if dry_run else "ingest",
        dry_run=dry_run,
        state=IngestionState.DRY_RUN if dry_run else IngestionState.RECEIVED,
    )
    payload = text.encode("utf-8")
    flags = quarantine_flags(text)
    raw, raw_stage = _store_raw(payload, mime_type)
    normalized, norm_stage = _normalize(text)
    source = Source(
        source_id=new_source_id(),
        owner_principal_id=owner_principal_id,
        scope_slug=f"user/{owner_principal_id}/private" if visibility == "private" else "company",
        visibility=visibility,
        source_type=source_type,
        title=title,
        content_sha256=raw.content_sha256,
        raw_object_id=raw.raw_object_id,
        classification=classification,
        status=SourceStatus.QUARANTINED if flags else SourceStatus.ACTIVE,
        instruction_trust="none",
        metadata={"quarantine_flags": flags, "dry_run": dry_run},
    )
    chunks, chunk_stage = _chunk(source.source_id, raw.raw_object_id, normalized)
    embed_stage = _embed(chunks)
    job.source_id = source.source_id
    job.raw_object_id = raw.raw_object_id
    if flags:
        job.state = IngestionState.QUARANTINED
        job.notes.append("untrusted-content boundary: quarantined")
    elif dry_run:
        job.state = IngestionState.DRY_RUN
    else:
        job.state = IngestionState.CHUNKED
        job.notes.append("embed/index not configured; stopping before AVAILABLE")

    proposed_acl = {
        "owner": owner_principal_id,
        "visibility": visibility,
        "classification": classification.value,
        "restricted_requires_domain_approver": classification is Classification.RESTRICTED,
    }
    return IngestionPlan(
        job=job,
        stages=[raw_stage, norm_stage, chunk_stage, embed_stage],
        source=source,
        raw=raw,
        chunks=chunks,
        proposed_acl=proposed_acl,
        flags=flags,
    )


def bulk_import_dry_run(items: Iterable[dict[str, Any]], owner_principal_id: str) -> dict[str, Any]:
    """Phase 2 bulk import dry-run (spec 23.4). No writes."""
    plans: list[IngestionPlan] = []
    types: dict[str, int] = {}
    total_bytes = 0
    hashes: dict[str, int] = {}
    for item in items:
        text = str(item.get("text") or item.get("content") or "")
        source_type = str(item.get("source_type") or "user_paste")
        visibility = str(item.get("visibility") or "private")
        classification = Classification(item.get("classification") or "internal")
        plan = run_ingestion(
            owner_principal_id=owner_principal_id,
            text=text,
            source_type=source_type,
            visibility=visibility,
            classification=classification,
            dry_run=True,
            title=item.get("title"),
        )
        plans.append(plan)
        types[source_type] = types.get(source_type, 0) + 1
        if plan.raw:
            total_bytes += plan.raw.byte_length
            hashes[plan.raw.content_sha256] = hashes.get(plan.raw.content_sha256, 0) + 1
    duplicates = sum(1 for count in hashes.values() if count > 1)
    restricted = sum(
        1 for p in plans if p.source and p.source.classification is Classification.RESTRICTED
    )
    return {
        "status": "dry_run",
        "configured": False,
        "count": len(plans),
        "file_types": types,
        "total_bytes": total_bytes,
        "duplicate_hash_groups": duplicates,
        "restricted_count": restricted,
        "restricted_indexing": "blocked_pending_approval" if restricted else "n/a",
        "proposed_acls": [p.proposed_acl for p in plans],
        "quarantine_flagged": sum(1 for p in plans if p.flags),
        "claims_promoted": 0,
        "detail": "TODO: persist only after D020-D024 data scope and D055 postgres host",
    }


def ingest_from_connector(
    connector_id: str,
    *,
    owner_principal_id: str,
    documents: Iterable[dict[str, Any]] | None = None,
    dry_run: bool = True,
    visibility: str = "company",
    classification: Classification = Classification.INTERNAL,
) -> dict[str, Any]:
    """Pull connector docs → raw evidence → normalize/chunk.

    No network. Live Notion connect is TODO (D025). Caller MAY pass already
    fetched (or fixture) documents for a dry-run. Provenance is always
    recorded; quarantine_flags still apply.
    """
    if documents is None:
        return {
            "status": "not_configured",
            "configured": False,
            "connector_id": connector_id,
            "dry_run": dry_run,
            "count": 0,
            "detail": "TODO: live connector pull (D025 Notion / TBD-decision)",
            "provenance": {
                "kind": "connector",
                "connector_id": connector_id,
                "instruction_trust": "none",
            },
        }
    items = []
    for doc in documents:
        items.append(
            {
                "text": str(doc.get("plain_text") or doc.get("text") or ""),
                "source_type": f"connector:{connector_id}",
                "visibility": visibility,
                "classification": classification.value,
                "title": doc.get("title"),
            }
        )
    report = bulk_import_dry_run(items, owner_principal_id)
    report["connector_id"] = connector_id
    report["dry_run"] = dry_run
    report["provenance"] = {
        "kind": "connector",
        "connector_id": connector_id,
        "instruction_trust": "none",
        "quarantine": True,
    }
    return report
