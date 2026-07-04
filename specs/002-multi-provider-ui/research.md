# Research: Multi-Provider Model Choice & Live Deliberation UI

**Feature**: 002-multi-provider-ui | **Date**: 2026-07-05 | **Plan**: [plan.md](plan.md)

Each decision states the choice, rationale, and rejected alternatives. Items marked
**⚠ verify at implementation** are cheap checks GLM performs before relying on them.

## R1 — Multi-provider mechanism: ADK's LiteLlm model wrapper

**Decision**: Non-Google providers are reached via `google.adk.models.lite_llm.LiteLlm`,
passed as the `model=` argument to `LlmAgent`. Google Gemini keeps using the plain model
string (`"gemini-2.5-flash"`) — that code path is byte-for-byte unchanged (FR-004/FR-014).

**Rationale**: `LlmAgent.model` accepts a string **or** a `BaseLlm` instance — the
project's own offline tests already inject `FakeLlm` objects through this exact seam, so
the object path is proven in this codebase. `LiteLlm` is ADK's documented multi-provider
adapter; one wrapper covers OpenAI, Anthropic, and any OpenAI-compatible endpoint
(OpenCode Zen, local runtimes) via `model` prefix + `api_base` + `api_key` arguments.

**Alternatives rejected**:
- Native SDKs per provider (openai, anthropic, …): 3–4 new dependencies, per-provider
  request/response mapping, bypasses the ADK model layer — breadth Principle I forbids.
- Replacing ADK: absurd for a course-native capstone (Principle II).

**⚠ verify at implementation**: `from google.adk.models.lite_llm import LiteLlm` imports
cleanly under the pinned google-adk 2.3.0, and structured output (`output_schema` +
`output_key`) works through LiteLlm for at least one provider. If structured output
proves flaky on a provider, that provider's error message says so upfront (spec edge
case "model lacks required capabilities") — the pipeline is not changed to accommodate it.

## R2 — New dependency: litellm (exact pin at implementation)

**Decision**: Add `litellm` to `requirements.txt`, pinned to the exact version resolved
by `pip install litellm && pip freeze` at implementation time (constitution VI requires
pinned deps; a version guessed at plan time could be yanked or incompatible).

**Rationale**: `LiteLlm` imports it lazily; it is not in the current pin list. MIT
license — OSI-approved, CC-BY-4.0 compatible (Principle VII).

**Alternatives rejected**: vendoring or optional-install (`pip install` on demand) —
breaks "reproducible by a stranger on a clean machine" (Principle VI).

## R3 — Provider registry as data

**Decision**: A single `PROVIDERS` dict in `src/council/providers.py`. Per entry:
`id`, `display_name`, `key_env_var`, `litellm_prefix`, `default_base_url` (OpenCode Zen
preset), `allows_custom_base_url`, `default_model`, `curated_models`. Free-text model
override is always allowed (FR-005).

Initial registry (curated lists deliberately short; **⚠ verify model ids at
implementation** against each provider's current catalog):

| id | display | litellm form | key env var | base URL |
|----|---------|--------------|-------------|----------|
| `google` | Google Gemini (default) | plain string, no LiteLlm | `GOOGLE_API_KEY` | — |
| `openai` | OpenAI | `openai/<model>` | `OPENAI_API_KEY` | — |
| `anthropic` | Anthropic | `anthropic/<model>` | `ANTHROPIC_API_KEY` | — |
| `opencode` | OpenCode Zen | `openai/<model>` + preset base URL | `OPENCODE_API_KEY` | `https://opencode.ai/zen/v1` preset |
| `custom` | Custom (OpenAI-compatible) | `openai/<model>` + user base URL | UI/`COUNCIL_API_KEY` | required from user |

Curated starting lists: google → `gemini-2.5-flash` (default), `gemini-2.5-pro`;
openai → `gpt-4o`, `gpt-4o-mini`; anthropic → `claude-sonnet-4-5`, `claude-haiku-4-5`;
opencode → free-text-first (gateway catalog shifts); custom → free-text only.

**Rationale**: one data structure drives the settings UI (`GET /api/providers`), model
resolution, and validation — no scattered per-provider branches.

## R4 — Precedence, lifetime, and run binding

**Decision** (implements the recorded clarifications):
- One server-wide `ActiveProviderConfig`, held in a module-level holder in
  `providers.py`. Last write wins; no per-browser-session state.
- Precedence: **UI choice → environment default → built-in Gemini default**.
  Environment default = `COUNCIL_PROVIDER` (+ optional `COUNCIL_MODEL`) naming a
  registry id whose key env var is set; absent that, `google` iff `GOOGLE_API_KEY`
  set; absent everything, unconfigured (guided get-started state).
- **Run binding**: the SSE endpoint resolves the active config **once at stream start**
  into an immutable snapshot passed through the deliberation. Mid-run settings changes
  never affect a running deliberation; no silent provider switching mid-run (FR-016 —
  the existing same-provider retry-then-degrade in `app.py` is untouched).

## R5 — Credential validation (FR-007)

**Decision**: `POST /api/providers/active` runs a minimal live probe (one tiny
completion, short timeout ~10 s) whenever a new key/base-URL is supplied, and maps
failures to typed, provider-specific errors: `invalid_key`, `invalid_model`,
`unreachable_endpoint`, `missing_key`, `invalid_base_url`, `unknown_provider`.
Run start re-checks only cheap presence (key exists for bound provider) — no second
network round-trip. The probe function is injectable so offline tests fake it.

**Rationale**: validating at save time gives the user the error in the settings panel
*before* any long deliberation wait (US1 acceptance #3, SC-001); classifying probe
errors separates "bad key" from "bad model name" (spec edge case).

**Alternatives rejected**: validating only at run start (error arrives after the user
already left settings); provider `models.list` calls (inconsistent across providers).

## R6 — Live UI stage model: derive client-side from the existing SSE stream

**Decision**: No pipeline redesign (spec assumption). The page derives stages from the
existing event vocabulary — `recruit`→Assembling panel, `turn`(round N)→Debate round N,
`tool_call`→Fact-checking, `synthesize`→Synthesizing, terminal→Verdict/Refusal/Clarify.
One **additive** server change: every stream begins with a `run_config` event
(`{provider, model, panel, rounds}`) so the UI can show the active provider/model for
the whole run (FR-011, US1 acceptance #2).

**Rationale**: satisfies FR-009's 2-second stage visibility for free — events are
emitted the moment the pipeline produces them. FR-010/SC-003 ("never >5 s without
visible progress") is met by a continuous CSS activity animation on the active stage,
which needs no server keepalives and cannot stall.

**Alternatives rejected**: new server-side `stage` events (touches the frozen
orchestration for presentation-only data); WebSockets (EventSource already works).

## R7 — Static asset split (supersedes 001's "inline only" rule)

**Decision**: `index.html` (markup) + `app.js` (logic) + `style.css` (design), each
<500 lines, served same-origin by FastAPI. Invariants kept from the 001 contract:
**no CDN, no external requests, no build step, no JS toolchain**. Recorded in
`contracts/web-ui-v2.md`.

**Rationale**: the US2 revamp (stage timeline, cards, animations, settings panel) cannot
fit in one file under the repo's 500-line cap. Same-origin static files preserve every
security/simplicity property the inline rule protected.

## R8 — Launcher: guided get-started replaces exit-3

**Decision**: `council` starts the server even with no key configured anywhere; the page
opens in a "get started" state that walks the user into the settings panel (spec edge
case). The exit-3 path is removed; exit codes 0/1 remain.

**Rationale**: with UI key entry, "no key in .env" is now a normal first-run state, not
an error. Verified by grep: **no existing test pins exit-3 / `has_api_key`**, so
FR-014's "currently passing tests stay green" holds. The friendly Google-key hint moves
into the get-started panel.

## R9 — OAuth (US3/FR-013): cut

The spec's own dated condition triggered (2026-07-05, US1–2 not code-complete by end of
2026-07-04). No design, contracts, or tasks. Recorded here and in plan.md Summary.

## R10 — Credential hygiene

**Decision**: keys live only inside the `ActiveProviderConfig` holder; `__repr__`
masks; API responses expose `configured: true/false` + `source` and never any key
fragment; logging audit task confirms no handler logs request bodies (FastAPI docs
endpoints already disabled in `server.py`). `.env.example` documents the new variable
names with placeholder values only. Secret-scan gate untouched (SC-004).
