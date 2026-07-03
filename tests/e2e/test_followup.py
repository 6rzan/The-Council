"""US2 follow-up continuity E2E (T038, FR-011/FR-012).

A follow-up question in the SAME session builds on prior deliberation: prior
questions/verdicts accumulate in-memory, prior context is threaded into the
Moderator recruit and Synthesizer prompts, and a fresh session starts empty
(nothing persists beyond the session — FR-012).
"""
from __future__ import annotations

import pytest

from council.app import CouncilApp
from council.orchestration import deliberation as delib
from council.orchestration import session_state
from council.schemas.session import SessionContext
from tests import _fakes


@pytest.mark.asyncio
async def test_follow_up_threads_prior_context(app):
    """Two runs on one session: the 2nd recruit + synthesis carry prior context."""
    models = _fakes.build_followup_models()
    session = await app.create_session()

    # --- first deliberation ---
    evs1 = [e async for e in delib.run_deliberation(
        app, session, "Should a mid-size city ban gas leaf blowers by 2030?",
        rounds=1, panel=3, models=models, toolset=None)]
    verdict1 = evs1[-1]
    assert verdict1.kind == "verdict"

    ctx = session_state.get_session_context(session)
    assert isinstance(ctx, SessionContext)
    assert len(ctx.prior_questions) == 1
    assert len(ctx.prior_verdicts) == 1

    # --- follow-up in the SAME session ---
    evs2 = [e async for e in delib.run_deliberation(
        app, session, "Given the phased ban, how should subsidies target small operators?",
        rounds=1, panel=3, models=models, toolset=None)]
    verdict2 = evs2[-1]
    assert verdict2.kind == "verdict"
    # the scripted follow-up verdict references the prior deliberation
    assert "prior phased-ban verdict" in verdict2.data["recommendation"]

    ctx = session_state.get_session_context(session)
    assert len(ctx.prior_questions) == 2  # FR-011: accumulates
    assert len(ctx.prior_verdicts) == 2

    # --- T038: prior context actually reached the agents' prompts ---
    # The moderator's 2nd recruit call carried the prior-context block.
    mod_calls = models["moderator"]._calls
    assert len(mod_calls) >= 2
    assert any("PRIOR SESSION CONTEXT" in str(c.contents) for c in mod_calls)
    # The synthesizer's 2nd call payload carried prior_context with the prior recommendation.
    synth_calls = models["synthesizer"]._calls
    assert len(synth_calls) >= 2
    assert "prior_context" in str(synth_calls[1].contents)
    assert "phased ban with subsidies" in str(synth_calls[1].contents).lower()


@pytest.mark.asyncio
async def test_no_persistence_beyond_session(app):
    """FR-012: a fresh session starts with empty prior context (in-memory only)."""
    session = await app.create_session()
    ctx = session_state.get_session_context(session)
    assert ctx.prior_questions == []
    assert ctx.prior_verdicts == []
