"""Twin↔observation ``Δ^aux`` reconciliation + THD validation (CLAUDE.md §6).

Compares the Stage-2 twin-implied aggregate ``Δ^aux`` against the Stage-1
DiD-implied ``ΔD^aux`` (the integration diagnostic), and validates the ``Λ`` map
against observed Whisker-Labs THD. If the twin-only path cannot reproduce the
aggregate, the DiD number is binding and technical-decomposition counterfactuals
are flagged provisional.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CrossCheckResult:
    twin_delta_aux: float
    did_delta_aux: float
    rel_gap: float
    within_tolerance: bool
    technical_cf_provisional: bool


def reconcile_delta_aux(
    twin_delta_aux: float,
    did_delta_aux: float,
    *,
    tolerance_rel: float = 0.25,
) -> CrossCheckResult:
    r"""Reconcile twin vs DiD ``Δ^aux``; flag technical CFs provisional on failure."""
    denom = abs(did_delta_aux) if did_delta_aux != 0 else 1.0
    rel_gap = abs(twin_delta_aux - did_delta_aux) / denom
    ok = rel_gap <= tolerance_rel
    return CrossCheckResult(
        twin_delta_aux=twin_delta_aux,
        did_delta_aux=did_delta_aux,
        rel_gap=rel_gap,
        within_tolerance=ok,
        technical_cf_provisional=not ok,
    )


def validate_thd(predicted_thd, observed_thd) -> dict:
    """Aggregate Whisker-Labs THD validation of the ``Λ`` map (predicted vs observed).

    Returns correlation and mean-absolute-error at the utility-month grain.
    """
    import numpy as np

    p = np.asarray(predicted_thd, dtype=float)
    o = np.asarray(observed_thd, dtype=float)
    mask = ~(np.isnan(p) | np.isnan(o))
    p, o = p[mask], o[mask]
    if len(p) < 2:
        return {"n": int(len(p)), "corr": float("nan"), "mae": float("nan")}
    return {
        "n": int(len(p)),
        "corr": float(np.corrcoef(p, o)[0, 1]),
        "mae": float(np.mean(np.abs(p - o))),
    }
