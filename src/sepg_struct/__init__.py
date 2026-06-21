"""Structural econometric suite for the AI-demand / generator-investment paper.

Implements the four-stage pipeline described in ``CLAUDE.md`` and the structural
paper *A Structural Econometric Model of AI Demand, Generator Investment, and
Power Quality*:

1. ``data``          - acquire raw sources into ``data/raw/`` with a manifest.
2. ``build``         - construct network / blocks / demand / exposure / carbon.
3. ``estimation``    - three-stage estimator + Markov-perfect equilibrium solver.
4. ``validation`` /  - identifying-assumption diagnostics and policy
   ``counterfactual``  counterfactuals.

The reduced-form DiD companion suite (``sepg``) is an imported dependency, never
re-implemented here.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
