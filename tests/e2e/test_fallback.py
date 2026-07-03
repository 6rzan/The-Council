"""Fallback-roster E2E (T021, FR-016).

Recruitment fails (invalid roster) → a ``fallback`` SSE event, a deterministic
roster with ``source=fallback``, and the run still completes to ``verdict``.
"""
from __future__ import annotations

from council.schemas.verdict import VerdictBrief
from tests.e2e.test_deliberation import _parse_sse


def test_fallback_roster_completes_to_verdict(web_client, fallback_models, monkeypatch):
    # Re-point the web's model provider at the fallback script set.
    from council.orchestration import deliberation as delib
    monkeypatch.setattr(delib, "resolve_models", lambda: fallback_models)

    with web_client.stream(
        "GET", "/api/deliberate/stream",
        params={"question": "Any question at all", "rounds": 2, "panel": 3},
    ) as r:
        assert r.status_code == 200
        events = list(_parse_sse(r.iter_lines()))

    kinds = [k for k, _ in events]
    assert "fallback" in kinds
    assert kinds[-1] == "verdict"

    fallback_data = [d for k, d in events if k == "fallback"][0]
    assert fallback_data["roster"]["source"] == "fallback"
    assert any(p["is_challenger"] for p in fallback_data["roster"]["panelists"])

    verdict = VerdictBrief.model_validate(events[-1][1])
    assert verdict.roster.source.value == "fallback"
