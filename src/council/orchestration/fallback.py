"""Deterministic fallback roster (FR-016).

When run-time recruitment fails, errors, or returns an empty/invalid panel,
the shell substitutes this roster so every deliberation still completes with a
full Verdict Brief. Satisfies the roster validators (size, ≥1 challenger,
unique names).
"""
from __future__ import annotations

from council.schemas.roster import Panelist, PanelRoster, RosterSource


def fallback_roster() -> PanelRoster:
    """The deterministic default panel (FR-016)."""
    return PanelRoster(
        panelists=[
            Panelist(
                name="The Advocate",
                expertise="generalist advocate",
                stance="favorable",
                recruitment_reason="argues the strongest case for the proposal",
                is_challenger=False,
            ),
            Panelist(
                name="The Skeptic",
                expertise="generalist skeptic",
                stance="critical",
                recruitment_reason="argues the strongest case against the proposal",
                is_challenger=True,
            ),
            Panelist(
                name="The Pragmatist",
                expertise="implementation realist",
                stance="pragmatic",
                recruitment_reason="weighs feasibility and trade-offs",
                is_challenger=False,
            ),
        ],
        source=RosterSource.fallback,
    )
