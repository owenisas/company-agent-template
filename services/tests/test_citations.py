"""Research packet renders exact source locators (spec 35.1, Phase 2 exit)."""

import pytest

from packages.knowledge.models import (
    Claim,
    Chunk,
    ResearchPacket,
    Source,
    SourceLocator,
)
from packages.knowledge.research import build_packet, render_packet_citations


def test_locator_render_and_parse():
    loc = SourceLocator(source_id="src_abc", locator="chunk:3#char:10-40")
    assert loc.render() == "src_abc@chunk:3#char:10-40"
    parsed = SourceLocator.parse(loc.render())
    assert parsed.source_id == "src_abc"
    assert parsed.locator == "chunk:3#char:10-40"


def test_chunk_locator_is_stable_id_plus_offsets():
    chunk = Chunk(
        source_id="src_stable",
        raw_object_id="raw_1",
        ordinal=2,
        content="hello",
        char_start=10,
        char_end=15,
        page_start=4,
    )
    rendered = chunk.locator().render()
    assert rendered.startswith("src_stable@")
    assert "chunk:2" in rendered
    assert "char:10-15" in rendered
    assert "page:4" in rendered


def test_packet_renders_locator_for_every_cited_claim():
    loc = SourceLocator(source_id="src_01j", locator="chunk:0#char:0-80")
    claim = Claim(statement="Vendor X announced Y", source_locators=[loc])
    packet = ResearchPacket(question="What did X announce?", claims=[claim], output="Y")
    citations = render_packet_citations(packet)
    assert citations == ["src_01j@chunk:0#char:0-80"]


def test_packet_refuses_claim_without_locator():
    packet = ResearchPacket(
        question="?",
        claims=[Claim(statement="bare assertion", source_locators=[])],
    )
    with pytest.raises(ValueError, match="no source locators"):
        packet.render_citations()


def test_build_packet_preserves_source_ids():
    source = Source(
        source_id="src_keep",
        owner_principal_id="employee-a",
        content_sha256="abc",
        raw_object_id="raw_keep",
    )
    loc = source.locator("page:1")
    claim = Claim(statement="noted", source_locators=[loc])
    packet = build_packet(
        question="q",
        created_by="employee-a",
        sources=[source],
        claims=[claim],
        queries=["q"],
    )
    assert "src_keep@page:1" in packet.render_citations()
    assert packet.sources[0].source_id == "src_keep"
