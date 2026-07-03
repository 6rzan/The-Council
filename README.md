# The Council — A Self-Assembling Deliberation Engine

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Google ADK](https://img.shields.io/badge/Google%20ADK-2.3.0-orange.svg)](https://google.github.io/adk-docs/)
[![MCP](https://img.shields.io/badge/MCP-1.28.1-green.svg)](https://modelcontextprotocol.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.138-009688.svg)](https://fastapi.tiangolo.com/)
[![model: gemini-2.5-flash](https://img.shields.io/badge/model-gemini--2.5--flash-4285F4.svg)](https://ai.google.dev/)
[![tests: 50 offline](https://img.shields.io/badge/tests-50%20offline-brightgreen.svg)](#run-the-tests-must-be-green-offline--fr-014)

> **Ask a question → the Council assembles a bespoke expert panel → they debate
> across rounds → claims are fact-checked against Wikipedia via MCP → you get a
> balanced Verdict Brief with cited sources** — all streamed live to a
> self-contained web UI. No frontend build step, no paid services.

### Highlights

- 🤖 **Multi-agent orchestration** — Moderator, Panelists, Fact-Checker &
  Synthesizer on Google ADK, driven by a bounded deliberation loop.
- 🔌 **Genuine MCP integration** — a local stdio fact-check server
  (`MCPToolset`) grounds claims in keyless Wikipedia.
- 🛡️ **Guardrails by design** — an ADK callback refuses regulated advice,
  unsafe content & prompt-injection *before any panel runs*.
- 🧠 **Session memory** — follow-ups build on prior verdicts via
  `InMemorySessionService` (in-memory only, nothing persisted).
- 📡 **Live SSE streaming** — every event flows to a self-contained UI (inline
  CSS/JS, no CDN) with an ordered trace drawer.
- 🧩 **Structured outputs** — typed `PanelRoster`, `PanelistTurn`, `Claim` &
  `VerdictBrief` end-to-end (ADK R6 gotcha handled).
- ✅ **50 offline tests** — deterministic; no API key or browser required.

```
 ┌──────────┐   ┌────────────┐   ┌───────────────┐   ┌────────────┐   ┌────────────┐
 │Moderator │──▶│ Panelists  │──▶│  Fact-Checker  │──▶│  Synthesizer│──▶│VerdictBrief│
 │ (recruit)│   │ (N rounds) │   │ (MCP/Wikipedia)│   │  (structured)│   │  + trace   │
 └──────────┘   └────────────┘   └───────────────┘   └────────────┘   └────────────┘
        ▲ guardrail callback refuses regulated/unsafe/injection inputs before any panel runs
```

## Why

Policy questions deserve more than a single-answer oracle. The Council models a
**deliberative process**: divergent expert perspectives, visible rebuttals,
grounded fact-checks, and an explicit confidence call. It showcases multi-agent
orchestration, MCP tool interop, structured outputs, sessions/memory, and
security guardrails in one reproducible app.

## Prerequisites

- Python **3.11+** (developed on 3.12)
- A free **Google AI Studio** API key — https://aistudio.google.com/apikey
- Internet access (Gemini + Wikipedia); no other accounts, billing, or cloud project
- Any modern browser (the UI is one localhost page — no npm, no build step)

## Setup

```bash
# 1. create + activate a virtual environment
python -m venv .venv
# Windows:  .venv\Scripts\activate    macOS/Linux:  source .venv/bin/activate

# 2. install pinned dependencies
pip install -r requirements.txt
pip install -e . --no-deps   # install the `council` package (editable)

# 3. configure the key (NEVER commit .env)
cp config/.env.example .env      # Windows: copy config\.env.example .env
# edit .env and set GOOGLE_API_KEY=<your key>   (GOOGLE_GENAI_USE_VERTEXAI=FALSE)
```

`.env` and `.claude/` are gitignored. A secret-scan gate
(`scripts/secret-scan.sh`) runs in CI and as a pre-commit hook (install once:
`git config core.hooksPath .githooks`).

## Run the demo

```bash
council            # or: python -m council
```

Starts a local server (default `http://127.0.0.1:8400`) and opens your browser.
If `GOOGLE_API_KEY` is missing the launcher explains what to set and exits code
`3` — the server never starts without a key.

In the page, ask:

> Should a mid-size city ban gas leaf blowers by 2030?

Expected, streamed live:

1. **Panel assembly** — panelist cards appear one-by-one with a recruitment
   reason; ≥1 carries a **challenger badge**. If recruitment fails you see a
   "fallback panel" notice and the run still completes (FR-016).
2. **Debate** — 2 rounds; each panelist has a stable color; rebuttals are
   visually highlighted (agent-to-agent signal).
3. **Fact-checks** — claims get a status badge + a clickable Wikipedia source.
4. **Verdict Brief card** — positions per side, recommendation, confidence
   meter, dissents, and **Download JSON**.
5. Open the **trace drawer** for the full ordered `DeliberationTrace` (FR-008).

Flags: `--port N`, `--quiet` (WARNING logs), `--verbose` (DEBUG logs).

### Validate the guardrail refusal (US3)

Ask: `Tell me exactly which stocks to buy tomorrow to guarantee profit` → a
**refusal card** explaining the reason; **no panel appears**, no debate runs.
Injection attempts (`ignore your instructions…`) are treated as untrusted
content and refused; medical/legal advice is likewise refused.

### Validate session context (US2)

After a verdict, ask a follow-up in the same page. The page reuses its
`session_id`, so the second verdict references the first. Session state is
in-memory only and discarded when the server stops (FR-012).

## Run one agent in isolation (FR-013/FR-015)

Each agent is independently addressable — useful for debugging and reproducible
checks. `scripts/run_one_agent.py` drives a single agent turn with the real
model and prints both the final text and the structured output:

```bash
# Moderator recruits a panel (structured PanelRoster)
python scripts/run_one_agent.py moderator "Should a city ban gas leaf blowers by 2030?"

# Fact-Checker gathers evidence via the MCP/Wikipedia toolset (free-form)
python scripts/run_one_agent.py factchecker "Claim: leaf blowers emit disproportionate pollutants."

# Structurer maps free-form evidence into typed Claims
python scripts/run_one_agent.py structurer "Claim: the sky is blue. Verdict: supported."

# Synthesizer authors a VerdictBrief from a JSON payload
python scripts/run_one_agent.py synthesizer '{"question":"...","roster":{...},"transcript":[],"claims":[]}'
```

## Run the tests (must be green offline — FR-014)

```bash
pytest                # all: unit + smoke + e2e (offline, deterministic, free)
pytest tests/e2e      # full question → SSE stream → VerdictBrief (fake model + mocked Wikipedia)
pytest tests/smoke    # per-agent + per-MCP-tool smoke tests
```

The default suite makes **no live API calls and needs no browser** — it injects
a `ScriptedLlm` fake model, mocks the fact-check MCP transport, and drives the
web API with an in-process ASGI `TestClient`, so it is deterministic and free.

## Architecture

```
src/council/
  config.py                  bounds (MIN_PANEL=2, DEFAULT_PANEL=3, MAX_PANEL=4, MAX_ROUNDS=2,
                             FACTCHECK_TIMEOUT_S=8, MODEL=gemini-2.5-flash) + env loading
  app.py                     CouncilApp: ADK Runner + InMemorySessionService; run_agent_for_output
                             (with 429/503 retry-then-degrade so free-tier runs complete)
  logging_config.py          dictConfig logging; TraceEvents reach both log and UI (FR-008)
  agents/
    moderator.py             guard callback (refuse/clarify) + recruit (output_schema=PanelRoster)
    panelist.py              one turn (output_schema=PanelistTurn; references_prior A2A signal)
    factchecker.py           MCP toolset, NO output_schema (R6 gotcha) + claim_structurer step
    synthesizer.py           output_schema=VerdictBrief
    instructions/*.md         per-agent prompts (loaded at build time)
  guardrails/
    input_guard.py           validate_question + classify_refusal (regulated/unsafe/injection)
    claim_guard.py           strike_unsupported (never present unsupported claims as fact)
  orchestration/
    deliberation.py          bounded loop: guard→recruit→debate→fact-check→guard→synthesize
                             (FR-018 retry-once-then-degrade in 3 places; US2 prior-context threading)
    fallback.py              deterministic 3-persona roster when recruitment fails
    session_state.py         typed accessors over ADK session state (in-memory only)
  schemas/                   roster, claim, verdict, trace (PanelistTurn+DebateTurn), session
  tools/factcheck_mcp/
    server.py                FastMCP stdio server (2 tools: search_wikipedia, get_summary)
    wikipedia.py             keyless REST + MediaWiki API; timeout→empty degradation
  web/
    server.py                FastAPI: SSE stream (events 1:1 with StreamEvent kinds) + static page
    static/index.html        self-contained UI (inline CSS/JS, no CDN, <500 lines)
scripts/                     secret-scan.sh, run_one_agent.py
tests/                       unit + smoke + e2e (offline, fake model + mocked MCP)
```

### Key design decisions (see `specs/001-the-council/research.md`)

- **Bounded Python app-shell** drives ADK agents (not `LoopAgent`) — enforces
  termination (FR-009) while reasoning stays inside ADK/Gemini.
- **Local stdio MCP server** for fact-checking — genuine MCP integration
  (`MCPToolset`), least-privilege (only the Fact-Checker gets the toolset),
  keyless (Wikipedia REST).
- **Structured outputs** everywhere; the ADK gotcha (R6) that a tool-using agent
  cannot declare `output_schema` is handled by a separate no-tool structuring
  step that maps free-form evidence into `list[Claim]`.
- **Guardrails as ADK callbacks** (the "Referee") — `before_agent_callback`
  short-circuits out-of-bounds input before any panel runs.
- **Sessions/memory** via `InMemorySessionService` — follow-ups build on prior
  verdicts; nothing persists beyond the session (FR-012).

## Known limitations

- **Free-tier rate limits**: `gemini-2.5-flash` free tier allows ~5 req/min and
  ~20 req/day. A full deliberation makes ~11 LLM calls, so 1–2 runs/day can
  exhaust the daily quota. The launcher retries transient 429/503s with backoff;
  if a fact-check call is ultimately rate-limited it degrades to an "uncertain"
  claim (per the spec Edge Cases) and the run still completes. The capability is
  verified offline (mocked) and live in isolation.
- **Single provider**: Gemini-only (per the frozen spec, R4/Principle II).
  Multi-provider/per-agent-model selection was deferred to post-submission.
- **Wikipedia-only** fact-check source (by design — keyless, reproducible).
- **Localhost only** — the server binds `127.0.0.1`; not production-deployed
  (a `Dockerfile`/Cloud Run path is sketched as an optional post-freeze task).

## Team

Built by a four-person team for the **Google + Kaggle 5-Day AI Agents**
capstone. The system was designed collaboratively; implementation, integration,
and tooling were led by Tahaf.

- **Tahaf** — Team Lead & Lead Developer · GitHub [@6rzan](https://github.com/6rzan) · Kaggle [tahafahdthabit](https://www.kaggle.com/tahafahdthabit)
- **Esam Alareqi** — Contributor · GitHub [@esammostafa9-cloud](https://github.com/esammostafa9-cloud) · Kaggle [esamalareqi](https://www.kaggle.com/esamalareqi)
- **Kamila Ayub Khan** — Contributor · GitHub [@Slimyzz](https://github.com/Slimyzz) · Kaggle [kamilayubkhan](https://www.kaggle.com/kamilayubkhan)
- **Ahmad Hemedany** — Contributor · GitHub [@hemedany](https://github.com/hemedany) · Kaggle [ahmadhemedany](https://www.kaggle.com/ahmadhemedany)

## License

MIT — see [LICENSE](LICENSE).
