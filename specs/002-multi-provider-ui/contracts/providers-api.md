# Contract: Provider Configuration API

**Feature**: 002-multi-provider-ui | localhost only (127.0.0.1) | implemented in
`src/council/web/server.py`, backed by `src/council/providers.py`.

Covers FR-001…FR-007, FR-012, FR-016. All request data is untrusted and validated
server-side (Principle IV). **No response, log line, or trace ever contains any part of
a credential** (FR-006, SC-004).

## `GET /api/providers`

Returns the registry plus the current effective configuration. Safe to call anytime;
no side effects.

```json
{
  "providers": [
    {
      "id": "openai",
      "display_name": "OpenAI",
      "default_model": "gpt-4o",
      "curated_models": ["gpt-4o", "gpt-4o-mini"],
      "allows_custom_base_url": false,
      "requires_key": true,
      "configured": true,
      "key_source": "env"
    }
  ],
  "active": { "provider": "google", "model": "gemini-2.5-flash", "source": "default" },
  "configured_any": true
}
```

- `configured` — a usable credential exists for this provider (UI-supplied or env).
  Booleans + `key_source` (`"ui"` | `"env"` | `null`) only — never key material,
  never a masked fragment (US1 acceptance #4).
- `active` — result of the precedence resolution (data-model.md). `active: null` when
  unconfigured → the page shows the guided get-started state.
- `configured_any: false` is the get-started trigger.

## `POST /api/providers/active`

Sets the one server-wide active configuration (last write wins). Body (JSON):

| Field | Required | Rule |
|-------|----------|------|
| `provider` | yes | must be a registry id |
| `model` | no | default: provider's `default_model`; trimmed, non-empty; free-text allowed (FR-005) |
| `api_key` | no | trimmed of whitespace/newlines; omitted → env var for that provider is used |
| `base_url` | `custom` only | http(s) URL; rejected for providers that do not allow it |

Behavior:
1. Structural validation (table above) — fails fast with 400, no network.
2. If a new key/base-URL was supplied (or provider changed): run the validation probe
   (research R5 — one minimal completion, ~10 s timeout, injectable for tests).
3. On success: store `ActiveProviderConfig` (memory only), return 200:

```json
{ "ok": true, "active": { "provider": "openai", "model": "gpt-4o", "source": "ui" } }
```

4. On failure: 400 with a typed, provider-specific error (FR-007/FR-012):

```json
{
  "error": {
    "code": "invalid_key",
    "provider": "openai",
    "message": "OpenAI rejected the API key (401 Unauthorized).",
    "hint": "Check the key at https://platform.openai.com/api-keys and paste it again."
  }
}
```

Error codes: `unknown_provider`, `missing_key`, `invalid_key`, `invalid_model`,
`invalid_base_url`, `unreachable_endpoint`. `message` names the cause; `hint` names the
next step. A probe failure MUST distinguish `invalid_model` from `invalid_key`
(spec edge case: valid key, bad model name).

## Interaction with the deliberation stream

- `GET /api/deliberate/stream` resolves the active config **once at stream start** into
  an immutable RunBinding; every SSE stream now begins with a `run_config` event
  (contracts/web-ui-v2.md).
- If unconfigured at stream start → immediate terminal `error` event
  (`detail` explains no provider is configured; the page routes to get-started).
  HTTP status stays 200 (matches 001 stream semantics).
- A run failure never retries on a different provider/credential (FR-016); the existing
  same-provider retry-then-degrade behavior is unchanged.

## Test hooks (FR-015 — all offline)

- Probe injectable: tests replace it with a fake accepting/rejecting configured keys.
- Smoke: GET shape; POST happy path; every error code; precedence UI→env→default;
  masking (assert no response string contains the posted key); trim behavior.
- E2E: POST an (fake-validated) OpenAI config → run a full deliberation with the fake
  model injected at the model-factory seam → verdict received; `run_config` names
  the non-default provider.
