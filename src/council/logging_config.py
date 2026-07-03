"""Logging configuration (T042).

dictConfig-based: INFO to stdout by default. The launcher (T043) selects the
level via ``--quiet`` (WARNING) / ``--verbose`` (DEBUG). No secrets are ever
logged: ``GOOGLE_API_KEY`` is read from the environment and never placed in a
log record. Noisy third-party libraries (ADK, genai, httpx, mcp, uvicorn) are
tamed to WARNING so the Council's own lines stay readable.
"""
from __future__ import annotations

import logging.config

DEFAULT_LEVEL = "INFO"
_VALID = {"DEBUG", "INFO", "WARNING", "ERROR"}


def configure_logging(level: str = DEFAULT_LEVEL) -> str:
    """Configure logging; return the resolved level string (normalized)."""
    level = (level or DEFAULT_LEVEL).upper()
    if level not in _VALID:
        level = DEFAULT_LEVEL
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "plain": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
            },
            "handlers": {
                "stdout": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "formatter": "plain",
                    "level": level,
                },
            },
            "loggers": {
                "council": {"level": level, "handlers": ["stdout"], "propagate": False},
                "google.adk": {"level": "WARNING"},
                "google_genai": {"level": "WARNING"},
                "httpx": {"level": "WARNING"},
                "httpcore": {"level": "WARNING"},
                "mcp": {"level": "WARNING"},
                "uvicorn": {"level": "WARNING"},
                "uvicorn.error": {"level": "WARNING"},
                "uvicorn.access": {"level": "WARNING"},
            },
            "root": {"level": "WARNING", "handlers": ["stdout"]},
        }
    )
    return level
