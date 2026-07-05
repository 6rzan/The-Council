"""Multi-provider registry, active config, precedence, and model factory (feature 002).

Verified import path (T001): ``from google.adk.models.lite_llm import LiteLlm``
resolves under google-adk==2.3.0 (imported lazily below so the module loads even
before litellm is installed). Google keeps the plain-string model path — that code
path is byte-identical to before (FR-004/FR-014); every other provider routes
through ADK's own ``LiteLlm`` wrapper.

Everything here is in-memory only (constitution Principle VII): credentials live
at most for the process lifetime, are never written to disk/logs/traces, and are
masked in every serialization (FR-006, SC-004).

Contracts: specs/002-multi-provider-ui/data-model.md and contracts/providers-api.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

from council.config import (
    MODEL as GOOGLE_DEFAULT_MODEL,
    google_api_key,
    key_from_env,
    provider_env_default,
)

# Roles that receive the resolved model — every one runs on the user's selection
# (FR-008). Kept here so deliberation.py and tests share one source of truth.
ROLES = ("moderator", "panelist", "factchecker", "structurer", "synthesizer")


# ---------- ProviderSpec registry (static data — research R3) ----------

@dataclass(frozen=True)
class ProviderSpec:
    """One row of the provider registry (frozen data, not user state)."""

    id: str
    display_name: str
    key_env_var: str
    litellm_prefix: str | None  # None => plain Gemini string path
    default_base_url: str | None
    allows_custom_base_url: bool
    default_model: str
    curated_models: tuple[str, ...]
    requires_key: bool = True


PROVIDERS: dict[str, ProviderSpec] = {
    "google": ProviderSpec(
        id="google", display_name="Google Gemini", key_env_var="GOOGLE_API_KEY",
        litellm_prefix=None, default_base_url=None, allows_custom_base_url=False,
        default_model="gemini-2.5-flash",
        curated_models=("gemini-2.5-flash", "gemini-2.5-pro"),
    ),
    "openai": ProviderSpec(
        id="openai", display_name="OpenAI", key_env_var="OPENAI_API_KEY",
        litellm_prefix="openai", default_base_url=None, allows_custom_base_url=False,
        default_model="gpt-4o", curated_models=("gpt-4o", "gpt-4o-mini"),
    ),
    "anthropic": ProviderSpec(
        id="anthropic", display_name="Anthropic", key_env_var="ANTHROPIC_API_KEY",
        litellm_prefix="anthropic", default_base_url=None, allows_custom_base_url=False,
        default_model="claude-sonnet-4-5",
        curated_models=("claude-sonnet-4-5", "claude-haiku-4-5"),
    ),
    "opencode": ProviderSpec(
        id="opencode", display_name="OpenCode Zen", key_env_var="OPENCODE_API_KEY",
        litellm_prefix="openai", default_base_url="https://opencode.ai/zen/v1",
        allows_custom_base_url=False, default_model="",  # gateway catalog shifts → free-text
        curated_models=(),
    ),
    "custom": ProviderSpec(
        id="custom", display_name="Custom (OpenAI-compatible)", key_env_var="COUNCIL_API_KEY",
        litellm_prefix="openai", default_base_url=None, allows_custom_base_url=True,
        default_model="", curated_models=(),
    ),
}


# ---------- Typed provider error (FR-007/FR-012) ----------

_ERROR_CODES = frozenset({
    "unknown_provider", "missing_key", "invalid_key",
    "invalid_model", "invalid_base_url", "unreachable_endpoint",
})


class ProviderError(Exception):
    """A provider-specific, human-readable failure carrying a recovery hint."""

    def __init__(self, code: str, provider: str, message: str, hint: str) -> None:
        assert code in _ERROR_CODES, f"unknown error code {code!r}"
        self.code = code
        self.provider = provider
        self.message = message
        self.hint = hint
        super().__init__(message)

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "provider": self.provider,
                "message": self.message, "hint": self.hint}


# ---------- ActiveProviderConfig (the one server-wide selection) ----------

class ActiveProviderConfig(BaseModel):
    """Runtime state — the single active selection. Credential is memory-only.

    ``api_key`` is excluded from every serialization (``model_dump``/JSON) and
    masked in ``repr``/``str`` (FR-006). Status views expose only ``configured``
    + ``source``, never key material.
    """

    provider_id: str
    model: str
    api_key: str | None = Field(default=None, exclude=True, repr=False)
    base_url: str | None = None
    source: str = "ui"
    set_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("api_key", "base_url", "model", mode="before")
    @classmethod
    def _trim(cls, v: Any) -> Any:
        # Trim surrounding whitespace/newlines on intake (spec edge case).
        return v.strip() if isinstance(v, str) else v

    def __repr__(self) -> str:  # never leak the key
        key = "***" if self.api_key else None
        return (f"ActiveProviderConfig(provider_id={self.provider_id!r}, "
                f"model={self.model!r}, api_key={key!r}, base_url={self.base_url!r}, "
                f"source={self.source!r})")

    __str__ = __repr__


# ---------- Module-level holder (last write wins — clarification 2026-07-03) ----------

_ACTIVE: ActiveProviderConfig | None = None


def set_active(cfg: ActiveProviderConfig) -> None:
    """Store the active config (last write wins)."""
    global _ACTIVE
    _ACTIVE = cfg


def get_active() -> ActiveProviderConfig | None:
    return _ACTIVE


def reset_active() -> None:
    """Clear the active config (process start / tests)."""
    global _ACTIVE
    _ACTIVE = None


# ---------- Precedence resolution (data-model.md) ----------

def resolve_effective() -> ActiveProviderConfig | None:
    """Effective config via precedence: UI -> COUNCIL_PROVIDER env -> GOOGLE_API_KEY -> None."""
    # 1. UI: a POST since process start.
    if _ACTIVE is not None:
        return _ACTIVE
    # 2. Env: COUNCIL_PROVIDER names a registry id whose key env var is set.
    envd = provider_env_default()
    if envd is not None:
        pid, model, base = envd
        spec = PROVIDERS.get(pid)
        if spec is not None:
            has_key = (not spec.requires_key) or bool(key_from_env(spec.key_env_var))
            base_ok = (not spec.allows_custom_base_url) or bool(base)
            if has_key and base_ok:
                return ActiveProviderConfig(
                    provider_id=pid,
                    model=model or spec.default_model or GOOGLE_DEFAULT_MODEL,
                    api_key=None, base_url=base or spec.default_base_url, source="env",
                )
    # 3. Env-Google: GOOGLE_API_KEY set -> the existing default, unchanged.
    if google_api_key():
        return ActiveProviderConfig(
            provider_id="google", model=GOOGLE_DEFAULT_MODEL, api_key=None, source="env",
        )
    # 4. Unconfigured — no run possible; UI shows guided get-started.
    return None


def configured_providers() -> dict[str, str | None]:
    """Map provider id -> key_source ('ui' | 'env' | None) for GET /api/providers."""
    active = _ACTIVE
    out: dict[str, str | None] = {}
    for pid, spec in PROVIDERS.items():
        if active is not None and active.provider_id == pid and active.api_key:
            out[pid] = "ui"
        elif key_from_env(spec.key_env_var):
            out[pid] = "env"
        else:
            out[pid] = None
    return out


# ---------- RunBinding (immutable per-run snapshot — research R4) ----------

@dataclass(frozen=True)
class RunBinding:
    """Resolved once at stream start; mid-run changes never affect it (FR-016)."""

    provider_id: str
    model: str
    api_key: str | None
    base_url: str | None
    litellm_prefix: str | None


def binding_from_config(cfg: ActiveProviderConfig) -> RunBinding:
    """Resolve an ActiveProviderConfig into a RunBinding (fills key/base from env)."""
    spec = PROVIDERS[cfg.provider_id]
    key = cfg.api_key or key_from_env(spec.key_env_var)
    base = cfg.base_url or spec.default_base_url
    return RunBinding(cfg.provider_id, cfg.model, key, base, spec.litellm_prefix)


def bind_run() -> RunBinding | None:
    """Snapshot the effective config into an immutable binding, or None if unconfigured."""
    cfg = resolve_effective()
    return binding_from_config(cfg) if cfg is not None else None


def resolve_model(binding: RunBinding) -> Any:
    """Factory: Google -> plain model string (byte-identical); others -> LiteLlm."""
    if binding.litellm_prefix is None:  # google
        return binding.model
    from google.adk.models.lite_llm import LiteLlm  # lazy (research R1)

    kwargs: dict[str, Any] = {"model": f"{binding.litellm_prefix}/{binding.model}"}
    if binding.api_key:
        kwargs["api_key"] = binding.api_key
    if binding.base_url:
        kwargs["api_base"] = binding.base_url
    return LiteLlm(**kwargs)


# ---------- Structural validation (trust boundary — POST /api/providers/active) ----------

def _is_http_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except Exception:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def build_config(
    provider: str,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> ActiveProviderConfig:
    """Validate an untrusted request into an ActiveProviderConfig (raises ProviderError).

    Structural checks only (no network). The live probe is a separate step.
    """
    if provider not in PROVIDERS:
        raise ProviderError("unknown_provider", provider,
                            f"Unknown provider {provider!r}.",
                            "Choose one of: " + ", ".join(PROVIDERS))
    spec = PROVIDERS[provider]

    model = (model or "").strip() or spec.default_model
    if not model:
        raise ProviderError("invalid_model", provider,
                            "No model was specified for this provider.",
                            "Pick a model from the list or type one the provider accepts.")

    base = (base_url or "").strip() or None
    if base is not None and not spec.allows_custom_base_url and spec.default_base_url is None:
        raise ProviderError("invalid_base_url", provider,
                            f"{spec.display_name} does not accept a custom base URL.",
                            "Remove the base URL, or pick the Custom provider for a custom endpoint.")
    if spec.allows_custom_base_url and not base:
        raise ProviderError("invalid_base_url", provider,
                            "A custom OpenAI-compatible endpoint needs a base URL.",
                            "Enter the endpoint URL, e.g. http://localhost:11434/v1")
    if base is not None and not _is_http_url(base):
        raise ProviderError("invalid_base_url", provider,
                            f"{base!r} is not a valid http(s) URL.",
                            "Enter a full URL beginning with http:// or https://")

    key = (api_key or "").strip() or None
    effective_key = key or key_from_env(spec.key_env_var)
    if spec.requires_key and not effective_key:
        raise ProviderError("missing_key", provider,
                            f"No API key is configured for {spec.display_name}.",
                            f"Paste a key in Settings, or set {spec.key_env_var} in your .env")

    return ActiveProviderConfig(
        provider_id=provider, model=model, api_key=key,
        base_url=base or spec.default_base_url, source="ui",
    )


# ---------- Credential validation probe (research R5 — injectable for tests) ----------

def _classify_probe_error(binding: RunBinding, exc: Exception) -> ProviderError:
    msg = str(exc).lower()
    spec = PROVIDERS[binding.provider_id]
    if any(m in msg for m in ("auth", "401", "403", "api key", "unauthorized", "permission")):
        return ProviderError("invalid_key", binding.provider_id,
                             f"{spec.display_name} rejected the API key.",
                             "Check the key and paste it again.")
    if any(m in msg for m in ("model", "404", "not found", "does not exist", "unknown model")):
        return ProviderError("invalid_model", binding.provider_id,
                             f"The model {binding.model!r} was not accepted by {spec.display_name}.",
                             "Pick a different model or check the exact model name.")
    if any(m in msg for m in ("connect", "timeout", "timed out", "unreachable", "refused", "dns")):
        return ProviderError("unreachable_endpoint", binding.provider_id,
                             "The provider endpoint could not be reached.",
                             "Check the base URL and your network, then try again.")
    return ProviderError("invalid_key", binding.provider_id,
                         f"{spec.display_name} could not validate the credentials ({type(exc).__name__}).",
                         "Verify the key, model, and endpoint, then try again.")


async def _default_probe(binding: RunBinding) -> None:
    """One minimal live completion; raises ProviderError on failure (~10 s timeout).

    Injectable: tests replace the module attribute ``probe`` with a fake. Google
    keeps a presence-only check here (a genai round-trip is heavier than warranted
    at save time); deep validation happens on the first real run.
    """
    if binding.litellm_prefix is None:  # google
        if not binding.api_key:
            raise ProviderError("missing_key", binding.provider_id,
                                "No Google API key is configured.",
                                "Paste a key in Settings, or set GOOGLE_API_KEY in your .env")
        return
    import litellm  # lazy

    try:
        await litellm.acompletion(
            model=f"{binding.litellm_prefix}/{binding.model}",
            api_key=binding.api_key, api_base=binding.base_url,
            messages=[{"role": "user", "content": "ping"}], max_tokens=1, timeout=10,
        )
    except ProviderError:
        raise
    except Exception as exc:  # noqa: BLE001 — classify any provider/network failure
        raise _classify_probe_error(binding, exc)


# Module attribute so tests can inject a fake probe (research R5).
probe: Callable[[RunBinding], Awaitable[None]] = _default_probe


async def validate_and_probe(binding: RunBinding) -> None:
    """Run the (injectable) probe for a binding; raises ProviderError on failure."""
    await probe(binding)
