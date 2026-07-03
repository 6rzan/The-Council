# Feature Specification: Multi-Provider Model Choice & Live Deliberation UI

**Feature Branch**: `002-multi-provider-ui`

**Created**: 2026-07-03

**Status**: Draft

**Input**: User description: "I need to add a feature that lets the user to choose their preferred AI model — not only Google API key. I need also OpenCode Zen API keys, or OpenAI API key, or their OAuth Codex, or the user can use Anthropic API key, or whatever the user wishes to use. Also the UI is so ugly and just static — it does not do anything, just a field to write and that is it. That is so boring and not impressive at all, so take care of that too."

## Clarifications

### Session 2026-07-03

*(The user was away during the interactive loop; best-judgment defaults were applied autonomously. Override any answer by re-running `/speckit-clarify` or editing this section plus the linked requirements.)*

- Q: How should OAuth account sign-in (US3 / FR-013) be scoped? → A: Keep as P3 stretch — the user's explicit request is preserved, but it is planned and tasked last and MUST be cut without renegotiation if User Stories 1–2 are not code-complete by end of 2026-07-04 (constitution Principle I).
- Q: Is the provider/model/credential selection scoped per browser session or server-wide? → A: One server-wide active configuration — the app is a single-user local tool; each run binds the configuration active at submission (last write wins).
- Q: On provider failure mid-run (outage/quota), may the system automatically switch providers? → A: No — the system never silently switches provider or spends a different credential; existing same-provider retry-then-degrade behavior is preserved, then the run fails with a clear message. Switching providers is always an explicit user action.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Choose a provider and bring your own key (Priority: P1)

A user opens The Council and, before asking a question, opens a "Model & Provider" settings panel. They pick their preferred AI provider — Google Gemini (the default), OpenAI, Anthropic, OpenCode Zen, or a custom OpenAI-compatible endpoint — paste their own API key, choose a model offered by that provider, and run a full deliberation powered by that provider. They never have to edit files or restart the app to do this.

**Why this priority**: This is the core of the request — users who do not have a Google API key are currently locked out of the product entirely. Removing that single-provider lock-in delivers the largest value and is independently demoable.

**Independent Test**: Can be fully tested by starting the app with no Google key configured, entering an OpenAI (or Anthropic, or OpenCode Zen) key in the settings panel, and completing one full deliberation end-to-end on that provider.

**Acceptance Scenarios**:

1. **Given** no Google key is configured anywhere, **When** the user selects OpenAI in the settings panel and enters a valid key, **Then** a full deliberation (recruit → debate → fact-check → verdict) completes using the chosen OpenAI model.
2. **Given** a provider and model are selected, **When** the user submits a question, **Then** the active provider and model are visibly indicated in the UI for the whole run.
3. **Given** the user enters an invalid or expired key, **When** they start a deliberation, **Then** the UI shows a clear, provider-specific error message with a recovery hint before any long wait occurs — never a silent hang.
4. **Given** a key is already configured via the environment file, **When** the user opens the settings panel, **Then** that provider is shown as "configured" without ever revealing the stored key value.
5. **Given** the user selects a provider but supplies no key for it, **When** they try to run a question, **Then** the UI blocks the run and points them to exactly what is missing.

---

### User Story 2 - A live, engaging deliberation experience (Priority: P2)

Instead of a bare text field and a static wall of text, the user watches the council work in real time: the panel being recruited, each expert's argument streaming in as a visually distinct, persona-attributed card, fact-check verdicts appearing on claims as they are checked, and the final verdict presented as a clearly distinguished conclusion. Progress through the deliberation stages is always visible, the interface feels alive (transitions, activity indicators, stage progression), and it looks polished enough to feature in the demo video.

**Why this priority**: The user explicitly called the current UI "static and boring". The deliberation pipeline already produces live events; presenting them well is what makes the product impressive and demoable — a direct submission-quality concern.

**Independent Test**: Can be fully tested by running one deliberation (with the existing offline fake-model mode) and observing that every pipeline stage and every panelist turn appears live in the UI as a distinct visual element, with no blank waiting periods.

**Acceptance Scenarios**:

1. **Given** a deliberation is running, **When** the pipeline moves to a new stage (recruiting, debate round, fact-check, synthesis), **Then** the UI reflects the stage change within 2 seconds.
2. **Given** panelists are debating, **When** a panelist turn arrives, **Then** it appears as a visually distinct element attributed to that panelist's persona (name/role clearly shown).
3. **Given** the fact-checker evaluates claims, **When** a claim's status resolves, **Then** the claim's status (e.g., supported / unsupported) is visible on screen.
4. **Given** the deliberation finishes, **When** the verdict is produced, **Then** it is presented distinctly from the debate transcript (not just more text in the same stream).
5. **Given** any moment during an active run, **When** the user looks at the screen, **Then** some activity or progress indication is visible — there is never a dead, unchanging screen while work is in progress.

---

### User Story 3 - Sign in with an existing AI subscription (OAuth) (Priority: P3)

A user who has no API key but does have an existing AI coding subscription (e.g., an OpenAI account usable via Codex/ChatGPT sign-in) chooses "Sign in" for that provider instead of pasting a key, completes the provider's sign-in flow, and can then run deliberations on that account.

**Why this priority**: Explicitly requested, but it is an alternative path to the same outcome as User Story 1 (authenticated access to a provider). API-key entry already unlocks every listed provider, so this is a convenience layer — and it is the first scope cut if the submission timeline is at risk (constitution Principle I).

**Independent Test**: Can be fully tested by selecting the OAuth option for a supported provider, completing the sign-in flow, and running one deliberation without ever entering an API key.

**Acceptance Scenarios**:

1. **Given** the user selects a provider that supports account sign-in, **When** they choose "Sign in" and complete the provider's flow, **Then** the app shows the provider as connected and deliberations run on that account.
2. **Given** the sign-in flow fails or is cancelled, **When** the user returns to the app, **Then** the app clearly shows the provider as not connected and offers both retry and the API-key alternative.

---

### Edge Cases

- **Provider outage / quota exhaustion mid-deliberation**: the run must end with a clear, human-readable explanation (which provider failed and why), preserving the existing same-provider retry-then-degrade behavior — never an infinite spinner, and never a silent switch to a different provider or credential.
- **Chosen model lacks required capabilities**: the deliberation depends on structured responses and tool use; if a selected model cannot provide them, the user gets an upfront, understandable error naming the model — not a mid-run crash.
- **Valid key, invalid model name** (free-text model override): error identifies the model name as the problem, not the key.
- **Custom endpoint unreachable or malformed URL**: validated with a clear error before a deliberation is attempted.
- **Pasted key contains surrounding whitespace/newlines**: trimmed and accepted rather than failing mysteriously.
- **Browser refresh mid-run**: the page recovers to a sane state (at minimum: no corrupted rendering; the user can start a new run).
- **No key for any provider at all**: instead of refusing to launch, the app opens to a guided "get started" state that walks the user to the settings panel.
- **Two browser tabs open at once**: the selection is one server-wide active configuration (last write wins); each run binds the configuration active at the moment it was submitted; no cross-tab corruption.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to select the AI provider used for deliberations from at least: Google Gemini (default), OpenAI, Anthropic, OpenCode Zen, and a custom OpenAI-compatible endpoint (which covers "whatever the user wishes to use", including local model runtimes).
- **FR-002**: Users MUST be able to supply an API key for their chosen provider through the UI at runtime — no file editing and no app restart required.
- **FR-003**: The existing environment-file configuration path MUST keep working; a key entered in the UI takes precedence over the environment for that session only.
- **FR-004**: Google Gemini MUST remain the default provider and model family whenever the user makes no explicit choice (constitution Principle II).
- **FR-005**: Users MUST be able to pick a model from a curated list per provider, with a free-text override for any model name the provider accepts.
- **FR-006**: Credentials entered through the UI MUST be held in server memory only, at most for the lifetime of the running app process — never written to disk, logs, traces, or version control — and MUST be masked in the UI once entered (constitution Principles IV & VII).
- **FR-007**: The system MUST validate the selected provider + credential + model combination before starting a deliberation and report actionable, provider-specific errors.
- **FR-008**: Every deliberation role (moderator/recruiter, panelists, fact-checker, synthesizer) MUST run on the user's selected provider and model for that run.
- **FR-009**: The UI MUST present the deliberation live as it happens: visible stage progression (recruiting → debate rounds → fact-checking → synthesis), each panelist turn as a distinct persona-attributed element, claim fact-check statuses, and the final verdict as a visually distinct conclusion.
- **FR-010**: The UI MUST always show an activity/progress state while a run is active; there is never a blank or unresponsive waiting state.
- **FR-011**: The UI MUST indicate the active provider and model during and after each run.
- **FR-012**: All failure modes (invalid key, quota exceeded, network failure, unsupported model, unreachable custom endpoint) MUST surface as human-readable messages that name the cause and suggest a next step.
- **FR-013**: For at least one provider that supports it, users MUST be able to authenticate by signing in with their existing account (OAuth-style flow, e.g., OpenAI via Codex/ChatGPT sign-in) as an alternative to pasting an API key (P3 stretch — planned and tasked last; MUST be cut without renegotiation if User Stories 1–2 are not code-complete by end of 2026-07-04).
- **FR-014**: Existing behavior for a Google-only, environment-configured setup MUST remain unchanged — all currently passing tests stay green.
- **FR-015**: The feature MUST ship with smoke and end-to-end tests, runnable offline without any real key (fake-model mode): provider selection and precedence, credential validation errors, one full deliberation on a non-default provider, and the live UI event contract (constitution Principle VI).
- **FR-016**: A run that fails on the selected provider MUST NOT automatically retry on a different provider or credential; the pipeline's existing same-provider retry/degrade behavior is preserved, and switching providers is always an explicit user action.

### Key Entities

- **Provider**: an AI model supplier the user can choose (Google Gemini, OpenAI, Anthropic, OpenCode Zen, custom OpenAI-compatible endpoint). Has a display name, an authentication method (API key and/or account sign-in), and a curated model list.
- **Credential**: a secret proving access to one provider (API key or sign-in token). Held in server memory only (at most the running app process's lifetime), masked in the UI, never persisted or logged.
- **Model Selection**: the single server-wide active choice of provider + model (the app is a single-user local tool); each run binds the selection active at submission. Resolves with precedence UI choice → environment default → built-in default (Gemini).
- **Deliberation Stage Event**: a live progress signal (stage entered, panelist turn, claim status, verdict ready) that the UI renders as it arrives.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user holding only a non-Google API key (e.g., OpenAI) can go from opening the app to a completed deliberation in under 2 minutes, without editing any file or restarting.
- **SC-002**: Switching provider or model between two runs takes under 30 seconds and requires no restart.
- **SC-003**: During a run, every stage change is visible in the UI within 2 seconds, and no active run ever shows more than 5 seconds without some visible progress indication.
- **SC-004**: No credential value ever appears in the repository, server logs, traces, or on-disk state; the repository's secret-scan gate stays green throughout the feature's life.
- **SC-005**: The full test suite — existing plus new provider/UI tests — passes offline with no real API key.
- **SC-006**: A viewer of the demo video can tell, from the screen alone, which provider and model produced the verdict and what stage the council is in at any moment.
- **SC-007**: 90% of first-time users can configure a provider and start a run on their first attempt without external help (validated informally with the team's own members as testers).

## Assumptions

- "OpenCode go or zen" is interpreted as **OpenCode Zen** (the API-key-based model gateway); the custom OpenAI-compatible endpoint option is what covers "whatever the user wishes to use", including local runtimes.
- "OAuth Codex" is interpreted as sign-in with an existing OpenAI account (Codex/ChatGPT-style flow). It is deliberately priority P3: API-key entry already unlocks every requested provider, and constitution Principle I requires cutting breadth first if the 2026-07-05 freeze is at risk.
- Google Gemini remains the **default** model family (constitution Principle II); every other provider is an explicit opt-in. This feature adds choice — it does not change the course-native default stack.
- Credentials live only in the running app's memory (constitution Principle VII: no persistence beyond the session). Persisting keys to disk or across app restarts is intentionally excluded.
- The deliberation pipeline requires models that support structured responses and tool use; providers/models that cannot are surfaced as errors rather than silently degraded.
- The UI revamp stays within the existing single-page application — richer live presentation of the deliberation, settings panel, and visual polish. No accounts system, no multi-page redesign.
- Users bring their own keys/subscriptions; the feature adds no paid infrastructure (competition Reasonableness Standard).
- The existing live event stream from the deliberation pipeline is the data source for the UI's live view; this feature presents it better rather than redesigning the pipeline.

### Out of Scope

- Persisting credentials beyond the session (server-side key storage, key vaults).
- User accounts, profiles, or billing/usage dashboards.
- Changing the deliberation logic itself (roster rules, debate rounds, guardrails, fact-check flow).
- Provider marketplace/auto-discovery beyond the fixed list plus custom endpoint.
- Mobile-native apps; the target remains a desktop-first web page that degrades gracefully.
