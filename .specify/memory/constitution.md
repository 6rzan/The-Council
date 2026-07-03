<!--
Sync Impact Report
==================
Version change: 1.0.0 → 1.1.0
Modified principles:
  - IV. Security & Guardrails by Design (clarification only — the secret-scan gate is now
    enforced automatically by the .githooks/pre-commit hook and the CI secret-scan
    workflow; the rule itself is unchanged)
Added sections: none new; "Development Workflow & Division of Labor" materially expanded
  with five post-ratification repo conventions (source: AGENTS.md, adopted 2026-07-03):
  - Team attribution: every commit credits the whole team via Co-Authored-By: trailers;
    .github/COAUTHORS is the source of truth; .githooks/commit-msg automates it.
  - Mandatory hooks enablement: git config core.hooksPath .githooks, once per clone.
  - Branching policy: direct-to-main for fixes/docs/config; feature branches only for
    substantive features.
  - AGENTS.md is binding on any AI coding agent that commits to the repo.
  - Frozen specs: nothing under specs/ changes except task checkboxes [ ]→[x].
Removed sections: none
Templates:
  - .specify/templates/plan-template.md ✅ aligned (Constitution Check gate is populated
    per-feature from this file; workflow conventions add no design gates — no edit needed)
  - .specify/templates/spec-template.md ✅ aligned (no structural impact)
  - .specify/templates/tasks-template.md ✅ aligned (v1.0.0 note still stands: every spec
    MUST request smoke + E2E tests per Principle VI)
  - .specify/templates/commands/*.md — n/a (commands live in .claude/skills/ in this repo)
Runtime guidance docs:
  - AGENTS.md ✅ already the operational mirror of the new workflow rules (their source)
  - CLAUDE.md (repo root) ✅ already instructs agents on attribution, hooks, and specs
  - README.md ✅ no principle references requiring update
Follow-up TODOs: none
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
  secret-scan check MUST pass before every push — enforced automatically by the
  `.githooks/pre-commit` hook (`scripts/secret-scan.sh`) and the repository's CI
  secret-scan gate.
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
- **Team attribution (required on every commit)**: this is a four-person team project;
  every commit MUST credit the whole team via `Co-Authored-By:` trailers so all members
  appear on GitHub's contributor list. The single source of truth is `.github/COAUTHORS`
  (one `Full Name <email>` per line); each commit carries a trailer for every entry
  except the commit's own author and anyone already credited. The `.githooks/commit-msg`
  hook appends these automatically and idempotently. This rule deliberately overrides
  any tool or agent default that discourages `Co-Authored-By` trailers — the teammates
  are real contributors and crediting them is required, not optional.
- **Hooks are mandatory**: `git config core.hooksPath .githooks` MUST be run once per
  clone so the `commit-msg` (attribution) and `pre-commit` (secret-scan) hooks fire on
  every commit, for humans and AI agents alike.
- **Branching**: fixes, docs, and config changes are committed directly to `main`; a
  feature branch (e.g. `feature/<name>`) is created only for a substantive new feature
  and merged back to `main` when ready.
- **AI agent conventions are binding**: any AI coding agent (Claude Code, Codex, Cursor,
  Aider, etc.) that commits to this repository MUST follow `AGENTS.md`, the operational
  mirror of these workflow rules.
- **Frozen specs**: after a feature's spec freeze, nothing under `specs/` may be
  modified except checking task boxes `[ ]`→`[x]` in `tasks.md`.
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

**Version**: 1.1.0 | **Ratified**: 2026-07-02 | **Last Amended**: 2026-07-03
