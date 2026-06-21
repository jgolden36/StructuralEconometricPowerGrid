"""Schema/range checks for built objects (CLAUDE.md §4).

Reconciles Aterio capacity against S&P / interconnection-queue filings and
verifies ancillary-services panel completeness by product ``j`` before the
estimator trusts the processed tensors.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class BuildReport:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def raise_if_failed(self) -> None:
        if not self.ok:
            raise ValueError("build validation failed:\n- " + "\n- ".join(self.errors))


def check_capacity_reconciliation(
    aterio: pd.DataFrame,
    queue: pd.DataFrame,
    *,
    key: str = "facility_id",
    cap_col: str = "mw_capacity",
    rel_tol: float = 0.25,
) -> BuildReport:
    """Flag facilities where Aterio MW disagrees with queue filings beyond tol."""
    report = BuildReport(ok=True)
    merged = aterio.merge(queue, on=key, suffixes=("_aterio", "_queue"), how="inner")
    if merged.empty:
        report.warnings.append("no overlapping facilities to reconcile")
        return report
    a, q = merged[f"{cap_col}_aterio"], merged[f"{cap_col}_queue"]
    rel = (a - q).abs() / q.replace(0, float("nan"))
    bad = merged.loc[rel > rel_tol, key].tolist()
    if bad:
        report.warnings.append(f"{len(bad)} facilities exceed {rel_tol:.0%} capacity gap")
    return report


def check_aux_panel_complete(
    aux: pd.DataFrame,
    *,
    products: list[str],
    product_col: str = "product",
    keys: tuple[str, ...] = ("zone", "block", "period"),
) -> BuildReport:
    """Verify every (zone, block, period) cell has all ancillary products ``j``."""
    report = BuildReport(ok=True)
    present = set(aux[product_col].unique())
    missing = set(products) - present
    if missing:
        report.ok = False
        report.errors.append(f"aux panel missing products: {sorted(missing)}")
    counts = aux.groupby(list(keys))[product_col].nunique()
    incomplete = int((counts < len(products)).sum())
    if incomplete:
        report.warnings.append(f"{incomplete} cells missing ≥1 ancillary product")
    return report
