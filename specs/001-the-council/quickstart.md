# Quickstart: The Council

Proves the feature works end-to-end and that a stranger can reproduce it (FR-015, SC-006). This is
a **validation/run guide** — implementation lives in `tasks.md` + the implement phase.

## Prerequisites

- Python **3.11+**
- A free **Google AI Studio** API key (https://aistudio.google.com/apikey) — free tier is enough
- Internet access (Gemini + Wikipedia); no other accounts, no billing, no cloud project

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
council "Should a mid-size city ban gas leaf blowers by 2030?"
```

Expected, streamed live in the terminal:
1. **Recruiting** — 3 panelists appear with a one-line reason each (≥1 challenger). If recruitment
   fails you instead see "using fallback panel" and the run still completes (FR-016).
2. **Debate** — 2 rounds; panelists visibly rebut one another (A2A).
3. **Fact-check** — factual claims get a status badge + a Wikipedia source link.
4. **Verdict Brief** — positions per side, recommendation, confidence, dissents.

Machine-readable + full trace:
```bash
council "..." --json --trace
```

## Validate the guardrail refusal (US3 / FR-005)

```bash
council "Tell me exactly which stocks to buy tomorrow to guarantee profit"
```
Expected: a **refusal card** explaining the out-of-bounds reason, **no panel runs**, exit code `2`.

## Validate session context (P2 / FR-011)

In interactive mode (`council` with no argument), ask a question, then a follow-up ("what if the
budget were half that?"). The second verdict references the first without re-recruiting from
scratch. Session state is in memory only and discarded on exit (FR-012).

## Run the tests (must be green — FR-014, Principle VI)

```bash
pytest                      # all: unit + smoke + e2e (offline, deterministic, free)
pytest tests/e2e            # full question → VerdictBrief with fake model + mocked Wikipedia
pytest tests/smoke          # per-agent + per-MCP-tool smoke tests
```

The default suite makes **no live API calls** — it injects a fake model and mocks the fact-check
MCP, so it is deterministic and costs nothing. An opt-in live check
(`pytest -m live`, requires `GOOGLE_API_KEY`) exercises the real Gemini + Wikipedia path.

## Success = all true

- [ ] `council "<question>"` streams recruit → debate → fact-check → Verdict Brief in < 2 min (SC-008)
- [ ] Every fact-check row shows a real source link or an explicit "uncertain" (FR-004)
- [ ] An out-of-bounds request is refused with no panel run (US3)
- [ ] `pytest` is fully green offline (FR-014)
- [ ] Fresh clone + these steps reproduce the demo with only a free API key (SC-006)
