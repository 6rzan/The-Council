# Quickstart: The Council

Proves the feature works end-to-end and that a stranger can reproduce it (FR-015, SC-006). This is
a **validation/run guide** — implementation lives in `tasks.md` + the implement phase.

## Prerequisites

- Python **3.11+**
- A free **Google AI Studio** API key (https://aistudio.google.com/apikey) — free tier is enough
- Internet access (Gemini + Wikipedia); no other accounts, no billing, no cloud project
- Any modern browser (the UI is a single localhost page — no npm, no build step)

## Setup

```bash
# 1. create + activate a virtual environment
python -m venv .venv
# Windows:  .venv\Scripts\activate    macOS/Linux:  source .venv/bin/activate

# 2. install pinned dependencies
pip install -r requirements.txt

# 3. configure the key (never commit .env)
cp config/.env.example .env      # Windows: copy config\.env.example .env
# edit .env and set GOOGLE_API_KEY=<your key>   (GOOGLE_GENAI_USE_VERTEXAI=FALSE)
```

`.env` and `.claude/` are gitignored; run the secret-scan gate before any push (Principle IV).

## Run the demo (P1 happy path — SC-001/SC-002)

```bash
council            # or: python -m council
```

This starts a local server and opens your browser (if it doesn't, visit the printed URL —
default `http://127.0.0.1:8400`). If `GOOGLE_API_KEY` is missing the launcher explains what to
set and exits with code `3` — the server never starts without a key.

In the page, ask:

> Should a mid-size city ban gas leaf blowers by 2030?

Expected, streamed live into the page:

1. **Panel assembly** — 3 panelist cards appear one-by-one, each with a one-line recruitment
   reason; at least one carries a **challenger badge**. If recruitment fails you instead see a
   "using fallback panel" notice and the run still completes (FR-016).
2. **Debate** — 2 rounds; each panelist has a stable color; rebuttals are visually highlighted
   (A2A).
3. **Fact-checks** — factual claims get a status badge + a clickable Wikipedia source link.
4. **Verdict Brief card** — positions per side, recommendation, a confidence meter, dissents,
   and a **Download JSON** button (machine-readable brief).

Open the **trace drawer** to see the full ordered `DeliberationTrace` (FR-008).

## Validate the guardrail refusal (US3 / FR-005)

Ask in the same page:

> Tell me exactly which stocks to buy tomorrow to guarantee profit

Expected: a **refusal card** explaining the out-of-bounds reason; **no panel appears** and no
debate runs.

## Validate session context (P2 / FR-011)

After the leaf-blower verdict, ask a follow-up in the same page ("what if the budget were half
that?"). The page reuses its `session_id`, so the second verdict references the first without
re-recruiting from scratch. Session state is in memory only and discarded when the server stops
(FR-012).

## Run the tests (must be green — FR-014, Principle VI)

```bash
pytest                      # all: unit + smoke + e2e (offline, deterministic, free)
pytest tests/e2e            # full question → SSE stream → VerdictBrief (fake model + mocked Wikipedia, ASGI TestClient)
pytest tests/smoke          # per-agent + per-MCP-tool smoke tests
```

The default suite makes **no live API calls and needs no browser** — it injects a fake model,
mocks the fact-check MCP, and drives the web API with an in-process ASGI TestClient, so it is
deterministic and costs nothing. An opt-in live check (`pytest -m live`, requires
`GOOGLE_API_KEY`) exercises the real Gemini + Wikipedia path.

## Success = all true

- [ ] `council` opens the page; a question streams recruit → debate → fact-check → Verdict Brief in < 2 min (SC-008)
- [ ] Every fact-check row shows a real source link or an explicit "uncertain" (FR-004)
- [ ] An out-of-bounds request shows a refusal card with no panel run (US3)
- [ ] `pytest` is fully green offline (FR-014)
- [ ] Fresh clone + these steps reproduce the demo with only a free API key (SC-006)
