"""Counterfactual: fleet-wide technical changes (CLAUDE.md §7).

INT8 quantization, distilled models, power-factor correction, cross-firm batch
scheduling: perturb ``θ^tech``, map through ``Λ̂`` to a new ``ζ``, re-aggregate
to a zone demand shift, and re-solve. **Uniquely enabled by the experimental
platform.** Flagged provisional if the twin↔obs cross-check failed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TechnicalChange:
    name: str = "technical"
    theta_perturbation: dict[str, Any] = field(default_factory=dict)
    lambda_map: Any = None  # estimation.stage2_calibration.LambdaMap

    def apply(self, env: dict, *, entry_responds: bool) -> dict:
        env = dict(env)
        if self.lambda_map is None:
            raise ValueError("technical CF requires a calibrated Λ̂ (Stage 2) to map θ->ζ")
        env["theta_tech"] = {**env.get("theta_tech", {}), **self.theta_perturbation}
        env["zeta_override_map"] = self.lambda_map
        env["entry_fixed"] = not entry_responds
        env["provisional"] = env.get("twin_crosscheck_failed", False)
        return env
