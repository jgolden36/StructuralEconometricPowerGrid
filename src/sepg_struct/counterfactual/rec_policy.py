"""Counterfactual: REC-market policy (CLAUDE.md §7).

Three levers:
- REC-market elimination (``φ = 0``).
- National REC market (``S^qual = Σ_{z'} S``).
- **24/7 CFE**: granularity ``h = 1`` (hourly matching) -> shift toward
  colocation-plus-storage.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RECPolicy:
    name: str = "rec_policy"
    phi: float | None = None            # None = unchanged; 0.0 = eliminate RECs
    national_market: bool = False       # S^qual pooled across zones
    granularity_h: float | None = None  # 1.0 = 24/7 CFE hourly matching

    def apply(self, env: dict, *, entry_responds: bool) -> dict:
        env = dict(env)
        if self.phi is not None:
            env["phi"] = self.phi
        if self.granularity_h is not None:
            env["granularity_h"] = self.granularity_h
        env["national_rec_market"] = self.national_market
        env["entry_fixed"] = not entry_responds
        return env
