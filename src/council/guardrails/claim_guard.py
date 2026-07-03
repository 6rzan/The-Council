"""Claim guard — strike unsupported claims before synthesis (T029, FR-005).

Deterministic, runs between the Fact-Checker and the Synthesizer. Removes any
``unsupported`` claim so none can be presented as established fact in the
Verdict Brief, regardless of model behavior. ``supported`` and ``uncertain``
claims pass through (uncertain claims are retained but never asserted as fact).
"""
from __future__ import annotations

from council.schemas.claim import Claim, ClaimStatus


def strike_unsupported(claims: list[Claim]) -> list[Claim]:
    """Return claims with every ``unsupported`` one removed (FR-005)."""
    return [c for c in claims if c.status is not ClaimStatus.unsupported]
