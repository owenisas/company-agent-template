"""Raw vs derived records reference each other via provenance id.

Phase 2 exit: raw and derived data are separable. Derived tables MUST NOT
carry a raw dump field.
"""

from packages.knowledge.ingestion import run_ingestion
from packages.knowledge.models import Chunk, Claim, Note, RawObject, Source


DERIVED_FORBIDDEN_FIELDS = {
    "payload",
    "raw_bytes",
    "raw_text_dump",
    "original_bytes",
    "blob",
}


def test_source_points_at_raw_object_id_not_payload():
    source = Source(
        owner_principal_id="employee-a",
        content_sha256="00" * 32,
        raw_object_id="raw_deadbeef",
    )
    assert source.raw_object_id == "raw_deadbeef"
    assert not hasattr(source, "payload")
    fields = set(Source.model_fields)
    assert fields.isdisjoint(DERIVED_FORBIDDEN_FIELDS)


def test_chunk_and_claim_are_derived():
    assert "raw_object_id" in Chunk.model_fields
    assert "content" in Chunk.model_fields
    assert set(Chunk.model_fields).isdisjoint(DERIVED_FORBIDDEN_FIELDS)
    assert set(Claim.model_fields).isdisjoint(DERIVED_FORBIDDEN_FIELDS)
    assert "source_id" in Note.model_fields
    assert set(Note.model_fields).isdisjoint(DERIVED_FORBIDDEN_FIELDS)


def test_only_raw_object_has_payload_ref():
    raw = RawObject(
        raw_object_id="raw_1",
        content_sha256="ab",
        object_key="sha256/ab/cd/ab",
        payload_ref="not_configured://x",
    )
    assert raw.payload_ref.startswith("not_configured://")
    assert "payload_ref" in RawObject.model_fields
    assert "payload_ref" not in Source.model_fields
    assert "payload_ref" not in Chunk.model_fields
    assert "payload_ref" not in Claim.model_fields


def test_ingestion_links_derived_to_raw_via_id():
    plan = run_ingestion(
        owner_principal_id="employee-a",
        text="A short private note.",
        dry_run=True,
    )
    assert plan.raw is not None and plan.source is not None
    assert plan.source.raw_object_id == plan.raw.raw_object_id
    assert plan.chunks
    for chunk in plan.chunks:
        assert chunk.raw_object_id == plan.raw.raw_object_id
        assert chunk.source_id == plan.source.source_id
        assert not hasattr(chunk, "payload")
