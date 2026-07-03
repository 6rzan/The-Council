"""Smoke test for the Fact-Checker evidence + claim-structuring step (T018).

Includes the FR-018 branch: an unparseable/invalid structured claim retries
**once** then degrades that claim to ``uncertain`` (never crashes the run).
"""
from __future__ import annotations

import json

import pytest

from council.agents.factchecker import build_claim_structurer, build_factchecker
from council.app import CouncilApp, run_agent_for_output
from council.orchestration.deliberation import structure_claims_with_retry
from council.schemas.claim import Claim, ClaimStatus
from tests._fakes import ScriptedLlm, FACTCHECKER_EVIDENCE, CLAIMS


@pytest.mark.asyncio
async def test_factchecker_gathers_evidence(app: CouncilApp, scripted_models):
    fc = build_factchecker(model=scripted_models["factchecker"], toolset=None)
    session = await app.create_session()
    text, structured = await run_agent_for_output(app, fc, session, "transcript: ...")
    assert FACTCHECKER_EVIDENCE.split("Claim:")[1] in text
    assert structured is None  # no output_schema on a tool-using agent (R6)


@pytest.mark.asyncio
async def test_structurer_produces_typed_claims(app: CouncilApp, scripted_models):
    session = await app.create_session()
    claims = await structure_claims_with_retry(
        app, session, scripted_models["structurer"], FACTCHECKER_EVIDENCE
    )
    assert claims and all(isinstance(c, Claim) for c in claims)
    assert any(c.status is ClaimStatus.supported for c in claims)
    assert any(c.status is ClaimStatus.uncertain for c in claims)


@pytest.mark.asyncio
async def test_structurer_retry_then_degrade_to_uncertain(app: CouncilApp):
    """FR-018: invalid structured output twice → the claim degrades to
    ``uncertain`` rather than crashing."""
    bad = ScriptedLlm(["not json at all", "still not json"])  # two failures
    session = await app.create_session()
    claims = await structure_claims_with_retry(app, session, bad, "Claim: the sky is green.")
    assert claims and all(c.status is ClaimStatus.uncertain for c in claims)


@pytest.mark.asyncio
async def test_structurer_retries_once_then_succeeds(app: CouncilApp):
    """FR-018: first call invalid, second call valid → succeeds (one retry)."""
    flaky = ScriptedLlm(["bad", json.dumps(CLAIMS)])
    session = await app.create_session()
    claims = await structure_claims_with_retry(app, session, flaky, FACTCHECKER_EVIDENCE)
    assert any(c.status is ClaimStatus.supported for c in claims)
