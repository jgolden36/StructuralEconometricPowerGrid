"""Counterfactual scenario engine (CLAUDE.md §7).

A scenario is a transformation of the equilibrium environment (constraints,
admissible action sets, cost shifters) re-solved at the estimated parameters.
Every scenario reports the partial-equilibrium (entry fixed) and
general-equilibrium (entry responds) effects against baseline.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from sepg_struct.build.network import Network
from sepg_struct.estimation.equilibrium import (
    EquilibriumConfig,
    EquilibriumResult,
    solve_equilibrium,
)
from sepg_struct.utils.logging import get_logger

log = get_logger(__name__)


class Scenario(Protocol):
    """A policy lever. ``apply`` mutates the environment passed to the solver."""

    name: str

    def apply(self, env: dict, *, entry_responds: bool) -> dict:
        """Return a modified copy of ``env`` for this scenario."""
        ...


@dataclass
class ScenarioResult:
    name: str
    baseline: EquilibriumResult
    partial_eq: EquilibriumResult
    general_eq: EquilibriumResult
    deltas: dict = field(default_factory=dict)


def _compare(baseline: EquilibriumResult, cf: EquilibriumResult) -> dict:
    """Portfolio/price deltas vs baseline (emissions/aux/reliability filled by caller)."""
    import numpy as np

    return {
        "mean_price_change": float(np.mean(cf.prices - baseline.prices)),
        "headroom_shadow_change": float(
            np.mean(cf.shadow_prices.headroom - baseline.shadow_prices.headroom)
        ),
        "cleanpool_shadow_change": float(
            np.mean(cf.shadow_prices.cleanpool - baseline.shadow_prices.cleanpool)
        ),
    }


def run_scenario(
    scenario: Scenario,
    network: Network,
    cfg: EquilibriumConfig,
    *,
    build_clearer: Callable[[dict], Callable],
    env: dict,
    baseline: EquilibriumResult,
    init_prices,
) -> ScenarioResult:
    """Re-solve under ``scenario`` for both PE and GE entry assumptions.

    ``build_clearer(env) -> clear_markets`` constructs the market-clearing
    callback for a (possibly modified) environment; baseline is supplied so the
    deltas are computed once.
    """
    log.info("counterfactual scenario: %s", scenario.name)
    pe_env = scenario.apply(dict(env), entry_responds=False)
    ge_env = scenario.apply(dict(env), entry_responds=True)

    pe = solve_equilibrium(
        network, cfg, clear_markets=build_clearer(pe_env), init_prices=init_prices
    )
    ge = solve_equilibrium(
        network, cfg, clear_markets=build_clearer(ge_env), init_prices=init_prices
    )

    return ScenarioResult(
        name=scenario.name,
        baseline=baseline,
        partial_eq=pe,
        general_eq=ge,
        deltas={
            "partial_equilibrium": _compare(baseline, pe),
            "general_equilibrium": _compare(baseline, ge),
        },
    )
