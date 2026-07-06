# Data Model: Multi-Provider Model Choice & Live Deliberation UI

**Feature**: 002-multi-provider-ui | **Date**: 2026-07-05 | **Plan**: [plan.md](plan.md)

All entities are in-memory only (Principle VII). Nothing here touches disk. Pydantic v2
models except where noted; module: `src/council/providers.py` unless stated otherwise.

## ProviderSpec (static registry entry — frozen data, not user state)

| Field | Type | Notes |
|-------|------|-------|
| `id` | str | registry key: `google` \| `openai` \| `anthropic` \| `opencode` \| `custom` |
| `display_name` | str | shown in UI |
| `key_env_var` | str | env var read as the environment-configured credential |
| `litellm_prefix` | str \| None | `None` for `google` (plain string path); `"openai"` / `"anthropic"` otherwise |
| `default_base_url` | str \| None | preset for `opencode`; `None` elsewhere |
| `allows_custom_base_url` | bool | `True` only for `custom` |
| `default_model` | str | preselected model |
| `curated_models` | list[str] | short list; free-text override always allowed (FR-005) |

Registry: `PROVIDERS: dict[str, ProviderSpec]` — the single source for the settings UI,
resolution, and validation (research R3).

## ActiveProviderConfig (runtime state — the one server-wide selection)

| Field | Type | Notes |
|-------|------|-------|
| `provider_id` | str | must be a `PROVIDERS` key |
| `model` | str | curated or free-text, non-empty after trim |
| `api_key` | str \| None | **memory only**; trimmed of whitespace/newlines on intake (spec edge case); `None` = fall back to `key_env_var` |
| `base_url` | str \| None | only when spec allows; http(s) URL |
| `source` | `"ui"` \| `"env"` \| `"default"` | how this config was established |
| `set_at` | datetime | for "last write wins" bookkeeping |

Rules:
- Held in a module-level holder; **last write wins** (clarification 2026-07-03).
- `__repr__`/`__str__` mask `api_key` entirely; the field is excluded from every
  serialization (FR-006). Status views expose only `configured: bool` + `source`.
- Never written to disk, logs, or traces (SC-004).

### Precedence resolution (produces the effective config)

1. **UI**: a `POST /api/providers/active` since process start → that config.
2. **Env**: `COUNCIL_PROVIDER` names a registry id whose `key_env_var` is set
   (model from `COUNCIL_MODEL` or the spec's `default_model`; base URL for `custom`
   from `COUNCIL_BASE_URL`).
3. **Env-Google**: `GOOGLE_API_KEY` set → `google` + `gemini-2.5-flash` (FR-003/FR-004,
   the existing behavior, unchanged).
4. **Unconfigured**: no run possible; UI shows guided get-started (research R8).

## RunBinding (immutable per-run snapshot)

Resolved **once** when the SSE stream starts (research R4): `provider_id`, `model`,
resolved credential, `base_url`, plus the model object/string handed to agents.
Mid-run settings changes never affect an active run; failure never switches provider
or credential (FR-016). Consumed by `deliberation.py`'s role→model map — every role
(moderator, panelist, factchecker, structurer, synthesizer) receives the same resolved
model (FR-008).

## Model resolution (factory, not entity)

`resolve_model(binding) -> str | LiteLlm`:
- `google` → the plain model string (existing path, byte-identical — FR-014).
- others → `LiteLlm(model=f"{prefix}/{model}", api_key=…, api_base=…)` (research R1).

## Validation rules (trust boundary — `POST /api/providers/active`)

| Rule | Error code |
|------|-----------|
| `provider_id` ∈ `PROVIDERS` | `unknown_provider` |
| effective key present (body or env) for providers requiring one | `missing_key` |
| `model` non-empty after trim | `invalid_model` |
| `base_url` only when `allows_custom_base_url` (or `opencode` preset); parses as http(s) URL | `invalid_base_url` |
| live probe (research R5) auth failure | `invalid_key` |
| live probe unknown-model failure | `invalid_model` |
| live probe connect/timeout failure | `unreachable_endpoint` |

Every error carries a human-readable `message` naming the cause and a `hint` naming the
next step (FR-012).

## Deliberation Stage Event (UI-side derivation — no new server entity)

Client-side mapping from the existing SSE vocabulary (001 contract, unchanged) plus the
new `run_config` event (contracts/web-ui-v2.md):

| SSE kind | UI stage |
|----------|----------|
| `run_config` | header chip: provider + model (FR-011) |
| `recruit` / `fallback` | Assembling the panel |
| `turn` (with `round`) | Debate — round N |
| `tool_call` | Fact-checking |
| `synthesize` | Synthesizing |
| `verdict` / `refusal` / `clarify` / `error` | terminal state card |

State transitions: `unconfigured → configured(env) [boot] → configured(ui) [POST]`;
any configured state → RunBinding snapshot at stream start.
