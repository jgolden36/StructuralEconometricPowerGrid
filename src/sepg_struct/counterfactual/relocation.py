"""Counterfactual: relocate inference/training across zones (CLAUDE.md §7).

Alters the admissible ``Z_f`` and the train/infer split per zone, trading
ancillary-services relief at downstream zones against transmission utilization.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Relocation:
    name: str = "relocation"
    # zone -> zone reassignment of inference/training capacity shares
    reassignment: dict[str, str] = field(default_factory=dict)

    def apply(self, env: dict, *, entry_responds: bool) -> dict:
        env = dict(env)
        env["admissible_zones"] = {**env.get("admissible_zones", {}), **self.reassignment}
        env["entry_fixed"] = not entry_responds
        return env
