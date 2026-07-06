"""Shared pytest fixtures (T013).

Offline, deterministic, free — no network, no key, no browser.

* ``app`` — a ``CouncilApp`` over a fresh ``InMemorySessionService``.
* ``scripted_models`` / ``fallback_models`` — per-agent ``ScriptedLlm`` sets.
* ``mock_wikipedia`` — patches ``httpx`` in the wikipedia module so the MCP
  server's tools return canned evidence (T015).
* ``web_client`` — a FastAPI ASGI ``TestClient`` over the web app wired with
  scripted models + a mocked fact-check toolset (added once the web layer
  exists; re-exported from here for smoke/E2E tests).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

# Make the tests package importable for `tests._fakes`.
sys.path.insert(0, str(Path(__file__).parent))

from council.app import CouncilApp  # noqa: E402
from tests import _fakes  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate_provider_state():
    """Reset the module-level active provider config around every test (feature 002)."""
    from council import providers

    providers.reset_active()
    yield
    providers.reset_active()


@pytest.fixture()
def app() -> CouncilApp:
    """A fresh in-memory CouncilApp (nothing persists across tests)."""
    return CouncilApp()


@pytest.fixture()
def scripted_models() -> dict:
    return _fakes.build_happy_path_models()


@pytest.fixture()
def fallback_models() -> dict:
    return _fakes.build_fallback_models()


@pytest.fixture()
def canned_roster() -> dict:
    return _fakes.ROSTER


@pytest.fixture()
def canned_claims() -> list:
    return _fakes.CLAIMS


@pytest.fixture()
def canned_verdict() -> dict:
    return _fakes.VERDICT


@pytest.fixture()
def mock_wikipedia(monkeypatch) -> dict:
    """Patch httpx calls in council.tools.factcheck_mcp.wikipedia.

    Returns the canned payloads so tests can assert against them. The MCP
    server's tools call into this module, so patching here isolates the server
    from the live network (T015 smoke test).
    """
    from council.tools.factcheck_mcp import wikipedia as wiki

    class _FakeResponse:
        def __init__(self, payload, status_code=200):
            self._payload = payload
            self.status_code = status_code

        def json(self) -> Any:
            return self._payload

        def raise_for_status(self) -> None:
            return None

    def fake_get(url, *, params=None, timeout=None, **kwargs):
        if "api.php" in url:
            return _FakeResponse({"query": {"search": [
                {"title": r["title"], "snippet": r["snippet"]} for r in _fakes.WIKI_SEARCH["results"]
            ]}})
        if "/summary/" in url:
            return _FakeResponse({
                "title": _fakes.WIKI_SUMMARY["title"],
                "extract": _fakes.WIKI_SUMMARY["extract"],
                "content_urls": {"desktop": {"page": _fakes.WIKI_SUMMARY["url"]}},
            })
        return _FakeResponse({}, status_code=404)

    async def fake_get_async(client, url, **kwargs):
        return fake_get(url, **kwargs)

    # Patch the synchronous httpx.Client.get and async client get used by wikipedia.py.
    monkeypatch.setattr(wiki.httpx.Client, "get", lambda self, url, **kw: fake_get(url, **kw))
    monkeypatch.setattr(
        wiki.httpx.AsyncClient,
        "get",
        lambda self, url, **kw: fake_get(url, **kw),
    )
    return {"search": _fakes.WIKI_SEARCH, "summary": _fakes.WIKI_SUMMARY}


@pytest.fixture()
def web_client(app, scripted_models, monkeypatch):
    """ASGI TestClient over the web app wired with scripted models.

    Injects the scripted fake model and a None fact-check toolset into the
    deliberation loop so the stream runs fully offline. (Added in T032/T020.)
    """
    from fastapi.testclient import TestClient

    from council import providers
    from council.web import server as webserver
    from council.orchestration import deliberation as delib

    # Bind a Google provider so the stream runs offline (feature 002 gate).
    binding = providers.RunBinding(
        provider_id="google", model="gemini-2.5-flash",
        api_key="test-key", base_url=None, litellm_prefix=None,
    )
    monkeypatch.setattr(providers, "bind_run", lambda: binding, raising=True)
    # Inject a model provider that returns our scripted per-agent fakes.
    monkeypatch.setattr(delib, "resolve_models", lambda binding=None: scripted_models, raising=False)
    # Force the fact-checker to skip the real MCP subprocess (offline).
    monkeypatch.setattr(delib, "resolve_factcheck_toolset", lambda: None, raising=False)

    fastapi_app = webserver.create_app(app=app)
    return TestClient(fastapi_app)
