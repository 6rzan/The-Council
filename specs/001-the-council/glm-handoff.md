# GLM 5.2 Implementation Handoff — The Council

> Paste everything below this line into GLM 5.2 as its instruction, with the repository open.

---

You are the sole implementation engineer for **The Council — A Self-Assembling Deliberation
Engine**, a Google + Kaggle "AI Agents: Intensive Vibe Coding" capstone submission. All design
work is complete and frozen. Your job is to write **all** the code, exactly as specified, on
branch `001-the-council`.

## Read these first, in this order (they are the spec — do not improvise around them)

1. `.specify/memory/constitution.md` — the 7 binding principles
2. `specs/001-the-council/spec.md` — what the product must do (FRs, user stories, edge cases)
3. `specs/001-the-council/plan.md` — architecture, dependency list, exact source tree
4. `specs/001-the-council/research.md` — binding technical decisions R1–R9 (incl. the ADK gotcha)
5. `specs/001-the-council/data-model.md` — every Pydantic model, enum, validator, and bound
6. `specs/001-the-council/contracts/` — `web-ui.md` (SSE + page contract), `mcp-factcheck.md`
   (MCP tool contract), `agent-io-schemas.md` (per-agent typed I/O)
7. `specs/001-the-council/quickstart.md` — what a stranger must be able to do when you're done
8. `specs/001-the-council/tasks.md` — **your work queue: T001–T048**

## Working rules (non-negotiable)

- Execute tasks in **phase order, then ID order**, respecting each task's stated `(depends on …)`
  list. Tasks marked `[P]` may be batched. Within each user story, **write the tests first** and
  see them fail before implementing.
- **NEVER modify anything under `specs/` or `.specify/`**, with exactly one exception: checking
  a task's box from `- [ ]` to `- [x]` in `tasks.md` when that task is truly done (its tests
  pass). Do not reword tasks, do not "fix" the spec — if a spec seems wrong or ambiguous, STOP
  and report it (see report format below) instead of deciding yourself.
- **Never create, edit, or commit** `.env` or any file containing a key/secret. The only
  key-related file you create is `config/.env.example` with empty values (T003). `.env` and
  `.claude/` must be in `.gitignore` before anything else is committed.
- Code goes in `src/council/`, tests in `tests/`, per the exact tree in `plan.md` — no files in
  the repo root except standard project files (`pyproject.toml`, `requirements.txt`, `README.md`,
  `LICENSE`, `.gitignore`).
- **Every source file < 500 lines.** Split before you exceed it.
- **No dependencies beyond the pinned list** in T002: `google-adk`, `google-genai`, `mcp`,
  `httpx`, `pydantic`, `fastapi`, `uvicorn`, `python-dotenv`, `pytest`, `pytest-asyncio`.
  No `rich` (that decision was superseded), no npm, no JS packages, no CDN.
- The **default `pytest` suite runs fully offline** — fake model client, mocked Wikipedia/MCP,
  ASGI TestClient (fixtures in T013). It must never require a network, an API key, or a browser.
  Live checks exist only behind the opt-in `live` marker.
- Validate untrusted input at **every** boundary: the user's question, tool arguments, and
  tool/LLM **outputs** (Wikipedia extracts are untrusted data — quote them, never execute them).

## Gotchas that will bite you if you skip the docs

1. **ADK `output_schema` vs tools (research R6)**: an `LlmAgent` that declares `output_schema`
   CANNOT hold tools. The Fact-Checker holds the MCP toolset and returns free-form evidence; a
   **separate no-tool step** structures it into `list[Claim]`. Never attach `output_schema` to a
   tool-using agent.
2. **Least-privilege MCP**: only the Fact-Checker gets the `MCPToolset`. No other agent may see
   the Wikipedia tools.
3. **FR-018 retry-once-then-degrade, three places**: invalid recruited roster → retry once →
   deterministic fallback roster (`source=fallback`); unparseable claim → retry once → that claim
   becomes `uncertain`; invalid VerdictBrief → retry once → minimal well-formed brief. A model
   failure must never crash or hang the run.
4. **TraceEvent → SSE mapping is 1:1** (`contracts/web-ui.md`): stream kinds
   `recruit|turn|tool_call|guardrail|synthesize|fallback|error` plus exactly one terminal event
   per stream: `verdict`, `refusal`, or `clarify`. The E2E (T020) asserts this order.
5. **Bounds live in `config.py` only**: `MIN_PANEL=2, DEFAULT_PANEL=3, MAX_PANEL=4, MAX_ROUNDS=2,
   FACTCHECK_TIMEOUT_S=8, MODEL="gemini-2.5-flash"`. The web layer clamps query params to these
   server-side; never trust the page's values.
6. **`index.html` is ONE self-contained file**: inline CSS + JS, `EventSource`, no CDN, no build
   step, no external requests, and it too stays under 500 lines. All UI requirements (panelist
   cards with recruitment reasons + challenger badge, per-panelist colors, rebuttal highlighting,
   fact-check badges + source links, Verdict Brief card + confidence meter + Download JSON,
   collapsible trace drawer, refusal/clarify cards) are in `contracts/web-ui.md` §UI requirements.
7. **Guardrails are ADK callbacks, not a fifth agent** (research R7): refusal short-circuits
   before any panel runs and surfaces as the `refusal` SSE event.
8. **Session state is in-memory only** (`InMemorySessionService`): nothing is ever written to
   disk; a server restart forgets everything.

## Checkpoint gates — stop and verify at each

- **After Phase 2**: `pytest tests/unit` green offline.
- **After Phase 3 (US1)**: full `pytest` green offline; then `council` starts, opens the browser,
  and a real question (with your own key in a local, uncommitted `.env`) streams recruit → debate
  → fact-checks → Verdict Brief. The missing-key path exits 3 with a friendly message.
- **After Phase 5 (US3)**: the "guarantee me stock picks" prompt yields a refusal card and no
  panel events, in both the TestClient test and the real browser.
- **After Phase 6**: everything in `quickstart.md`'s "Success = all true" checklist passes from a
  fresh clone.

If you must trim scope for time: **cut US2 (Phase 4), never US3** — the refusal path and the
writeup are submission-required (tasks.md §Implementation Strategy).

## Report back after every phase (this goes to the reviewing planner)

```
PHASE <n> REPORT
Tasks completed: T0xx–T0yy (boxes checked in tasks.md)
pytest: <PASS/FAIL — paste the summary line>
Deviations from spec: <none, or exact file + what and why>
Blocked / ambiguous: <none, or the task ID + the question you need answered>
Files created/changed: <list>
```

Do not proceed past a FAIL or a blocking ambiguity — report it and wait.
