"""Markov-perfect equilibrium solver (CLAUDE.md §5.4).

The object the counterfactuals re-solve. Structure:

- Hyperscaler Bellman (eq:hyper_bellman) over ``(ΔK, σ, ΔS, B)``.
- Generator Bellman (eq:gen_bellman) with the financing-rate entry hierarchy
  ``entry_Colo ≥ entry_PPA ≥ entry_merch``.
- Short-run market clearing per block: energy, capacity, REC, and the behavioral
  ancillary-services market (rest imported as cost curves).
- Resource constraints clear via shadow prices: headroom ``λ^H`` (eq:headroom)
  and clean-MW pool ``λ^Z`` (eq:cleanpool).
- **Combinatorial location pruning** (Arkolakis-style, eq:separability) nested as
  the inner loop of the price-clearing fixed point.

Equilibrium discipline (CLAUDE.md §9): log fixed-point residuals and iteration
counts; fail loud if clearing does not converge within tolerance.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from sepg_struct.build.network import Network
from sepg_struct.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class EquilibriumConfig:
    discount_beta: float = 0.92
    storage_roundtrip_eta: float = 0.88
    max_iter: int = 200
    tol: float = 1e-6
    damping: float = 0.5
    entry_ordering: tuple[str, ...] = ("Colo", "PPA", "merch")
    verify_single_crossing: bool = True


@dataclass
class ShadowPrices:
    headroom: np.ndarray   # λ^H per zone (eq:headroom)
    cleanpool: np.ndarray  # λ^Z per zone (eq:cleanpool)

    def stack(self) -> np.ndarray:
        return np.concatenate([self.headroom, self.cleanpool])

    @classmethod
    def from_stack(cls, v: np.ndarray, n_zones: int) -> ShadowPrices:
        return cls(headroom=v[:n_zones], cleanpool=v[n_zones:])


@dataclass
class EquilibriumResult:
    converged: bool
    iterations: int
    residual: float
    prices: np.ndarray
    shadow_prices: ShadowPrices
    portfolios: dict
    residual_history: list[float] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Resource constraints -> shadow prices.
# --------------------------------------------------------------------------- #


def headroom_residual(draw_mw: np.ndarray, capacity_mw: np.ndarray) -> np.ndarray:
    r"""Interconnection-headroom slack per zone (eq:headroom).

    Positive => spare headroom; negative => violated. The complementarity
    ``λ^H ≥ 0 ⟂ (capacity − draw) ≥ 0`` pins ``λ^H``.
    """
    return capacity_mw - draw_mw


def cleanpool_residual(clean_demand_mw: np.ndarray, clean_supply_mw: np.ndarray) -> np.ndarray:
    r"""Clean-MW-pool slack per zone (eq:cleanpool); pins ``λ^Z`` by complementarity."""
    return clean_supply_mw - clean_demand_mw


def update_shadow_prices(
    sp: ShadowPrices,
    headroom_slack: np.ndarray,
    cleanpool_slack: np.ndarray,
    *,
    step: float,
) -> ShadowPrices:
    """Projected-subgradient update enforcing ``λ ≥ 0`` complementary slackness."""
    new_h = np.maximum(sp.headroom - step * headroom_slack, 0.0)
    new_z = np.maximum(sp.cleanpool - step * cleanpool_slack, 0.0)
    return ShadowPrices(headroom=new_h, cleanpool=new_z)


# --------------------------------------------------------------------------- #
# Location pruning (Arkolakis-style, eq:separability) - inner loop.
# --------------------------------------------------------------------------- #


def verify_single_crossing(profit_in_C: Callable[[float], np.ndarray], grid: np.ndarray) -> bool:
    r"""Numerically verify single-crossing of profit in the cost index ``C``.

    Required for the conditional separability in ``(C_{f,t}, E_{f,t})`` that makes
    Arkolakis-style pruning valid. Checks that the sign of the cross-difference
    does not flip more than once along ``grid``.
    """
    vals = np.array([profit_in_C(c) for c in grid])
    diffs = np.diff(vals, axis=0)
    sign_changes = np.sum(np.abs(np.diff(np.sign(diffs), axis=0)) > 0, axis=0)
    return bool(np.all(sign_changes <= 1))


def prune_locations(
    candidate_sets: dict,
    shadow_prices: ShadowPrices,
    profit_oracle: Callable[[dict, ShadowPrices], float],
) -> dict:
    r"""Prune the combinatorial location choice given ``(λ^H, λ^Z)`` (eq:separability).

    Uses conditional separability to discard dominated zone bundles without
    enumerating the full lattice. Returns the surviving choice per firm. The
    bound-and-discard inner logic is a focused TODO; the contract (inputs/outputs
    and its nesting inside the price loop) is fixed here.
    """
    raise NotImplementedError(
        "Arkolakis-style bound-and-discard pruning is a focused TODO. It nests "
        "inside solve_equilibrium()'s price loop: prune given (λ^H, λ^Z), "
        "re-clear constraints, iterate. verify_single_crossing() guards validity."
    )


# --------------------------------------------------------------------------- #
# Price-clearing fixed point.
# --------------------------------------------------------------------------- #


def solve_equilibrium(
    network: Network,
    cfg: EquilibriumConfig,
    *,
    clear_markets: Callable[
        [np.ndarray, ShadowPrices], tuple[np.ndarray, np.ndarray, np.ndarray, dict]
    ],
    init_prices: np.ndarray,
    init_shadow: ShadowPrices | None = None,
) -> EquilibriumResult:
    r"""Solve the MPE price-clearing fixed point with damping.

    ``clear_markets(prices, shadow) -> (new_prices, headroom_slack,
    cleanpool_slack, portfolios)`` evaluates the short-run clearing and the
    hyperscaler/generator best responses (with location pruning nested inside).
    Iterates a damped update until the joint residual on prices and shadow prices
    falls below ``cfg.tol``; raises if it does not converge.
    """
    n = network.n_zones
    prices = np.asarray(init_prices, dtype=float)
    shadow = init_shadow or ShadowPrices(headroom=np.zeros(n), cleanpool=np.zeros(n))
    history: list[float] = []

    for it in range(1, cfg.max_iter + 1):
        new_prices, h_slack, z_slack, portfolios = clear_markets(prices, shadow)
        new_shadow = update_shadow_prices(shadow, h_slack, z_slack, step=cfg.damping)

        price_res = float(np.max(np.abs(new_prices - prices))) if prices.size else 0.0
        shadow_res = float(np.max(np.abs(new_shadow.stack() - shadow.stack())))
        residual = max(price_res, shadow_res)
        history.append(residual)
        log.info("iter=%d price_res=%.3e shadow_res=%.3e", it, price_res, shadow_res)

        prices = (1 - cfg.damping) * prices + cfg.damping * new_prices
        shadow = new_shadow

        if residual < cfg.tol:
            log.info("equilibrium converged in %d iterations (res=%.3e)", it, residual)
            return EquilibriumResult(
                converged=True, iterations=it, residual=residual,
                prices=prices, shadow_prices=shadow, portfolios=portfolios,
                residual_history=history,
            )

    raise RuntimeError(
        f"price-clearing fixed point did NOT converge in {cfg.max_iter} iters "
        f"(last residual {history[-1]:.3e} > tol {cfg.tol:.3e}). Failing loud "
        "per equilibrium discipline (CLAUDE.md §9)."
    )
