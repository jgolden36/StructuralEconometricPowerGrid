"""Standard estimation-result container shared across stages (CLAUDE.md §5).

Carries point estimates and/or a partial-identification confidence set, the
matched/realized moments, and full provenance (spec hash, data vintages, git
SHA) so every downstream artifact is reproducible.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from sepg_struct.utils.io import ensure_dir, git_sha, utc_now_iso


@dataclass
class EstimationResult:
    stage: str
    params: dict[str, Any] = field(default_factory=dict)
    # Partial-ID confidence set: param -> [lo, hi]. Uniqueness is not assumed.
    confidence_set: dict[str, list[float]] = field(default_factory=dict)
    moments: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    spec_hash: str = ""
    data_vintages: dict[str, str] = field(default_factory=dict)
    estimates_vintage: str = "dev"
    git_sha: str = field(default_factory=git_sha)
    created_at: str = field(default_factory=utc_now_iso)

    def to_json(self, out_dir: str | Path = "outputs/estimates") -> Path:
        ensure_dir(out_dir)
        path = Path(out_dir) / f"{self.stage}.json"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(asdict(self), fh, indent=2, sort_keys=True, default=str)
        return path

    @classmethod
    def from_json(cls, path: str | Path) -> EstimationResult:
        with open(path, encoding="utf-8") as fh:
            return cls(**json.load(fh))
