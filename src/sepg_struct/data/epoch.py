"""Epoch + corporate announcements: model release timing and workload mix.

Provides the treatment anchor for the Stage-1 DiD (model release date), model
quality ``q_{f,t}``, and the train/inference allocation (CLAUDE.md §3).
"""

from __future__ import annotations

from pathlib import Path

from sepg_struct.data.base import context_from_config, with_retries

SCHEMA = [
    "model_id", "firm", "release_date", "training_compute_flop",
    "release_window", "train_share", "infer_share", "quality_index", "vintage",
]


def _pull(ctx) -> Path:
    raise NotImplementedError(
        "Live Epoch pull not wired. Implement the public dataset client, or use "
        "tests/fixtures/epoch_releases.parquet."
    )


def fetch(config: dict) -> Path:
    ctx = context_from_config("epoch", config)
    return with_retries(lambda: _pull(ctx))
