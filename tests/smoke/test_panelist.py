"""Smoke test for the Panelist agent (T017).

Given a fixed persona + transcript, returns a non-empty argument and sets
``references_prior`` when it rebuts a named prior turn (the A2A signal).
"""
from __future__ import annotations

import pytest

from council.agents.panelist import build_panelist
from council.app import CouncilApp, run_agent_for_output
from council.schemas.roster import Panelist
from council.schemas.trace import PanelistTurn


def _persona(challenger: bool = False) -> Panelist:
    return Panelist(
        name="Vex the Contrarian" if challenger else "Dr. Ada Economic",
        expertise="ratepayer advocate" if challenger else "energy-systems economist",
        stance="affordability skeptic" if challenger else "net-positive economics",
        recruitment_reason="challenges the consensus",
        is_challenger=challenger,
    )


@pytest.mark.asyncio
async def test_panelist_returns_nonempty_argument(app: CouncilApp, scripted_models):
    agent = build_panelist(model=scripted_models["panelist"], persona=_persona())
    session = await app.create_session()
    transcript_text = "Round 1 so far: (none)"
    _text, structured = await run_agent_for_output(app, agent, session, transcript_text)
    turn = PanelistTurn.model_validate(structured)
    assert turn.content.strip()


@pytest.mark.asyncio
async def test_panelist_marks_rebuttal(app: CouncilApp, scripted_models):
    """The scripted model returns references_prior=True for the challenger's
    rebuttal turn (A2A evidence, spec US1 acceptance #4)."""
    agent = build_panelist(model=scripted_models["panelist"], persona=_persona(challenger=True))
    session = await app.create_session()
    # advance the shared scripted model to a rebuttal response (index 2 = challenger r1)
    scripted_models["panelist"]._cursor = 2
    _text, structured = await run_agent_for_output(
        app, agent, session, "Prior: Dr. Ada said costs are favorable."
    )
    turn = PanelistTurn.model_validate(structured)
    assert turn.references_prior is True
