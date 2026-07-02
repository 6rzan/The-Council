# Contract: Agent I/O Schemas

Every agent is runnable in isolation (Principle V) with a typed input and a typed/structured
output. Schemas reference the Pydantic models in `data-model.md`. **Reminder (research R6):** any
agent that declares `output_schema` MUST NOT hold tools; the Fact-Checker (tool-using) therefore
returns free-form evidence that a separate no-tool step maps into `Claim`s.

## Moderator (root) — two responsibilities

### 1. Guardrail gate (before recruit)
- **In**: `Question.text` (untrusted).
- **Out**: `{ allowed: bool, refusal_reason: str | None }`.
- **Behavior**: implemented as `before_agent_callback` / validators; on `allowed=false` the run
  short-circuits with a visible refusal card and exit code 2 (no panel runs). Neutralizes prompt
  injection (treats embedded instructions as content, never as commands).

### 2. Recruit step (structured)
- **In**: `Question.text`.
- **Out (`output_schema=PanelRoster`)**: `PanelRoster` — 2–4 `Panelist`s, ≥1 challenger, each with
  a `recruitment_reason`.
- **Failure → fallback**: if the model errors or returns an invalid/degenerate roster, the shell
  substitutes the deterministic fallback roster (`source=fallback`) and continues (FR-016).

## Panelist (specialist, N instances)

- **In**: `{ persona: Panelist, question: str, transcript: list[DebateTurn], round: int }`.
- **Out**: `{ content: str, references_prior: bool }` (free-form argument; `references_prior=true`
  when it rebuts a named prior turn — the A2A signal).
- **Isolation test**: given a fixed persona + transcript, returns a non-empty argument.

## Fact-Checker (specialist, holds MCP toolset — NO output_schema)

- **In**: `{ transcript: list[DebateTurn] }` (extracts candidate factual claims).
- **Tools**: `search_encyclopedia`, `get_article_summary` (MCP; see `mcp-factcheck.md`).
- **Out**: free-form evidence notes per claim: `{ claim, verdict_text, source_title, source_url,
  extract }`.
- **Structuring step (separate, no tools, `output_schema=list[Claim]`)**: maps the evidence notes
  into typed `Claim`s with `status ∈ {supported, unsupported, uncertain}`. Unreachable source →
  `uncertain` (FR degrade path).

## Synthesizer (specialist — structured, NO tools)

- **In**: `{ question: str, roster: PanelRoster, transcript: list[DebateTurn],
  claims: list[Claim] }` (claims already filtered by `claim_guard` — no `unsupported` passed as
  fact).
- **Out (`output_schema=VerdictBrief`)**: complete `VerdictBrief` (positions ≥2 for a substantive
  question, `fact_checks`, recommendation, confidence, dissents).
- **Isolation test**: given a canned transcript + claims, returns a schema-valid `VerdictBrief`.

## Guardrail: claim_guard (deterministic, between Fact-Checker and Synthesizer)

- **In**: `list[Claim]`.
- **Out**: `list[Claim]` with every `status == unsupported` removed (or demoted to a flagged note),
  guaranteeing FR-005 at the boundary regardless of model behavior.

## Cross-cutting: every agent invocation appends `TraceEvent`s

Recruit → `recruit`; each Panelist turn → `turn`; each MCP call → `tool_call`; each guardrail
decision → `guardrail`; fallback substitution → `fallback`; synthesis → `synthesize`. The ordered
`DeliberationTrace` is the observability artifact (FR-008) and streams live in the CLI.
