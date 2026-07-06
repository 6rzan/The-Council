"""Smoke tests for the provider core (feature 002, T006 / FR-001..FR-007, FR-016).

Offline, no key, no network. Covers the registry, precedence resolution, last-write-
wins, whitespace trimming (spec edge case), credential masking (FR-006/SC-004), and
each structural ProviderError code from the data-model.md validation table.
"""
from __future__ import annotations

import json

import pytest

from council import config, providers


@pytest.fixture()
def clean_env(monkeypatch, tmp_path):
    """No .env, no provider env vars — a blank slate for precedence tests."""
    monkeypatch.setenv("COUNCIL_ENV_FILE", str(tmp_path / "nonexistent.env"))
    for var in ("GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                "OPENCODE_API_KEY", "COUNCIL_API_KEY", "COUNCIL_PROVIDER",
                "COUNCIL_MODEL", "COUNCIL_BASE_URL"):
        monkeypatch.delenv(var, raising=False)
    config.reset_cache()
    providers.reset_active()
    yield
    config.reset_cache()


# ---------- registry ----------

def test_registry_has_five_providers_with_required_fields():
    assert set(providers.PROVIDERS) == {"google", "openai", "anthropic", "opencode", "custom"}
    for spec in providers.PROVIDERS.values():
        assert spec.id and spec.display_name and spec.key_env_var
        assert isinstance(spec.curated_models, tuple)
        assert isinstance(spec.allows_custom_base_url, bool)
    # Google keeps the plain-string path; others go through a LiteLlm prefix.
    assert providers.PROVIDERS["google"].litellm_prefix is None
    assert providers.PROVIDERS["openai"].litellm_prefix == "openai"
    assert providers.PROVIDERS["anthropic"].litellm_prefix == "anthropic"
    assert providers.PROVIDERS["custom"].allows_custom_base_url is True


# ---------- precedence (UI -> COUNCIL_PROVIDER -> GOOGLE_API_KEY -> None) ----------

def test_precedence_unconfigured_is_none(clean_env):
    assert providers.resolve_effective() is None


def test_precedence_google_env(clean_env, monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "g-key")
    config.reset_cache()
    eff = providers.resolve_effective()
    assert eff is not None and eff.provider_id == "google" and eff.source == "env"
    assert eff.model == "gemini-2.5-flash"


def test_precedence_council_provider_env_beats_google(clean_env, monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "g-key")
    monkeypatch.setenv("COUNCIL_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "o-key")
    monkeypatch.setenv("COUNCIL_MODEL", "gpt-4o-mini")
    config.reset_cache()
    eff = providers.resolve_effective()
    assert eff.provider_id == "openai" and eff.source == "env" and eff.model == "gpt-4o-mini"


def test_precedence_ui_beats_env(clean_env, monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "g-key")
    config.reset_cache()
    providers.set_active(providers.ActiveProviderConfig(
        provider_id="anthropic", model="claude-sonnet-4-5", api_key="a-key"))
    eff = providers.resolve_effective()
    assert eff.provider_id == "anthropic" and eff.source == "ui"


def test_council_provider_without_key_falls_through(clean_env, monkeypatch):
    # COUNCIL_PROVIDER names openai but no OPENAI_API_KEY -> skip to google.
    monkeypatch.setenv("COUNCIL_PROVIDER", "openai")
    monkeypatch.setenv("GOOGLE_API_KEY", "g-key")
    config.reset_cache()
    assert providers.resolve_effective().provider_id == "google"


def test_last_write_wins():
    providers.set_active(providers.ActiveProviderConfig(provider_id="openai", model="gpt-4o", api_key="x"))
    providers.set_active(providers.ActiveProviderConfig(provider_id="anthropic", model="claude-sonnet-4-5", api_key="y"))
    assert providers.get_active().provider_id == "anthropic"


# ---------- trimming (spec edge case: pasted key with whitespace/newlines) ----------

def test_key_and_model_are_trimmed():
    cfg = providers.ActiveProviderConfig(
        provider_id="openai", model="  gpt-4o\n", api_key="  sk-abc123 \n")
    assert cfg.model == "gpt-4o"
    assert cfg.api_key == "sk-abc123"


# ---------- masking (FR-006 / SC-004): key never in any serialization ----------

def test_key_never_appears_in_serialization():
    secret = "sk-SUPER-SECRET-VALUE-123"
    cfg = providers.ActiveProviderConfig(provider_id="openai", model="gpt-4o", api_key=secret)
    assert secret not in repr(cfg)
    assert secret not in str(cfg)
    assert secret not in json.dumps(cfg.model_dump(mode="json"))
    assert secret not in cfg.model_dump_json()
    assert "api_key" not in cfg.model_dump()


# ---------- structural ProviderError codes (data-model.md validation table) ----------

def test_unknown_provider(clean_env):
    with pytest.raises(providers.ProviderError) as e:
        providers.build_config("not-a-provider")
    assert e.value.code == "unknown_provider"


def test_missing_key(clean_env):
    with pytest.raises(providers.ProviderError) as e:
        providers.build_config("openai", model="gpt-4o")
    assert e.value.code == "missing_key"


def test_invalid_model(clean_env, monkeypatch):
    monkeypatch.setenv("OPENCODE_API_KEY", "x")
    config.reset_cache()
    with pytest.raises(providers.ProviderError) as e:
        providers.build_config("opencode", model="   ")  # opencode has no default model
    assert e.value.code == "invalid_model"


def test_invalid_base_url_not_allowed(clean_env):
    with pytest.raises(providers.ProviderError) as e:
        providers.build_config("openai", model="gpt-4o", api_key="x", base_url="http://oops")
    assert e.value.code == "invalid_base_url"


def test_invalid_base_url_missing_for_custom(clean_env):
    with pytest.raises(providers.ProviderError) as e:
        providers.build_config("custom", model="local-model", api_key="x")
    assert e.value.code == "invalid_base_url"


def test_invalid_base_url_malformed(clean_env):
    with pytest.raises(providers.ProviderError) as e:
        providers.build_config("custom", model="local-model", api_key="x", base_url="not a url")
    assert e.value.code == "invalid_base_url"


def test_every_structural_error_carries_message_and_hint(clean_env):
    with pytest.raises(providers.ProviderError) as e:
        providers.build_config("openai", model="gpt-4o")
    assert e.value.message and e.value.hint  # FR-012: cause + next step
