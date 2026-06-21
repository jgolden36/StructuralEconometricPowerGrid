"""Thin IO wrappers so side effects stay mockable (CLAUDE.md §2).

All downloads and file writes route through here; ``build/`` and ``estimation/``
stay pure. Includes the raw-data manifest writer and the reproducibility sidecar
JSON every figure/table must emit (CLAUDE.md §9).
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MANIFEST_COLUMNS = ["source", "file", "vintage", "rows", "sha256", "fetched_at"]


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def sha256_file(path: str | Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def git_sha(default: str = "unknown") -> str:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
            .decode()
            .strip()
        )
    except Exception:
        return default


def append_manifest(
    manifest_path: str | Path,
    *,
    source: str,
    file: str | Path,
    vintage: str,
    rows: int,
) -> None:
    """Append one row to ``data/raw/manifest.csv`` (CLAUDE.md §3)."""
    manifest_path = Path(manifest_path)
    ensure_dir(manifest_path.parent)
    new = not manifest_path.exists()
    with open(manifest_path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=MANIFEST_COLUMNS)
        if new:
            writer.writeheader()
        writer.writerow(
            {
                "source": source,
                "file": str(file),
                "vintage": vintage,
                "rows": rows,
                "sha256": sha256_file(file),
                "fetched_at": utc_now_iso(),
            }
        )


def write_sidecar(artifact_path: str | Path, *, spec_hash: str, estimates_vintage: str,
                  data_vintages: dict[str, str], extra: dict[str, Any] | None = None) -> Path:
    """Write the reproducibility sidecar JSON next to ``artifact_path``.

    Records spec hash, estimates vintage, data vintages, and git SHA so figures
    and tables are reproducible (CLAUDE.md §9).
    """
    artifact_path = Path(artifact_path)
    sidecar = artifact_path.with_suffix(artifact_path.suffix + ".meta.json")
    payload = {
        "artifact": artifact_path.name,
        "spec_hash": spec_hash,
        "estimates_vintage": estimates_vintage,
        "data_vintages": data_vintages,
        "git_sha": git_sha(),
        "written_at": utc_now_iso(),
    }
    if extra:
        payload["extra"] = extra
    with open(sidecar, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
    return sidecar


def spec_hash(spec: Any) -> str:
    """Stable hash of a (dataclass/dict/list) spec for sidecars and caching."""
    if is_dataclass(spec) and not isinstance(spec, type):
        spec = asdict(spec)
    blob = json.dumps(spec, sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()[:16]
