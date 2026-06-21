"""Aterio data-center registry (proprietary).

Pulls DC location, operator, MW capacity, build status, announced expansions,
and AI-use / on-site-generation flags; cross-validated against S&P 451 / DC
Bytes and interconnection-queue filings. Informs the hyperscaler capacity stock
``K_{f,z,t}^σ`` and zone exposure shares (CLAUDE.md §3).
"""

from __future__ import annotations

from pathlib import Path

from sepg_struct.data.base import context_from_config, require_credential, with_retries

SCHEMA = [
    "facility_id", "operator", "lon", "lat", "iso", "ba",
    "mw_capacity", "build_status", "ai_use_flag", "onsite_gen_flag",
    "announced_expansion_mw", "vintage",
]


def _pull(ctx, credential: str) -> Path:
    raise NotImplementedError(
        "Live Aterio pull not wired. Provide ATERIO_API_KEY and implement the "
        "registry client, or run against tests/fixtures/aterio_*.parquet."
    )


def fetch(config: dict) -> Path:
    ctx = context_from_config("aterio", config)
    credential = require_credential(ctx.options.get("credentials_env"))
    return with_retries(lambda: _pull(ctx, credential))
