"""S&P Capital IQ Pro (proprietary): PPA terms, FID/COD events, REC & gas prices.

Informs the contracting-vs-entry margin, financing rate ``r_l(σ²)``, PPA
bargaining ``ζ_f``, and ``p^REC`` (CLAUDE.md §3). Also ingests SEC filings and
the LevelTen PPA index for cross-validation.
"""

from __future__ import annotations

from pathlib import Path

from sepg_struct.data.base import context_from_config, require_credential, with_retries

SCHEMA = [
    "deal_id", "counterparty", "buyer_type", "form", "tenor_years",
    "contracted_capacity_mw", "ppa_price", "fid_date", "cod_date",
    "rec_price", "gas_price", "vintage",
]


def _pull(ctx, credential: str) -> Path:
    raise NotImplementedError(
        "Live S&P Capital IQ pull not wired. Provide SP_CAPITALIQ_KEY and "
        "implement the client, or use tests/fixtures/spglobal_*.parquet."
    )


def fetch(config: dict) -> Path:
    ctx = context_from_config("spglobal", config)
    credential = require_credential(ctx.options.get("credentials_env"))
    return with_retries(lambda: _pull(ctx, credential))
