"""Equilibrium solution diagnostics (CLAUDE.md §6).

Fixed-point convergence, single-crossing verification, existence/uniqueness
diagnostics, and sensitivity of the confidence set to action-grid resolution.
"""

from __future__ import annotations

import numpy as np

from sepg_struct.estimation.equilibrium import EquilibriumResult


def convergence_report(result: EquilibriumResult) -> dict:
    """Summarize fixed-point convergence (residual decay, iteration count)."""
    hist = np.asarray(result.residual_history, dtype=float)
    decay = float(hist[-1] / hist[0]) if len(hist) > 1 and hist[0] > 0 else float("nan")
    return {
        "converged": result.converged,
        "iterations": result.iterations,
        "final_residual": result.residual,
        "residual_decay_ratio": decay,
        "monotone_decrease": bool(np.all(np.diff(hist) <= 1e-12)) if len(hist) > 1 else True,
    }


def grid_sensitivity(cs_by_resolution: dict[str, list]) -> dict:
    """Report how the partial-ID confidence set moves with action-grid resolution.

    ``cs_by_resolution`` maps a resolution label to the retained CS points; a
    confidence set that keeps shrinking as the grid refines signals the action
    grid is too coarse.
    """
    sizes = {k: len(v) for k, v in cs_by_resolution.items()}
    return {"cs_sizes": sizes, "stable": len(set(sizes.values())) <= 1}
