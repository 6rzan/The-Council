---
description: "Task list for The Council — self-assembling deliberation engine"
---

# Tasks: The Council — A Self-Assembling Deliberation Engine

**Input**: Design documents from `specs/001-the-council/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md
**Tests**: INCLUDED — FR-014 mandates smoke tests per role/tool + a green-on-main E2E test (Principle VI).
**Implementer note**: Per the project's division of labor, Claude authored these tasks; **GLM 5.2
writes the code**. Each task is self-contained (exact file path + which design doc governs it) so it
is executable without extra context.
**Revised 2026-07-03**: primary interface is now a **local web UI** (FastAPI + SSE + one
self-contained page — contracts/web-ui.md supersedes the old CLI contract), and the analysis
remediations (writeup/video tasks, guardrail-scope fix, untrusted-tool-output and degrade branches)
are folded in. Task IDs T001–T046 are stable; T047–T048 are new.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizable (different file, no dependency on an incomplete task)
- **[Story]**: US1 / US2 / US3 (Setup, Foundational, Polish carry no story label)
- Single-project layout (plan.md): code in `src/council/`, tests in `tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project skeleton and dependencies

- [x] T001 Create the project structure per plan.md: `src/council/{schemas,agents/instructions,tools/factcheck_mcp,guardrails,orchestration,web/static}/`, `tests/{unit,smoke,e2e}/`, `config/`, `docs/`, with `__init__.py` in each package
- [x] T002 Initialize the Python 3.11 project: `pyproject.toml` + pinned `requirements.txt` (google-adk, google-genai, mcp, httpx, pydantic, fastapi, uvicorn, python-dotenv, pytest, pytest-asyncio) and a `council` console-script entry point pointing at `council.__main__:main`
- [x] T003 [P] Create `config/.env.example` (`GOOGLE_API_KEY=`, `GOOGLE_GENAI_USE_VERTEXAI=FALSE`) and a `.gitignore` covering `.env`, `.claude/`, `.venv/`, `__pycache__/` (Principle IV/VII)
- [x] T004 [P] Configure tooling: ruff + black config and pytest config in `pyproject.toml` (`asyncio_mode=auto`, register a `live` marker for opt-in API tests)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared schemas, config, session/state, and the offline test harness that every story needs

**⚠️ CRITICAL**: No user-story work begins until this phase is complete

- [x] T005 Implement `src/council/config.py`: load env via python-dotenv; expose `GOOGLE_API_KEY` and bounds constants `MIN_PANEL=2, DEFAULT_PANEL=3, MAX_PANEL=4, MAX_ROUNDS=2, FACTCHECK_TIMEOUT_S=8, MODEL="gemini-2.5-flash"` (data-model §bounds)
- [x] T006 [P] Implement `src/council/schemas/roster.py`: `RosterSource` enum, `Panelist`, `PanelRoster` with validators (size within [MIN_PANEL,MAX_PANEL], ≥1 `is_challenger`, unique names) (data-model §Panelist/§PanelRoster)
- [x] T007 [P] Implement `src/council/schemas/claim.py`: `ClaimStatus` enum + `Claim` (source_title/url required when status ≠ uncertain) (data-model §Claim)
- [x] T008 [P] Implement `src/council/schemas/verdict.py`: `Confidence` enum, `Position`, `Dissent`, `VerdictBrief` (data-model §VerdictBrief)
- [x] T009 [P] Implement `src/council/schemas/trace.py`: `TraceEvent` (kind ∈ recruit|turn|tool_call|guardrail|synthesize|fallback|error) and `DeliberationTrace` (data-model §Trace)
- [x] T010 Implement `src/council/orchestration/session_state.py`: base accessors over ADK `InMemorySessionService` for transcript/roster/claims/trace (plan §Storage)
- [x] T011 Implement `src/council/guardrails/input_guard.py` boundary validation only: trim/non-empty, length cap, normalize — FR-006 trust boundary; empty / too-short / undecipherable input returns a `NEEDS_CLARIFICATION` outcome carrying **one focused clarifying question** (spec Edge Cases → the web UI's `clarify` event; refusal-category logic deferred to US3)
- [x] T012 [P] Implement `src/council/app.py` wiring skeleton: `Runner` + `InMemorySessionService` factory and a model provider read from config (no agent logic yet)
- [x] T013 Create `tests/conftest.py`: an offline **fake-model injection** fixture (schema-valid canned responses), a **mocked Wikipedia/MCP** fixture, and a **FastAPI ASGI TestClient** fixture over the web app so all smoke/E2E tests run deterministically offline with no browser (research R5, contracts/web-ui.md)
- [x] T014 [P] Unit tests in `tests/unit/test_schemas.py`: challenger-required, panel bounds, unique names, claim source-required-when-supported (data-model rules)

**Checkpoint**: Foundation ready — user-story implementation can begin

---

## Phase 3: User Story 1 - Convene a self-assembling council and get a grounded verdict (Priority: P1) 🎯 MVP

**Goal**: A free-text question → Moderator recruits a custom panel (or falls back) → bounded multi-round debate → claims fact-checked via the MCP server → Verdict Brief streamed live to the browser over SSE.

**Independent Test**: Run `council`, ask a substantive question in the opened page, and confirm streamed panelist cards (with recruitment reasons + a challenger badge), visible rebuttals across rounds, fact-checks with a source link or "uncertain", and a complete Verdict Brief card — end to end, offline E2E green.

### Tests for User Story 1 (write first; ensure they fail before implementing) ⚠️

- [x] T015 [P] [US1] Smoke test for the fact-check MCP server (both tools + timeout→empty degradation) in `tests/smoke/test_factcheck_mcp.py` (mocked wiki, contracts/mcp-factcheck.md)
- [x] T016 [P] [US1] Smoke test for the Moderator recruit step (valid roster + invalid/malformed → fallback) in `tests/smoke/test_moderator.py`
- [x] T017 [P] [US1] Smoke test for the Panelist agent (returns argument, sets `references_prior`) in `tests/smoke/test_panelist.py`
- [x] T018 [P] [US1] Smoke test for the Fact-Checker evidence + claim-structuring step in `tests/smoke/test_factchecker.py`, including the FR-018 branch: an unparseable/invalid structured claim retries **once** then degrades that claim to `uncertain` (never crashes the run)
- [x] T019 [P] [US1] Smoke test for the Synthesizer structured `VerdictBrief` (+ retry→degrade) in `tests/smoke/test_synthesizer.py`
- [x] T020 [P] [US1] **Green-on-main E2E through the web API**: drive `GET /api/deliberate/stream` with the ASGI TestClient (fake model + mocked wiki) and assert the SSE event order `recruit`×N → `turn`/`tool_call` → `synthesize` → terminal `verdict` carrying a schema-valid `VerdictBrief`, in `tests/e2e/test_deliberation.py` (FR-014, contracts/web-ui.md)
- [x] T021 [P] [US1] Fallback-roster E2E: recruitment fails → `fallback` SSE event, deterministic roster with `source=fallback`, run still completes to `verdict`, in `tests/e2e/test_fallback.py` (FR-016)

### Implementation for User Story 1

- [x] T022 [P] [US1] Implement `src/council/tools/factcheck_mcp/wikipedia.py`: httpx search (Action API) + summary (REST) with `FACTCHECK_TIMEOUT_S`; on error/timeout return empty/`found:false`; **treat fetched article content as untrusted data** — length-cap extracts and return them as plain quoted text, never interpolated as instructions (FR-006, contracts/mcp-factcheck.md)
- [x] T023 [US1] Implement `src/council/tools/factcheck_mcp/server.py`: MCP stdio server exposing `search_encyclopedia` and `get_article_summary` (depends on T022)
- [x] T024 [P] [US1] Author versioned instruction files `src/council/agents/instructions/{moderator,recruiter,panelist,factchecker,synthesizer}.md` (Principle V)
- [x] T025 [P] [US1] Implement `src/council/orchestration/fallback.py`: deterministic default roster (Advocate, Skeptic, Synthesizer-lens) satisfying roster validators (FR-016)
- [x] T026 [US1] Implement `src/council/agents/moderator.py`: input-guard callback wiring + recruit step (`output_schema=PanelRoster`); on invalid/malformed roster retry once then use fallback (FR-010/FR-016/FR-018) (depends on T006, T011, T024, T025)
- [x] T027 [P] [US1] Implement `src/council/agents/panelist.py`: persona-parameterized debater factory that reads the running transcript and marks rebuttals (`references_prior`) (depends on T024)
- [x] T028 [US1] Implement `src/council/agents/factchecker.py`: `MCPToolset` wiring (least-privilege — only here) + free-form evidence gathering, then a **no-tool** structuring step → `list[Claim]` (research R6); evidence extracts are **untrusted quoted data**, never executed as instructions (FR-006); an unparseable claim retries once then degrades to `uncertain` (FR-018) (depends on T007, T023, T024)
- [x] T029 [US1] Implement `src/council/guardrails/claim_guard.py`: remove/flag `unsupported` claims before synthesis so none appears as established fact (FR-005) (depends on T007)
- [x] T030 [US1] Implement `src/council/agents/synthesizer.py`: `output_schema=VerdictBrief`, excludes unsupported-as-fact; retry once then degrade to a minimal well-formed brief (FR-007/FR-018) (depends on T008, T024)
- [x] T031 [US1] Implement `src/council/orchestration/deliberation.py`: the bounded loop — recruit → N rounds × panelists (sequential, shared transcript) → fact-check → claim_guard → synthesize — appending `TraceEvent`s and enforcing MAX_ROUNDS/MAX_PANEL (FR-002/FR-003/FR-009); expose it as an async generator yielding events so the web layer can stream them (depends on T026–T030, T010)
- [x] T032 [US1] Implement the web server + launcher (FR-017, contracts/web-ui.md): `src/council/web/server.py` — FastAPI app with `GET /` serving the static page and `GET /api/deliberate/stream` emitting SSE events mapped 1:1 from `TraceEvent` kinds plus terminal `verdict`/`refusal`/`clarify`, with `question`/`rounds`/`panel`/`session_id` validated and clamped to config bounds server-side; and `src/council/__main__.py` — launcher that starts uvicorn on localhost and opens the browser, exiting **3** with a friendly `.env.example` pointer when `GOOGLE_API_KEY` is missing (`council` / `python -m council`) (depends on T031)
- [x] T033 [US1] Implement `src/council/web/static/index.html`: ONE self-contained page (inline CSS/JS, `EventSource`, **no CDN, no build step, no external requests**) rendering the cinematic deliberation per contracts/web-ui.md — panelist cards appearing one-by-one with recruitment reason + challenger badge; "using fallback panel" notice; round-grouped debate feed with a stable per-panelist color identity and highlighted rebuttals; fact-check status badges with clickable source links; a formal Verdict Brief card with confidence meter + Download-JSON button; a collapsible trace drawer; refusal and clarify cards (depends on T032)

**Checkpoint**: MVP — a full grounded deliberation is demoable in the browser and the offline E2E is green

---

## Phase 4: User Story 2 - Context carries across a session (Priority: P2)

**Goal**: Within one session, a follow-up question builds on prior verdicts without re-recruiting from scratch; nothing persists past the session.

**Independent Test**: Via the web API (or the page), ask a question, then a follow-up ("what if the budget were half?") reusing the same `session_id`; the second brief references the first. Restarting the server forgets everything.

### Tests for User Story 2 ⚠️

- [x] T034 [P] [US2] E2E via the web API: two `GET /api/deliberate/stream` calls sharing a `session_id` — the second verdict references the prior one; a fresh app instance has no memory of it, in `tests/e2e/test_session_followup.py` (FR-011/FR-012)

### Implementation for User Story 2

- [x] T035 [US2] Add `SessionContext` (prior_questions, prior_verdicts) in `src/council/schemas/session.py` (data-model §SessionContext)
- [x] T036 [US2] Extend `src/council/orchestration/session_state.py` to store/retrieve prior questions + verdicts across turns, in memory only (FR-011/FR-012) (depends on T010, T035)
- [x] T037 [US2] Wire follow-ups through the UI: the page keeps its `session_id` after a verdict and reuses it on the next question; the server resolves it to the same ADK session (contracts/web-ui.md §Follow-ups) (depends on T032, T033, T036)
- [x] T038 [US2] Thread prior-verdict context into the Moderator recruit and Synthesizer prompts so follow-ups build on earlier deliberation (depends on T036, T026, T030)

**Checkpoint**: US1 and US2 both work independently

---

## Phase 5: User Story 3 - Guardrails refuse out-of-bounds requests on demand (Priority: P3 — **submission-required, never cut**)

**Goal**: Regulated-advice / unsafe / prompt-injection inputs are refused with a clear explanation and no panel run; injection is neutralized as untrusted content.

**Independent Test**: Submit a "guarantee me stock picks" request and an injection ("ignore your instructions…") to the stream endpoint; each yields a terminal `refusal` SSE event (no `verdict`, no panel events) and the page shows the refusal card.

### Tests for User Story 3 ⚠️

- [x] T039 [P] [US3] Guardrail tests in `tests/smoke/test_guardrails.py`: regulated-advice, unsafe, and injection inputs each classify as refuse (unit level) AND, driven through the ASGI TestClient, produce a stream whose only terminal event is `refusal` with no `recruit`/`verdict` (FR-005/FR-006, contracts/web-ui.md)

### Implementation for User Story 3

- [x] T040 [US3] Extend `src/council/guardrails/input_guard.py`: classify regulated-advice / unsafe / injection and neutralize injected instructions as untrusted content (FR-006, research R7) (depends on T011)
- [x] T041 [US3] Wire the refusal path end-to-end: Moderator `before_agent_callback` short-circuits → the stream emits the terminal `refusal` SSE event → the page renders the refusal card with the reason (US3, contracts/web-ui.md) (depends on T040, T026, T032, T033)

**Checkpoint**: All three stories independently functional

---

## Phase 6: Polish & Submission Deliverables

- [x] T042 [P] Write `README.md` quickstart (setup, run, demo, refusal, tests) mirroring quickstart.md, plus MIT `LICENSE`, **plus a short "run one agent in isolation" section with a concrete per-agent example** (FR-013/FR-015, Principle V/VI/VII)
- [x] T043 [P] Observability polish: structured logging config in `src/council/orchestration/` and make sure every `TraceEvent` reaches both the log and the UI trace drawer in order (FR-008) (depends on T032, T033)
- [x] T044 Run the secret-scan gate and confirm `.env` / `.claude/` are gitignored before any push (Principle IV)
- [ ] T045 Run the full `pytest` suite green offline, then execute quickstart.md validation end-to-end in a real browser (FR-014, SC-006/SC-008)
- [x] T046 [P] Optional (cut-able, post-freeze): `Dockerfile` + Cloud Run deploy notes in `docs/` for the deployment bonus — deploys the FastAPI web app (P3, contracts/web-ui.md)
- [x] T047 [P] Write the Kaggle submission writeup in `docs/writeup.md`: name **≥4 course concepts** with where each is demonstrated (use research.md's course-concept coverage table as the skeleton), a **security/guardrails section** (callbacks, injection neutralization, untrusted tool output, secrets handling), the external APIs used (Gemini free tier, keyless Wikipedia via MCP), the chosen track, and the project rationale/impact story (SC-009, Constitution IV) — content-complete once US1+US3 are demoable
- [ ] T048 Script and record the **2-minute demo video**: happy path in the browser (panel assembles → debate → fact-check badges → Verdict Brief card), the refusal card, and a one-line nod to the fallback/trace; publish it (public link) and reference it from the writeup (SC-008) (depends on T045; refusal segment needs T041)

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (P1)**: no dependencies
- **Foundational (P2)**: after Setup — **blocks all stories**
- **US1 (P3)**: after Foundational — the MVP core; no dependency on US2/US3
- **US2 (P4)**: after Foundational; integrates with US1 but is independently testable
- **US3 (P5)**: after Foundational; extends the US1 guardrail wiring but is independently testable
- **Polish (P6)**: after the desired stories are complete; T047/T048 are **submission-blocking**, not optional

### Within each story

- Tests written first and failing → schemas/tools → agents → orchestration → web layer
- The always-green E2E (T020) stays green from the moment US1 lands and must never regress (Principle I/VI)

### Parallel opportunities

- Setup: T003, T004 in parallel
- Foundational: T006–T009 (schemas) and T014 in parallel; T012 in parallel with schemas
- US1 tests T015–T021 all parallel; then T022/T024/T025/T027 parallel before the sequential wiring (T026→T028→T029→T030→T031→T032→T033)
- Polish: T042/T043/T046/T047 parallel; T048 last (needs a working demo)

---

## Parallel Example: User Story 1 tests

```bash
# Author all US1 tests together (they fail until the code lands):
Task: "Smoke test the fact-check MCP server in tests/smoke/test_factcheck_mcp.py"
Task: "Smoke test the Moderator recruit + fallback in tests/smoke/test_moderator.py"
Task: "E2E SSE stream → VerdictBrief in tests/e2e/test_deliberation.py"
Task: "Fallback-roster E2E in tests/e2e/test_fallback.py"
```

---

## Implementation Strategy

### Minimum complete submission (US1 + US3 + deliverables)

1. Setup (Phase 1) → 2. Foundational (Phase 2) → 3. US1 (Phase 3) → **STOP & VALIDATE**: run
   `council` + `pytest`. This is the demoable core — but it is **not yet a complete submission**:
   FR-005(a) and Constitution IV make the guardrail refusal path (US3) and the writeup security
   section mandatory. **If time runs short, cut US2 (session memory), never US3.** The minimum
   complete submission = Phases 1–3 + Phase 5 + T042–T045 + T047 + T048.

### Incremental delivery

Foundation → **US1 (core, green E2E)** → US3 (refusals — submission-required) → US2 (session
memory) → Polish + writeup + video. Each story adds value without breaking the green E2E.
Target: US1 demoable by 2026-07-04, feature freeze 2026-07-05, submit ≥6h early
(2026-07-06 11:59 PM PT deadline).

---

## Notes

- `[P]` = different files, no incomplete dependency. `[Story]` maps each task to a spec user story.
- Tests are mandated (FR-014); keep the offline E2E green on main at every checkpoint.
- No production code is written by the planner — GLM 5.2 implements these tasks; the handoff
  prompt lives at `specs/001-the-council/glm-handoff.md`.
- Keep every source file < 500 lines; validate untrusted input at every boundary — user question,
  tool arguments, AND tool/LLM outputs (Constitution IV).
