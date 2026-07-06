"""E2E: a full deliberation on a non-default provider, fully offline (feature 002, T008).

POST an OpenAI config (fake-validated), then stream a full deliberation with a fake
model injected at the ``providers.resolve_model`` factory seam. Asserts the first SSE
event is ``run_config`` naming OpenAI, a terminal ``verdict`` arrives, and no event ever
switches to a different provider (FR-008/FR-016 — never a silent provider switch).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from council import config, providers
from council.app import CouncilApp
from council.orchestration import deliberation as delib
from council.web import server as webserver
from tests import _fakes
from tests._fakes import ScriptedLlm
from tests.e2e.test_deliberation import _parse_sse


@pytest.fixture()
def clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("COUNCIL_ENV_FILE", str(tmp_path / "nonexistent.env"))
    for var in ("GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                "OPENCODE_API_KEY", "COUNCIL_API_KEY", "COUNCIL_PROVIDER",
                "COUNCIL_MODEL", "COUNCIL_BASE_URL"):
        monkeypatch.delenv(var, raising=False)
    config.reset_cache()
    providers.reset_active()
    yield
    config.reset_cache()


async def _ok_probe(binding):
    return None


def test_full_deliberation_on_openai_offline(clean_env, monkeypatch):
    # One shared scripted model: the pipeline calls it in a deterministic order
    # (moderator -> 3x2 panelists -> factchecker -> structurer -> synthesizer = 10).
    shared = ScriptedLlm([
        _fakes.ROSTER, *_fakes.PANELIST_TURNS,
        _fakes.FACTCHECKER_EVIDENCE, _fakes.CLAIMS, _fakes.VERDICT,
    ])
    monkeypatch.setattr(providers, "probe", _ok_probe)
    monkeypatch.setattr(providers, "resolve_model", lambda binding: shared)
    monkeypatch.setattr(delib, "resolve_factcheck_toolset", lambda: None, raising=False)

    client = TestClient(webserver.create_app(app=CouncilApp()))

    # 1. Configure OpenAI in the UI (no Google key anywhere).
    r = client.post("/api/providers/active",
                    json={"provider": "openai", "model": "gpt-4o", "api_key": "sk-dummy"})
    assert r.status_code == 200 and r.json()["active"]["provider"] == "openai"

    # 2. Run one full deliberation on that provider.
    with client.stream(
        "GET", "/api/deliberate/stream",
        params={"question": "Should a mid-size city ban gas leaf blowers by 2030?",
                "rounds": 2, "panel": 3},
    ) as resp:
        assert resp.status_code == 200
        events = list(_parse_sse(resp.iter_lines()))

    # First event is run_config naming OpenAI (FR-011).
    assert events[0][0] == "run_config"
    assert events[0][1]["provider"] == "openai"
    assert events[0][1]["model"] == "gpt-4o"

    kinds = [k for k, _ in events]
    assert kinds[-1] == "verdict"           # terminal verdict arrived
    assert "error" not in kinds

    # FR-016: exactly one run_config, and no event ever names a different provider.
    assert kinds.count("run_config") == 1
    for k, d in events:
        if k == "run_config":
            assert d["provider"] == "openai"
