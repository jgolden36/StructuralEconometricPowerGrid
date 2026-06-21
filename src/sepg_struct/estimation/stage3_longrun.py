"""Stage 3 - long-run estimation via moment inequalities (CLAUDE.md §5.3).

Holmes/Pakes-style revealed-preference inequalities (eq:moment_ineq): observed
firm portfolios dominate small unilateral deviations in expected discounted
profit. Four deviation classes — location / procurement / capacity / storage
swaps — feasible under headroom / clean-pool given observed rival capacity.
Plus generator free-entry moments (eq:gen_free_entry) and PPA bargaining
(eq:ppa_bargain). Inference is partial-identification (Andrews–Soares);
uniqueness is not assumed.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

import numpy as np

from sepg_struct.estimation.result import EstimationResult
from sepg_struct.utils.logging import get_logger

log = get_logger(__name__)

# A profit oracle maps (params θ, observed portfolio, a deviation) to the
# expected discounted profit difference  Π(observed) − Π(deviation).  It is
# supplied by the equilibrium/payoff layer; Stage 3 only forms moments from it.
ProfitGap = Callable[[np.ndarray, dict, dict], float]


@dataclass
class Deviation:
    cls: str       # one of: location_swap, procurement_swap, capacity_swap, storage_swap
    firm: str
    payload: dict  # e.g. {"from_zone": ..., "to_zone": ...}


def generate_deviations(observed: dict, spec: dict) -> list[Deviation]:
    """Construct feasible unilateral deviations for each class (eq:moment_ineq).

    Deviations must be feasible under interconnection headroom / clean-pool given
    observed rival capacity — infeasible perturbations are dropped so the
    inequality ``Π(obs) ≥ Π(dev)`` is well posed.
    """
    devs: list[Deviation] = []
    classes = spec.get("deviation_classes", [])
    pert = spec.get("perturbation", {})
    for firm, port in observed.get("portfolios", {}).items():
        if "location_swap" in classes:
            for z in port.get("feasible_zones", []):
                devs.append(Deviation("location_swap", firm, {"to_zone": z}))
        if "procurement_swap" in classes:
            for mode in pert.get("procurement", {}).get("modes", []):
                devs.append(Deviation("procurement_swap", firm, {"mode": mode}))
        if "capacity_swap" in classes:
            for dk in pert.get("capacity", {}).get("dk_grid_mw", []):
                devs.append(Deviation("capacity_swap", firm, {"delta_k_mw": dk}))
        if "storage_swap" in classes:
            for ds in pert.get("storage", {}).get("ds_grid_mwh", []):
                for ch in pert.get("storage", {}).get("channels", []):
                    devs.append(Deviation("storage_swap", firm, {"delta_s_mwh": ds, "channel": ch}))
    log.info("generated %d candidate deviations", len(devs))
    return devs


def moment_function(
    theta: np.ndarray,
    observed: dict,
    deviations: Iterable[Deviation],
    profit_gap: ProfitGap,
) -> np.ndarray:
    r"""Stack the inequality moments ``m_d(θ) = Π(obs) − Π(dev) ≥ 0``.

    A negative entry is a violated inequality. The criterion below penalizes only
    violations (one-sided), per the moment-inequality framework.
    """
    return np.array(
        [profit_gap(theta, observed, {"firm": d.firm, "cls": d.cls, **d.payload})
         for d in deviations],
        dtype=float,
    )


def criterion(theta: np.ndarray, m: Callable[[np.ndarray], np.ndarray]) -> float:
    r"""One-sided (modified-method-of-moments) criterion ``Σ [min(m_d, 0)]^2``."""
    mv = m(theta)
    neg = np.minimum(mv, 0.0)
    return float(neg @ neg)


def confidence_set(
    theta_grid: np.ndarray,
    m: Callable[[np.ndarray], np.ndarray],
    *,
    alpha: float = 0.05,
    subsample_B: int = 500,
    seed: int = 0,
) -> list[np.ndarray]:
    r"""Andrews–Soares-style CS by test inversion over ``theta_grid``.

    For each θ on the grid, test ``H_0: E[m(θ)] ≥ 0`` via subsampled critical
    values and keep θ if not rejected at level ``α``. Returns the retained grid
    points (the partial-ID confidence set). Subsampling is seeded for
    determinism (CLAUDE.md §9).

    NOTE: the subsample critical-value machinery (generalized-moment-selection)
    is left as a focused TODO; this scaffold keeps the seed/contract and the
    test-inversion loop so the inference path is wired end-to-end.
    """
    rng = np.random.default_rng(seed)
    retained: list[np.ndarray] = []
    for theta in theta_grid:
        stat = criterion(theta, m)
        # Placeholder critical value: GMS subsampling to replace this line.
        crit = _subsample_critical_value(theta, m, rng, subsample_B, alpha)
        if stat <= crit:
            retained.append(theta)
    log.info("confidence set: %d/%d grid points retained at α=%.2f",
             len(retained), len(theta_grid), alpha)
    return retained


def _subsample_critical_value(theta, m, rng, B, alpha) -> float:  # noqa: ANN001
    raise NotImplementedError(
        "Generalized-moment-selection subsampling critical values are a focused "
        "TODO; wire the reduced-form inference utilities or implement Andrews–"
        "Soares GMS here. The test-inversion loop in confidence_set() is ready."
    )


def estimate(
    observed: dict,
    spec: dict,
    profit_gap: ProfitGap,
    theta_grid: np.ndarray,
    *,
    data_vintages: dict[str, str] | None = None,
) -> EstimationResult:
    """Form moments, invert the test over ``theta_grid``, report the CS."""
    devs = generate_deviations(observed, spec)
    m = lambda th: moment_function(th, observed, devs, profit_gap)  # noqa: E731
    inf = spec.get("inference", {})
    cs = confidence_set(
        theta_grid, m,
        alpha=inf.get("alpha", 0.05),
        subsample_B=inf.get("subsample_B", 500),
        seed=spec.get("seed", 0),
    )
    cs_arr = np.array(cs) if cs else np.empty((0, theta_grid.shape[1]))
    bounds = (
        {f"theta_{i}": [float(cs_arr[:, i].min()), float(cs_arr[:, i].max())]
         for i in range(cs_arr.shape[1])}
        if len(cs_arr)
        else {}
    )
    return EstimationResult(
        stage="stage3_longrun",
        confidence_set=bounds,
        diagnostics={"n_deviations": len(devs), "cs_points": len(cs)},
        data_vintages=data_vintages or {},
    )
