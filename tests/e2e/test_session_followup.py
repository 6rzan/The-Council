"""US2 follow-up E2E through the web API (T034, FR-011/FR-012).

Two ``GET /api/deliberate/stream`` calls sharing a ``session_id``: the second
verdict references the prior deliberation. A fresh app instance has no memory of
the first session (nothing persists beyond the session — FR-012).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from council.orchestration import deliberation as delib
from council.web import server as webserver
from tests import _fakes
from tests.e2e.test_deliberation import _parse_sse


def _client_with(app, models, monkeypatch) -> TestClient:
    """A TestClient wired with the given scripted models + no MCP toolset."""
    monkeypatch.setattr(delib, "resolve_models", lambda: models, raising=False)
    monkeypatch.setattr(delib, "resolve_factcheck_toolset", lambda: None, raising=False)
    return TestClient(webserver.create_app(app=app))


def _stream(client: TestClient, question: str, session_id: str):
    with client.stream(
        "GET", "/api/deliberate/stream",
        params={"question": question, "rounds": 1, "panel": 3, "session_id": session_id},
    ) as r:
        assert r.status_code == 200
        return list(_parse_sse(r.iter_lines()))


def test_two_streams_share_session_second_references_prior(app, monkeypatch):
    """FR-011: a follow-up in the same session references the prior verdict."""
    models = _fakes.build_followup_models()
    client = _client_with(app, models, monkeypatch)
    sid = "shared-session-1"

    e1 = _stream(client, "Should a mid-size city ban gas leaf blowers by 2030?", sid)
    assert e1[-1][0] == "verdict"

    e2 = _stream(client, "Given the ban, how should subsidies target small operators?", sid)
    assert e2[-1][0] == "verdict"
    # the scripted follow-up verdict references the prior deliberation
    assert "prior phased-ban verdict" in e2[-1][1]["recommendation"]
    # the second run still recruited a panel (it did not start cold silently)
    assert any(k == "recruit" for k, _ in e2)


def test_fresh_app_has_no_memory(app, monkeypatch):
    """FR-012: a brand-new session on a fresh app has no prior context."""
    models = _fakes.build_followup_models()
    client = _client_with(app, models, monkeypatch)
    e = _stream(client, "Is nuclear power net-positive for 2035 climate goals?", "brand-new-session")
    assert e[-1][0] == "verdict"
    # no guardrail/refusal/clarify leaked from a non-existent prior session
    assert "refusal" not in [k for k, _ in e]
