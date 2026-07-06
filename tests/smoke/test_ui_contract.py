"""SSE / static-asset contract tests (feature 002, T014, contracts/web-ui-v2.md).

Offline (FastAPI test client). Every configured stream's first event is run_config;
an unconfigured stream emits exactly one terminal error and closes; the three static
assets serve 200; the served index.html references only same-origin URLs (no CDN);
and the existing 001 SSE vocabulary is still emitted (FR-014).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from council import config, providers
from council.web import server as webserver
from tests.e2e.test_deliberation import _parse_sse


@pytest.fixture()
def clean_client(monkeypatch, tmp_path) -> TestClient:
    """A client with NO provider configured (get-started / unconfigured path)."""
    monkeypatch.setenv("COUNCIL_ENV_FILE", str(tmp_path / "none.env"))
    for var in ("GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                "OPENCODE_API_KEY", "COUNCIL_API_KEY", "COUNCIL_PROVIDER",
                "COUNCIL_MODEL", "COUNCIL_BASE_URL"):
        monkeypatch.delenv(var, raising=False)
    config.reset_cache()
    providers.reset_active()
    return TestClient(webserver.create_app())


def test_static_assets_return_200(web_client):
    for path in ("/", "/static/app.js", "/static/style.css"):
        assert web_client.get(path).status_code == 200


def test_index_references_only_same_origin(web_client):
    html = web_client.get("/").text
    assert "http://" not in html and "https://" not in html  # no CDN / external refs


def test_first_event_is_run_config_and_001_vocabulary_intact(web_client):
    with web_client.stream(
        "GET", "/api/deliberate/stream",
        params={"question": "Should a mid-size city ban gas leaf blowers by 2030?",
                "rounds": 2, "panel": 3},
    ) as r:
        events = list(_parse_sse(r.iter_lines()))

    assert events[0][0] == "run_config"
    assert {"provider", "model", "panel", "rounds"} <= set(events[0][1])
    kinds = [k for k, _ in events]
    for expected in ("recruit", "turn", "tool_call", "synthesize", "verdict"):
        assert expected in kinds  # FR-014: 001 vocabulary unchanged


def test_unconfigured_stream_single_terminal_error(clean_client):
    with clean_client.stream(
        "GET", "/api/deliberate/stream", params={"question": "anything at all"},
    ) as r:
        assert r.status_code == 200
        events = list(_parse_sse(r.iter_lines()))

    assert len(events) == 1
    assert events[0][0] == "error"
    assert events[0][1].get("code") == "unconfigured"
