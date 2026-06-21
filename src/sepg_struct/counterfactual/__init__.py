"""Stage 4b - counterfactual policy engine (CLAUDE.md §7).

Each scenario re-solves the Markov-perfect equilibrium with a modified
constraint set, holding structural parameters at their estimated values, and
reports **both** the partial-equilibrium effect (entry fixed) and the
general-equilibrium effect (entry responds) — the gap is itself informative.
"""

from sepg_struct.counterfactual.base import Scenario, ScenarioResult, run_scenario

__all__ = ["Scenario", "ScenarioResult", "run_scenario"]
