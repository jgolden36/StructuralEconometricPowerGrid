"""Typed configuration models (pydantic) and YAML loaders.

These mirror the four ``config/*.yaml`` files. Loading is validated so a
malformed spec fails at parse time rather than deep inside an estimator.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

# --------------------------------------------------------------------------- #
# network.yaml
# --------------------------------------------------------------------------- #


class Echelon(BaseModel):
    id: int
    name: str


class Zone(BaseModel):
    id: str
    echelon: int
    iso: str
    ba: str


class Arc(BaseModel):
    src: str
    dst: str
    t_bar_mw: float


class NetworkConfig(BaseModel):
    echelons: list[Echelon]
    zones: list[Zone]
    arcs: list[Arc]
    intra_arcs: list[Arc] = Field(default_factory=list)
    clean_pool: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------------------- #
# blocks.yaml
# --------------------------------------------------------------------------- #


class Block(BaseModel):
    id: str
    time_of_day: str
    season: str
    renewables: str
    omega: float
    ren_avail: float
    aux_req_mult: float


class BlocksConfig(BaseModel):
    partition: dict[str, Any]
    blocks: list[Block]
    granularity_h: float = 0.0


# --------------------------------------------------------------------------- #
# structural.yaml  (kept loose: declarative spec consumed by estimators)
# --------------------------------------------------------------------------- #


class StructuralConfig(BaseModel):
    seed: int = 0
    stage1_shortrun: dict[str, Any] = Field(default_factory=dict)
    stage2_calibration: dict[str, Any] = Field(default_factory=dict)
    stage3_longrun: dict[str, Any] = Field(default_factory=dict)
    equilibrium: dict[str, Any] = Field(default_factory=dict)
    counterfactual: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------------------- #
# sources.yaml
# --------------------------------------------------------------------------- #


class SourcesConfig(BaseModel):
    defaults: dict[str, Any] = Field(default_factory=dict)
    sources: dict[str, Any] = Field(default_factory=dict)
    geo: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Loaders
# --------------------------------------------------------------------------- #


def _read_yaml(path: str | Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_network(path: str | Path = "config/network.yaml") -> NetworkConfig:
    return NetworkConfig.model_validate(_read_yaml(path))


def load_blocks(path: str | Path = "config/blocks.yaml") -> BlocksConfig:
    return BlocksConfig.model_validate(_read_yaml(path))


def load_structural(path: str | Path = "config/structural.yaml") -> StructuralConfig:
    return StructuralConfig.model_validate(_read_yaml(path))


def load_sources(path: str | Path = "config/sources.yaml") -> SourcesConfig:
    return SourcesConfig.model_validate(_read_yaml(path))
