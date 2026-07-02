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

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizable (different file, no dependency on an incomplete task)
- **[Story]**: US1 / US2 / US3 (Setup, Foundational, Polish carry no story label)
- Single-project layout (plan.md): code in `src/council/`, tests in `tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project skeleton and dependencies

- [ ] T001 Create the project structure per plan.md: `src/council/{schemas,agents/instructions,tools/factcheck_mcp,guardrails,orchestration,cli}/`, `tests/{unit,smoke,e2e}/`, `config/`, `docs/`, with `__init__.py` in each package
- [ ] T002 Initialize the Python 3.11 project: `pyproject.toml` + pinned `requirements.txt` (google-adk, google-genai, mcp, httpx, pydantic, rich, python-dotenv, pytest, pytest-asyncio) and a `council` console-script entry point
- [ ] T003 [P] Create `config/.env.example` (`GOOGLE_API_KEY=`, `GOOGLE_GENAI_USE_VERTEXAI=FALSE`) and a `.gitignore` covering `.env`, `.claude/`, `.venv/`, `__pycache__/` (Principle IV/VII)
- [ ] T004 [P] Configure tooling: ruff + black config and pytest config in `pyproject.toml` (`asyncio_mode=auto`, register a `live` marker for opt-in API tests)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared schemas, config, session/state, and the offline test harness that every story needs

**⚠️ CRITICAL**: No user-story work begins until this phase is complete

- [ ] T005 Implement `src/council/config.py`: load env via python-dotenv; expose `GOOGLE_API_KEY` and bounds constants `MIN_PANEL=2, DEFAULT_PANEL=3, MAX_PANEL=4, MAX_ROUNDS=2, FACTCHECK_TIMEOUT_S=8, MODEL="gemini-2.5-flash"` (data-model §bounds)
- [ ] T006 [P] Implement `src/council/schemas/roster.py`: `RosterSource` enum, `Panelist`, `PanelRoster` with validators (size within [MIN_PANEL,MAX_PANEL], ≥1 `is_challenger`, unique names) (data-model §Panelist/§PanelRoster)
- [ ] T007 [P] Implement `src/council/schemas/claim.py`: `ClaimStatus` enum + `Claim` (source_title/url required when status ≠ uncertain) (data-model §Claim)
- [ ] T008 [P] Implement `src/council/schemas/verdict.py`: `Confidence` enum, `Position`, `Dissent`, `VerdictBrief` (data-model §VerdictBrief)
- [ ] T009 [P] Implement `src/council/schemas/trace.py`: `TraceEvent` (kind ∈ recruit|turn|tool_call|guardrail|synthesize|fallback|error) and `DeliberationTrace` (data-model §Trace)
- [ ] T010 Implement `src/council/orchestration/session_state.py`: base accessors over ADK `InMemorySessionService` for transcript/roster/claims/trace (plan §Storage)
- [ ] T011 Implement `src/council/guardrails/input_guard.py` boundary validation only: trim/non-empty, length cap, normalize — FR-006 trust boundary (refusal-category logic deferred to US3)
- [ ] T012 [P] Implement `src/council/app.py` wiring skeleton: `Runner` + `InMemorySessionService` factory and a model provider read from config (no agent logic yet)
- [ ] T013 Create `tests/conftest.py`: an offline **fake-model injection** fixture (schema-valid canned responses) and a **mocked Wikipedia/MCP** fixture so all smoke/E2E tests run deterministically offline (research R5)
- [ ] T014 [P] Unit tests in `tests/unit/test_schemas.py`: challenger-required, panel bounds, unique names, claim source-required-when-supported (data-model rules)

**Checkpoint**: Foundation ready — user-story implementation can begin

---

## Phase 3: User Story 1 - Convene a self-assembling council and get a grounded verdict (Priority: P1) 🎯 MVP

**Goal**: A free-text question → Moderator recruits a custom panel (or falls back) → bounded multi-round debate → claims fact-checked via the MCP server → Verdict Brief streamed to the CLI.

**Independent Test**: Run `council "<substantive question>"` and confirm a streamed roster (with reasons), visible rebuttals across rounds, fact-checks with a source or "uncertain", and a complete Verdict Brief — end to end, offline test green.

### Tests for User Story 1 (write first; ensure they fail before implementing) ⚠️

- [ ] T015 [P] [US1] Smoke test for the fact-check MCP server (both tools + timeout→empty degradation) in `tests/smoke/test_factcheck_mcp.py` (mocked wiki, contracts/mcp-factcheck.md)
- [ ] T016 [P] [US1] Smoke test for the Moderator recruit step (valid roster + invalid/malformed → fallback) in `tests/smoke/test_moderator.py`
- [ ] T017 [P] [US1] Smoke test for the Panelist agent (returns argument, sets `references_prior`) in `tests/smoke/test_panelist.py`
- [ ] T018 [P] [US1] Smoke test for the Fact-Checker evidence + claim-structuring step in `tests/smoke/test_factchecker.py`
- [ ] T019 [P] [US1] Smoke test for the Synthesizer structured `VerdictBrief` (+ retry→degrade) in `tests/smoke/test_synthesizer.py`
- [ ] T020 [P] [US1] **Green-on-main E2E**: full question → `VerdictBrief` with fake model + mocked wiki in `tests/e2e/test_deliberation.py` (FR-014)
- [ ] T021 [P] [US1] Fallback-roster E2E: recruitment fails → deterministic roster, `source=fallback`, run still completes in `tests/e2e/test_fallback.py` (FR-016)

### Implementation for User Story 1

- [ ] T022 [P] [US1] Implement `src/council/tools/factcheck_mcp/wikipedia.py`: httpx search (Action API) + summary (REST) with `FACTCHECK_TIMEOUT_S`; on error/timeout return empty/`found:false` (contracts/mcp-factcheck.md)
- [ ] T023 [US1] Implement `src/council/tools/factcheck_mcp/server.py`: MCP stdio server exposing `search_encyclopedia` and `get_article_summary` (depends on T022)
- [ ] T024 [P] [US1] Author versioned instruction files `src/council/agents/instructions/{moderator,recruiter,panelist,factchecker,synthesizer}.md` (Principle V)
- [ ] T025 [P] [US1] Implement `src/council/orchestration/fallback.py`: deterministic default roster (Advocate, Skeptic, Synthesizer-lens) satisfying roster validators (FR-016)
- [ ] T026 [US1] Implement `src/council/agents/moderator.py`: input-guard callback wiring + recruit step (`output_schema=PanelRoster`); on invalid/malformed roster retry once then use fallback (FR-010/FR-016/FR-018) (depends on T006, T011, T024, T025)
- [ ] T027 [P] [US1] Implement `src/council/agents/panelist.py`: persona-parameterized debater factory that reads the running transcript and marks rebuttals (`references_prior`) (depends on T024)
- [ ] T028 [US1] Implement `src/council/agents/factchecker.py`: `MCPToolset` wiring (least-privilege — only here) + free-form evidence gathering, then a **no-tool** structuring step → `list[Claim]` (research R6) (depends on T007, T023, T024)
- [ ] T029 [US1] Implement `src/council/guardrails/claim_guard.py`: remove/flag `unsupported` claims before synthesis so none appears as established fact (FR-005) (depends on T007)
- [ ] T030 [US1] Implement `src/council/agents/synthesizer.py`: `output_schema=VerdictBrief`, excludes unsupported-as-fact; retry once then degrade to a minimal well-formed brief (FR-007/FR-018) (depends on T008, T024)
- [ ] T031 [US1] Implement `src/council/orchestration/deliberation.py`: the bounded loop — recruit → N rounds × panelists (sequential, shared transcript) → fact-check → claim_guard → synthesize — appending `TraceEvent`s and enforcing MAX_ROUNDS/MAX_PANEL (FR-002/FR-003/FR-009) (depends on T026–T030, T010)
- [ ] T032 [US1] Implement `src/council/cli/main.py` (rich streaming): one-shot `council "<q>"`, live recruit/debate/fact-check/brief, flags `--rounds/--panel/--no-stream/--json/--trace`, exit codes 0/1/3 (FR-017, contracts/cli.md) (depends on T031)
- [ ] T033 [US1] Add `src/council/__main__.py` so `python -m council` runs the CLI; verify the `council` console script (depends on T032)

**Checkpoint**: MVP — a full grounded deliberation is demoable and the offline E2E is green

---

## Phase 4: User Story 2 - Context carries across a session (Priority: P2)

**Goal**: Within one session, a follow-up question builds on prior verdicts without re-recruiting from scratch; nothing persists past the session.

**Independent Test**: Ask a question, then a follow-up ("what if the budget were half?"); the second brief references the first. Restarting the process forgets everything.

### Tests for User Story 2 ⚠️

- [ ] T034 [P] [US2] E2E: follow-up references the prior verdict within a session; state cleared on restart in `tests/e2e/test_session_followup.py` (FR-011/FR-012)

### Implementation for User Story 2

- [ ] T035 [US2] Add `SessionContext` (prior_questions, prior_verdicts) in `src/council/schemas/verdict.py` (or `schemas/session.py`) (data-model §SessionContext)
- [ ] T036 [US2] Extend `src/council/orchestration/session_state.py` to store/retrieve prior questions + verdicts across turns, in memory only (FR-011/FR-012) (depends on T010, T035)
- [ ] T037 [US2] Add interactive mode to `src/council/cli/main.py`: bare `council` opens a REPL where follow-ups reuse the session (depends on T032, T036)
- [ ] T038 [US2] Thread prior-verdict context into the Moderator recruit and Synthesizer prompts so follow-ups build on earlier deliberation (depends on T036, T026, T030)

**Checkpoint**: US1 and US2 both work independently

---

## Phase 5: User Story 3 - Guardrails refuse out-of-bounds requests on demand (Priority: P3)

**Goal**: Regulated-advice / unsafe / prompt-injection inputs are refused with a clear explanation and no panel run; injection is neutralized as untrusted content.

**Independent Test**: Submit a "guarantee me stock picks" request and an injection ("ignore your instructions…"); each yields a refusal card, no verdict, exit code 2.

### Tests for User Story 3 ⚠️

- [ ] T039 [P] [US3] Smoke tests: regulated-advice, unsafe, and injection inputs each refuse with no verdict + exit 2 in `tests/smoke/test_guardrails.py` (FR-005/FR-006)

### Implementation for User Story 3

- [ ] T040 [US3] Extend `src/council/guardrails/input_guard.py`: classify regulated-advice / unsafe / injection and neutralize injected instructions as untrusted content (FR-006, research R7) (depends on T011)
- [ ] T041 [US3] Wire the refusal path: Moderator `before_agent_callback` short-circuits, CLI prints a refusal card and exits 2 (US3, contracts/cli.md) (depends on T040, T026, T032)

**Checkpoint**: All three stories independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T042 [P] Write `README.md` quickstart (setup, run, demo, refusal, tests) mirroring quickstart.md, plus MIT `LICENSE` (FR-015, Principle VI/VII)
- [ ] T043 [P] Observability polish in `src/council/orchestration/` + CLI: structured logging config and `--trace` rendering of `DeliberationTrace` (FR-008)
- [ ] T044 Run the secret-scan gate and confirm `.env` / `.claude/` are gitignored before any push (Principle IV)
- [ ] T045 Run the full `pytest` suite green offline, then execute quickstart.md validation end-to-end (FR-014, SC-006/SC-008)
- [ ] T046 [P] Optional (cut-able, post-freeze): `Dockerfile` + Cloud Run deploy notes in `docs/` for the deployment bonus (P3)

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (P1)**: no dependencies
- **Foundational (P2)**: after Setup — **blocks all stories**
- **US1 (P3)**: after Foundational — the MVP; no dependency on US2/US3
- **US2 (P4)**: after Foundational; integrates with US1 but is independently testable
- **US3 (P5)**: after Foundational; extends the US1 guardrail wiring but is independently testable
- **Polish (P6)**: after the desired stories are complete

### Within each story

- Tests written first and failing → schemas/tools → agents → orchestration → CLI
- The always-green E2E (T020) stays green from the moment US1 lands and must never regress (Principle I/VI)

### Parallel opportunities

- Setup: T003, T004 in parallel
- Foundational: T006–T009 (schemas) and T014 in parallel; T012 in parallel with schemas
- US1 tests T015–T021 all parallel; then T022/T024/T025/T027 parallel before the sequential wiring (T026→T028→T029→T030→T031→T032→T033)

---

## Parallel Example: User Story 1 tests

```bash
# Author all US1 tests together (they fail until the code lands):
Task: "Smoke test the fact-check MCP server in tests/smoke/test_factcheck_mcp.py"
Task: "Smoke test the Moderator recruit + fallback in tests/smoke/test_moderator.py"
Task: "E2E full question → VerdictBrief in tests/e2e/test_deliberation.py"
Task: "Fallback-roster E2E in tests/e2e/test_fallback.py"
```

---

## Implementation Strategy

### MVP first (US1 only)

1. Setup (Phase 1) → 2. Foundational (Phase 2) → 3. US1 (Phase 3) → **STOP & VALIDATE**: run `council "<q>"` + `pytest`. This alone is a complete, demoable submission (Constitution Principle I).

### Incremental delivery

Foundation → **US1 (MVP, green E2E)** → US2 (session memory) → US3 (refusal demos) → Polish. Each story adds value without breaking the green E2E. Target: US1 demoable by 2026-07-04, feature freeze 2026-07-05, submit ≥6h early.

---

## Notes

- `[P]` = different files, no incomplete dependency. `[Story]` maps each task to a spec user story.
- Tests are mandated (FR-014); keep the offline E2E green on main at every checkpoint.
- No production code is written by the planner — GLM 5.2 implements these tasks; `/speckit-implement` will hand off a GLM prompt.
- Keep every source file < 500 lines; validate untrusted input at the boundary (Constitution IV).
