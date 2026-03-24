#!/usr/bin/env python3
"""Shared helpers for small Python analysis scripts."""
from __future__ import annotations

import csv
import math
from pathlib import Path
from statistics import median
from typing import Dict, Iterable, List, Sequence


ROOT = Path(__file__).resolve().parents[2]
PREPARED_DATA_DIR = ROOT / "data" / "prepared"
PYTHON_OUTPUT_DIR = ROOT / "analysis" / "python_outputs"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Dict[str, object]]) -> int:
    ensure_dir(path.parent)
    count = 0
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def parse_int(value: str) -> int:
    return int(value) if value else 0


def parse_float(value: str) -> float | None:
    if value == "":
        return None
    return float(value)


def safe_ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def format_float(value: float | None, digits: int = 6) -> str:
    if value is None:
        return ""
    return f"{value:.{digits}f}"


def median_or_none(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return float(median(values))


def pearson_correlation(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    x_var = sum((x - x_mean) ** 2 for x in xs)
    y_var = sum((y - y_mean) ** 2 for y in ys)
    if x_var == 0 or y_var == 0:
        return None
    covariance = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    return covariance / math.sqrt(x_var * y_var)
