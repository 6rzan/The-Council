"""Session context for US2 follow-up continuity (data-model §SessionContext).

Held in ADK session state only — in memory, never persisted to disk
(FR-012, Principle VII). A follow-up question in the same session can build on
the prior questions and verdicts rather than starting cold (FR-011).
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from council.schemas.verdict import VerdictBrief


class SessionContext(BaseModel):
    """Prior deliberation context for a session (US2, FR-011).

    ``prior_questions`` and ``prior_verdicts`` are parallel lists; verdict ``i``
    answers question ``i``. Discarded when the in-memory session ends.
    """

    prior_questions: list[str] = Field(default_factory=list)
    prior_verdicts: list[VerdictBrief] = Field(default_factory=list)
