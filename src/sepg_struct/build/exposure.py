"""Shift-share treatment exposure ``D^k_{z,t,m}`` (CLAUDE.md §4, eq:aux_did).

The "shock" is a firm-``f`` model-release event ``m``; the "share" is zone
``z``'s differential exposure, built from the Aterio DC operator mix and the
Epoch-inferred train/inference allocation. Feeds the Stage-1 ancillary-services
DiD.
"""

from __future__ import annotations

import pandas as pd


def exposure_share(
    dc_mix: pd.DataFrame,
    *,
    firm: str,
    zone_col: str = "zone_id",
    operator_col: str = "operator",
    capacity_col: str = "mw_capacity",
    alloc_col: str | None = None,
) -> pd.Series:
    r"""Zone exposure share to ``firm``: firm MW / total MW per zone.

    If ``alloc_col`` (train/infer allocation weight) is provided, MW is scaled by
    it so a zone heavy in training capacity loads differently than one heavy in
    inference. Returns a Series indexed by zone.
    """
    df = dc_mix.copy()
    weight = df[capacity_col]
    if alloc_col is not None:
        weight = weight * df[alloc_col]
    df = df.assign(_w=weight)
    total = df.groupby(zone_col)["_w"].sum()
    firm_w = df[df[operator_col] == firm].groupby(zone_col)["_w"].sum()
    share = (firm_w / total).reindex(total.index).fillna(0.0)
    share.name = f"exposure_{firm}"
    return share


def stacked_event_panel(
    exposure: pd.DataFrame,
    releases: pd.DataFrame,
    *,
    pre: int,
    post: int,
) -> pd.DataFrame:
    r"""Build the stacked-DiD panel with event-time indicators ``D^k_{z,t,m}``.

    For each release event ``m`` (firm, release_date), stack a (zone × event-time)
    window of width ``[-pre, +post]`` months, carrying the zone's exposure to the
    releasing firm. The reduced-form suite's stacked-DiD estimator consumes this.
    """
    frames = []
    for _, ev in releases.iterrows():
        firm = ev["firm"]
        t0 = pd.Timestamp(ev["release_date"]).to_period("M")
        col = f"exposure_{firm}"
        if col not in exposure.columns:
            continue
        for k in range(-pre, post + 1):
            period = (t0 + k).to_timestamp()
            block = exposure[["zone_id", col]].rename(columns={col: "exposure"}).copy()
            block["event_id"] = ev.get("model_id", f"{firm}_{t0}")
            block["event_time"] = k
            block["period"] = period
            block["firm"] = firm
            frames.append(block)
    if not frames:
        return pd.DataFrame(
            columns=["zone_id", "exposure", "event_id", "event_time", "period", "firm"]
        )
    out = pd.concat(frames, ignore_index=True)
    # Continuous treatment intensity D^k = exposure × 1{event_time = k}.
    out["treat_intensity"] = out["exposure"].astype(float)
    return out
