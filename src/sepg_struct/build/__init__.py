"""Stage 2 - build structural objects from raw sources (CLAUDE.md §4).

Pure functions turning raw sources into the primitives the estimator and
equilibrium solver consume, keyed by ``(firm, zone, block, period)`` and
``(zone, period, event)``.
"""

from sepg_struct.build.network import Network, build_network

__all__ = ["Network", "build_network"]
