"""Build the directed network ``G = (Z, A)`` (CLAUDE.md §4, eq:lr_state).

Echelons ``E`` (canonical ``E=3``: upstream/transit/downstream), zones ``Z_e``,
forward inter-echelon arcs (``e(j)=e(i)+1``), optional intra-echelon arcs, and
transfer capacities ``T̄_{a,t}``. Emits adjacency + capacity tensors used by the
headroom (eq:headroom) and clean-pool (eq:cleanpool) shadow prices.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np

from sepg_struct.utils.config import NetworkConfig


@dataclass
class Network:
    """Immutable network primitive consumed by the equilibrium solver."""

    graph: nx.DiGraph
    zones: list[str]
    zone_echelon: dict[str, int]
    capacity_mw: np.ndarray  # T̄: (n_zones, n_zones), forward arcs only

    @property
    def n_zones(self) -> int:
        return len(self.zones)

    def transfer_cap(self, src: str, dst: str) -> float:
        i, j = self.zones.index(src), self.zones.index(dst)
        return float(self.capacity_mw[i, j])


def build_network(cfg: NetworkConfig) -> Network:
    """Assemble :class:`Network` from a validated ``network.yaml`` config.

    Enforces the forward-arc restriction ``e(dst) = e(src) + 1`` for the arcs in
    ``cfg.arcs``; intra-echelon arcs (``e(dst) == e(src)``) are allowed only via
    ``cfg.intra_arcs``.
    """
    zones = [z.id for z in cfg.zones]
    zone_echelon = {z.id: z.echelon for z in cfg.zones}
    index = {z: i for i, z in enumerate(zones)}

    g = nx.DiGraph()
    for z in cfg.zones:
        g.add_node(z.id, echelon=z.echelon, iso=z.iso, ba=z.ba)

    cap = np.zeros((len(zones), len(zones)), dtype=float)

    for arc in cfg.arcs:
        e_src, e_dst = zone_echelon[arc.src], zone_echelon[arc.dst]
        if e_dst != e_src + 1:
            raise ValueError(
                f"forward inter-echelon arc {arc.src}->{arc.dst} violates "
                f"e(dst)=e(src)+1 (got {e_src}->{e_dst})"
            )
        g.add_edge(arc.src, arc.dst, t_bar_mw=arc.t_bar_mw)
        cap[index[arc.src], index[arc.dst]] = arc.t_bar_mw

    for arc in cfg.intra_arcs:
        if zone_echelon[arc.dst] != zone_echelon[arc.src]:
            raise ValueError(f"intra-echelon arc {arc.src}->{arc.dst} crosses echelons")
        g.add_edge(arc.src, arc.dst, t_bar_mw=arc.t_bar_mw, intra=True)
        cap[index[arc.src], index[arc.dst]] = arc.t_bar_mw

    return Network(graph=g, zones=zones, zone_echelon=zone_echelon, capacity_mw=cap)
