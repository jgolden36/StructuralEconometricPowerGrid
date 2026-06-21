"""Project-wide logging.

Equilibrium discipline (CLAUDE.md §9): the price-clearing loop must log
fixed-point residuals and iteration counts and fail loud on non-convergence.
Use :func:`get_logger` everywhere so that behaviour is consistent.
"""

from __future__ import annotations

import logging
import os

_CONFIGURED = False


def _configure_root() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    level = os.environ.get("SEPG_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger.

    Parameters
    ----------
    name:
        Usually ``__name__`` of the calling module.
    """
    _configure_root()
    return logging.getLogger(name)
