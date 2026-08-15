"""Knowledge models.

Normative: spec 4.1, 14.1, 22.2, 22.6, 24, 26.3, 35.1, 36.3.

Stable locators: every citation MUST include a stable source ID plus a locator
(page / char range / chunk ordinal / clause). Format:

    {source_id}@{locator}

Example: src_01JABC@chunk:3#char:12-80
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


def new_source_id() -> str:
    return f"src_{uuid4().hex}"


def new_claim_id() -> str:
    return f"clm_{uuid4().hex}"


def new_chunk_id() -> str:
    return f"chk_{uuid4().hex}"


def new_job_id() -> str:
    return f"job_{uuid4().hex}"


def new_packet_id() -> str:
    return f"rpk_{uuid4().hex}"


class Classification(str, Enum):
    """Spec 28.1 / data-classification-retention.md."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class SourceStatus(str, Enum):
    QUARANTINED = "quarantined"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DELETED = "deleted"
    LEGAL_HOLD = "legal_hold"


class ClaimStatus(str, Enum):
    CANDIDATE = "candidate"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


class IngestionState(str, Enum):
    RECEIVED = "RECEIVED"
    QUARANTINED = "QUARANTINED"
    PARSED = "PARSED"
    CLASSIFIED = "CLASSIFIED"
    ACL_ASSIGNED = "ACL_ASSIGNED"
    DEDUPLICATED = "DEDUPLICATED"
    CHUNKED = "CHUNKED"
    EMBEDDED = "EMBEDDED"
    INDEXED = "INDEXED"
    DERIVED = "DERIVED"
    AVAILABLE = "AVAILABLE"
    PARSE_FAILED = "PARSE_FAILED"
    MALWARE_REVIEW = "MALWARE_REVIEW"
    ACL_REVIEW = "ACL_REVIEW"
    EMBEDDING_FAILED = "EMBEDDING_FAILED"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    DRY_RUN = "DRY_RUN"


class SourceLocator(BaseModel):
    """Exact citation target (spec 35.1, Phase 2 exit criterion)."""

    source_id: str
    locator: str = Field(
        description="chunk:N, page:N, char:START-END, clause:ID, raw, or a join of those"
    )

    def render(self) -> str:
        return f"{self.source_id}@{self.locator}"

    @classmethod
    def parse(cls, text: str) -> "SourceLocator":
        source_id, _, locator = text.partition("@")
        if not source_id or not locator:
            raise ValueError(f"locator must be source_id@locator, got {text!r}")
        return cls(source_id=source_id, locator=locator)


class Source(BaseModel):
    """Evidence source (spec 22.2). Raw bytes live in RawObject, not here."""

    source_id: str = Field(default_factory=new_source_id)
    workspace_id: str = "company"
    owner_principal_id: str
    scope_slug: str = "user/private"
    visibility: str = "private"
    source_type: str = "user_paste"
    title: str | None = None
    origin_uri: str | None = None
    external_id: str | None = None
    author_name: str | None = None
    published_at: datetime | None = None
    captured_at: datetime = Field(default_factory=_now)
    content_sha256: str
    raw_object_id: str = Field(description="Provenance id into the raw store")
    classification: Classification = Classification.INTERNAL
    retention_class: str = "research-evidence"
    trust_prior: str = "unverified"
    instruction_trust: str = "none"
    status: SourceStatus = SourceStatus.QUARANTINED
    parser_name: str | None = None
    parser_version: str | None = None
    legal_hold: bool = False
    retention_hold: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    def locator(self, fragment: str = "raw") -> SourceLocator:
        return SourceLocator(source_id=self.source_id, locator=fragment)


class RawObject(BaseModel):
    """Immutable captured bytes (spec 14.5, 22.6 raw layer)."""

    raw_object_id: str
    content_sha256: str
    object_key: str = Field(description="content-addressed: sha256/ab/cd/<full>")
    mime_type: str | None = None
    byte_length: int = 0
    # Scaffold never stores the payload in derived models. Tests assert this field
    # exists only on the raw type.
    payload_ref: str = Field(description="URI or not_configured handle")


class Note(BaseModel):
    """User-facing note row. References a source; does not embed raw bytes."""

    note_id: str
    source_id: str
    owner_principal_id: str
    title: str | None = None
    visibility: str = "private"
    classification: Classification = Classification.INTERNAL


class Chunk(BaseModel):
    """Retrieval unit (spec 22.6 chunk layer). Derived — no raw dump."""

    chunk_id: str = Field(default_factory=new_chunk_id)
    source_id: str
    raw_object_id: str = Field(description="Provenance id; not the payload")
    ordinal: int
    content: str
    char_start: int | None = None
    char_end: int | None = None
    page_start: int | None = None
    page_end: int | None = None
    heading_path: list[str] = Field(default_factory=list)
    token_count: int | None = None
    embedding_model: str | None = None
    embedding_dimensions: int | None = None
    quarantined: bool = False

    def locator(self) -> SourceLocator:
        parts = [f"chunk:{self.ordinal}"]
        if self.char_start is not None and self.char_end is not None:
            parts.append(f"char:{self.char_start}-{self.char_end}")
        if self.page_start is not None:
            parts.append(f"page:{self.page_start}")
        return SourceLocator(source_id=self.source_id, locator="#".join(parts))


class Claim(BaseModel):
    """Structured assertion derived from evidence (spec 4.1, 26.3 §6)."""

    claim_id: str = Field(default_factory=new_claim_id)
    statement: str
    kind: str = "fact"
    status: ClaimStatus = ClaimStatus.CANDIDATE
    confidence: str = "low"
    source_locators: list[SourceLocator] = Field(default_factory=list)
    contradicting_locators: list[SourceLocator] = Field(default_factory=list)
    as_of: str | None = None
    scope_slug: str = "company"
    created_by: str | None = None
    verification_needed: bool = True

    def citation_strings(self) -> list[str]:
        return [loc.render() for loc in self.source_locators]


class ResearchPacket(BaseModel):
    """Question, queries, sources, claims, conflicts, output (spec 1, 26, 36.3)."""

    packet_id: str = Field(default_factory=new_packet_id)
    question: str
    mode: str = "quick"
    as_of: str | None = None
    queries: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    output: str = ""
    unknowns: list[str] = Field(default_factory=list)
    recommendation: str | None = None
    created_by: str | None = None
    status: str = "draft"

    def render_citations(self) -> list[str]:
        """Exact source locators for every cited claim (Phase 2 exit)."""
        rendered: list[str] = []
        for claim in self.claims:
            if not claim.source_locators:
                raise ValueError(f"claim {claim.claim_id} has no source locators")
            rendered.extend(claim.citation_strings())
        return rendered


class IngestionJob(BaseModel):
    job_id: str = Field(default_factory=new_job_id)
    source_id: str | None = None
    raw_object_id: str | None = None
    job_type: str = "ingest"
    state: IngestionState = IngestionState.RECEIVED
    dry_run: bool = False
    attempts: int = 0
    last_error: str | None = None
    created_at: datetime = Field(default_factory=_now)
    notes: list[str] = Field(default_factory=list)
