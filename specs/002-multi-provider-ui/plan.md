# Implementation Plan: Multi-Provider Model Choice & Live Deliberation UI

**Branch**: `002-multi-provider-ui` | **Date**: 2026-07-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-multi-provider-ui/spec.md`

## Summary

Two deliverables. **(1) Bring-your-own-provider (US1/P1)**: users pick an AI provider —
Google Gemini (default), OpenAI, Anthropic, OpenCode Zen, or a custom OpenAI-compatible
endpoint — paste a key in a settings panel, and run a full deliberation on it, no file
edits or restart. **(2) Live deliberation UI (US2/P2)**: replace the static page with a
stage timeline, persona-attributed panelist cards, claim fact-check badges, a distinct
verdict card, and an always-visible activity state, all driven by the existing SSE stream.

Technical approach: ADK's `LlmAgent(model=...)` already accepts either a Gemini model
string or a `BaseLlm` instance (the offline `FakeLlm` tests prove the object path). A new
`src/council/providers.py` registry resolves the active provider config into either the
Gemini string (default, unchanged) or a `google.adk.models.lite_llm.LiteLlm` instance,
injected at the single existing seam — the role→model map in
`src/council/orchestration/deliberation.py:48-52`. Two new localhost endpoints
(`GET /api/providers`, `POST /api/providers/active`) manage the one server-wide active
configuration; credentials live in process memory only. The UI revamp derives stage
progression client-side from the existing SSE vocabulary plus one additive `run_config`
event — the deliberation pipeline itself is untouched.

**Scope ruling (binding)**: US3/FR-013 (OAuth sign-in) is **cut at plan time**. The spec's
own condition — "MUST be cut without renegotiation if User Stories 1–2 are not
code-complete by end of 2026-07-04" — has triggered: it is 2026-07-05 and implementation
has not started. No OAuth design, tasks, or contracts are produced. This plan covers
US1 + US2 only.

## Technical Context

**Language/Version**: Python 3.11+ (backend); vanilla HTML/CSS/JS, no toolchain (frontend)

**Primary Dependencies**: google-adk 2.3.0 (`LlmAgent`, `Runner`, `LiteLlm` wrapper),
**litellm (NEW — exact version pinned at implementation via `pip freeze`)**, FastAPI
0.138.2 + uvicorn 0.49.0, pydantic 2.13.4, python-dotenv 1.2.2. Frontend uses only
`EventSource` + `fetch` — no CDN, no external requests, no build step.

**Storage**: N/A. Sessions in-memory (unchanged); credentials in server process memory
only, never disk/logs/traces (FR-006).

**Testing**: pytest 9.1.1 + pytest-asyncio, fully offline (fake-model injection via
`tests/_fakes.py`; FastAPI test client for endpoint/SSE contracts). No real key ever
required (FR-015, SC-005).

**Target Platform**: local desktop web app, localhost only (127.0.0.1), Windows/macOS/Linux

**Project Type**: single project — FastAPI web service + self-served static page

**Performance Goals**: stage change visible in UI ≤2 s (SC-003); provider switch between
runs ≤30 s with no restart (SC-002); no active run shows >5 s without visible progress
indication (SC-003, satisfied by continuous CSS activity animation)

**Constraints**: offline-runnable test suite; every source file **and** every static asset
<500 lines (repo rule — drives the static-asset split, research R7); no new paid
infrastructure (users bring keys); secrets never enter git (secret-scan gate stays green,
SC-004); Gemini remains the built-in default (FR-004, Principle II)

**Scale/Scope**: single user, one deliberation at a time typical; ≤4 panelists, ≤2 rounds
(existing bounds unchanged); 5 providers in the registry; ~4 source files touched,
~5 files added

## Constitution Check

*GATE: evaluated pre-research 2026-07-05; re-evaluated after Phase 1 design — both PASS.*

| # | Principle | Verdict | Notes |
|---|-----------|---------|-------|
| I | Ship the Submission First | PASS | Breadth cut first: US3/OAuth cut at plan time per the spec's own dated condition (see Summary). Plan lands **on** feature-freeze day 2026-07-05 — scope is the minimum that satisfies US1+US2; both trace directly to submission assets (US2 is the demo-video visual; US1 is reproducibility/usability for judges). Anything not demoable gets cut, not shipped broken. |
| II | ADK Multi-Agent + Gemini default | PASS | Agent roster, orchestration, and the three layers are untouched. Gemini stays the built-in default whenever the user makes no choice (FR-004). Other providers route through ADK's own `LiteLlm` model wrapper — the ADK architecture is unchanged; only the `model=` argument varies. |
| III | Tools & MCP as capability boundary | PASS | No ad-hoc HTTP in agents or prompts: provider access goes through the ADK model layer. MCP fact-check integration unchanged. The two new `/api/providers*` endpoints are app-shell I/O (settings), not agent capability. |
| IV | Security & Guardrails | PASS | Credentials: memory-only, masked in every response, never logged (FR-006; contracts/providers-api.md security section). Trust boundary: POST body validated with pydantic — provider whitelist, model non-empty, base-URL parse + scheme check, key trimming (spec edge case). Secret-scan gate unaffected: no key material in repo. |
| V | Prompts versioned | PASS | No agent instruction changes. |
| VI | Demonstrable Quality | PASS | FR-015 enumerates offline smoke + E2E tests (provider precedence, validation errors, full deliberation on a non-default provider via fake-model injection, SSE/UI event contract). Existing suite stays green — verified no test pins the launcher exit-3 path being changed (research R8). Quickstart updated for reproducibility. |
| VII | Data & Privacy | PASS | No persistence of credentials beyond process lifetime; no personal data. litellm is MIT-licensed (OSI-approved, CC-BY-4.0-compatible). |

## Project Structure

### Documentation (this feature)

```text
specs/002-multi-provider-ui/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── providers-api.md # Phase 1 output — provider config endpoints
│   └── web-ui-v2.md     # Phase 1 output — UI + SSE additions (supersedes parts of 001)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/council/
├── config.py                  # MODIFIED — env defaults COUNCIL_PROVIDER / COUNCIL_MODEL,
│                              #   per-provider key readers (OPENAI_API_KEY, ANTHROPIC_API_KEY,
│                              #   OPENCODE_API_KEY, COUNCIL_BASE_URL)
├── providers.py               # NEW — registry, ActiveProviderConfig (memory-only),
│                              #   precedence resolution, model factory (str | LiteLlm),
│                              #   validation probe, masking
├── app.py                     # MODIFIED — has_api_key() generalized to provider-aware check
├── __main__.py                # MODIFIED — no-key start no longer exits 3; server starts and
│                              #   UI shows guided get-started (spec edge case, research R8)
├── orchestration/
│   └── deliberation.py        # MODIFIED — role→model map (lines 48-52) resolved via providers
└── web/
    ├── server.py              # MODIFIED — + GET /api/providers, POST /api/providers/active,
    │                          #   `run_config` SSE event emitted first on every stream
    └── static/
        ├── index.html         # REWRITTEN — markup only, <500 lines
        ├── app.js             # NEW — SSE handling, stage timeline, settings panel
        └── style.css          # NEW — visual design (dark, animated, demo-quality)

tests/
├── smoke/test_providers.py            # NEW — registry, precedence, masking, validation errors
├── smoke/test_web.py                  # EXTENDED — /api/providers contract, run_config event
└── e2e/test_provider_deliberation.py  # NEW — full offline deliberation on a non-default
                                       #   provider (fake model injected at the factory seam)

requirements.txt                       # MODIFIED — + litellm==<exact pin at implementation>
config/.env.example                    # MODIFIED — new optional vars documented, no values
```

**Structure Decision**: single project, existing three-layer layout preserved (agents /
tools / app shell — Principle II). All provider logic concentrates in the new
`providers.py`; agents and orchestration only see a resolved `model` value. The static
page splits into three same-origin assets solely to honor the 500-line cap (research R7);
the "no CDN, no external requests, no build step" invariant from the 001 contract is
retained and re-stated in contracts/web-ui-v2.md.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New dependency `litellm` (requirements.txt header says "no dependencies beyond this list") | Only supported ADK path to OpenAI/Anthropic/OpenAI-compatible endpoints (`google.adk.models.lite_llm.LiteLlm` imports it) | Hand-rolled per-provider HTTP clients would add far more code, bypass the ADK model layer, and violate Principle III's "no ad-hoc HTTP" rule; the 001 header note predates this spec — FR-001 is the authorization to amend it |

## Post-Design Constitution Re-Check

Re-evaluated after Phase 1 artifacts (research.md, data-model.md, contracts/,
quickstart.md) were produced: no new violations introduced. The single Complexity
Tracking entry above remains the only justified deviation. Note: this repo has no
`update-agent-context` script in `.specify/scripts/powershell/` — the agent-context
update step of the plan workflow is skipped by design.
