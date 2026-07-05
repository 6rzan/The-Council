# Tasks: Multi-Provider Model Choice & Live Deliberation UI

**Input**: Design documents from `/specs/002-multi-provider-ui/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/providers-api.md, contracts/web-ui-v2.md, quickstart.md

**Tests**: INCLUDED — mandatory, not optional. FR-015 and constitution Principle VI ("Tests in every spec") explicitly require offline smoke + E2E tests. Test tasks are written FIRST within each story and must FAIL before implementation.

**Scope note**: User Story 3 (OAuth) was **cut at plan time** per the spec's own FR-013 condition (see plan.md Summary). It has no phase and no tasks.

**Implementer note (GLM handoff)**: every task is self-contained; where a task says "per `<doc>`", that document under `specs/002-multi-provider-ui/` is the exact behavioral contract. Hard rules from the constitution: every file <500 lines; no secrets in git; offline suite (`pytest`, no key) must be green at every checkpoint; the Google-string model path stays byte-identical (FR-004/FR-014).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: dependency + config groundwork

- [x] T001 Add `litellm` to `requirements.txt`: run `pip install litellm`, pin the exact resolved version (`pip freeze`), amend the file's header comment to also cite `specs/002-multi-provider-ui/plan.md`. Verify `from google.adk.models.lite_llm import LiteLlm` imports cleanly under pinned `google-adk==2.3.0` and record the verified import path in a code comment in `src/council/providers.py` when created (research R1/R2). Acceptance: fresh `pip install -r requirements.txt` succeeds; import works.
- [x] T002 [P] Update `config/.env.example` with the new OPTIONAL variables, placeholder values only (never real keys): `COUNCIL_PROVIDER`, `COUNCIL_MODEL`, `COUNCIL_BASE_URL`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENCODE_API_KEY`, `COUNCIL_API_KEY`, each with a one-line comment (precedence: UI > env > built-in Gemini default). Acceptance: `scripts/secret-scan.sh` still passes.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: provider core + static-asset split that BOTH stories consume

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 [P] Extend `src/council/config.py` with env readers (keep `google_api_key()`/`use_vertex()`/`reset_cache()` byte-identical): `key_from_env(var: str) -> str | None` (generic, trimmed), `provider_env_default() -> tuple[str, str | None, str | None] | None` returning (`COUNCIL_PROVIDER`, `COUNCIL_MODEL` or None, `COUNCIL_BASE_URL` or None) when `COUNCIL_PROVIDER` is set, else None. All read through the existing `_settings()` cache so `reset_cache()` covers them. File stays <500 lines.
- [x] T004 Create `src/council/providers.py` implementing data-model.md exactly: `ProviderSpec` + `PROVIDERS` registry (5 entries per research R3 table, curated model lists as listed there), `ActiveProviderConfig` (pydantic; `api_key` excluded from all serialization; `__repr__`/`__str__` mask it entirely; keys/models trimmed of whitespace+newlines on intake), module-level holder with `set_active()` (last write wins) / `get_active()`, `resolve_effective()` implementing the 4-step precedence (UI → `COUNCIL_PROVIDER` env → `GOOGLE_API_KEY` env → unconfigured/None), `RunBinding` immutable snapshot + `bind_run()`, `resolve_model(binding) -> str | LiteLlm` (google → plain string, unchanged; others → `LiteLlm(model=f"{prefix}/{model}", api_key=…, api_base=…)`), `ProviderError(code, provider, message, hint)` with codes `unknown_provider|missing_key|invalid_key|invalid_model|invalid_base_url|unreachable_endpoint`, structural validators (data-model.md validation table), and an **injectable async probe** (module attribute; default = one minimal completion via the resolved model, ~10 s timeout; error classification maps auth→`invalid_key`, unknown-model→`invalid_model`, connect/timeout→`unreachable_endpoint`). Depends on T003. File <500 lines.
- [x] T005 [P] Split the static page (contracts/web-ui-v2.md Delta 1): create skeleton `src/council/web/static/app.js` and `src/council/web/static/style.css`, move the existing inline JS/CSS out of `src/council/web/static/index.html` into them (no behavior change yet), reference them same-origin, and serve them from `src/council/web/server.py` (StaticFiles mount or explicit routes for `/static/app.js`, `/static/style.css`). No CDN, no external requests, no build step. Acceptance: existing web smoke tests pass unchanged; `/`, `/static/app.js`, `/static/style.css` all return 200.

**Checkpoint**: provider core + asset split ready — user stories can begin

---

## Phase 3: User Story 1 — Choose provider, bring your own key (Priority: P1) 🎯 MVP

**Goal**: pick Google Gemini (default) / OpenAI / Anthropic / OpenCode Zen / custom endpoint, paste a key in the UI, run a full deliberation on it — no file edits, no restart.

**Independent Test**: start the app with no Google key configured anywhere, enter an OpenAI (or other non-Google) key in the settings panel, complete one full deliberation end-to-end (offline variant: fake probe + fake model at the factory seam).

### Tests for User Story 1 — write FIRST, must FAIL before implementation

- [x] T006 [P] [US1] Smoke tests in `tests/smoke/test_providers.py` (offline; fake probe; use `config.reset_cache()` + monkeypatched env): registry has the 5 ids with required fields; precedence UI→env(`COUNCIL_PROVIDER`)→env(`GOOGLE_API_KEY`→google)→unconfigured; last-write-wins on `set_active()`; key/model trim (spec edge case); `repr()`/`str()`/`model_dump()`/JSON of `ActiveProviderConfig` never contain the key value; each structural `ProviderError` code from the data-model.md validation table.
- [x] T007 [P] [US1] Smoke tests in `tests/smoke/test_provider_api.py` (FastAPI test client, fake probe injected): `GET /api/providers` response matches contracts/providers-api.md (fields, `configured` booleans, `key_source`, `active`, `configured_any`; assert the raw response text never contains any configured key); `POST /api/providers/active` happy path returns `{ok, active}`; one test per error code returning 400 with `{error: {code, provider, message, hint}}`; probe distinguishes `invalid_model` from `invalid_key`.
- [x] T008 [P] [US1] E2E test in `tests/e2e/test_provider_deliberation.py` (offline): inject fake probe, `POST /api/providers/active` with provider=`openai` + dummy key; monkeypatch the `resolve_model` factory seam (or the LiteLlm constructor) to return a `FakeLlm` from `tests/_fakes.py`; stream `GET /api/deliberate/stream` to completion; assert first SSE event is `run_config` with `provider == "openai"`, a terminal `verdict` arrives, and no event ever references a different provider (FR-016 — no silent switch).

### Implementation for User Story 1

- [x] T009 [US1] Wire the model seam in `src/council/orchestration/deliberation.py`: replace the `MODEL`-constant role map (currently lines 48–52) with models resolved from a `RunBinding` (accept the binding as a parameter to `run_deliberation`, or call `providers.bind_run()` at its top — pick one, document in docstring). Every role (moderator, panelist, factchecker, structurer, synthesizer) gets the same resolved model (FR-008). Do NOT touch the retry-then-degrade logic in `src/council/app.py` (FR-016). Acceptance: with google active, resolved values are the identical strings as before (FR-014); existing e2e/smoke tests green.
- [x] T010 [US1] Endpoints + stream binding in `src/council/web/server.py` per contracts/providers-api.md: `GET /api/providers`, `POST /api/providers/active` (structural validation → probe only when key/base_url/provider changed → store; typed 400 errors); `GET /api/deliberate/stream` now calls `bind_run()` once at stream start, emits `run_config` (`{provider, model, panel, rounds}`) as the FIRST event, and when unconfigured emits a single terminal `error` event and closes (HTTP 200). Never log request bodies. File <500 lines.
- [x] T011 [US1] Launcher/get-started gate: in `src/council/app.py` replace `has_api_key()` with `any_provider_configured()` delegating to `providers.resolve_effective()`; in `src/council/__main__.py` remove the exit-3 path and `_missing_key_message()` (server always starts; exit codes 0/1 remain — contracts/web-ui-v2.md Delta 2). Verified: no existing test pins exit-3 (research R8).
- [x] T012 [US1] Settings panel + get-started UI in `src/council/web/static/index.html`, `app.js`, `style.css` per contracts/web-ui-v2.md items 2–4: settings panel driven by `GET /api/providers` (provider select, model select + free-text override, `type="password"` key input, base-URL field only for `custom`, "configured via environment" badge with zero key reveal), Save → `POST /api/providers/active` rendering typed `message`+`hint` errors inline; get-started state when `configured_any` is false (includes the free Google AI Studio key guidance moved from the old launcher message); header provider chip populated from the `run_config` SSE event; question submission blocked while unconfigured with a pointer to exactly what is missing. Each file <500 lines.
- [x] T013 [US1] Credential-hygiene audit + green run: grep `src/` for any logging of request bodies/keys (fix if found); confirm FastAPI docs endpoints remain disabled; run `bash scripts/secret-scan.sh` and the full offline `pytest` — all green. Acceptance: T006–T008 now PASS; every pre-existing test still passes (FR-014).

**Checkpoint**: US1 fully functional — app is demoable with any supported provider. **This is the MVP.**

---

## Phase 4: User Story 2 — Live, engaging deliberation experience (Priority: P2)

**Goal**: replace the static wall of text with a live stage timeline, persona-attributed panelist cards, claim fact-check badges, a visually distinct verdict card, and an always-alive activity state — demo-video quality.

**Independent Test**: run one deliberation (offline fake-model harness or live key) and observe every pipeline stage and every panelist turn appear live as distinct visual elements, with no blank waiting period at any moment.

### Tests for User Story 2 — write FIRST, must FAIL before implementation

- [x] T014 [P] [US2] SSE/UI contract smoke tests in `tests/smoke/test_ui_contract.py` (offline, FastAPI test client): every stream's first event is `run_config`; unconfigured → exactly one terminal `error` event then close; `/`, `/static/app.js`, `/static/style.css` return 200; the served `index.html` contains no external `http://`/`https://` references (no CDN — contracts/web-ui-v2.md Delta 1); existing 001 stream event vocabulary still emitted unchanged (FR-014).

### Implementation for User Story 2

- [x] T015 [P] [US2] Live rendering logic in `src/council/web/static/app.js` per contracts/web-ui-v2.md items 1, 5–10 and the data-model.md stage-mapping table: stage-timeline state machine (`recruit`/`fallback`→Assembling panel, `turn.round`→Debate round N of M, `tool_call`→Fact-checking, `synthesize`→Synthesizing, terminal→Verdict/Refusal/Clarify/Error); panelist cards on `recruit` (name, expertise, stance, recruitment reason, challenger badge, stable per-panelist color identity) and fallback notice on `fallback`; debate feed grouped by round with `references_prior` rebuttal highlight; claim status badges with source links; verdict card (positions, recommendation, confidence meter, dissents, client-side Download JSON); refusal/clarify/error cards (error shows cause + next step, FR-012); trace drawer; `session_id` reuse for follow-ups; question bar disabled while streaming. <500 lines.
- [x] T016 [P] [US2] Visual design in `src/council/web/static/style.css`: polished dark theme; stage stepper with a **continuous CSS activity animation** on the active stage (this alone satisfies FR-010/SC-003 — no keepalives); card enter transitions; persona color identities; confidence meter; distinct verdict styling clearly separated from the debate feed (US2 acceptance #4); desktop-first. <500 lines.
- [x] T017 [US2] Final markup in `src/council/web/static/index.html`: header (title + provider chip), stage timeline, panel assembly area, debate feed, verdict area, settings panel, get-started state, trace drawer — wiring T015 element ids/classes to T016 styles. Same-origin references only. <500 lines. Depends on T015 + T016.
- [x] T018 [US2] Validate US2 acceptance scenarios #1–5 (spec.md) with a real run-through (offline fake harness from T008's setup, or a live key if available): stage change reflected ≤2 s; persona-attributed turn cards; claim statuses visible; verdict visually distinct; no dead unchanging screen at any point (SC-003). Fix any gaps found; re-run full `pytest` green.

**Checkpoint**: US1 AND US2 both work — the demo video can be recorded from this build

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T019 [P] Update `README.md`: short "Choose your AI provider" section (settings panel, supported providers, env-var alternative, precedence rule, memory-only credential note) consistent with `specs/002-multi-provider-ui/quickstart.md` and `config/.env.example` (Principle VI reproducibility).
- [x] T020 Final release gate: walk `specs/002-multi-provider-ui/quickstart.md` top-to-bottom on a clean checkout; run full offline `pytest` + `bash scripts/secret-scan.sh`; verify every touched file (`config.py`, `providers.py`, `app.py`, `__main__.py`, `deliberation.py`, `server.py`, `index.html`, `app.js`, `style.css`) is <500 lines; regression-confirm the Google-only `.env` path behaves exactly as before (FR-014: start app with only `GOOGLE_API_KEY` set — no settings interaction needed, Gemini runs).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none — start immediately; T001 ∥ T002
- **Foundational (Phase 2)**: needs T001; T003 ∥ T005; T004 after T003. BLOCKS both stories
- **US1 (Phase 3)**: needs Phase 2. Within: T006 ∥ T007 ∥ T008 first (fail) → T009 → T010 → T011 (∥ T010) → T012 → T013
- **US2 (Phase 4)**: needs Phase 2 + T010 (run_config event) and shares static files with T012 — in this single-implementer pipeline, run after US1. Within: T014 first (fail) → T015 ∥ T016 → T017 → T018
- **Polish (Phase 5)**: needs US1 + US2; T019 ∥ (start of) T020

### Parallel Opportunities

- Phase 1: T001 ∥ T002
- Phase 2: T003 ∥ T005
- US1 tests: T006 ∥ T007 ∥ T008 (three different new files)
- US1 impl: T010 ∥ T011 (different files)
- US2 impl: T015 ∥ T016 (app.js vs style.css)
- Polish: T019 ∥ T020's test run

## Implementation Strategy

**MVP = Phase 1 + Phase 2 + User Story 1 (T001–T013).** Stop at the US1 checkpoint, validate the independent test (non-Google key → full deliberation), and the feature is already demoable. US2 (T014–T018) is the demo-video polish layer and lands second. If time runs out mid-US2, the constitution's cut rule applies: ship US1 working rather than US2 half-broken. OAuth/US3 is already cut and must not be attempted.

**Total: 20 tasks** — Setup 2, Foundational 3, US1 8 (3 test + 5 impl), US2 5 (1 test + 4 impl), Polish 2.
