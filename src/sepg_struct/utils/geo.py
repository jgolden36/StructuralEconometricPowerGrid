"""Spatial harmonization: facility -> zone -> echelon -> BA.

Geographic/topology assets (ISO zone boundaries, FERC 715 arcs) are digitized
and stored as GeoJSON under ``data/raw/geo/`` (CLAUDE.md §3). This module maps
point facilities into model zones via point-in-polygon.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def assign_zone(
    facilities: pd.DataFrame,
    zones_geojson: str | Path,
    *,
    lon_col: str = "lon",
    lat_col: str = "lat",
    zone_id_col: str = "zone_id",
) -> pd.DataFrame:
    """Spatial-join facility points to model zones.

    Returns ``facilities`` with an added ``zone_id`` column. Imports geopandas
    lazily so the heavy geo stack is optional for non-geo code paths.
    """
    import geopandas as gpd

    zones = gpd.read_file(zones_geojson)
    pts = gpd.GeoDataFrame(
        facilities.copy(),
        geometry=gpd.points_from_xy(facilities[lon_col], facilities[lat_col]),
        crs=zones.crs,
    )
    joined = gpd.sjoin(pts, zones[[zone_id_col, "geometry"]], how="left", predicate="within")
    out = pd.DataFrame(joined.drop(columns="geometry"))
    return out
