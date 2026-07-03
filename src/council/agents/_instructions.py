"""Helper to load versioned instruction files (Principle V).

Instructions live as ``.md`` files under ``agents/instructions/`` so they are
reviewable and version-controlled, never inline string literals.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_INSTRUCTIONS_DIR = Path(__file__).resolve().parent / "instructions"


@lru_cache(maxsize=None)
def load(name: str) -> str:
    """Load an instruction file by stem, e.g. load('recruiter')."""
    path = _INSTRUCTIONS_DIR / f"{name}.md"
    if not path.exists():  # pragma: no cover - defensive
        raise FileNotFoundError(f"instruction file not found: {path}")
    return path.read_text(encoding="utf-8")
