"""Placebo & alternative-estimator robustness for the Stage-1 DiD (CLAUDE.md §6).

**Reuses the reduced-form suite**: randomized treatment-timing / assignment
placebos plus the Callaway–Sant'Anna and Borusyak–Jaravel–Spiess alternative
estimators. Seeded for determinism (CLAUDE.md §9).
"""

from __future__ import annotations

import pandas as pd


def randomized_placebo(panel: pd.DataFrame, *, n_draws: int = 500, seed: int = 0) -> dict:
    """Randomize treatment timing/assignment and re-estimate; reuse reduced-form."""
    try:
        from sepg.validation import placebo as rf_placebo  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "Placebo suite is reused from the reduced-form suite "
            "(`from sepg.validation import placebo`)."
        ) from exc
    return rf_placebo.randomized(panel, n_draws=n_draws, seed=seed)


def alternative_estimators(panel: pd.DataFrame) -> dict:
    """Callaway–Sant'Anna and Borusyak–Jaravel–Spiess robustness; reuse reduced-form."""
    try:
        from sepg.validation import alt_estimators as rf_alt  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "CS / BJS estimators are reused from the reduced-form suite "
            "(`from sepg.validation import alt_estimators`)."
        ) from exc
    return {"callaway_santanna": rf_alt.cs(panel), "borusyak": rf_alt.bjs(panel)}
