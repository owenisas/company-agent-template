"""Claim extraction / verification skeleton (spec 23.3 step 9, 26.3, 28.4).

Candidate claims are provenance-driven. They MUST NOT be marked verified by
this module. Promotion is an approval-gated action (spec 28.3).
"""

from __future__ import annotations

from packages.knowledge.models import (
    Claim,
    ClaimStatus,
    Chunk,
    Source,
    SourceLocator,
)


def extract_candidate_claims(source: Source, chunks: list[Chunk]) -> list[Claim]:
    """Conservative stub: one candidate per chunk, always unverified."""
    claims: list[Claim] = []
    for chunk in chunks:
        excerpt = chunk.content.strip()
        if not excerpt:
            continue
        statement = excerpt.split(". ", 1)[0][:240]
        claims.append(
            Claim(
                statement=statement,
                kind="fact",
                status=ClaimStatus.CANDIDATE,
                confidence="low",
                source_locators=[chunk.locator()],
                as_of=None,
                scope_slug=source.scope_slug,
                created_by=source.owner_principal_id,
                verification_needed=True,
            )
        )
    return claims


def verify_claim(claim: Claim) -> Claim:
    """Scaffold: never auto-verifies (spec 29.2 poisoning control)."""
    updated = claim.model_copy(deep=True)
    updated.status = ClaimStatus.CANDIDATE
    updated.verification_needed = True
    return updated


def link_contradiction(older: Claim, newer: Claim, reason: str) -> dict:
    """Spec 28.4: do not erase; link."""
    return {
        "type": "contradicted_by",
        "from": older.claim_id,
        "to": newer.claim_id,
        "reason": reason,
        "from_locators": older.citation_strings(),
        "to_locators": newer.citation_strings(),
    }


def require_locator(claim: Claim) -> list[SourceLocator]:
    if not claim.source_locators:
        raise ValueError("claim missing exact source locator (spec 35.1)")
    return list(claim.source_locators)
