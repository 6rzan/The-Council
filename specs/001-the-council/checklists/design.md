# Design Quality Checklist: The Council — A Self-Assembling Deliberation Engine

**Purpose**: Post-plan requirements & design quality gate — "unit tests for English" over spec.md
+ plan.md/research.md/data-model.md/contracts before `/speckit-tasks`
**Created**: 2026-07-03
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md)
**Depth**: Standard (reviewer gate) · **Audience**: author + reviewer, pre-tasks

> Each item tests whether the *requirements/design are well-written* (complete, clear, consistent,
> measurable), NOT whether code works. Check `[x]` when the underlying spec/plan text satisfies it.

## Requirement Completeness

- [ ] CHK001 Are the bounds of a complete deliberation (min/max panelists, max rounds) specified numerically? [Completeness, Spec §FR-009, data-model bounds]
- [ ] CHK002 Are the validity conditions for a recruited roster (size range, ≥1 challenger, unique names) fully enumerated before fallback applies? [Completeness, Spec §FR-010/FR-016]
- [ ] CHK003 Are all required fields of the Verdict Brief artifact enumerated? [Completeness, Spec §FR-007, §Key Entities]
- [ ] CHK004 Is the fact-check status vocabulary (supported / unsupported / uncertain) defined with the condition that produces each? [Completeness, data-model ClaimStatus]
- [ ] CHK005 Are requirements documented for every course concept the submission claims (orchestration, MCP, A2A, memory, guardrails, observability)? [Completeness, Spec §SC-009, research coverage table]
- [ ] CHK006 Is it specified what session context carries into a follow-up (prior questions, prior verdicts) and what is discarded? [Completeness, Spec §FR-011/FR-012]
- [ ] CHK007 Is the single required MCP integration and its two tool operations documented as requirements, not just implementation notes? [Completeness, Constitution III, contracts/mcp-factcheck.md]

## Requirement Clarity

- [ ] CHK008 Is "self-assembling / recruits its own panel" defined by observable criteria (a stated persona + recruitment reason per panelist)? [Clarity, Spec §US1/FR-010]
- [ ] CHK009 Is the recruitment-succeeded vs recruitment-failed→fallback boundary defined by objective conditions rather than judgment? [Ambiguity, Spec §FR-016]
- [ ] CHK010 Is "out-of-bounds request" broken into concrete categories (regulated advice, unsafe, prompt-injection) rather than a vague label? [Clarity, Spec §US3/FR-005/FR-006]
- [ ] CHK011 Is "grounded against a public knowledge source" specified testably (a real source reference, or an explicit "uncertain" when none found)? [Clarity, Spec §FR-004]
- [ ] CHK012 Is "strike unsupported claims" expressed as an objective rule tied to fact-check status? [Clarity, Spec §FR-005, data-model Claim rule]

## Requirement Consistency

- [ ] CHK013 Does the plan's "Referee = ADK callbacks" mapping stay consistent with every spec reference to a Referee/guardrail role? [Consistency, plan Referee note vs Spec §US3/FR-005]
- [ ] CHK014 Is the specialist-agent count consistent between Constitution II ("2–4 specialists") and the plan (root + 3 specialists)? [Consistency, Constitution II / plan]
- [ ] CHK015 Are entity names consistent across Spec Key Entities, data-model.md, and agent-io-schemas.md? [Consistency]
- [ ] CHK016 Do the web UI refusal requirements (refusal event → card, no panel run) align with the guardrail refusal requirements in the spec? [Consistency, contracts/web-ui.md vs Spec §US3/FR-005]

## Acceptance Criteria & Measurability

- [ ] CHK017 Is each Success Criterion (SC-001..SC-009) objectively measurable without referencing implementation internals? [Measurability, Spec §Success Criteria]
- [ ] CHK018 Is the demo/performance target tied to a defined scenario scope (recruit + N rounds × M panelists + fact-check + synthesis)? [Measurability, Spec §SC-008 / plan Performance Goals]
- [x] CHK019 Is "≥2 positions for a substantive question" backed by a testable notion of "substantive"? [Ambiguity, Spec §SC-002] — resolved 2026-07-03: "substantive" defined in §Assumptions
- [ ] CHK020 Can "stranger-reproducible" be verified against an enumerated setup that needs only a free API key? [Measurability, Spec §FR-015/SC-006, quickstart]

## Scenario Coverage

- [ ] CHK021 Are requirements defined for the primary happy-path deliberation end-to-end? [Coverage, Spec §US1]
- [ ] CHK022 Are alternate-path requirements defined for a deliberation that runs on the fallback roster? [Coverage, Spec §FR-016]
- [ ] CHK023 Are exception-path requirements defined for an unreachable / timed-out knowledge source? [Coverage, Exception, Spec §Edge Cases]
- [ ] CHK024 Are requirements defined for a deadlocked "no clear winner" debate outcome? [Coverage, Spec §Edge Cases]
- [x] CHK025 Are degradation/recovery requirements defined when the model returns invalid structured output? [Coverage, Gap, research R6] — resolved 2026-07-03: §Edge Cases + FR-018 (retry-once → graceful degrade)

## Edge Case Coverage

- [ ] CHK026 Are requirements defined for empty / whitespace / oversized question input at the trust boundary? [Edge Case, Spec §FR-006, data-model Question]
- [ ] CHK027 Are requirements defined for prompt-injection content inside the question (neutralize as content, never execute)? [Edge Case, Spec §FR-006, research R7]
- [ ] CHK028 Is the behavior for a claim with no supporting source specified as "degrade to uncertain," not silently dropped? [Edge Case, Spec §FR-004]

## Non-Functional Requirements

- [ ] CHK029 Is observability specified as a concrete artifact (ordered deliberation trace with defined event kinds)? [Completeness, Spec §FR-008, data-model Trace]
- [ ] CHK030 Are secret-handling requirements specified (env-only, `.env`/`.claude` gitignored, secret-scan before push)? [Completeness, Constitution IV, plan Constraints]
- [ ] CHK031 Are data-privacy requirements specified (synthetic/public only, in-memory session, no persistence)? [Completeness, Spec §FR-012, Constitution VII]
- [ ] CHK032 Are cost/licensing constraints specified (keyless source, free-tier model, OSI-approved deps)? [Completeness, Constitution III/VII]

## Dependencies, Assumptions & Conflicts

- [ ] CHK033 Is the assumption "the public knowledge source is available and keyless" documented with a degradation path? [Assumption, Spec §Assumptions / Edge Cases]
- [ ] CHK034 Are external dependencies (ADK, Gemini free tier, Wikipedia, MCP SDK) documented with their access requirements? [Dependency, plan Technical Context / research]
- [ ] CHK035 Is the mandatory-test requirement unambiguous that smoke + E2E stay green offline without live API calls? [Clarity, Spec §FR-014, research R5]
- [ ] CHK036 Is the tension between "full self-assembly in P1" and the always-green gate explicitly resolved by the fallback roster? [Conflict, Spec §US1/FR-016 vs Constitution I]

## Notes

- Check items off as the spec/plan text is confirmed to satisfy them; annotate findings inline.
- `[Gap]`/`[Ambiguity]`/`[Conflict]`/`[Assumption]` mark items testing for something *missing or
  unresolved* rather than validating existing text.
- This is a design-stage gate; the spec-stage checklist is [requirements.md](./requirements.md).
