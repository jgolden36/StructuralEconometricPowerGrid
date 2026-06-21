"""Lightweight stage-output caching.

Each pipeline stage caches its outputs (CLAUDE.md §1) so downstream stages do
not re-fetch or re-estimate. Keys are the spec hash of the inputs; values are
parquet/json on disk under ``data/interim`` or ``outputs/``.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from sepg_struct.utils.io import ensure_dir, spec_hash

T = TypeVar("T")


def cache_path(cache_dir: str | Path, key: str, suffix: str = ".json") -> Path:
    return Path(cache_dir) / f"{key}{suffix}"


def memoize_json(cache_dir: str | Path, spec: Any, compute: Callable[[], dict]) -> dict:
    """Return cached JSON for ``spec`` or compute, store, and return it."""
    ensure_dir(cache_dir)
    key = spec_hash(spec)
    path = cache_path(cache_dir, key)
    if path.exists():
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    result = compute()
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, sort_keys=True, default=str)
    return result
