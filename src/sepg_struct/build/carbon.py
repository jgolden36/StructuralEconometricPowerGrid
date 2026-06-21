"""Marginal carbon intensity ``MCI_{z,b,t}`` (CLAUDE.md §4, eq:emissions).

Reconstructs dispatch from EPA CAMD + ISO unit-level data and computes the
marginal emitting unit's intensity per (zone, block, period) for emissions
accounting.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def marginal_carbon_intensity(
    dispatch: pd.DataFrame,
    *,
    zone_col: str = "zone",
    block_col: str = "block",
    period_col: str = "period",
    gen_col: str = "gross_load_mwh",
    co2_col: str = "co2_tons",
    marginal_unit_col: str | None = "is_marginal",
) -> pd.DataFrame:
    r"""Compute ``MCI`` as tons CO2 per MWh of the marginal unit.

    If ``marginal_unit_col`` flags the marginal unit per (zone, block, period),
    MCI is that unit's emission rate; otherwise it falls back to the dispatch-
    weighted average rate as a documented approximation.
    """
    df = dispatch.copy()
    df["_rate"] = df[co2_col] / df[gen_col].replace(0, np.nan)
    keys = [zone_col, block_col, period_col]

    if marginal_unit_col and marginal_unit_col in df.columns:
        marg = df[df[marginal_unit_col].astype(bool)]
        mci = marg.groupby(keys)["_rate"].mean()
    else:
        # dispatch-weighted average emission rate (approximation; flagged)
        w = df.groupby(keys).apply(
            lambda g: np.average(g["_rate"].fillna(0), weights=g[gen_col]),
            include_groups=False,
        )
        mci = w

    return mci.rename("mci_tons_per_mwh").reset_index()
