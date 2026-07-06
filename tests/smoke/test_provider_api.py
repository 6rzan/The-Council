"""Smoke tests for the provider config API (feature 002, T007).

contracts/providers-api.md: GET /api/providers shape + no key leakage;
POST /api/providers/active happy path + every error code; the probe distinguishes
invalid_model from invalid_key. Offline — the live probe is injected as a fake.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from council import config, providers
from council.web import server as webserver


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


@pytest.fixture()
def client(clean_env) -> TestClient:
    return TestClient(webserver.create_app())


async def _ok_probe(binding):
    return None


# ---------- GET /api/providers ----------

def test_get_providers_shape_and_no_key_leak(client, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "env-SECRET-key-xyz")
    config.reset_cache()
    r = client.get("/api/providers")
    assert r.status_code == 200
    body = r.json()

    assert {p["id"] for p in body["providers"]} == {"google", "openai", "anthropic", "opencode", "custom"}
    openai = next(p for p in body["providers"] if p["id"] == "openai")
    assert openai["configured"] is True and openai["key_source"] == "env"
    assert set(openai) >= {"id", "display_name", "default_model", "curated_models",
                           "allows_custom_base_url", "requires_key", "configured", "key_source"}
    assert body["configured_any"] is True
    # A configured key value must never appear in the response (FR-006/SC-004).
    assert "env-SECRET-key-xyz" not in r.text


def test_get_providers_unconfigured(client):
    body = client.get("/api/providers").json()
    assert body["active"] is None
    assert body["configured_any"] is False


# ---------- POST /api/providers/active ----------

def test_post_active_happy_path(client, monkeypatch):
    monkeypatch.setattr(providers, "probe", _ok_probe)
    r = client.post("/api/providers/active",
                    json={"provider": "openai", "model": "gpt-4o", "api_key": "sk-LIVE-123"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["active"] == {"provider": "openai", "model": "gpt-4o", "source": "ui"}
    assert "sk-LIVE-123" not in r.text  # posted key never echoed back


def test_post_unknown_provider(client):
    r = client.post("/api/providers/active", json={"provider": "nope"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "unknown_provider"


def test_post_missing_key(client):
    r = client.post("/api/providers/active", json={"provider": "openai", "model": "gpt-4o"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "missing_key"


def test_post_invalid_base_url(client):
    r = client.post("/api/providers/active",
                    json={"provider": "openai", "model": "gpt-4o", "api_key": "x", "base_url": "http://nope"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "invalid_base_url"


def test_post_invalid_key_from_probe(client, monkeypatch):
    async def bad(binding):
        raise providers.ProviderError("invalid_key", "openai", "rejected", "recheck the key")
    monkeypatch.setattr(providers, "probe", bad)
    r = client.post("/api/providers/active",
                    json={"provider": "openai", "model": "gpt-4o", "api_key": "sk-bad"})
    assert r.status_code == 400
    err = r.json()["error"]
    assert err["code"] == "invalid_key" and err["message"] and err["hint"]


def test_probe_distinguishes_invalid_model_from_invalid_key(client, monkeypatch):
    async def picky(binding):
        if binding.model == "no-such-model":
            raise providers.ProviderError("invalid_model", "openai", "bad model", "pick another")
        return None
    monkeypatch.setattr(providers, "probe", picky)

    r_bad = client.post("/api/providers/active",
                        json={"provider": "openai", "model": "no-such-model", "api_key": "sk-x"})
    assert r_bad.status_code == 400 and r_bad.json()["error"]["code"] == "invalid_model"

    r_ok = client.post("/api/providers/active",
                       json={"provider": "openai", "model": "gpt-4o", "api_key": "sk-x"})
    assert r_ok.status_code == 200
