"""Temporal harmonization helpers: hour -> load block -> annual period.

Stage 2 (``build/``) harmonizes the temporal grain so the estimator and
equilibrium solver consume ``(firm, zone, block, period)`` tensors.
"""

from __future__ import annotations

import pandas as pd


def to_annual_period(ts: pd.Series | pd.DatetimeIndex) -> pd.Series:
    """Map timestamps to the integer annual period ``t`` used by the model."""
    idx = pd.DatetimeIndex(ts)
    return pd.Series(idx.year, index=getattr(ts, "index", None))


def assign_block(
    ts: pd.Series | pd.DatetimeIndex,
    *,
    peak_hours: range = range(8, 22),
    summer_months: tuple[int, ...] = (5, 6, 7, 8, 9, 10),
) -> pd.Series:
    """Coarse hour -> (time_of_day, season) tag used by :mod:`build.blocks`.

    The renewable-availability tercile is resolved downstream from realized
    generation, so this returns only the deterministic calendar dimensions.
    """
    idx = pd.DatetimeIndex(ts)
    tod = pd.Series(["peak" if h in peak_hours else "offpeak" for h in idx.hour])
    season = pd.Series(["summer" if m in summer_months else "winter" for m in idx.month])
    return tod.str.cat(season, sep="_")
