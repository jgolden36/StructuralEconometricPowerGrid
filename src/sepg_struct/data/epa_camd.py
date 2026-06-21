"""EPA CAMD (+ ISO unit-level dispatch): generation, fuel use, emissions.

Feeds dispatch reconstruction and the marginal carbon intensity ``MCI_{z,b,t}``
panel (CLAUDE.md §3).
"""

from __future__ import annotations

from pathlib import Path

from sepg_struct.data.base import context_from_config, with_retries

SCHEMA = ["unit_id", "ba", "date", "gross_load_mwh", "fuel_mmbtu", "co2_tons", "nox_lbs"]


def _pull(ctx) -> Path:
    raise NotImplementedError(
        "Live EPA CAMD (easey) pull not wired. Implement the client, or use "
        "tests/fixtures/camd_emissions.parquet."
    )


def fetch(config: dict) -> Path:
    ctx = context_from_config("epa_camd", config)
    return with_retries(lambda: _pull(ctx))
