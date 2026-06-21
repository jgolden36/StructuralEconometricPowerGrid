"""Stage 1 - data acquisition. One module per source (CLAUDE.md §3).

Each source module exposes ``fetch(config) -> Path`` and writes to
``data/raw/<source>/`` plus a row in ``data/raw/manifest.csv``. Proprietary
sources are gated behind credentials; synthetic fixtures in ``tests/fixtures/``
stand in for CI.
"""

from __future__ import annotations

import importlib
from pathlib import Path

# source name -> module path (mirrors config/sources.yaml)
SOURCE_MODULES: dict[str, str] = {
    "aterio": "sepg_struct.data.aterio",
    "spglobal": "sepg_struct.data.spglobal",
    "epoch": "sepg_struct.data.epoch",
    "eia": "sepg_struct.data.eia",
    "epa_camd": "sepg_struct.data.epa_camd",
    "iso": "sepg_struct.data.iso",
    "recs": "sepg_struct.data.recs",
    "whisker": "sepg_struct.data.whisker",
    "twin": "sepg_struct.data.twin",
}


def fetch_source(name: str, config: dict) -> Path:
    """Dispatch to a single source module's ``fetch``."""
    if name not in SOURCE_MODULES:
        raise KeyError(f"unknown source {name!r}; known: {sorted(SOURCE_MODULES)}")
    mod = importlib.import_module(SOURCE_MODULES[name])
    return mod.fetch(config)


def fetch_all(config: dict) -> dict[str, Path]:
    """Fetch every configured source; returns {name: raw_path}."""
    return {name: fetch_source(name, config) for name in SOURCE_MODULES}
