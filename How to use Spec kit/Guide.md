# How to Use Spec Kit

> Your project is ready. Spec-Kit skills are installed to `.claude/skills`.

---

## ⚠️ Agent Folder Security

Some agents may store credentials, auth tokens, or other private artifacts in the agent folder within your project.

✅ **Recommendation:** Add `.claude/` (or parts of it) to `.gitignore` to prevent accidental credential leakage.

---

## Step 1 — Open the Project

You're already in the project directory.

## Step 2 — Start Claude

Start Claude **in this project directory**. Spec-Kit skills were installed to `.claude/skills` and are now available as slash commands.

## Step 3 — Run the Core Workflow

Use these skills with your coding agent, **in order**:

| Step | Command | Purpose |
|------|---------|---------|
| 3.1 | `/speckit-constitution` | Establish project principles |
| 3.2 | `/speckit-specify` | Create baseline specification |
| 3.3 | `/speckit-plan` | Create implementation plan |
| 3.4 | `/speckit-tasks` | Generate actionable tasks |
| 3.5 | `/speckit-implement` | Execute implementation |
| 3.6 | `/speckit-converge` | Assess the codebase and append remaining work as tasks |

---

## Step 4 — Enhancement Skills (Optional)

These optional skills improve the quality and confidence of your specs. They are **not required**, but recommended where noted.

1. `/speckit-clarify` — Ask structured questions to de-risk ambiguous areas **before planning**. Run before `/speckit-plan` if used.
2. `/speckit-analyze` — Cross-artifact consistency and alignment report. Run **after `/speckit-tasks`, before `/speckit-implement`**.
3. `/speckit-checklist` — Generate quality checklists to validate requirements completeness, clarity, and consistency. Run **after `/speckit-plan`**.

### Where They Fit in the Flow

```
constitution → specify → clarify* → plan → checklist* → tasks → analyze* → implement → converge
                          └ optional                └ optional              └ optional
```

---