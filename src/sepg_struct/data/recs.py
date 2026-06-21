"""REC markets: S&P Global Platts, M-RETS, PJM-GATS, state compliance reports.

REC issuance / retirement records and compliance prices -> REC market clearing
and the granularity standard ``h`` (CLAUDE.md §3).
"""

from __future__ import annotations

from pathlib import Path

from sepg_struct.data.base import context_from_config, require_credential, with_retries

SCHEMA = ["rec_id", "zone", "vintage_year", "issued_mwh", "retired_mwh", "compliance_price", "tier"]


def _pull(ctx, credential: str | None) -> Path:
    raise NotImplementedError(
        "Live REC registry pull not wired. Provide SP_PLATTS_KEY (+ registry "
        "exports), or use tests/fixtures/recs_*.parquet."
    )


def fetch(config: dict) -> Path:
    ctx = context_from_config("recs", config)
    credential = require_credential(ctx.options.get("credentials_env"))
    return with_retries(lambda: _pull(ctx, credential))
