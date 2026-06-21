"""Partition the annual period into load blocks ``B`` with weights ``ω_b``.

Per ``config/blocks.yaml`` (CLAUDE.md §4). Each block carries representative
load, renewable availability, and an ancillary-services requirement multiplier.
Weights must sum to 1.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sepg_struct.utils.config import BlocksConfig

_WEIGHT_TOL = 1e-6


@dataclass
class LoadBlocks:
    ids: list[str]
    omega: np.ndarray          # (B,) weights, sum to 1
    ren_avail: np.ndarray      # (B,) renewable availability in [0,1]
    aux_req_mult: np.ndarray   # (B,) baseline aux-services requirement multiplier
    granularity_h: float

    @property
    def n_blocks(self) -> int:
        return len(self.ids)

    def weighted_sum(self, per_block: np.ndarray) -> float:
        """Σ_b ω_b · x_b  (the block aggregation used throughout the model)."""
        return float(np.dot(self.omega, np.asarray(per_block)))


def build_blocks(cfg: BlocksConfig) -> LoadBlocks:
    ids = [b.id for b in cfg.blocks]
    omega = np.array([b.omega for b in cfg.blocks], dtype=float)
    total = omega.sum()
    if abs(total - 1.0) > _WEIGHT_TOL:
        raise ValueError(f"block weights ω_b must sum to 1; got {total:.6f}")
    return LoadBlocks(
        ids=ids,
        omega=omega,
        ren_avail=np.array([b.ren_avail for b in cfg.blocks], dtype=float),
        aux_req_mult=np.array([b.aux_req_mult for b in cfg.blocks], dtype=float),
        granularity_h=cfg.granularity_h,
    )
