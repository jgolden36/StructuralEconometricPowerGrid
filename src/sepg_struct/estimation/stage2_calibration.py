"""Stage 2 - experimental calibration of the ``Λ`` map (CLAUDE.md §5.2).

Estimate ``Λ`` (eq:zeta_map) by **partially-linear regression** of each
load-shape signature component ``ζ`` on technical parameters ``θ^tech``,
controlling **nonparametrically** for the experimental design state ``X^exp``.
Compose ``Λ̂`` with the engineering map ``g_j`` to get per-MW aux-services
demand, aggregate to the within-facility partial ``Δ^aux_j(ζ, K)``, then
cross-validate against the Stage-1 DiD-implied ``ΔD^aux``.

The twin is *tested*, not assumed correct: if the twin-only path cannot
reproduce the aggregate, the DiD number is binding (handled in
``validation/cross_check.py``).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from sepg_struct.estimation.result import EstimationResult
from sepg_struct.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class LambdaMap:
    """Estimated ``ζ = Λ(θ^tech) + control(X^exp)`` (linear part only stored)."""

    components: list[str]
    tech_params: list[str]
    coefs: dict[str, dict[str, float]]  # component -> {tech_param: coef}

    def predict_zeta(self, theta: pd.DataFrame) -> pd.DataFrame:
        """Predict the linear (causal) part of ζ for technical params ``theta``."""
        out = {}
        for comp, beta in self.coefs.items():
            cols = [p for p in self.tech_params if p in theta.columns]
            out[comp] = theta[cols].mul([beta[c] for c in cols], axis=1).sum(axis=1)
        return pd.DataFrame(out)


def _partial_linear_fit(
    y: pd.Series, theta: pd.DataFrame, x_exp: pd.DataFrame
) -> dict[str, float]:
    r"""Robinson partial-linear: residualize ``y`` and ``θ`` on ``X^exp``, regress.

    Nonparametric nuisance ``E[y|X]``, ``E[θ|X]`` are approximated here by an OLS
    basis expansion of ``X^exp`` (placeholder for the configured learner, e.g. a
    random forest); the structural coefficient is OLS of residualized y on
    residualized θ. Returns ``{tech_param: coef}``.
    """
    import statsmodels.api as sm

    xb = sm.add_constant(x_exp, has_constant="add")

    def residualize(v: pd.Series) -> np.ndarray:
        model = sm.OLS(v.to_numpy(), xb.to_numpy(), missing="drop").fit()
        return v.to_numpy() - model.predict(xb.to_numpy())

    y_res = residualize(y)
    theta_res = np.column_stack([residualize(theta[c]) for c in theta.columns])
    beta = np.linalg.lstsq(theta_res, y_res, rcond=None)[0]
    return dict(zip(theta.columns, beta.tolist(), strict=False))


def estimate_lambda(
    trials: pd.DataFrame,
    *,
    components: list[str],
    tech_params: list[str],
    nonparam_controls: list[str],
) -> LambdaMap:
    """Fit the ``Λ`` map component-by-component from twin trial data."""
    theta = trials[tech_params]
    x_exp = trials[[c for c in nonparam_controls if c in trials.columns]]
    if x_exp.empty:
        x_exp = pd.DataFrame({"_const": np.ones(len(trials))})
    coefs = {}
    for comp in components:
        coefs[comp] = _partial_linear_fit(trials[comp], theta, x_exp)
        log.info("Λ component %s fitted on %d trials", comp, len(trials))
    return LambdaMap(components=components, tech_params=tech_params, coefs=coefs)


def twin_implied_delta_aux(
    lam: LambdaMap,
    facility_theta: pd.DataFrame,
    capacity_mw: pd.Series,
    g_j: callable,
) -> float:
    r"""Aggregate twin-implied ``Δ^aux`` = Σ_f g_j(Λ̂(θ_f)) · K_f.

    ``g_j`` is the engineering signature->aux-demand map (per-MW); composing with
    ``Λ̂`` and scaling by capacity yields the within-facility partial summed
    across facilities.
    """
    zeta = lam.predict_zeta(facility_theta)
    per_mw = zeta.apply(g_j, axis=1).to_numpy()
    return float(np.sum(per_mw * capacity_mw.to_numpy()))


def estimate(
    trials: pd.DataFrame,
    cfg: dict,
    *,
    data_vintages: dict[str, str] | None = None,
) -> EstimationResult:
    """Fit ``Λ̂`` and emit it as an :class:`EstimationResult`.

    The twin↔observation cross-check itself lives in ``validation/cross_check.py``
    so it can be gated independently; here we just persist the calibrated map.
    """
    lam = estimate_lambda(
        trials,
        components=cfg["zeta_components"],
        tech_params=cfg["tech_params"],
        nonparam_controls=cfg.get("nonparam_controls", []),
    )
    return EstimationResult(
        stage="stage2_calibration",
        params={"lambda_coefs": lam.coefs},
        diagnostics={"n_trials": int(len(trials)), "components": lam.components},
        data_vintages=data_vintages or {},
    )
