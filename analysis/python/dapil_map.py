#!/usr/bin/env python3
"""Helpers for building a lightweight DAPIL map payload for the dashboard."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Dict, Iterable, Iterator, List, Tuple

from common import ROOT, read_csv


DAPIL_GEOJSON_PATH = ROOT / "analysis" / "reference" / "dapil_map" / "gadm41_IDN_2.json"
DAPIL_LOOKUP_PATH = ROOT / "analysis" / "reference" / "dapil_map" / "gadm_sf_dapil.csv"
DISTRICT_ALIASES = {
    "PAPUA": "P A P U A",
}


def normalize_district_name(value: str) -> str:
    normalized = " ".join(str(value or "").upper().split())
    return DISTRICT_ALIASES.get(normalized, normalized)


def build_dapil_map_payload(width: float = 960.0, padding: float = 20.0) -> dict:
    gid_to_district = {}
    for row in read_csv(DAPIL_LOOKUP_PATH):
        gid = row.get("GID_2", "").strip()
        district = row.get("DAPIL", "").strip()
        if gid and district:
            gid_to_district[gid] = {
                "label": district,
                "districtKey": normalize_district_name(district),
            }

    geojson = json.loads(DAPIL_GEOJSON_PATH.read_text(encoding="utf-8"))
    features = [
        feature
        for feature in geojson.get("features", [])
        if feature.get("properties", {}).get("TYPE_2") != "WaterBody"
        and feature.get("properties", {}).get("GID_2") in gid_to_district
    ]
    min_lon, min_lat, max_lon, max_lat = _bounds_for_features(features)
    lon_span = max(max_lon - min_lon, 1e-6)
    lat_span = max(max_lat - min_lat, 1e-6)
    usable_width = max(width - (padding * 2.0), 1.0)
    scale = usable_width / lon_span
    height = (lat_span * scale) + (padding * 2.0)

    def project(lon: float, lat: float) -> Tuple[float, float]:
        x = padding + ((lon - min_lon) * scale)
        y = padding + ((max_lat - lat) * scale)
        return (x, y)

    districts: Dict[str, dict] = {}
    for feature in features:
        geometry = feature.get("geometry")
        if not geometry:
            continue
        gid = feature.get("properties", {}).get("GID_2", "")
        district_meta = gid_to_district.get(gid)
        if not district_meta:
            continue
        path_data = _geometry_to_path(geometry, project)
        if not path_data:
            continue
        entry = districts.setdefault(
            district_meta["districtKey"],
            {
                "label": district_meta["label"],
                "districtKey": district_meta["districtKey"],
                "paths": [],
            },
        )
        entry["paths"].append(path_data)

    return {
        "viewBox": f"0 0 {width:.1f} {height:.1f}",
        "districts": sorted(districts.values(), key=lambda item: item["label"]),
    }


def _bounds_for_features(features: Iterable[dict]) -> Tuple[float, float, float, float]:
    min_lon = float("inf")
    min_lat = float("inf")
    max_lon = float("-inf")
    max_lat = float("-inf")
    for feature in features:
        for lon, lat in _iter_geometry_points(feature.get("geometry", {})):
            min_lon = min(min_lon, lon)
            min_lat = min(min_lat, lat)
            max_lon = max(max_lon, lon)
            max_lat = max(max_lat, lat)
    if min_lon == float("inf"):
        return (0.0, 0.0, 1.0, 1.0)
    return (min_lon, min_lat, max_lon, max_lat)


def _iter_geometry_points(geometry: dict) -> Iterator[Tuple[float, float]]:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])
    if geometry_type == "Polygon":
        for ring in coordinates:
            for point in ring:
                yield (float(point[0]), float(point[1]))
        return
    if geometry_type == "MultiPolygon":
        for polygon in coordinates:
            for ring in polygon:
                for point in ring:
                    yield (float(point[0]), float(point[1]))


def _geometry_to_path(geometry: dict, project: Callable[[float, float], Tuple[float, float]]) -> str:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])
    path_segments: List[str] = []
    if geometry_type == "Polygon":
        path_segments.extend(_polygon_to_segments(coordinates, project))
    elif geometry_type == "MultiPolygon":
        for polygon in coordinates:
            path_segments.extend(_polygon_to_segments(polygon, project))
    return " ".join(path_segments)


def _polygon_to_segments(
    polygon: List[List[List[float]]],
    project: Callable[[float, float], Tuple[float, float]],
) -> List[str]:
    segments = []
    for ring in polygon:
        if len(ring) < 3:
            continue
        if ring[0] == ring[-1]:
            ring = ring[:-1]
        commands = []
        for index, point in enumerate(ring):
            x, y = project(float(point[0]), float(point[1]))
            prefix = "M" if index == 0 else "L"
            commands.append(f"{prefix}{x:.1f},{y:.1f}")
        commands.append("Z")
        segments.append(" ".join(commands))
    return segments
