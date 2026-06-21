"""Stage 3 - three-stage estimator + equilibrium solver (CLAUDE.md §5).

Each stage writes a standard :class:`EstimationResult` (parameters / confidence
set, moments, spec hash, data vintages) to ``outputs/estimates/``.
"""

from sepg_struct.estimation.result import EstimationResult

__all__ = ["EstimationResult"]
