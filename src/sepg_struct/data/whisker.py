"""Whisker Labs (proprietary): THD / voltage-sag at utility-month.

Used for the aggregate validation of the ``Λ`` map (predicted vs observed THD)
in ``validation/cross_check.py`` (CLAUDE.md §3, §6).
"""

from __future__ import annotations

from pathlib import Path

from sepg_struct.data.base import context_from_config, require_credential, with_retries

SCHEMA = ["utility", "month", "thd_pct", "voltage_sag_events", "vintage"]


def _pull(ctx, credential: str) -> Path:
    raise NotImplementedError(
        "Live Whisker Labs pull not wired. Provide WHISKER_LABS_KEY, or use "
        "tests/fixtures/whisker_thd.parquet."
    )


def fetch(config: dict) -> Path:
    ctx = context_from_config("whisker", config)
    credential = require_credential(ctx.options.get("credentials_env"))
    return with_retries(lambda: _pull(ctx, credential))
