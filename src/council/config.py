"""Central configuration for The Council.

Loads environment via python-dotenv and exposes the bounds constants from
data-model.md §Configurable bounds. Bounds are defined HERE ONLY — the web
layer clamps query params to them server-side and never trusts page values.
"""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

# Bounds (data-model.md §Configurable bounds). Enforce FR-009 termination.
MIN_PANEL: int = 2
DEFAULT_PANEL: int = 3
MAX_PANEL: int = 4
MAX_ROUNDS: int = 2
FACTCHECK_TIMEOUT_S: float = 8.0
MODEL: str = "gemini-2.5-flash"

# Optional higher-quality model for the Synthesizer (research R4 — MAY use pro).
SYNTH_MODEL: str = "gemini-2.5-flash"

# Web server defaults (contracts/web-ui.md §Launcher).
HOST: str = "127.0.0.1"
DEFAULT_PORT: int = 8400
APP_NAME: str = "council"
USER_ID: str = "local-user"

# Where the repo-root .env lives (one level above the package install).
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _load_env() -> None:
    """Load .env from the repo root (never raises; python-dotenv no-op if absent)."""
    env_path = os.environ.get("COUNCIL_ENV_FILE") or os.path.join(_REPO_ROOT, ".env")
    try:
        load_dotenv(env_path, override=False)
    except Exception:  # pragma: no cover - defensive; never crash on config
        pass


@lru_cache(maxsize=1)
def _settings() -> dict[str, str]:
    """Resolve env once; tests may clear the cache to reload."""
    _load_env()
    return dict(os.environ)


def google_api_key() -> str | None:
    """The Google AI Studio API key, or None if missing/empty."""
    val = _settings().get("GOOGLE_API_KEY", "")
    return val or None


def key_from_env(var: str) -> str | None:
    """Generic env-key reader for any provider (feature 002).

    Trimmed of surrounding whitespace/newlines (spec edge case). Reads through
    the same ``_settings()`` cache as everything else, so ``reset_cache()``
    covers it too. Returns None when unset or empty after trim.
    """
    val = (_settings().get(var, "") or "").strip()
    return val or None


def provider_env_default() -> tuple[str, str | None, str | None] | None:
    """The environment-configured provider default (feature 002).

    Returns ``(COUNCIL_PROVIDER, COUNCIL_MODEL_or_None, COUNCIL_BASE_URL_or_None)``
    when ``COUNCIL_PROVIDER`` is set, else None. Does not itself check that the
    provider's key is present — precedence resolution (providers.py) does that.
    """
    prov = (_settings().get("COUNCIL_PROVIDER", "") or "").strip()
    if not prov:
        return None
    model = (_settings().get("COUNCIL_MODEL", "") or "").strip() or None
    base = (_settings().get("COUNCIL_BASE_URL", "") or "").strip() or None
    return (prov, model, base)


def use_vertex() -> bool:
    """Whether to use the Vertex backend (default FALSE = AI Studio)."""
    return _settings().get("GOOGLE_GENAI_USE_VERTEXAI", "FALSE").strip().upper() == "TRUE"


def reset_cache() -> None:
    """Clear the cached environment (used by tests that mutate env vars)."""
    _settings.cache_clear()
