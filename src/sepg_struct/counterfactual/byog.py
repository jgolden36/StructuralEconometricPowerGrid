"""Counterfactual: bring-your-own-generation (CLAUDE.md §7).

Restrict ``σ ∈ {PPA, Colo}`` at constrained zones; quantify the entry response
via the financing channel ``r_l(σ²)``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BringYourOwnGeneration:
    name: str = "byog"
    constrained_zones: list[str] = field(default_factory=list)
    allowed_modes: tuple[str, ...] = ("PPA", "Colo")

    def apply(self, env: dict, *, entry_responds: bool) -> dict:
        env = dict(env)
        restrictions = dict(env.get("procurement_restrictions", {}))
        for z in self.constrained_zones:
            restrictions[z] = list(self.allowed_modes)
        env["procurement_restrictions"] = restrictions
        env["entry_fixed"] = not entry_responds
        return env
