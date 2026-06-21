"""ISO market data (PJM, ERCOT, CAISO, MISO, NYISO, ISO-NE, SPP).

Pulls nodal/zonal LMPs, capacity-auction clears (+ ELCC derating), and the
**ancillary-services clearing prices & quantities by product ``j`` and zone**
plus supply-curve slopes. Provides exogenous ``p^ene`` / ``p^cap`` and the
behavioral aux-services price ``p^aux`` (the Stage-1 DiD outcome) and supply
elasticity ``ε^s`` (CLAUDE.md §3).
"""

from __future__ import annotations

from pathlib import Path

from sepg_struct.data.base import context_from_config, with_retries

LMP_SCHEMA = ["iso", "zone", "block", "period", "lmp"]
ANCILLARY_SCHEMA = [
    "iso", "zone", "product", "block", "period", "price", "cleared_mw", "supply_slope",
]
CAPACITY_SCHEMA = ["iso", "zone", "period", "clearing_price", "elcc_derate"]


def _pull(ctx, iso_name: str) -> Path:
    raise NotImplementedError(
        f"Live {iso_name.upper()} pull not wired. Implement the per-ISO client "
        f"(Data Miner / MIS / OASIS / ...), or use tests/fixtures/iso_{iso_name}.parquet."
    )


def fetch(config: dict) -> Path:
    ctx = context_from_config("iso", config)
    isos = list(ctx.options.get("isos", {}))
    # Real impl pulls every ISO and concatenates; scaffold targets the first.
    return with_retries(lambda: _pull(ctx, isos[0] if isos else "pjm"))
