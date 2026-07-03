"""Smoke test for the Moderator recruit step (T016).

Valid model → a schema-valid PanelRoster with ≥1 challenger; the deterministic
fallback roster is also valid. The retry→fallback *integration* is exercised in
tests/e2e/test_fallback.py (FR-016/FR-018).
"""
from __future__ import annotations

import pytest

from council.agents.moderator import build_moderator
from council.app import CouncilApp, run_agent_for_output
from council.orchestration.fallback import fallback_roster
from council.schemas.roster import PanelRoster


@pytest.mark.asyncio
async def test_moderator_recruits_valid_roster(app: CouncilApp, scripted_models):
    moderator = build_moderator(model=scripted_models["moderator"])
    session = await app.create_session()
    _text, structured = await run_agent_for_output(app, moderator, session, "Should a city ban gas leaf blowers by 2030?")
    roster = PanelRoster.model_validate(structured)
    assert 2 <= len(roster.panelists) <= 4
    assert any(p.is_challenger for p in roster.panelists)
    assert all(p.recruitment_reason for p in roster.panelists)


@pytest.mark.asyncio
async def test_moderator_invalid_roster_triggers_fallback(app: CouncilApp, fallback_models):
    """When the model returns an invalid roster, recruit_with_fallback retries
    once then substitutes the deterministic fallback (FR-016/FR-018)."""
    from council.orchestration.deliberation import recruit_with_fallback

    session = await app.create_session()
    roster, source, events = await recruit_with_fallback(
        app, session, fallback_models["moderator"], "any question", panel_size=3
    )
    assert source.value == "fallback"
    assert any(p.is_challenger for p in roster.panelists)
    # a fallback trace event must be recorded
    assert any(e.kind == "fallback" for e in events.events)


def test_fallback_roster_is_valid():
    r = fallback_roster()
    assert isinstance(r, PanelRoster)
    assert r.source.value == "fallback"
    assert any(p.is_challenger for p in r.panelists)
    assert 2 <= len(r.panelists) <= 4
