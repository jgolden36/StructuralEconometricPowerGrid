"""Counterfactual: multi-lever composite scenarios (CLAUDE.md §7).

Stacks several levers (e.g. "high-clean", "high-efficiency") to reveal policy
complementarities / substitutions. ``apply`` composes each lever's transform in
order.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Composite:
    name: str = "composite"
    levers: list[Any] = field(default_factory=list)  # each a Scenario

    def apply(self, env: dict, *, entry_responds: bool) -> dict:
        for lever in self.levers:
            env = lever.apply(env, entry_responds=entry_responds)
        env["composite_of"] = [getattr(lev, "name", type(lev).__name__) for lev in self.levers]
        return env


# Convenience presets referenced in the paper's counterfactual section.
def high_clean(rec_policy, byog) -> Composite:
    """24/7 CFE + BYOG at constrained zones."""
    return Composite(name="high_clean", levers=[rec_policy, byog])


def high_efficiency(technical, aux_market) -> Composite:
    """Fleet-wide efficiency (θ^tech) + aux-market redesign."""
    return Composite(name="high_efficiency", levers=[technical, aux_market])
