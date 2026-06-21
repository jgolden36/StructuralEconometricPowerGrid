"""Stage 1 - short-run estimation (CLAUDE.md §5.1).

Two pieces:

1. **Ancillary-services stacked DiD** (eq:aux_did): estimate ``β^j_k`` per product
   ``j`` using model releases as the staggered shock. The estimator itself is
   **reused from the reduced-form suite** (``sepg.estimation.stacked_did``); this
   module only assembles the panel/spec and post-processes coefficients.
2. **Price -> demand mapping** (eq:aux_demand_from_price): convert the price
   coefficient to an implied demand shift. This is fully implemented here — it is
   the *moment* Stage 2 must reproduce.

LMPs, capacity prices, and REC prices are imported as data, never estimated.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from sepg_struct.estimation.result import EstimationResult
from sepg_struct.utils.logging import get_logger

log = get_logger(__name__)


# --------------------------------------------------------------------------- #
# Price -> demand mapping (eq:aux_demand_from_price) - fully implemented.
# --------------------------------------------------------------------------- #


def price_to_demand_shift(
    beta_j: float,
    supply_elasticity: float,
    cleared_quantity_mw: float,
    *,
    demand_elasticity: float = 0.0,
) -> float:
    r"""Implied ancillary-services demand shift ``ΔD^aux`` (eq:aux_demand_from_price).

    Baseline (inelastic demand, ``ε^d = 0``):
        ``ΔD^aux = β^j_k · ε^s · Q̄^aux``.
    General case nets the demand slope:
        ``ΔD^aux = β^j_k · (ε^s − ε^d) · Q̄^aux``  (with ``ε^d ≤ 0``).

    ``β^j_k`` is the log-price DiD coefficient, ``ε^s`` the ISO supply elasticity
    at the pre-shock clearing point, and ``Q̄^aux`` the pre-shock cleared MW.
    """
    return float(beta_j * (supply_elasticity - demand_elasticity) * cleared_quantity_mw)


@dataclass
class DiDSpec:
    products: list[str]
    pre: int
    post: int
    fixed_effects: list[str]
    controls: list[str]
    cluster: str = "unit"


def _import_reduced_form_did():
    """Import the reduced-form stacked-DiD estimator (a dependency, not vendored)."""
    try:
        from sepg.estimation import stacked_did  # type: ignore
    except Exception as exc:  # pragma: no cover - dependency may be absent in CI
        raise ImportError(
            "Stage 1 reuses the reduced-form suite's stacked-DiD estimator "
            "(`from sepg.estimation import stacked_did`). Install/point to the "
            "companion package; this suite does not re-implement DiD."
        ) from exc
    return stacked_did


def run_aux_did(panel: pd.DataFrame, spec: DiDSpec) -> dict[str, dict[int, float]]:
    r"""Estimate ``β^j_k`` per product by delegating to the reduced-form estimator.

    Panel columns expected: ``zone_id, period, event_id, event_time, product,
    log_p_aux, treat_intensity`` plus the controls in ``spec.controls`` and the
    zone-by-event / time-by-event FE keys. Returns ``{product: {event_time: β}}``.
    """
    stacked_did = _import_reduced_form_did()
    out: dict[str, dict[int, float]] = {}
    for j in spec.products:
        sub = panel[panel["product"] == j]
        fit = stacked_did.fit(
            sub,
            outcome="log_p_aux",
            treatment="treat_intensity",
            event_time="event_time",
            unit="zone_id",
            fixed_effects=spec.fixed_effects,
            controls=spec.controls,
            cluster=spec.cluster,
        )
        out[j] = dict(fit.event_study_coefs())  # {k: β^j_k}
    return out


def estimate(
    panel: pd.DataFrame,
    supply_curve: pd.DataFrame,
    spec: DiDSpec,
    *,
    demand_elasticity: float = 0.0,
    data_vintages: dict[str, str] | None = None,
) -> EstimationResult:
    """Run the aux DiD and produce the ``ΔD^aux`` moment for each product.

    ``supply_curve`` provides, per product, the pre-shock supply elasticity
    ``ε^s`` and cleared quantity ``Q̄^aux``. Uses the peak post-period coefficient
    (``event_time = post``) as the headline ``β^j``.
    """
    betas = run_aux_did(panel, spec)
    sc = supply_curve.set_index("product")

    moments: dict[str, float] = {}
    params: dict[str, float] = {}
    for j, by_k in betas.items():
        beta_j = by_k.get(spec.post, max(by_k.values(), key=abs))
        eps_s = float(sc.loc[j, "supply_elasticity"])
        qbar = float(sc.loc[j, "cleared_mw"])
        delta_d = price_to_demand_shift(
            beta_j, eps_s, qbar, demand_elasticity=demand_elasticity
        )
        params[f"beta_{j}"] = beta_j
        moments[f"delta_D_aux_{j}"] = delta_d
        log.info("product=%s β=%.4f ε^s=%.3f Q̄=%.1f -> ΔD^aux=%.2f MW",
                 j, beta_j, eps_s, qbar, delta_d)

    moments["delta_D_aux_total"] = float(np.sum(list(moments.values())))
    return EstimationResult(
        stage="stage1_shortrun",
        params=params,
        moments=moments,
        diagnostics={"event_study": {j: bk for j, bk in betas.items()}},
        data_vintages=data_vintages or {},
    )
