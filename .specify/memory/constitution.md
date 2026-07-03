<!--
Sync Impact Report
==================
Version change: (template, unversioned) → 1.0.0
Modified principles: n/a (initial ratification — all 5 template placeholder slots replaced;
  principle count expanded from 5 to 7 per project owner's approved structure)
Added sections:
  - Core Principles I–VII (Ship the Submission First; ADK-Style Multi-Agent Architecture;
    Tools & MCP as the Only Capability Boundary; Security & Guardrails by Design;
    Prompts as Versioned Artifacts; Demonstrable Quality; Data Handling & Privacy)
  - Capstone Constraints & Compliance (replaces [SECTION_2_NAME])
  - Development Workflow & Division of Labor (replaces [SECTION_3_NAME])
  - Governance (filled)
Removed sections: none
Templates:
  - .specify/templates/plan-template.md ✅ aligned (Constitution Check gate is populated
    per-feature from this file; no structural edit required)
  - .specify/templates/spec-template.md ✅ aligned (mandatory Success Criteria section is
    where rubric traceability per Principle I is expressed; no structural edit required)
  - .specify/templates/tasks-template.md ⚠ note: template marks tests "OPTIONAL — only if
    requested in the spec". Principle VI makes smoke + E2E tests mandatory, so every spec
    MUST request them; /speckit-tasks must therefore always emit test tasks. No file edit
    made — enforced via spec content per Governance.
  - .specify/templates/commands/*.md — n/a (commands live in .claude/skills/ in this repo)
Runtime guidance docs:
  - "How to use Spec kit/Guide.md" ✅ no principle references; no update needed
  - README.md — does not exist yet; Principle VI requires it as a submission artifact
Follow-up TODOs: none (no deferred placeholders)
-->

# Kaggle Vibe Coding Agents Capstone Constitution

Governing law for the Google + Kaggle "AI Agents: Intensive Vibe Coding Capstone Project"
submission (competition: vibecoding-agents-capstone-project). This constitution is
track-agnostic: it MUST hold for any use case chosen in Agents for Good, Agents for
Business, Concierge Agents, or Freestyle. The concrete use case and track are fixed at
`/speckit-specify` time, never here.

## Core Principles

### I. Ship the Submission First (Badge Over Brilliance)

The deliverable is a valid, complete Kaggle submission — writeup, public demo video,
brief rationale, and working code repository — submitted before
**2026-07-06 11:59 PM PT**. Everything else is secondary.

- Every work item MUST trace to a rubric criterion, a required course concept, or a
  submission asset (writeup / video / repo). Work that traces to none of these MUST be cut.
- Scope trade-offs MUST cut breadth (features, extra agents, extra tools), never depth
  (working demo, security, tests, writeup). A small working system beats a large broken one.
- An end-to-end happy path MUST be demoable by end of 2026-07-04. Feature freeze is
  2026-07-05; after freeze only fixes, docs, writeup, and video work are allowed.
- The team has exactly one submission with no retries; the submission MUST be filed at
  least 6 hours before the deadline.

**Rationale**: The badge/certificate requires a complete valid submission, not a win.
With ~4 working days, unfinished ambition is the primary failure mode.

### II. ADK-Style Multi-Agent Architecture

- The system MUST be a multi-agent design: one root/orchestrator agent delegating to 2–4
  specialist agents, each with a single, nameable responsibility.
- The system MUST be built on Google ADK with Gemini as the default model family
  (course-native stack; "Effective Use of Gemini" earns rubric bonus).
- Every agent MUST be exercised by the demo happy path. An agent that never runs in the
  demo MUST be removed. Agent count is justified by role, never by optics.
- Code MUST keep three separated layers: agents (reasoning/orchestration), tools
  (capability), and app shell (I/O, session wiring). No layer reaches around another.

**Rationale**: Multi-agent orchestration is the core scored concept; ADK + Gemini is what
the course teaches and judges expect to see demonstrated, not name-dropped.

### III. Tools & MCP as the Only Capability Boundary

- All external capability (APIs, data access, computation, side effects) MUST be exposed
  as declared tools — MCP servers or ADK tool definitions — with typed parameters.
  Ad-hoc HTTP calls or file access buried inside prompts or agent bodies are forbidden.
- At least one MCP integration MUST exist in the final system (scored course concept).
- Tool assignment is least-privilege: each agent receives only the tools its role needs.
- External services and data MUST be free or minimal-cost and publicly accessible
  (competition "Reasonableness Standard"); prefer free tiers and synthetic/public data.

**Rationale**: Declared tools are what make the agent auditable, demoable, and aligned
with the Day-2 interoperability concepts the rubric scores.

### IV. Security & Guardrails by Design

- Input validation MUST exist at every trust boundary: user input, tool arguments, and
  tool/LLM outputs consumed downstream.
- Explicit guardrails MUST constrain agent behavior (allowed topics/actions, refusal
  behavior, output filtering appropriate to the chosen use case).
- Actions with external side effects MUST be either excluded from scope or gated behind
  explicit user confirmation.
- Secrets MUST never enter git: API keys via environment variables only; `.env` and any
  agent-generated credential artifacts (e.g. `.claude/`) MUST be gitignored; a
  secret-scan check MUST pass before every push.
- The writeup MUST contain a security section describing guardrails and their testing.

**Rationale**: Day-4 "Agent Quality & Security" is a scored concept and a stated judging
dimension; a leaked key or unguarded agent is both a rubric and a real-world failure.

### V. Prompts & Agent Behavior Are Versioned Artifacts

- Every agent MUST have a written system instruction defining role, available tools,
  constraints, and output format — stored in version-controlled files, not scattered
  inline string literals.
- Wherever a machine consumes model output, structured outputs (function calling /
  schemas) MUST be used instead of free-text parsing.
- Each agent MUST be runnable and demonstrable in isolation with a documented example.

**Rationale**: Versioned prompts make the multi-agent design reviewable by judges and
debuggable by a two-model (planner/implementer) team.

### VI. Demonstrable Quality (Tests, Observability, Reproducibility)

- A runnable end-to-end happy-path check MUST exist from the first implementation day
  and MUST stay green on `main`.
- Every tool and every agent role MUST have at least a smoke test, runnable with a
  single documented command.
- Agent steps (delegations, tool calls, errors) MUST be logged/traced; observability
  output doubles as demo-video material.
- The repo MUST be reproducible by a stranger on a clean machine: README quickstart,
  pinned dependencies, `.env.example`. This is a Kaggle winner's obligation, treated as
  a release gate, not an afterthought.
- "Works in the demo script" is the release bar: a feature that cannot be demoed is cut,
  not shipped broken.

**Rationale**: Judges verify via video + repo; reproducibility is contractually required
for winners and cheap to maintain from day one, expensive to retrofit.

### VII. Data Handling & Privacy

- No real personal data in the repository or demos; use synthetic or public data only.
- User data processed at runtime MUST be minimized and MUST NOT persist beyond the
  session unless the spec explicitly requires it.
- Every external API and dataset used MUST be documented in the writeup with its access
  terms.
- Nothing may enter the submission that cannot be licensed under CC-BY 4.0 (winner
  license); dependencies MUST carry OSI-approved licenses without commercial-use limits.
  The repository license is MIT and MUST remain OSI-approved.

**Rationale**: Privacy failures disqualify credibility instantly; the CC-BY 4.0 winner
license makes licensing hygiene a hard legal requirement of the competition rules.

## Capstone Constraints & Compliance

Non-negotiable facts this project operates under (source: official competition rules and
timeline, confirmed 2026-07-02):

- **Deadline**: final submission 2026-07-06 11:59 PM PT. One (1) submission per team;
  team size ≤ 5.
- **Submission package**: Kaggle writeup + public video explanation (viewable without
  login) + brief rationale + link to the code repository.
- **Course concepts**: the system MUST implement and the writeup MUST explicitly name at
  least three (3) course concepts; target four or more. Qualifying concepts:
  multi-agent orchestration, tools/function-calling, MCP interoperability,
  agent-to-agent communication, sessions/memory/skills (context engineering),
  guardrails & security evaluation, observability, deployment.
- **Bonus criteria** (SHOULD, if timeline allows after freeze gates pass): effective
  Gemini use (satisfied via Principle II) and cloud deployment (e.g. Cloud Run).
- **Legal**: submission is original team work; no private sharing of competition code
  outside the team before submission; external data/tools satisfy the Reasonableness
  Standard; winning code licensable CC-BY 4.0.
- **Track**: exactly one of Agents for Good / Agents for Business / Concierge Agents /
  Freestyle, selected in the feature spec. This constitution MUST NOT be amended to
  encode track- or idea-specific rules.

## Development Workflow & Division of Labor

- **Spec Kit order is binding**: constitution → specify → (clarify) → plan → (checklist)
  → tasks → (analyze) → implement → converge. No implementation before tasks exist.
- **Two-model pipeline**: Claude (planning model) authors specs, plans, tasks, analyses,
  and performs code review. GLM 5.2 (implementation model) writes all production code
  during the implement phase, working from repository artifacts alone via a written
  handoff prompt. Claude MUST NOT write production code; GLM MUST NOT alter specs.
- **Self-contained tasks**: because the implementer starts with zero conversational
  context, every task in `tasks.md` MUST carry exact file paths, inputs, and acceptance
  criteria sufficient to implement without reading this conversation.
- **Review loop**: every implementation batch is reviewed by Claude against this
  constitution and the active checklist before merge; violations are fixed or the task
  is re-issued — never waived silently.
- **Repo discipline**: `main` is always demoable; commits are small and scoped; source
  in `/src`, tests in `/tests`, docs in `/docs`, config in `/config`, scripts in
  `/scripts`; files stay under 500 lines; no secrets (see Principle IV).
- **Tests in every spec**: per Principle VI, every feature spec MUST explicitly request
  smoke + end-to-end tests so that `/speckit-tasks` always generates test tasks
  (the tasks template treats tests as optional-by-default; this rule overrides it).

## Governance

- This constitution supersedes all other practices, templates, and preferences for this
  project. Conflicts resolve in the constitution's favor.
- **Amendments**: any team member may propose a change; the project lead approves.
  Amendments require a version bump, an updated Sync Impact Report, and propagation to
  dependent templates/specs in the same change.
- **Versioning**: semantic — MAJOR for principle removals/redefinitions, MINOR for new
  or materially expanded principles/sections, PATCH for clarifications.
- **Compliance checks**: `/speckit-plan` MUST pass its Constitution Check gate before
  design; `/speckit-analyze` SHOULD run before implement; the Claude review loop
  (Workflow section) verifies compliance after each implementation batch. Justified
  deviations MUST be recorded in the plan's Complexity Tracking table.

**Version**: 1.0.0 | **Ratified**: 2026-07-02 | **Last Amended**: 2026-07-02
