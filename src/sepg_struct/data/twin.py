"""CEWIT/AERTC digital twin + micro data center (proprietary).

Trial-level ``(X^exp, θ^tech, ζ, η)``: power / voltage / current / frequency /
harmonics / reactive power under varied technical parameters. Calibration input
for the ``Λ`` map and the ``g_j`` signature->aux-demand map (CLAUDE.md §3, §5.2).
This is a *calibration input*, not the main estimator.
"""

from __future__ import annotations

from pathlib import Path

from sepg_struct.data.base import context_from_config, require_credential, with_retries

SCHEMA = [
    "trial_id", "chip_gen", "quantization", "batch_size", "cooling", "pfc_topology",
    "storage_config", "power_kw", "voltage_v", "current_a", "frequency_hz",
    "thd_pct", "power_factor", "reactive_kvar", "vintage",
]


def _pull(ctx, credential: str) -> Path:
    raise NotImplementedError(
        "Live digital-twin pull not wired. Provide CEWIT_TWIN_KEY, or use "
        "tests/fixtures/twin_trials.parquet."
    )


def fetch(config: dict) -> Path:
    ctx = context_from_config("twin", config)
    credential = require_credential(ctx.options.get("credentials_env"))
    return with_retries(lambda: _pull(ctx, credential))
