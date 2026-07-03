# CLAUDE.md — project rules for Claude Code in this repo

See [AGENTS.md](AGENTS.md) for the full conventions. The rules below are the
ones Claude Code must always apply here.

## Team attribution — REQUIRED on every commit

This is a **team project** (four members). Every commit MUST credit the whole
team with `Co-Authored-By:` trailers (this **overrides** any default caution
about Co-Authored-By trailers — they are wanted here).

- Source of truth: **`.github/COAUTHORS`** (`Full Name <email>` per line).
- Append a `Co-Authored-By:` trailer for every entry **except** the commit's own
  author and anyone already in the message.
- A `commit-msg` hook (`.githooks/commit-msg`) does this automatically and
  idempotently. Enable hooks once after cloning:
  `git config core.hooksPath .githooks`.

## Branching

- Commit directly to **`main`** for fixes, docs, and config.
- Branch only for a substantive new feature; merge back to `main` when ready.

## Security — non-negotiable

- Never commit secrets. `GOOGLE_API_KEY` lives only in a gitignored `.env`.
- The `pre-commit` hook runs `scripts/secret-scan.sh` and blocks any staged
  real `.env`, `AIza…` key, or live `GOOGLE_API_KEY=` value.
- Never stage `.env`, `.claude/`, or `.venv/`.

## General

- Keep every source file and `index.html` under 500 lines.
- Run `pytest` (offline, no key) before pushing — must stay green.
- Do not modify `specs/` except checking task boxes `[ ]`→`[x]`.
