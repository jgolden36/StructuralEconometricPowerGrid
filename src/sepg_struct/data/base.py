"""Shared scaffolding for source fetchers.

A fetcher resolves credentials from the env-var named in ``config/sources.yaml``
(never hard-coded), pulls raw bytes, writes them under ``data/raw/<source>/``,
and appends a manifest row. Network access uses exponential-backoff retries.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from sepg_struct.utils.io import append_manifest, ensure_dir
from sepg_struct.utils.logging import get_logger

log = get_logger(__name__)


class CredentialError(RuntimeError):
    """Raised when a proprietary source is fetched without its credential."""


@dataclass(frozen=True)
class FetchContext:
    source: str
    raw_dir: Path
    manifest: Path
    vintage: str
    options: dict


def context_from_config(source: str, config: dict) -> FetchContext:
    defaults = config.get("defaults", {})
    raw_dir = Path(defaults.get("raw_dir", "data/raw")) / source
    manifest = Path(defaults.get("manifest", "data/raw/manifest.csv"))
    spec = config.get("sources", {}).get(source, {})
    return FetchContext(
        source=source,
        raw_dir=ensure_dir(raw_dir),
        manifest=manifest,
        vintage=config.get("vintage", "dev"),
        options=spec,
    )


def require_credential(env_name: str | None) -> str | None:
    """Return the credential or raise if the source declares one but it's unset."""
    if not env_name:
        return None
    val = os.environ.get(env_name)
    if not val:
        raise CredentialError(
            f"missing credential ${env_name}; set it or use a fixture for CI"
        )
    return val


def with_retries(fn: Callable[[], object], *, retries: int = 4, base_s: float = 2.0):
    """Run ``fn`` with exponential backoff (2s, 4s, 8s, 16s) on exceptions."""
    last: Exception | None = None
    for attempt in range(retries):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - retry any transient failure
            last = exc
            wait = base_s * (2**attempt)
            log.warning("fetch attempt %d failed (%s); retrying in %ss", attempt + 1, exc, wait)
            time.sleep(wait)
    raise RuntimeError("all retries exhausted") from last


def record(ctx: FetchContext, path: Path, rows: int) -> Path:
    """Append a manifest row and return the written path."""
    append_manifest(ctx.manifest, source=ctx.source, file=path, vintage=ctx.vintage, rows=rows)
    log.info("wrote %s rows=%d -> %s", ctx.source, rows, path)
    return path
