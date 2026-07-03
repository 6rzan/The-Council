# Phase 1 Data Model: The Council

Entities derived from the spec's Key Entities and Functional Requirements. These become the
Pydantic models in `src/council/schemas/`. Types are indicative; validation rules are binding.

## Enums

- **ClaimStatus**: `supported` | `unsupported` | `uncertain`
- **Confidence**: `high` | `medium` | `low`
- **RosterSource**: `recruited` | `fallback`  *(records how the roster was produced — FR-016)*

## Entity: Panelist

Represents one recruited expert persona.

| Field | Type | Rules |
|-------|------|-------|
| `name` | str | non-empty; ≤ 60 chars |
| `expertise` | str | non-empty; the domain/lens (e.g. "energy-systems economist") |
| `stance` | str | short description of the viewpoint they argue from |
| `recruitment_reason` | str | non-empty; one-line justification (FR-010) |
| `is_challenger` | bool | at least one Panelist in a roster MUST be `true` (FR-010) |

## Entity: PanelRoster

The assembled panel for one deliberation.

| Field | Type | Rules |
|-------|------|-------|
| `panelists` | list[Panelist] | length within `[MIN_PANEL, MAX_PANEL]` (default 3; MAX enforced per FR-009) |
| `source` | RosterSource | `fallback` when recruitment failed/invalid (FR-016) |

- **Validation**: at least one `panelist.is_challenger == True`; names unique; if the recruited
  roster fails these rules → substitute the deterministic fallback roster and set `source=fallback`.
- **Structured output**: produced by the Moderator recruit step via `output_schema=PanelRoster`.

## Entity: Question (Brief)

The user input starting a deliberation.

| Field | Type | Rules |
|-------|------|-------|
| `text` | str | non-empty after trim; length-capped; **untrusted** — passes input guardrails (FR-006) |
| `session_id` | str | ties the question to its session (P2 context) |

- Never persisted beyond the session (FR-012). Injection content is neutralized, not executed (R7).

## Entity: DebateTurn

One panelist's contribution in one round (internal transcript unit).

| Field | Type | Rules |
|-------|------|-------|
| `round` | int | 1..N (N = `MAX_ROUNDS`, default 2) |
| `panelist_name` | str | must exist in the roster |
| `content` | str | the argument / rebuttal text |
| `references_prior` | bool | true when the turn explicitly responds to another panelist (A2A evidence) |

## Entity: Claim

A factual assertion surfaced during debate and its check result.

| Field | Type | Rules |
|-------|------|-------|
| `text` | str | the asserted fact |
| `status` | ClaimStatus | set by the Fact-Checker structuring step |
| `source_title` | str \| None | required when status ≠ `uncertain` |
| `source_url` | str \| None | required when status ≠ `uncertain`; must be a real Wikipedia URL |
| `evidence` | str \| None | the extract snippet consulted |

- **Rule (FR-004/FR-005)**: a Claim with `status != supported` MUST NOT appear as an established
  fact in the Verdict Brief; `claim_guard` strips such claims before synthesis.

## Entity: Position + Dissent (Verdict components)

- **Position**: `{ label: str, strongest_argument: str }` — one per distinct side.
- **Dissent**: `{ panelist_name: str, objection: str }` — minority views retained.

## Entity: VerdictBrief

The final deliverable (FR-007). Structured output of the Synthesizer (`output_schema=VerdictBrief`).

| Field | Type | Rules |
|-------|------|-------|
| `question` | str | echoes the original question |
| `roster` | PanelRoster | who deliberated + why |
| `positions` | list[Position] | ≥ 2 for a substantive question (SC-002) |
| `fact_checks` | list[Claim] | only `supported`/`uncertain` claims; no unsupported-as-fact (FR-005) |
| `recommendation` | str | synthesized guidance; may be "no clear winner" on deadlock (Edge Cases) |
| `confidence` | Confidence | explicit level |
| `dissents` | list[Dissent] | may be empty |

## Entity: TraceEvent + DeliberationTrace (observability, FR-008)

- **TraceEvent**: `{ ts: float, kind: str, actor: str, detail: str }` where `kind` ∈
  `recruit | turn | tool_call | guardrail | synthesize | fallback | error`.
- **DeliberationTrace**: `{ events: list[TraceEvent] }` — ordered record sufficient to reconstruct
  how the verdict was reached; streamed live to the web UI (SSE) and shown in its trace panel.

## Entity: SessionContext (P2)

Held in ADK session state only (in memory).

| Field | Type | Rules |
|-------|------|-------|
| `prior_questions` | list[str] | for follow-up continuity (FR-011) |
| `prior_verdicts` | list[VerdictBrief] | referenced by later deliberations in the same session |

- Discarded at session end; never written to disk (FR-012, Principle VII).

## Relationships

```text
Session 1──* Question 1──1 Deliberation
Deliberation 1──1 PanelRoster 1──* Panelist
Deliberation 1──* DebateTurn
Deliberation 1──* Claim
Deliberation 1──1 VerdictBrief (1──* Position, 1──* Claim(fact_checks), 1──* Dissent)
Deliberation 1──1 DeliberationTrace 1──* TraceEvent
```

## Configurable bounds (config.py)

`MIN_PANEL=2`, `DEFAULT_PANEL=3`, `MAX_PANEL=4`, `MAX_ROUNDS=2`, `FACTCHECK_TIMEOUT_S=8`,
`MODEL="gemini-2.5-flash"`. All enforce FR-009 termination guarantees.
