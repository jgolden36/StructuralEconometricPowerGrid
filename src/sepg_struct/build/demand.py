"""Assemble the demand side (CLAUDE.md §4).

Implements the load equations from the structural paper:
- gross IT load (eq:gross_load),
- net grid draw with PPA/colo/storage/backup offsets (eq:grid_draw),
- storage energy-balance + ramp constraints (eq:storage_balance),
- residual non-AI load ``D^O`` (EIA Form-930 load − estimated DC load),
- the timing wedge per block ``w = G^M − R^{M,G}`` at granularity ``h``.
"""

from __future__ import annotations

import numpy as np


def gross_it_load(
    rho_train: np.ndarray,
    k_train: np.ndarray,
    rho_infer: np.ndarray,
    k_infer: np.ndarray,
) -> np.ndarray:
    r"""Gross IT load (eq:gross_load).

    ``D^M = ρ_train · K_train + ρ_infer · K_infer``. Utilization ``ρ`` is
    block-dependent; capacities ``K`` partition ``K_{f,z,t}`` into train/infer.
    Inputs broadcast over ``(firm, zone, block, period)``.
    """
    return rho_train * k_train + rho_infer * k_infer


def net_grid_draw(
    d_m: np.ndarray,
    q_contract: np.ndarray,
    q_colo: np.ndarray,
    q_stor_out: np.ndarray,
    q_stor_in: np.ndarray,
    b_run: np.ndarray,
) -> np.ndarray:
    r"""Net grid draw (eq:grid_draw), floored at zero.

    ``G^M = (D^M − Q^contract − Q^colo − Q^{stor,out} + Q^{stor,in} − B^run)_+``.
    """
    raw = d_m - q_contract - q_colo - q_stor_out + q_stor_in - b_run
    return np.maximum(raw, 0.0)


def storage_step(
    stock: np.ndarray,
    q_in: np.ndarray,
    q_out: np.ndarray,
    *,
    eta_s: float,
    capacity: np.ndarray,
    c_rate: float,
) -> np.ndarray:
    r"""One block of the storage energy balance (eq:storage_balance).

    ``S_{b+1} = S_b + η_S · Q^in − Q^out`` with ``0 ≤ S ≤ S_cap`` and ramp
    ``|Q^{in/out}| ≤ R̄_S · S_cap``. Raises on constraint violation so infeasible
    dispatch fails loud rather than silently clipping.
    """
    ramp_lim = c_rate * capacity
    if np.any(np.abs(q_in) > ramp_lim + 1e-9) or np.any(np.abs(q_out) > ramp_lim + 1e-9):
        raise ValueError("storage ramp constraint |Q| ≤ R̄_S·S_cap violated")
    next_stock = stock + eta_s * q_in - q_out
    if np.any(next_stock < -1e-9) or np.any(next_stock > capacity + 1e-9):
        raise ValueError("storage stock left [0, S_cap]")
    return np.clip(next_stock, 0.0, capacity)


def residual_nonai_load(ba_load_930: np.ndarray, estimated_dc_load: np.ndarray) -> np.ndarray:
    r"""Residual non-AI load ``D^O`` = EIA-930 BA load − estimated DC load."""
    return np.maximum(ba_load_930 - estimated_dc_load, 0.0)


def timing_wedge(
    grid_draw: np.ndarray,
    granular_rec_match: np.ndarray,
) -> np.ndarray:
    r"""Per-block timing wedge ``w = G^M − R^{M,G}`` at granularity ``h``.

    The wedge is the gap between net grid draw and granular (hourly-matched)
    clean delivery; it is what 24/7-CFE counterfactuals compress.
    """
    return grid_draw - granular_rec_match
