"""Counterfactual: supply-side policy (CLAUDE.md §7).

Transmission expansion (``↑T̄_a``) and generator build-rate subsidy
(``↓I^build``).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SupplyPolicy:
    name: str = "supply_policy"
    transfer_cap_scale: dict[str, float] = field(default_factory=dict)  # arc_id -> multiplier
    build_cost_scale: float = 1.0                                       # multiplies I^build

    def apply(self, env: dict, *, entry_responds: bool) -> dict:
        env = dict(env)
        caps = dict(env.get("transfer_caps", {}))
        for arc, mult in self.transfer_cap_scale.items():
            caps[arc] = caps.get(arc, 0.0) * mult
        env["transfer_caps"] = caps
        env["build_cost_scale"] = self.build_cost_scale
        env["entry_fixed"] = not entry_responds
        return env
