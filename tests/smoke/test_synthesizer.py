"""Smoke test for the Synthesizer structured VerdictBrief (T019).

Valid input → schema-valid VerdictBrief. FR-018: invalid twice → degrade to a
minimal well-formed brief that flags the degradation.
"""
from __future__ import annotations

import json

import pytest

from council.agents.synthesizer import build_synthesizer
from council.app import CouncilApp, run_agent_for_output
from council.orchestration.deliberation import synthesize_with_retry
from council.orchestration.fallback import fallback_roster
from council.schemas.claim import Claim, ClaimStatus
from council.schemas.verdict import VerdictBrief
from tests._fakes import ScriptedLlm, VERDICT, CLAIMS


def _claims():
    return [Claim.model_validate(c) for c in CLAIMS]


@pytest.mark.asyncio
async def test_synthesizer_produces_valid_brief(app: CouncilApp, scripted_models):
    session = await app.create_session()
    brief = await synthesize_with_retry(
        app, session, scripted_models["synthesizer"],
        question="q", roster=fallback_roster(), transcript=[], claims=_claims(),
    )
    assert isinstance(brief, VerdictBrief)
    assert len(brief.positions) >= 2
    assert brief.confidence


@pytest.mark.asyncio
async def test_synthesizer_retry_then_degrade(app: CouncilApp):
    """FR-018: invalid output twice → minimal well-formed brief (no crash)."""
    bad = ScriptedLlm(["nope", "still nope"])
    session = await app.create_session()
    brief = await synthesize_with_retry(
        app, session, bad, question="q", roster=fallback_roster(),
        transcript=[], claims=_claims(),
    )
    assert isinstance(brief, VerdictBrief)
    # degraded brief flags the degradation in the recommendation
    assert "degraded" in brief.recommendation.lower() or brief.confidence
