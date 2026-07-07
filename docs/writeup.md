# The Council — Kaggle Submission Writeup

**Track:** Freestyle (flagship demo questions flex toward *Agents for Good* /
*Agents for Business*). **Status:** feature-complete — 001 core deliberation
engine + 002 multi-provider choice & live web UI; offline suite green (79
tests); live path verified component-by-component against the real Gemini API.

**Demo video:** _PASTE THE PUBLIC VIDEO URL HERE before submitting (T048)._

## The problem

Important questions — policy, civic, strategic — rarely have a single right
answer. A one-shot LLM oracle collapses them into a confident paragraph. The
Council instead models a **deliberative process**: it recruits a bespoke expert
panel for the question, runs a bounded multi-round debate with visible
rebuttals, fact-checks the claims that surfaced against Wikipedia via MCP, and
synthesizes a balanced **Verdict Brief** with cited sources, an explicit
confidence call, and recorded dissents. The whole process streams live to a
self-contained web UI with an ordered trace.

## How it works

A bounded Python **app-shell** drives Google ADK agents over a shared
`InMemorySessionService` session (research R1). Order per run:

1. **Guard gate** — an ADK `before_agent_callback` validates the question and
   refuses regulated advice / unsafe content / prompt-injection **before any
   panel runs** (US3, FR-005/FR-006). Short-circuit → terminal `refusal` SSE.
2. **Recruit** — the Moderator returns a structured `PanelRoster` (2–4
   panelists, ≥1 challenger). On invalid output: retry once, then a
   deterministic fallback roster (FR-016/FR-018).
3. **Debate** — `MAX_ROUNDS` (2) rounds × panelists, each emitting a
   `PanelistTurn` with a `references_prior` A2A signal; rebuttals are visually
   flagged. Transcript threads through shared session state.
4. **Fact-check** — the Fact-Checker (MCP toolset, keyless Wikipedia) gathers
   free-form evidence; a separate no-tool **structuring step** maps it into
   typed `Claim`s (the ADK R6 gotcha: a tool-using agent cannot declare
   `output_schema`).
5. **Claim guard** — `strike_unsupported` removes unsupported claims so they
   are never presented as established fact (FR-005).
6. **Synthesize** — the Synthesizer authors a structured `VerdictBrief`
   (positions, recommendation, confidence, dissents). Invalid output: retry
   once, then a minimal well-formed brief flagging the degradation (FR-018).

Everything is an SSE event mapped 1:1 to `TraceEvent` kinds; the UI renders
panel assembly, debate, fact-check badges, the verdict card, and a live trace
drawer (FR-008).

## Course concepts demonstrated (SC-009 — six named, target was four)

| Course concept | Where demonstrated |
|---|---|
| **Multi-agent orchestration** | Moderator + Panelist + Fact-Checker + Synthesizer, driven by the bounded deliberation loop over a shared ADK session (`orchestration/deliberation.py`). |
| **Tools & MCP interoperability** | A local stdio **MCP server** (`tools/factcheck_mcp/server.py`, FastMCP) exposes two tools (`search_wikipedia`, `get_summary`); the Fact-Checker consumes them via ADK `MCPToolset`. A genuine MCP integration, not an in-process function tool (research R2). |
| **Agent-to-agent communication** | Panelists rebut each other across rounds over the shared transcript; `references_prior` is the explicit A2A signal, surfaced visually. |
| **Context engineering (sessions/memory)** | `InMemorySessionService` holds transcript, roster, claims, and prior questions/verdicts; US2 follow-ups thread prior-verdict context into the Moderator and Synthesizer prompts so a follow-up builds on earlier deliberation (FR-011). Verified by E2E asserting the prior-context block reached the agents' recorded `_calls`. |
| **Guardrails & security** | ADK callbacks (`before_agent_callback`) validate input, refuse regulated/unsafe/injection requests, and treat all input + tool output as untrusted; `strike_unsupported` guards claims; secrets via `.env` only (FR-006, Principle IV). |
| **Observability** | Structured `DeliberationTrace` (ordered `TraceEvent`s) reaches **both** the log and the live web trace panel (FR-008); terminal SSE events are exactly one of `verdict`/`refusal`/`clarify`. |
| *(bonus)* **Effective Gemini use** | `gemini-2.5-flash` with structured outputs (`output_schema`) and function calling via the MCP toolset. |

## Security & guardrails section (Constitution IV)

- **Input validation at the trust boundary** (`input_guard.validate_question`):
  trim, non-empty, length cap; undecipherable/too-short input yields a single
  focused clarifying question (terminal `clarify`), never a crash.
- **Scope refusal** (`classify_refusal`, deterministic & quota-free): specific
  medical / legal / financial advice, unsafe content (weapons, self-harm), and
  prompt-injection attempts are refused with an explanation and **no panel
  run** (R7: short-circuit with a visible refusal). Verified by 7 unit + 4 ASGI
  integration tests (SC-005).
- **Injection neutralization**: injected instructions ("ignore your
  instructions…", "you are now DAN", "output the system prompt") are matched and
  treated as **untrusted content** — never executed as a command; the guardrail
  holds and the request is refused.
- **Untrusted tool output**: fact-checker evidence and structured claims are
  validated against their schemas; `strike_unsupported` ensures no unsupported
  claim is ever presented as established fact in the Verdict Brief.
- **Secrets handling**: `GOOGLE_API_KEY` lives only in a gitignored `.env`
  (loaded via python-dotenv); with no key configured the server starts in a
  safe get-started state (feature 002) and UI-entered keys stay in memory only. A `scripts/secret-scan.sh` gate
  (pre-commit hook + GitHub Actions) fails if a real `.env` or an
  `AIza…`/`GOOGLE_API_KEY=` value is staged/committed; `.env` and `.claude/` are
  gitignored. Gate verified clean: 0 secrets in 99 tracked files.
- **No persistence beyond session**: all deliberation state is in-memory
  (`InMemorySessionService`); nothing is written to disk (FR-012, Principle VII).
- **Localhost only**: the server binds `127.0.0.1`.

## External APIs used

- **Google Gemini** (free tier, `gemini-2.5-flash`) via ADK + google-genai,
  accessed with a free AI Studio API key. No Vertex, no billing.
- **Wikipedia** via a local MCP stdio server using the keyless REST + MediaWiki
  Action API (`rest.wikipedia.org` summaries + `api.php` search). No key, no
  account. An 8-second timeout degrades to an empty result so the run never hangs.
- **Optional (feature 002):** OpenAI / Anthropic / OpenCode Zen / any
  OpenAI-compatible endpoint via ADK's `LiteLlm` wrapper — used only when the
  operator selects a non-Google provider and supplies their own key in-page.

## Rationale & impact story

The Council makes a deliberative process **visible and grounded**: you see *who*
spoke, *in what order*, *which claims were checked* and *against what source*,
and *why* the recommendation carries the confidence it does. That transparency is
the antidote to confident-but-ungrounded single-answer oracles. The flagship
demo (a city gas-leaf-blower ban) flexes toward *Agents for Good*: a civic
policy question where cost, emissions, and ratepayer trade-offs genuinely
conflict, and a balanced, fact-checked verdict is more useful than a polemic.

## Live verification results

The full live path was verified component-by-component against the real Gemini
API (before the free-tier **daily** quota of ~20 requests for
`gemini-2.5-flash` was exhausted by debugging runs):

- ✅ Missing-key launcher path exits code 3 with a friendly message.
- ✅ Live Moderator recruit returned a valid 4-panelist `PanelRoster` with a
  challenger.
- ✅ Live debate streamed 8 turns; rebuttals flagged `references_prior`.
- ✅ Live Fact-Checker + MCP + Wikipedia returned real grounded evidence, e.g.
  source `https://en.wikipedia.org/wiki/Leaf_blower`.
- ✅ Full live stream order verified: `recruit×N → turn×N → tool_call →
  guardrail → synthesize → verdict` in ~47s (under the 2-minute target).
- ⚠️ A single clean end-to-end run capturing a verdict **with a real cited
  source** was not captured in one run because the daily quota was exhausted
  mid-debugging. Each piece is proven live; the quota resets daily (UTC
  midnight), so the one-run demo is achievable with a fresh quota. The offline
  E2E (mocked Wikipedia) proves the integrated fact-check path with real source
  links deterministically.

## Known deviations & limits

- **Free-tier rate limits**: a full run makes ~11 LLM calls vs. ~20/day quota.
  Transient 429/503s are retried with backoff (`run_agent_for_output`); a
  rate-limited fact-check degrades to an "uncertain" claim (spec Edge Cases
  explicitly allow source-unavailable degradation; the run never hangs).
- **Provider default**: Gemini stays the built-in default per the 001 spec
  (R4); feature **002** adds opt-in OpenAI / Anthropic / OpenCode Zen / custom
  OpenAI-compatible endpoints via in-page Settings or env vars — credentials
  are held in server memory only (never disk, logs, or git). OAuth account
  sign-in is intentionally out of scope.
- **Wikipedia-only** fact-check source (by design — keyless, reproducible).
- **One `tool_call` SSE event per fact-check pass** (not per individual MCP
  call) — an honest approximation noted as a deviation.
- **Localhost only**; a `Dockerfile`/Cloud Run path is an optional cut-able
  post-freeze task (T046).

## Reproduce

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt && pip install -e . --no-deps
cp config/.env.example .env   # then set GOOGLE_API_KEY=<your free AI Studio key>
council                       # opens http://127.0.0.1:8400
pytest                        # 79 tests, fully offline & free
```

See [README.md](../README.md) for the full quickstart, architecture, per-agent
isolation examples, and known limitations.
