"""Counterfactual: ancillary-services market redesign (CLAUDE.md §7).

Fast-frequency-response product, incremental vs proportional cost attribution,
and a demand-response product.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AuxMarketRedesign:
    name: str = "aux_market"
    add_ffr_product: bool = False                 # fast frequency response
    cost_attribution: str = "proportional"        # or "incremental"
    add_dr_product: bool = False                  # demand response

    def apply(self, env: dict, *, entry_responds: bool) -> dict:
        if self.cost_attribution not in {"proportional", "incremental"}:
            raise ValueError("cost_attribution must be 'proportional' or 'incremental'")
        env = dict(env)
        products = list(env.get("aux_products", []))
        if self.add_ffr_product and "ffr" not in products:
            products.append("ffr")
        if self.add_dr_product and "dr" not in products:
            products.append("dr")
        env["aux_products"] = products
        env["aux_cost_attribution"] = self.cost_attribution
        env["entry_fixed"] = not entry_responds
        return env
