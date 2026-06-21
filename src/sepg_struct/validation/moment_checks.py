"""Over-identification / moment-match diagnostics for Stage 3 (CLAUDE.md §6).

Reports which moment inequalities bind and the slackness profile, so the reader
knows which deviations discipline the estimates.
"""

from __future__ import annotations

import numpy as np


def slackness_profile(moment_values: np.ndarray, *, atol: float = 1e-8) -> dict:
    r"""Classify each inequality moment as binding / slack / violated.

    ``m_d ≈ 0`` binds, ``m_d > 0`` is slack, ``m_d < 0`` is violated (the model is
    rejected on that deviation). Returns counts and the binding/violated indices.
    """
    m = np.asarray(moment_values, dtype=float)
    binding = np.where(np.abs(m) <= atol)[0]
    violated = np.where(m < -atol)[0]
    slack = np.where(m > atol)[0]
    return {
        "n_moments": int(m.size),
        "n_binding": int(binding.size),
        "n_slack": int(slack.size),
        "n_violated": int(violated.size),
        "binding_idx": binding.tolist(),
        "violated_idx": violated.tolist(),
        "min_slack": float(m.min()) if m.size else float("nan"),
    }
