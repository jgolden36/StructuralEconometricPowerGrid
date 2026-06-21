"""Pre-trends test for the Stage-1 aux-services DiD (CLAUDE.md §6).

**Reuses the reduced-form suite**: a joint F-test on the pre-period event-time
leads of eq:aux_did. This module only adapts inputs/outputs; it does not
re-implement the test.
"""

from __future__ import annotations

import pandas as pd


def joint_pretrend_test(event_study: dict[int, float], cov: pd.DataFrame | None = None) -> dict:
    """Joint F-test that pre-period leads (``event_time < 0``) are zero.

    Delegates to the reduced-form suite's implementation; falls back to a clear
    error if that dependency is absent.
    """
    try:
        from sepg.validation import pretrends as rf_pretrends  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "Pre-trends test is reused from the reduced-form suite "
            "(`from sepg.validation import pretrends`). Install the companion pkg."
        ) from exc
    return rf_pretrends.joint_lead_test(event_study, cov)
