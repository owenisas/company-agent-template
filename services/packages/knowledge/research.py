"""Research packet builder (spec 1, 26, 36.3).

A packet is: question, queries, sources, claims, conflicts, output.
Every cited claim MUST carry an exact source locator (Phase 2 exit criterion).
"""

from __future__ import annotations

from datetime import date
from typing import Iterable

from packages.knowledge.claims import extract_candidate_claims, link_contradiction
from packages.knowledge.models import Claim, ResearchPacket, Source


def build_packet(
    *,
    question: str,
    created_by: str,
    queries: Iterable[str] | None = None,
    sources: Iterable[Source] | None = None,
    claims: Iterable[Claim] | None = None,
    mode: str = "quick",
    output: str = "",
) -> ResearchPacket:
    source_list = list(sources or [])
    claim_list = list(claims or [])
    if not claim_list:
        # Dry structure only — no model call.
        for source in source_list:
            claim_list.extend(extract_candidate_claims(source, []))
    conflicts: list[dict] = []
    if len(claim_list) >= 2 and claim_list[0].statement != claim_list[1].statement:
        conflicts.append(link_contradiction(claim_list[0], claim_list[1], "possible_disagreement"))
    packet = ResearchPacket(
        question=question,
        mode=mode,
        as_of=date.today().isoformat(),
        queries=list(queries or []),
        sources=source_list,
        claims=claim_list,
        conflicts=conflicts,
        output=output or "not_configured: research worker / embedding / postgres (D040, D055)",
        created_by=created_by,
        status="draft",
    )
    return packet


def render_packet_citations(packet: ResearchPacket) -> list[str]:
    """Fail closed if any cited claim lacks a stable id + locator."""
    return packet.render_citations()
