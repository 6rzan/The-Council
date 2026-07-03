# AGENTS.md — conventions for AI coding agents working in this repo

Any AI coding agent (Claude Code, Codex, Cursor, Aider, etc.) that commits to
this repository MUST follow these rules.

## Team attribution (required on every commit)

This is a **team project** (four members). Every commit must credit the whole
team via `Co-Authored-By:` trailers so all members appear on GitHub's
contributor list.

- The single source of truth is **`.github/COAUTHORS`** — one `Full Name <email>`
  per line (comments start with `#`). Currently: Tahaf, Esam Alareqi, Kamila
  Ayub Khan, Ahmad Hemedany.
- When you create a commit, append a `Co-Authored-By:` trailer for **every**
  entry in `.github/COAUTHORS` **except** the commit's own author and anyone
  already credited in the message.
- A `commit-msg` git hook (`.githooks/commit-msg`) does this **automatically and
  idempotently** — it reads `.github/COAUTHORS`, skips the author and existing
  trailers, and never duplicates. If the hook is enabled you do not need to add
  the trailers by hand (but doing so is harmless — the hook won't duplicate).

### One-time setup (after cloning)

```bash
git config core.hooksPath .githooks   # enables commit-msg + pre-commit (secret-scan) hooks
```

This must be run once per clone so git runs the hooks. After that, every
commit by any human or agent is auto-credited.

## Branching

- Commit directly to **`main`** for fixes, docs, and config.
- Create a feature branch (e.g. `feature/<name>`) only for a substantive new
  feature; merge it back to `main` when ready.

## Security (non-negotiable)

- **Never commit secrets.** `GOOGLE_API_KEY` lives only in a gitignored `.env`.
  The `pre-commit` hook runs `scripts/secret-scan.sh` and fails the commit if a
  real `.env`, an `AIza…` key, or a live `GOOGLE_API_KEY=` value is staged.
- `.env`, `.claude/`, and `.venv/` are gitignored — do not stage them.

## General

- Keep source files and `index.html` under 500 lines.
- Run `pytest` (offline, no key needed) before pushing — it must stay green.
- Do not modify anything under `specs/` except checking task boxes `[ ]`→`[x]`.
