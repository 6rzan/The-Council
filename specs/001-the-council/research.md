# Phase 0 Research: The Council

All Technical Context unknowns are resolved below. Each item: **Decision → Rationale →
Alternatives considered**. These decisions are binding inputs to Phase 1 and to `/speckit-tasks`.

## R1. Orchestration pattern for a bounded multi-round debate

- **Decision**: A **deterministic Python app-shell loop** (`orchestration/deliberation.py`) drives
  the deliberation: it calls the ADK `Runner` for each agent turn and threads shared session
  state. Order per run: Moderator validates + recruits roster → for each of N rounds, each
  Panelist speaks sequentially (seeing the running transcript) → Fact-Checker → Synthesizer.
- **Rationale**: Determinism makes the flow testable (FR-014), bounds guaranteed (FR-009,
  SC-007), and demoable. Reasoning still happens entirely inside ADK/Gemini agents; the shell only
  enforces control flow — matching the constitution's agents/tools/app-shell separation.
- **Alternatives**: (a) Pure LLM-driven delegation via a root agent with `sub_agents` and
  transfers — more "agentic" but non-deterministic, harder to bound and test, risk to the E2E
  gate. (b) ADK `LoopAgent`/`SequentialAgent` static tree — clean for a *fixed* panel but awkward
  with a **dynamically recruited** roster; kept as a documented fallback. (c) LangGraph — not the
  course-native stack; rejected.

## R2. Satisfying the MCP requirement (Principle III)

- **Decision**: Implement a **local MCP server over stdio** (`tools/factcheck_mcp/server.py`) that
  exposes `search_encyclopedia(query)` and `get_article_summary(title)`, and connect to it from the
  Fact-Checker agent via ADK **`MCPToolset`** (`StdioServerParameters`/`StdioConnectionParams`).
- **Rationale**: This is a genuine MCP integration (the scored course concept + constitution III),
  not a plain in-process function tool. It is least-privilege (only the Fact-Checker receives the
  toolset) and keeps the external capability behind a declared, typed tool boundary.
- **Alternatives**: (a) ADK `FunctionTool` calling Wikipedia directly — simplest, but does **not**
  satisfy the mandatory MCP integration. (b) A public remote MCP server — adds network/keys/uptime
  risk and breaks keyless reproducibility. Local stdio MCP is the sweet spot.

## R3. Keyless, free fact-check knowledge source

- **Decision**: **Wikipedia** — Action API `https://en.wikipedia.org/w/api.php` (search) +
  REST summary `https://en.wikipedia.org/api/rest_v1/page/summary/{title}` (extract). Return
  `{title, url, extract}` as citable evidence; the Fact-Checker/Synthesizer judge whether the
  extract supports each claim.
- **Rationale**: Keyless, free, highly available, broadly citable, satisfies the Reasonableness
  Standard and Principle III. Provides a real, verifiable source URL for every fact-check.
- **Alternatives**: (a) DuckDuckGo Instant Answer — sparse/inconsistent coverage. (b) Wikidata
  SPARQL — powerful but heavy to query and format. (c) Web search APIs (Bing/Serp/Tavily) — require
  keys and/or cost; rejected on keyless/free grounds. Set a per-request timeout; on failure the
  claim degrades to "uncertain — unverifiable" (spec Edge Cases).

## R4. Gemini model & access path

- **Decision**: Default model **`gemini-2.5-flash`** for all agents, accessed via **Google AI
  Studio API key** (`GOOGLE_API_KEY`, `GOOGLE_GENAI_USE_VERTEXAI=FALSE`). Synthesizer MAY optionally
  use `gemini-2.5-pro` (config flag) if quality needs it and budget allows.
- **Rationale**: Flash is fast + cheap (free-tier friendly), supporting SC-007/SC-008 and
  Principle III. AI Studio key needs no GCP project → a stranger can reproduce it (FR-015, SC-006).
- **Alternatives**: Vertex AI backend — enterprise features but requires a GCP project/billing,
  hurting reproducibility. Pro-everywhere — higher latency/cost for marginal benefit at MVP.

## R5. Deterministic, free testing of LLM agents (Principle VI)

- **Decision**: The E2E and smoke tests inject a **fake model client** returning canned,
  schema-valid responses, and a **mocked MCP fact-check** returning fixed evidence — so tests run
  offline, cost nothing, and stay green in CI. A separate opt-in "live" smoke test (skipped without
  a key) can hit the real APIs during manual verification.
- **Rationale**: Live LLM calls are non-deterministic, rate-limited, and cost money — unfit for a
  green-on-main gate. Injected fakes make the E2E a real regression guard from day 1.
- **Alternatives**: Recorded cassettes (VCR-style) — heavier to maintain for streaming LLMs.
  Live-only tests — flaky, non-reproducible, violates the always-green rule.

## R6. Structured outputs & an ADK gotcha (Principle V)

- **Decision**: Machine-consumed outputs use **Pydantic `output_schema`** on the relevant
  `LlmAgent`: **Roster** (Moderator's recruit step), **VerdictBrief** (Synthesizer). Claims are
  produced via a **no-tool structuring step**.
- **Rationale**: Structured outputs remove brittle free-text parsing. **Gotcha**: in ADK an
  `LlmAgent` that declares `output_schema` cannot also use tools/transfers. Therefore the
  **Fact-Checker** (which holds the MCP toolset) gathers evidence in free-form, and a separate
  **no-tool** step maps that evidence into the `Claim` schema. GLM must not attach `output_schema`
  to any tool-using agent.
- **Alternatives**: JSON-in-prompt + manual parsing — rejected by Principle V. One mega-agent doing
  tools + structured output — impossible per the ADK constraint above.

## R7. Guardrails as callbacks — the "Referee" (Principle IV)

- **Decision**: Implement guardrails as ADK **callbacks**: `before_agent_callback` /
  `before_model_callback` on the Moderator validate the question, refuse regulated-advice / unsafe
  requests, and neutralize prompt-injection (short-circuit with a visible refusal, no panel run);
  a `claim_guard` step strips unsupported claims before synthesis.
- **Rationale**: Callbacks are the idiomatic ADK guardrail mechanism, keep the specialist count at
  3, and still yield a visible refusal for the US3 demo. Satisfies FR-005/FR-006.
- **Alternatives**: A dedicated Referee LLM agent — pushes specialist count to 4+ and adds latency
  for logic that is largely deterministic classification.

## R8. Streaming terminal UI (FR-017)

- **Decision**: **`rich`** — live panels/spinners/tables stream panel assembly, each debate turn,
  fact-checks, and the final Verdict Brief as they happen.
- **Rationale**: The live transcript *is* the visual for the 2-minute video (SC-008); `rich` is
  lightweight and cross-platform.
- **Alternatives**: Plain `print` — least impressive. `textual` — a full TUI framework, heavier
  than needed for a linear stream. Web UI — deferred to P3 bonus per clarification.

## R9. Sessions / memory (P2, course concept)

- **Decision**: ADK **`InMemorySessionService`** holds transcript, roster, claims, and prior
  verdicts in session state; P2 follow-ups read prior verdicts from the same session. Nothing is
  written to disk.
- **Rationale**: Demonstrates the sessions/memory course concept while honoring FR-012 / Principle
  VII (no persistence beyond session). Zero-config for reproducibility.
- **Alternatives**: Persistent `DatabaseSessionService`/vector memory — violates session-only data
  handling and adds setup a stranger must reproduce; rejected for this submission.

## Course-concept coverage (rubric traceability, SC-009)

| Course concept | Where demonstrated |
|----------------|--------------------|
| Multi-agent orchestration | Moderator + Panelist/Fact-Checker/Synthesizer via the deliberation loop |
| Tools & MCP interoperability | Local stdio MCP fact-check server via `MCPToolset` |
| Agent-to-agent communication | Panelists rebut each other across rounds over shared transcript |
| Context engineering (sessions/memory) | `InMemorySessionService` state; P2 follow-ups |
| Guardrails & security | ADK callbacks: validation, refusal, injection neutralization, claim striking |
| Observability | Structured `DeliberationTrace` + streamed CLI + ADK events |
| (Bonus) Effective Gemini use | `gemini-2.5-flash` with structured outputs/function calling |
| (Bonus) Deployment | Optional Cloud Run (P3) |

**All NEEDS CLARIFICATION resolved. Ready for Phase 1.**
