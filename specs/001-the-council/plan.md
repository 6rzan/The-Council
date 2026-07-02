# Implementation Plan: The Council — A Self-Assembling Deliberation Engine

**Branch**: `001-the-council` | **Date**: 2026-07-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-the-council/spec.md`

## Summary

The Council takes a free-text question, has a **root Moderator agent recruit a custom expert
panel at run time** (with a mandatory deterministic fallback roster), runs a **bounded
multi-round debate** where **Panelist** agents rebut each other, sends factual claims to a
**Fact-Checker** agent that grounds them via a **local MCP server wrapping Wikipedia**, applies
**guardrails as ADK callbacks** (input validation, scope/refusal, injection neutralization,
unsupported-claim striking), and a **Synthesizer** agent emits a structured **Verdict Brief**
streamed live to a **local web UI** — FastAPI + Server-Sent Events feeding one self-contained
browser page. Built on **Google ADK + Gemini 2.5 Flash**, session state
held **in memory only** (no persistence beyond the session). The deterministic app-shell loop
enforces round/panel bounds so every run terminates and stays demoable.

## Technical Context

**Language/Version**: Python 3.11 (ADK requires ≥3.10; 3.11 widely available)

**Primary Dependencies**:
- `google-adk` — agents (`LlmAgent`), tools, `MCPToolset`, `Runner`, `InMemorySessionService`,
  model/tool callbacks
- `google-genai` (pulled by ADK) — Gemini access via AI Studio API key
- `mcp` — Model Context Protocol SDK for the local stdio fact-check server
- `httpx` — HTTP client inside the MCP server (calls Wikipedia)
- `pydantic` (pulled by ADK) — structured-output schemas (Roster, Claim, VerdictBrief)
- `fastapi` + `uvicorn` — local web server; Server-Sent Events stream the deliberation to a
  single self-contained browser page (inline CSS/JS — no build step, no JS toolchain)
- `python-dotenv` — load `GOOGLE_API_KEY` from `.env`
- `pytest`, `pytest-asyncio` — tests

**Storage**: None persistent. Session state (transcript, roster, claims, prior verdicts) lives
in ADK `InMemorySessionService` for the session lifetime only (FR-012, Principle VII).

**Testing**: `pytest`. Smoke test per agent role + per tool; one offline end-to-end test using a
**fake/injected model client** and a **mocked Wikipedia MCP** so CI is deterministic, free, and
green (FR-014, Principle VI). Fallback-roster path has its own test (FR-016).

**Target Platform**: Local cross-platform web app (Windows/macOS/Linux) — `council` starts a
localhost server and opens the browser; Python 3.11 runtime.

**Project Type**: Single project — multi-agent CLI application.

**Performance Goals**: A full deliberation (recruit → ~2 rounds × ~3 panelists → fact-check →
synthesis) completes well within the 2-minute demo window (SC-008); default model
`gemini-2.5-flash` for low latency/cost.

**Constraints**: Free/minimal-cost only — Gemini AI Studio **free tier** + **keyless** Wikipedia
(Principle III). Bounded rounds/panel size so runs always terminate (FR-009, SC-007). Secrets via
env vars only; `.env` and `.claude/` gitignored; secret-scan before every push (Principle IV).
Every source file < 500 lines.

**Scale/Scope**: Single-user, session-based, advisory-only (no external side effects). P1 = the
full self-assembling loop; P2 = session memory; P3 = refusal demos + optional Cloud Run deploy.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| # | Principle | Plan compliance | Verdict |
|---|-----------|-----------------|---------|
| I | Ship the Submission First | Scope is the P1 loop; P2/P3 are cuttable; deterministic fallback roster (FR-016) keeps E2E green by 2026-07-04; feature freeze 2026-07-05 respected | ✅ PASS |
| II | ADK-Style Multi-Agent | Root **Moderator** + **3 specialists** (Panelist, Fact-Checker, Synthesizer), ADK + Gemini, all exercised in the P1 demo; three layers separated: `agents/` (reasoning), `tools/` (capability), `orchestration/`+`web/` (app shell) | ✅ PASS |
| III | Tools & MCP as Capability Boundary | All external capability is a declared tool; **≥1 MCP integration** = local stdio **fact-check MCP server** (Wikipedia) consumed via `MCPToolset`; least-privilege (only Fact-Checker holds it); free/keyless data | ✅ PASS |
| IV | Security & Guardrails by Design | Input validation + scope/refusal + injection-neutralization + unsupported-claim striking as ADK **callbacks** (the "Referee"); advisory-only (no side effects); `GOOGLE_API_KEY` via `.env`; `.env` + `.claude/` gitignored; secret-scan gate; writeup security section | ✅ PASS |
| V | Prompts as Versioned Artifacts | Every agent instruction in version-controlled files under `src/council/agents/instructions/`; **structured outputs** via Pydantic `output_schema` (no free-text parsing); each agent runnable in isolation | ✅ PASS |
| VI | Demonstrable Quality | Offline deterministic E2E green from day 1; smoke test per agent + per tool; structured deliberation trace (observability, FR-008); README quickstart + pinned deps + `.env.example` | ✅ PASS |
| VII | Data Handling & Privacy | Synthetic/public data only; in-memory session (no persistence); APIs (Wikipedia, Gemini) documented in writeup; MIT repo; deps OSI-approved | ✅ PASS |

**Result: PASS — no violations.** Complexity Tracking table below is intentionally empty.

**Post-Design Re-check (after Phase 1):** PASS. The Phase 1 design introduced no new complexity or
violations — it stayed at root + 3 specialists, exactly one MCP integration, guardrails as
callbacks, structured outputs via Pydantic, in-memory sessions, and an offline deterministic test
suite. One ADK constraint surfaced and was designed around (research R6): an `LlmAgent` with
`output_schema` cannot also hold tools, so the Fact-Checker gathers evidence free-form and a
separate no-tool step structures the `Claim`s. No principle is weakened by this.

### Note on the "Referee" (spec → plan mapping)

The spec describes a "Referee." In ADK the idiomatic realization of guardrails is **callbacks**
(`before_model_callback`, `before_agent_callback`, `before_tool_callback`), not a fifth LLM
agent. Mapping the Referee to callbacks + validation utilities (a) keeps us within the "2–4
specialists" rule, (b) is the ADK-native guardrail pattern, and (c) still produces a **visible**
refusal message for the US3 demo. FR-005/FR-006 are satisfied by these callbacks; the Synthesizer
enforces the "no unsupported claim as fact" rule using the Fact-Checker's labels.

## Project Structure

### Documentation (this feature)

```text
specs/001-the-council/
├── plan.md              # This file
├── research.md          # Phase 0 output (decisions + rationale)
├── data-model.md        # Phase 1 output (entities, schemas, validation)
├── quickstart.md        # Phase 1 output (setup + run + validate)
├── contracts/           # Phase 1 output
│   ├── web-ui.md         # Web UI + SSE stream contract
│   ├── mcp-factcheck.md  # MCP fact-check server tool contract
│   └── agent-io-schemas.md  # Structured I/O contracts for each agent
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
src/council/
├── __init__.py
├── app.py                    # Runner/SessionService wiring; entry into a deliberation
├── config.py                 # env loading (GOOGLE_API_KEY), model + bounds constants
├── schemas/                  # Pydantic models (structured outputs / entities)
│   ├── roster.py             # Panelist, PanelRoster
│   ├── claim.py              # Claim (+ status enum)
│   ├── verdict.py            # VerdictBrief, Position, Dissent
│   └── trace.py              # DeliberationTrace, TraceEvent
├── agents/                   # reasoning layer (ADK LlmAgents + instruction files)
│   ├── moderator.py          # root: validate → recruit roster (structured) → orchestrate
│   ├── panelist.py           # persona-parameterized debater factory
│   ├── factchecker.py        # holds the MCP toolset; gathers evidence
│   ├── synthesizer.py        # emits VerdictBrief (structured, no tools)
│   └── instructions/         # versioned system-instruction text files (one per role)
│       ├── moderator.md
│       ├── recruiter.md      # Moderator's recruit-panel instruction
│       ├── panelist.md
│       ├── factchecker.md
│       └── synthesizer.md
├── tools/
│   └── factcheck_mcp/        # the MCP stdio server (capability layer)
│       ├── server.py         # exposes search_encyclopedia, get_article_summary
│       └── wikipedia.py      # httpx calls to Wikipedia REST/Action API
├── guardrails/               # the "Referee": ADK callbacks + validators
│   ├── input_guard.py        # validate question; refuse regulated-advice/unsafe/injection
│   └── claim_guard.py        # strike unsupported claims before synthesis
├── orchestration/            # app shell: bounded loop, state, trace
│   ├── deliberation.py       # deterministic round loop (enforces FR-009 bounds)
│   ├── session_state.py      # transcript/roster/claims/prior-verdict access helpers
│   └── fallback.py           # deterministic fallback roster (FR-016)
├── web/
│   ├── server.py             # FastAPI app: serves the page + SSE deliberation stream
│   └── static/
│       └── index.html        # self-contained UI (inline CSS/JS, EventSource; no build step)
└── __main__.py               # launcher: starts uvicorn + opens the browser (`council` / `python -m council`)

tests/
├── unit/                     # schema validation, guardrails, fallback roster
├── smoke/                    # one per agent role + per MCP tool
└── e2e/                      # full question → VerdictBrief (fake model + mocked wiki)

config/
├── .env.example              # GOOGLE_API_KEY=..., GOOGLE_GENAI_USE_VERTEXAI=FALSE
scripts/
docs/
```

**Structure Decision**: Single-project multi-agent CLI. The three constitutional layers are
physically separated: **agents/** (reasoning), **tools/** (capability, incl. the MCP server), and
**orchestration/ + web/** (app shell / I/O). `guardrails/` holds the ADK callbacks. `schemas/`
centralizes the Pydantic structured-output contracts so every machine-consumed output is typed.

## Complexity Tracking

> No Constitution Check violations — table intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
