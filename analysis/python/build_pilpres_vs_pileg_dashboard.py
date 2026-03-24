#!/usr/bin/env python3
"""Build a standalone interactive dashboard for Pilpres vs Pileg coalition alignment."""
from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path

from common import PREPARED_DATA_DIR, PYTHON_OUTPUT_DIR, ROOT, ensure_dir, read_csv


OUTPUT_DIR = ensure_dir(PYTHON_OUTPUT_DIR / "pilpres_vs_pileg_dashboard")
SOURCE_CSV_PATH = ROOT / "Pilpres V Pileg" / "election_results.csv"
TRACKED_SOURCE_CSV_PATH = ROOT / "analysis" / "reference" / "pilpres_vs_pileg" / "election_results.csv"
PROVINCE_LOOKUP_PATH = PREPARED_DATA_DIR / "province_lookup.csv"

CANDIDATES = [
    {
        "key": "anies",
        "label": "Anies Baswedan",
        "shortLabel": "Anies",
        "color": "#2563eb",
        "coalitionParties": ["PKB", "PKS", "NasDem", "Ummat"],
    },
    {
        "key": "prabowo",
        "label": "Prabowo Subianto",
        "shortLabel": "Prabowo",
        "color": "#15803d",
        "coalitionParties": ["Gerindra", "Golkar", "PAN", "Demokrat", "PSI", "Gelora", "Garuda"],
    },
    {
        "key": "ganjar",
        "label": "Ganjar Pranowo",
        "shortLabel": "Ganjar",
        "color": "#dc2626",
        "coalitionParties": ["PDIP", "PPP", "Hanura", "Perindo"],
    },
]


def resolve_source_csv_path() -> Path:
    if SOURCE_CSV_PATH.exists():
        return SOURCE_CSV_PATH
    if TRACKED_SOURCE_CSV_PATH.exists():
        return TRACKED_SOURCE_CSV_PATH
    raise FileNotFoundError(
        "Missing Pilpres vs Pileg input CSV. Checked "
        f"{SOURCE_CSV_PATH} and {TRACKED_SOURCE_CSV_PATH}."
    )


def parse_float(value: str) -> float | None:
    raw = (value or "").strip()
    if not raw or raw.upper() == "NA":
        return None
    return float(raw)


def parse_int(value: str) -> int | None:
    raw = (value or "").strip()
    if not raw or raw.upper() == "NA":
        return None
    return int(float(raw))


def iso_timestamp(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")


def source_entry(path: Path, label: str, kind: str, row_count: int | None = None, note: str = "") -> dict:
    entry = {
        "label": label,
        "kind": kind,
        "path": path.relative_to(ROOT).as_posix(),
        "updatedAt": iso_timestamp(path),
        "note": note,
    }
    if row_count is not None:
        entry["rowCount"] = row_count
    return entry


def normalize_key(value: str) -> str:
    return " ".join((value or "").strip().upper().split())


def build_province_mapping() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for row in read_csv(PROVINCE_LOOKUP_PATH):
        raw = row.get("province_raw", "")
        canonical = row.get("province", "")
        if raw and canonical:
            mapping[normalize_key(raw)] = canonical
    return mapping


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2


def safe_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def make_payload() -> dict:
    source_csv_path = resolve_source_csv_path()
    province_mapping = build_province_mapping()
    source_rows = read_csv(source_csv_path)

    provinces: list[dict[str, object]] = []
    complete_provinces: list[dict[str, object]] = []
    incomplete_provinces: list[dict[str, object]] = []

    for row in source_rows:
        raw_region = row["Region"].strip()
        canonical_region = province_mapping.get(normalize_key(raw_region), raw_region)
        region_key = normalize_key(canonical_region)
        total_votes = parse_int(row["Total_Votes"])
        independent_votes = parse_int(row["Total_Independent_Votes"])
        independent_pct = parse_float(row["Independent_Percentage"])

        candidate_rows = []
        province_complete = True
        for candidate in CANDIDATES:
            prefix = candidate["shortLabel"]
            pilpres_pct = parse_float(row[f"{prefix}_Pilpres"])
            coalition_pct = parse_float(row[f"{prefix}_Percentage"])
            coalition_votes = parse_int(row[f"Total_{prefix}_Votes"])
            difference = None
            abs_difference = None
            if pilpres_pct is not None and coalition_pct is not None:
                difference = pilpres_pct - coalition_pct
                abs_difference = abs(difference)
            else:
                province_complete = False
            candidate_rows.append(
                {
                    "candidateKey": candidate["key"],
                    "candidateLabel": candidate["label"],
                    "candidateShortLabel": candidate["shortLabel"],
                    "color": candidate["color"],
                    "pilpresPct": pilpres_pct,
                    "coalitionPct": coalition_pct,
                    "difference": difference,
                    "absDifference": abs_difference,
                    "coalitionVotes": coalition_votes,
                }
            )

        valid_differences = [float(item["absDifference"]) for item in candidate_rows if item["absDifference"] is not None]
        sum_abs_diff = sum(valid_differences) if len(valid_differences) == len(CANDIDATES) else None
        max_abs_diff = max(valid_differences) if valid_differences else None
        record = {
            "regionKey": region_key,
            "region": canonical_region,
            "regionRaw": raw_region,
            "displayLabel": canonical_region,
            "totalVotes": total_votes,
            "independentVotes": independent_votes,
            "independentPct": independent_pct,
            "complete": province_complete,
            "sumAbsDiff": sum_abs_diff,
            "maxAbsDiff": max_abs_diff,
            "candidateRows": candidate_rows,
        }
        provinces.append(record)
        if province_complete:
            complete_provinces.append(record)
        else:
            incomplete_provinces.append(record)

    provinces.sort(
        key=lambda item: (
            item["sumAbsDiff"] is None,
            -(item["sumAbsDiff"] or -1),
            str(item["displayLabel"]),
        )
    )
    complete_provinces.sort(key=lambda item: (-(item["sumAbsDiff"] or 0), str(item["displayLabel"])))
    incomplete_provinces.sort(key=lambda item: str(item["displayLabel"]))

    candidate_summaries: dict[str, dict[str, object]] = {}
    for candidate in CANDIDATES:
        key = candidate["key"]
        rows = []
        for province in complete_provinces:
            match = next(item for item in province["candidateRows"] if item["candidateKey"] == key)
            rows.append(
                {
                    "regionKey": province["regionKey"],
                    "region": province["displayLabel"],
                    "pilpresPct": match["pilpresPct"],
                    "coalitionPct": match["coalitionPct"],
                    "difference": match["difference"],
                    "absDifference": match["absDifference"],
                    "coalitionVotes": match["coalitionVotes"],
                    "totalVotes": province["totalVotes"],
                }
            )
        rows.sort(key=lambda item: (-(item["absDifference"] or 0), str(item["region"])))
        diffs = [float(item["difference"]) for item in rows if item["difference"] is not None]
        abs_diffs = [abs(float(item["difference"])) for item in rows if item["difference"] is not None]
        candidate_summaries[key] = {
            "candidateKey": key,
            "avgDifference": mean(diffs),
            "avgAbsDifference": mean(abs_diffs),
            "medianAbsDifference": median(abs_diffs),
            "candidateLeadCount": sum(1 for item in rows if (item["difference"] or 0) > 0),
            "coalitionLeadCount": sum(1 for item in rows if (item["difference"] or 0) < 0),
            "closestProvinceKey": min(rows, key=lambda item: item["absDifference"])["regionKey"] if rows else "",
            "largestCandidateLeadKey": max(rows, key=lambda item: item["difference"])["regionKey"] if rows else "",
            "largestCoalitionLeadKey": min(rows, key=lambda item: item["difference"])["regionKey"] if rows else "",
            "rows": rows,
        }

    best_alignment_candidate = min(
        CANDIDATES,
        key=lambda item: candidate_summaries[item["key"]]["avgAbsDifference"] or float("inf"),
    )

    mismatch_ranking = [
        {
            "regionKey": province["regionKey"],
            "region": province["displayLabel"],
            "sumAbsDiff": province["sumAbsDiff"],
            "maxAbsDiff": province["maxAbsDiff"],
        }
        for province in complete_provinces
    ]

    payload = {
        "meta": {
            "title": "Pilpres vs Pileg Coalition Alignment Dashboard",
            "subtitle": "Province-level 2024 comparison between presidential vote share and coalition legislative strength",
            "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
            "provinceCount": len(provinces),
            "comparableProvinceCount": len(complete_provinces),
            "incompleteProvinceCount": len(incomplete_provinces),
            "bestAlignedCandidate": best_alignment_candidate["label"],
            "bestAlignedCandidateAvgAbsDiff": candidate_summaries[best_alignment_candidate["key"]]["avgAbsDifference"],
            "methodology": [
                {
                    "title": "Source Layer",
                    "body": (
                        "This dashboard uses the structured comparison table in the new Pilpres-vs-Pileg folder. "
                        "The comparison logic is rebuilt directly in Python from that CSV."
                    ),
                },
                {
                    "title": "Difference Definition",
                    "body": (
                        "Difference is computed as Pilpres percentage minus coalition Pileg percentage. Positive values mean the presidential "
                        "ticket ran ahead of its coalition, while negative values mean the coalition outperformed the ticket."
                    ),
                },
                {
                    "title": "Province Coverage",
                    "body": (
                        "Most provinces are fully comparable. One row, Daerah Istimewa Yogyakarta, is incomplete in the source CSV and is "
                        "called out separately rather than imputed."
                    ),
                },
                {
                    "title": "Why No Geographic Map",
                    "body": (
                        "This repo does not currently track province geometry locally, so the dashboard emphasizes richer scatter, ranking, "
                        "and matrix views instead of depending on external shapefiles."
                    ),
                },
            ],
            "sources": [
                source_entry(
                    source_csv_path,
                    "Pilpres vs Pileg Comparison Table",
                    "csv",
                    row_count=len(source_rows),
                    note=(
                        "Province-level presidential percentages, coalition vote percentages, coalition vote totals, and helper columns."
                        if source_csv_path == SOURCE_CSV_PATH
                        else "Tracked reference copy trimmed to the columns needed for the public dashboard build."
                    ),
                ),
                source_entry(
                    PROVINCE_LOOKUP_PATH,
                    "Province Lookup",
                    "prepared_csv",
                    row_count=len(read_csv(PROVINCE_LOOKUP_PATH)),
                    note="Used to normalize province names into the repo's standard naming.",
                ),
            ],
        },
        "candidates": CANDIDATES,
        "provinces": provinces,
        "candidateSummaries": candidate_summaries,
        "mismatchRanking": mismatch_ranking,
    }
    return payload


def build_html(payload: dict) -> str:
    template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Pilpres vs Pileg Coalition Alignment</title>
  <style>
    :root {
      --paper: #f6f2ea;
      --paper-2: #fbf9f4;
      --ink: #17222c;
      --muted: #5d6974;
      --line: rgba(23,34,44,0.12);
      --panel: rgba(255,255,255,0.86);
      --panel-strong: rgba(255,255,255,0.94);
      --shadow: 0 20px 44px rgba(23,34,44,0.10);
      --radius: 24px;
      --positive: #1d4ed8;
      --negative: #b45309;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--ink);
      font-family: "Avenir Next", "Trebuchet MS", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(37,99,235,0.14), transparent 32%),
        radial-gradient(circle at top right, rgba(220,38,38,0.12), transparent 28%),
        linear-gradient(180deg, #faf6ee 0%, #fbf9f4 52%, #f4eee1 100%);
      min-height: 100vh;
    }
    .skip-link {
      position: absolute;
      left: 16px;
      top: -46px;
      z-index: 40;
      padding: 10px 14px;
      border-radius: 999px;
      background: #fff;
      color: var(--ink);
      text-decoration: none;
      box-shadow: 0 12px 24px rgba(23,34,44,0.14);
    }
    .skip-link:focus { top: 16px; }
    .app {
      max-width: 1500px;
      margin: 0 auto;
      padding: 28px 20px 72px;
    }
    .hero {
      padding: 30px;
      border-radius: 34px;
      background:
        linear-gradient(135deg, rgba(255,255,255,0.9), rgba(255,255,255,0.76)),
        linear-gradient(135deg, rgba(37,99,235,0.09), rgba(180,83,9,0.08));
      border: 1px solid rgba(255,255,255,0.58);
      box-shadow: var(--shadow);
    }
    .hero-grid {
      display: grid;
      grid-template-columns: 1.4fr 1fr;
      gap: 22px;
      align-items: start;
    }
    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 7px 12px;
      border-radius: 999px;
      background: rgba(37,99,235,0.10);
      color: #1d4ed8;
      font-size: 0.82rem;
      font-weight: 700;
      letter-spacing: 0.07em;
      text-transform: uppercase;
    }
    h1, h2, h3 {
      margin: 0;
      font-family: "Baskerville", "Iowan Old Style", "Georgia", serif;
      letter-spacing: -0.02em;
    }
    h1 {
      margin-top: 16px;
      font-size: clamp(2.2rem, 4.8vw, 4.2rem);
      line-height: 0.95;
      max-width: 11ch;
    }
    .hero p {
      margin: 14px 0 0;
      max-width: 70ch;
      color: var(--muted);
      line-height: 1.56;
      font-size: 1rem;
    }
    .control-card, .summary-card, .panel {
      background: var(--panel);
      border-radius: var(--radius);
      border: 1px solid rgba(255,255,255,0.58);
      box-shadow: var(--shadow);
      backdrop-filter: blur(14px);
    }
    .control-card {
      padding: 18px;
      display: grid;
      gap: 14px;
    }
    .control-label {
      color: var(--muted);
      font-size: 0.76rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin-bottom: 8px;
    }
    .segmented {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .segment-btn {
      border: 1px solid rgba(23,34,44,0.10);
      background: rgba(255,255,255,0.76);
      color: var(--ink);
      padding: 10px 12px;
      border-radius: 14px;
      font: inherit;
      font-size: 0.93rem;
      font-weight: 700;
      cursor: pointer;
      transition: transform 120ms ease, border-color 120ms ease, background 120ms ease;
    }
    .segment-btn:hover,
    .segment-btn:focus-visible {
      transform: translateY(-1px);
      outline: none;
      border-color: rgba(37,99,235,0.35);
    }
    .segment-btn.active {
      color: #1d4ed8;
      border-color: rgba(37,99,235,0.4);
      background: rgba(37,99,235,0.10);
    }
    input[type="search"] {
      width: 100%;
      border: 1px solid rgba(23,34,44,0.10);
      background: rgba(255,255,255,0.82);
      border-radius: 14px;
      padding: 12px 14px;
      color: var(--ink);
      font: inherit;
    }
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      margin-top: 20px;
    }
    .summary-card {
      padding: 18px;
      min-height: 116px;
      display: grid;
      gap: 8px;
    }
    .summary-card .label {
      color: var(--muted);
      font-size: 0.75rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    .summary-card .value {
      font-size: 1.65rem;
      font-weight: 800;
      letter-spacing: -0.04em;
    }
    .summary-card .note {
      color: var(--muted);
      font-size: 0.92rem;
      line-height: 1.45;
    }
    main {
      display: grid;
      gap: 22px;
      margin-top: 22px;
    }
    .panel { padding: 22px; }
    .section-head {
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 12px;
      margin-bottom: 18px;
    }
    .section-head p {
      margin: 8px 0 0;
      color: var(--muted);
      line-height: 1.5;
      max-width: 70ch;
    }
    .analysis-grid {
      display: grid;
      grid-template-columns: 1.2fr 0.92fr;
      gap: 20px;
      align-items: start;
    }
    .subpanel {
      border-radius: 20px;
      background: rgba(255,255,255,0.74);
      border: 1px solid rgba(23,34,44,0.08);
      padding: 16px;
    }
    .search-row {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-bottom: 12px;
    }
    .btn {
      border: 1px solid rgba(23,34,44,0.10);
      background: rgba(255,255,255,0.82);
      color: var(--ink);
      border-radius: 14px;
      padding: 11px 14px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }
    .chart-note, .small-note {
      color: var(--muted);
      font-size: 0.9rem;
      line-height: 1.45;
    }
    .matrix-grid {
      display: grid;
      grid-template-columns: 0.96fr 1.04fr;
      gap: 20px;
      align-items: start;
    }
    .rank-table-wrap, .matrix-wrap {
      overflow: auto;
      border-radius: 16px;
      border: 1px solid rgba(23,34,44,0.08);
      background: rgba(255,255,255,0.74);
      max-height: 640px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 560px;
    }
    th, td {
      padding: 11px 12px;
      border-bottom: 1px solid rgba(23,34,44,0.08);
      text-align: left;
      font-size: 0.92rem;
      white-space: nowrap;
    }
    th {
      position: sticky;
      top: 0;
      z-index: 1;
      background: rgba(250,248,244,0.98);
      color: var(--muted);
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    tr[data-region] { cursor: pointer; }
    tr:hover td, tr.active td { background: rgba(37,99,235,0.06); }
    .candidate-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-weight: 700;
    }
    .candidate-swatch {
      width: 10px;
      height: 10px;
      border-radius: 999px;
      flex: 0 0 auto;
    }
    .delta-pos { color: #1d4ed8; font-weight: 700; }
    .delta-neg { color: #b45309; font-weight: 700; }
    .delta-zero { color: var(--muted); font-weight: 700; }
    .detail-shell {
      display: grid;
      gap: 16px;
    }
    .detail-header h3 {
      font-size: 2rem;
    }
    .detail-header p {
      margin: 8px 0 0;
      color: var(--muted);
      line-height: 1.45;
    }
    .detail-metrics {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }
    .metric {
      padding: 16px;
      border-radius: 18px;
      background: rgba(255,255,255,0.72);
      border: 1px solid rgba(23,34,44,0.08);
    }
    .metric .label {
      color: var(--muted);
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    .metric .value {
      margin-top: 8px;
      font-size: 1.42rem;
      font-weight: 800;
      letter-spacing: -0.04em;
    }
    .candidate-detail-grid {
      display: grid;
      gap: 12px;
    }
    .candidate-detail-card {
      padding: 16px;
      border-radius: 18px;
      background: rgba(255,255,255,0.72);
      border: 1px solid rgba(23,34,44,0.08);
    }
    .bar-stack {
      display: grid;
      gap: 10px;
      margin-top: 12px;
    }
    .bar-row {
      display: grid;
      gap: 6px;
    }
    .bar-label {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      font-size: 0.88rem;
    }
    .bar-track {
      width: 100%;
      height: 10px;
      border-radius: 999px;
      background: rgba(23,34,44,0.08);
      overflow: hidden;
    }
    .bar-fill {
      height: 100%;
      border-radius: 999px;
    }
    .matrix-legend {
      display: flex;
      flex-wrap: wrap;
      gap: 10px 16px;
      color: var(--muted);
      font-size: 0.9rem;
      margin-bottom: 12px;
      align-items: center;
    }
    .legend-chip {
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
    .legend-swatch {
      width: 18px;
      height: 12px;
      border-radius: 999px;
      border: 1px solid rgba(23,34,44,0.08);
    }
    .method-grid, .source-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
    }
    .method-card, .source-card {
      padding: 16px;
      border-radius: 18px;
      background: rgba(255,255,255,0.72);
      border: 1px solid rgba(23,34,44,0.08);
    }
    .method-card p, .source-card p {
      margin: 8px 0 0;
      color: var(--muted);
      line-height: 1.5;
    }
    .source-card code {
      display: inline-block;
      margin-top: 10px;
      font-size: 0.82rem;
      word-break: break-all;
      color: #1d4ed8;
    }
    .tooltip {
      position: fixed;
      z-index: 40;
      max-width: 260px;
      padding: 12px 14px;
      border-radius: 14px;
      background: rgba(17,24,39,0.94);
      color: #f8fafc;
      font-size: 0.88rem;
      line-height: 1.45;
      pointer-events: none;
      opacity: 0;
      transform: translateY(4px);
      transition: opacity 100ms ease, transform 100ms ease;
      box-shadow: 0 18px 36px rgba(0,0,0,0.24);
    }
    .tooltip.open {
      opacity: 1;
      transform: translateY(0);
    }
    @media (max-width: 1180px) {
      .hero-grid,
      .analysis-grid,
      .matrix-grid {
        grid-template-columns: 1fr;
      }
      .summary-grid,
      .detail-metrics,
      .method-grid,
      .source-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }
    @media (max-width: 720px) {
      .app { padding: 16px 14px 48px; }
      .hero, .panel { padding: 18px; }
      .summary-grid,
      .detail-metrics,
      .method-grid,
      .source-grid {
        grid-template-columns: 1fr;
      }
      h1 { font-size: 2.4rem; }
    }
  </style>
</head>
<body>
  <a class="skip-link" href="#main-content">Skip to dashboard</a>
  <div class="app">
    <header class="hero">
      <div class="hero-grid">
        <div>
          <div class="eyebrow">Pilpres vs Pileg</div>
          <h1>Where Did The Presidential Ticket And Coalition Move Together?</h1>
          <p>
            This dashboard compares each ticket's 2024 Pilpres vote share with the legislative coalition percentage attributed to that
            ticket in the source comparison table. Click a province anywhere to inspect how tightly the campaign and coalition stayed aligned.
          </p>
          <p class="small-note" id="hero-meta"></p>
        </div>
        <section class="control-card">
          <div>
            <div class="control-label">Candidate Focus</div>
            <div id="candidate-controls" class="segmented"></div>
          </div>
          <div>
            <div class="control-label">Province Search</div>
            <input id="province-search" type="search" placeholder="Filter provinces by name" />
          </div>
          <div class="small-note" id="candidate-note"></div>
        </section>
      </div>
      <div id="summary-cards" class="summary-grid"></div>
    </header>

    <main id="main-content">
      <section class="panel">
        <div class="section-head">
          <div>
            <h2>Alignment Scatter And Province Detail</h2>
            <p>
              Points near the diagonal show close alignment between the presidential ticket and the coalition. Points below the line mean
              the ticket outran its coalition; points above the line mean the coalition ran ahead of the ticket.
            </p>
          </div>
        </div>
        <div class="analysis-grid">
          <div class="subpanel">
            <div id="scatter-chart"></div>
            <p class="chart-note">Circle size scales with coalition vote totals in the comparison CSV. Click any point to lock that province into the detail panel.</p>
          </div>
          <div id="province-detail" class="detail-shell subpanel"></div>
        </div>
      </section>

      <section class="panel">
        <div class="section-head">
          <div>
            <h2>Mismatch Ranking And Cross-Candidate Matrix</h2>
            <p>
              The ranking view shows where the chosen ticket diverged most. The matrix shows all three candidate gaps at once, making it
              easier to spot provinces where only one coalition broke down versus places where the whole landscape was misaligned.
            </p>
          </div>
        </div>
        <div class="matrix-grid">
          <div class="subpanel">
            <div class="search-row">
              <button id="sort-total" class="btn" type="button">Sort by total mismatch</button>
              <button id="sort-candidate" class="btn" type="button">Sort by selected candidate</button>
              <button id="clear-region" class="btn" type="button">Clear province</button>
            </div>
            <div id="ranking-table" class="rank-table-wrap"></div>
          </div>
          <div class="subpanel">
            <div id="matrix-legend" class="matrix-legend"></div>
            <div id="matrix-table" class="matrix-wrap"></div>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="section-head">
          <div>
            <h2>Method And Sources</h2>
            <p>
              The dashboard uses the new Pilpres-vs-Pileg source table directly and rebuilds the comparison logic in Python so the
              interaction model can go well beyond the original notebook.
            </p>
          </div>
        </div>
        <div id="method-grid" class="method-grid"></div>
        <div id="source-grid" class="source-grid" style="margin-top:14px;"></div>
      </section>
    </main>
  </div>

  <div id="tooltip" class="tooltip" aria-hidden="true"></div>

  <script>
    const payload = __PAYLOAD__;
  </script>
  <script>
    const candidates = payload.candidates;
    const provinceList = payload.provinces;
    const provinceIndex = new Map(provinceList.map(item => [item.regionKey, item]));
    const candidateIndex = new Map(candidates.map(item => [item.key, item]));
    const defaultProvince = payload.mismatchRanking.length ? payload.mismatchRanking[0].regionKey : "";

    const state = {
      candidateKey: "anies",
      provinceKey: defaultProvince,
      query: "",
      sortMode: "total",
    };

    const elements = {
      heroMeta: document.getElementById("hero-meta"),
      candidateControls: document.getElementById("candidate-controls"),
      candidateNote: document.getElementById("candidate-note"),
      provinceSearch: document.getElementById("province-search"),
      summaryCards: document.getElementById("summary-cards"),
      scatterChart: document.getElementById("scatter-chart"),
      provinceDetail: document.getElementById("province-detail"),
      sortTotal: document.getElementById("sort-total"),
      sortCandidate: document.getElementById("sort-candidate"),
      clearRegion: document.getElementById("clear-region"),
      rankingTable: document.getElementById("ranking-table"),
      matrixLegend: document.getElementById("matrix-legend"),
      matrixTable: document.getElementById("matrix-table"),
      methodGrid: document.getElementById("method-grid"),
      sourceGrid: document.getElementById("source-grid"),
      tooltip: document.getElementById("tooltip"),
    };

    function currentCandidate() {
      return candidateIndex.get(state.candidateKey) || candidates[0];
    }

    function currentSummary() {
      return payload.candidateSummaries[state.candidateKey];
    }

    function currentProvince() {
      return provinceIndex.get(state.provinceKey) || null;
    }

    function provinceCandidateRow(province, candidateKey) {
      return province.candidateRows.find(item => item.candidateKey === candidateKey) || null;
    }

    function formatPct(value, digits = 2) {
      if (value === null || value === undefined || Number.isNaN(value)) return "NA";
      return `${Number(value).toFixed(digits)}%`;
    }

    function formatNumber(value) {
      if (value === null || value === undefined || Number.isNaN(value)) return "NA";
      return new Intl.NumberFormat("en-US").format(value);
    }

    function formatDelta(value, digits = 2) {
      if (value === null || value === undefined || Number.isNaN(value)) return "NA";
      const num = Number(value);
      if (num > 0) return `+${num.toFixed(digits)} pp`;
      if (num < 0) return `${num.toFixed(digits)} pp`;
      return `0.00 pp`;
    }

    function deltaClass(value) {
      if (value === null || value === undefined || Number.isNaN(value)) return "delta-zero";
      if (value > 0) return "delta-pos";
      if (value < 0) return "delta-neg";
      return "delta-zero";
    }

    function escapeHtml(value) {
      return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }

    function signedCellColor(value, maxAbs) {
      if (value === null || value === undefined || Number.isNaN(value)) {
        return "rgba(203,213,225,0.52)";
      }
      const ratio = Math.min(Math.abs(value) / Math.max(maxAbs, 1), 1);
      if (value > 0) {
        const lightness = 94 - (ratio * 38);
        return `hsl(218 76% ${lightness}%)`;
      }
      if (value < 0) {
        const lightness = 94 - (ratio * 36);
        return `hsl(28 82% ${lightness}%)`;
      }
      return "rgba(226,232,240,0.72)";
    }

    function filteredProvinces(includeIncomplete = true) {
      const query = state.query.trim().toLowerCase();
      let rows = provinceList.filter(item => includeIncomplete || item.complete);
      if (!query) return rows;
      return rows.filter(item => item.displayLabel.toLowerCase().includes(query) || item.regionRaw.toLowerCase().includes(query));
    }

    function rankingRows() {
      const rows = filteredProvinces(false);
      return [...rows].sort((a, b) => {
        const candidateA = provinceCandidateRow(a, state.candidateKey);
        const candidateB = provinceCandidateRow(b, state.candidateKey);
        if (state.sortMode === "candidate") {
          return (candidateB.absDifference || 0) - (candidateA.absDifference || 0) || (b.sumAbsDiff || 0) - (a.sumAbsDiff || 0) || a.displayLabel.localeCompare(b.displayLabel);
        }
        return (b.sumAbsDiff || 0) - (a.sumAbsDiff || 0) || (candidateB.absDifference || 0) - (candidateA.absDifference || 0) || a.displayLabel.localeCompare(b.displayLabel);
      });
    }

    function renderControls() {
      elements.candidateControls.innerHTML = candidates.map(candidate => `
        <button class="segment-btn ${candidate.key === state.candidateKey ? "active" : ""}" data-candidate="${escapeHtml(candidate.key)}" type="button">
          ${escapeHtml(candidate.shortLabel)}
        </button>
      `).join("");

      const summary = currentSummary();
      const avg = summary.avgAbsDifference === null ? "NA" : formatPct(summary.avgAbsDifference);
      elements.heroMeta.textContent = `${payload.meta.comparableProvinceCount} comparable provinces. ${payload.meta.incompleteProvinceCount} province has incomplete coalition data. ${currentCandidate().shortLabel} has an average absolute gap of ${avg}.`;
      elements.candidateNote.textContent = `${currentCandidate().shortLabel} coalition parties: ${currentCandidate().coalitionParties.join(", ")}. Positive differences mean the ticket outran the coalition.`;
    }

    function renderSummaryCards() {
      const summary = currentSummary();
      const closest = provinceIndex.get(summary.closestProvinceKey);
      const candidateLead = provinceIndex.get(summary.largestCandidateLeadKey);
      const coalitionLead = provinceIndex.get(summary.largestCoalitionLeadKey);
      const candidateLeadRow = candidateLead ? provinceCandidateRow(candidateLead, state.candidateKey) : null;
      const coalitionLeadRow = coalitionLead ? provinceCandidateRow(coalitionLead, state.candidateKey) : null;

      const cards = [
        {
          label: "Average Absolute Gap",
          value: summary.avgAbsDifference === null ? "NA" : formatPct(summary.avgAbsDifference),
          note: "Mean absolute distance from the 1:1 diagonal across comparable provinces.",
        },
        {
          label: "Closest Alignment",
          value: closest ? escapeHtml(closest.displayLabel) : "NA",
          note: closest ? `${formatDelta(provinceCandidateRow(closest, state.candidateKey).difference)} for ${currentCandidate().shortLabel}.` : "No comparable province available.",
        },
        {
          label: "Biggest Ticket Lead",
          value: candidateLead ? escapeHtml(candidateLead.displayLabel) : "NA",
          note: candidateLeadRow ? `${formatDelta(candidateLeadRow.difference)} where the ticket ran ahead of the coalition.` : "No province where the ticket leads.",
        },
        {
          label: "Biggest Coalition Lead",
          value: coalitionLead ? escapeHtml(coalitionLead.displayLabel) : "NA",
          note: coalitionLeadRow ? `${formatDelta(coalitionLeadRow.difference)} where the coalition outran the ticket.` : "No province where the coalition leads.",
        },
      ];

      elements.summaryCards.innerHTML = cards.map(card => `
        <article class="summary-card">
          <div class="label">${card.label}</div>
          <div class="value">${card.value}</div>
          <div class="note">${card.note}</div>
        </article>
      `).join("");
    }

    function renderScatter() {
      const candidate = currentCandidate();
      const rows = filteredProvinces(false).map(province => {
        const row = provinceCandidateRow(province, state.candidateKey);
        return { province, row };
      }).filter(item => item.row && item.row.pilpresPct !== null && item.row.coalitionPct !== null);

      const width = 860;
      const height = 460;
      const margin = { top: 24, right: 24, bottom: 54, left: 58 };
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;
      const maxPct = 100;
      const x = value => margin.left + (value / maxPct) * innerWidth;
      const y = value => margin.top + innerHeight - (value / maxPct) * innerHeight;
      const voteValues = rows.map(item => item.row.coalitionVotes || 0);
      const minVotes = Math.min(...voteValues, 0);
      const maxVotes = Math.max(...voteValues, 1);
      const radius = value => {
        if (value === null || value === undefined) return 5;
        if (maxVotes === minVotes) return 7;
        const t = (value - minVotes) / (maxVotes - minVotes);
        return 4 + (Math.sqrt(Math.max(t, 0)) * 10);
      };
      const diffAbsMax = Math.max(...rows.map(item => Math.abs(item.row.difference || 0)), 1);

      elements.scatterChart.innerHTML = `
        <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(candidate.label)} alignment scatter">
          <rect x="0" y="0" width="${width}" height="${height}" fill="transparent"></rect>
          ${[0, 25, 50, 75, 100].map(tick => `
            <g>
              <line x1="${margin.left}" y1="${y(tick)}" x2="${width - margin.right}" y2="${y(tick)}" stroke="rgba(23,34,44,0.08)"></line>
              <line x1="${x(tick)}" y1="${margin.top}" x2="${x(tick)}" y2="${height - margin.bottom}" stroke="rgba(23,34,44,0.05)"></line>
              <text x="${margin.left - 10}" y="${y(tick) + 4}" text-anchor="end" font-size="12" fill="#5d6974">${tick}%</text>
              <text x="${x(tick)}" y="${height - margin.bottom + 22}" text-anchor="middle" font-size="12" fill="#5d6974">${tick}%</text>
            </g>
          `).join("")}
          <line x1="${x(0)}" y1="${y(0)}" x2="${x(100)}" y2="${y(100)}" stroke="rgba(23,34,44,0.46)" stroke-width="1.6" stroke-dasharray="7 7"></line>
          <text x="${margin.left}" y="14" font-size="12" fill="#5d6974">Coalition Pileg %</text>
          <text x="${width - margin.right}" y="${height - 12}" text-anchor="end" font-size="12" fill="#5d6974">Pilpres %</text>
          ${rows.map(item => {
            const active = item.province.regionKey === state.provinceKey;
            const fill = signedCellColor(item.row.difference, diffAbsMax);
            const stroke = active ? "#111827" : candidate.color;
            const opacity = state.provinceKey && !active ? 0.44 : 0.92;
            return `
              <circle
                cx="${x(item.row.pilpresPct).toFixed(1)}"
                cy="${y(item.row.coalitionPct).toFixed(1)}"
                r="${radius(item.row.coalitionVotes).toFixed(1)}"
                fill="${fill}"
                stroke="${stroke}"
                stroke-width="${active ? 2.5 : 1.4}"
                data-region="${escapeHtml(item.province.regionKey)}"
                style="cursor:pointer;opacity:${opacity};"
              >
                <title>${escapeHtml(item.province.displayLabel)} | Pilpres ${formatPct(item.row.pilpresPct)} | Coalition ${formatPct(item.row.coalitionPct)} | Gap ${formatDelta(item.row.difference)}</title>
              </circle>
            `;
          }).join("")}
        </svg>
      `;
    }

    function renderProvinceDetail() {
      const province = currentProvince();
      if (!province) {
        elements.provinceDetail.innerHTML = `
          <div class="detail-header">
            <h3>Pick a Province</h3>
            <p>Click a point in the scatter or a row in the ranking table to inspect one province across all three tickets.</p>
          </div>
        `;
        return;
      }

      const heading = province.complete
        ? `${escapeHtml(province.displayLabel)} shows a combined mismatch of ${formatPct(province.sumAbsDiff)} across the three tickets.`
        : `${escapeHtml(province.displayLabel)} has incomplete coalition values in the source CSV, so only the available fields are shown.`;

      elements.provinceDetail.innerHTML = `
        <div class="detail-header">
          <h3>${escapeHtml(province.displayLabel)}</h3>
          <p>${heading}</p>
        </div>
        <div class="detail-metrics">
          <div class="metric">
            <div class="label">Total Coalition Votes</div>
            <div class="value">${formatNumber(province.totalVotes)}</div>
          </div>
          <div class="metric">
            <div class="label">Independent Share</div>
            <div class="value">${formatPct(province.independentPct)}</div>
          </div>
          <div class="metric">
            <div class="label">Province Status</div>
            <div class="value">${province.complete ? "Comparable" : "Incomplete"}</div>
          </div>
        </div>
        <div class="candidate-detail-grid">
          ${province.candidateRows.map(row => `
            <article class="candidate-detail-card">
              <div class="candidate-pill">
                <span class="candidate-swatch" style="background:${row.color};"></span>
                ${escapeHtml(row.candidateShortLabel)}
              </div>
              <div class="small-note" style="margin-top:8px;">Coalition parties: ${escapeHtml(candidateIndex.get(row.candidateKey).coalitionParties.join(", "))}</div>
              <div class="bar-stack">
                <div class="bar-row">
                  <div class="bar-label">
                    <span>Pilpres vote share</span>
                    <strong>${formatPct(row.pilpresPct)}</strong>
                  </div>
                  <div class="bar-track">
                    <div class="bar-fill" style="width:${row.pilpresPct === null ? 0 : row.pilpresPct}%; background:${row.color};"></div>
                  </div>
                </div>
                <div class="bar-row">
                  <div class="bar-label">
                    <span>Coalition pileg share</span>
                    <strong>${formatPct(row.coalitionPct)}</strong>
                  </div>
                  <div class="bar-track">
                    <div class="bar-fill" style="width:${row.coalitionPct === null ? 0 : row.coalitionPct}%; background:rgba(23,34,44,0.30);"></div>
                  </div>
                </div>
              </div>
              <p class="small-note" style="margin-top:10px;">
                Gap: <span class="${deltaClass(row.difference)}">${formatDelta(row.difference)}</span>.
                Coalition votes in source table: <strong>${formatNumber(row.coalitionVotes)}</strong>.
              </p>
            </article>
          `).join("")}
        </div>
      `;
    }

    function renderRankingTable() {
      const rows = rankingRows();
      elements.rankingTable.innerHTML = `
        <table>
          <thead>
            <tr>
              <th>Province</th>
              <th>Total Mismatch</th>
              <th>${escapeHtml(currentCandidate().shortLabel)} Gap</th>
              <th>Coalition Votes</th>
            </tr>
          </thead>
          <tbody>
            ${rows.map(province => {
              const row = provinceCandidateRow(province, state.candidateKey);
              return `
                <tr data-region="${escapeHtml(province.regionKey)}" class="${province.regionKey === state.provinceKey ? "active" : ""}">
                  <td>${escapeHtml(province.displayLabel)}</td>
                  <td>${formatPct(province.sumAbsDiff)}</td>
                  <td class="${deltaClass(row.difference)}">${formatDelta(row.difference)}</td>
                  <td>${formatNumber(row.coalitionVotes)}</td>
                </tr>
              `;
            }).join("")}
            ${filteredProvinces(true).filter(item => !item.complete).map(province => `
              <tr data-region="${escapeHtml(province.regionKey)}" class="${province.regionKey === state.provinceKey ? "active" : ""}">
                <td>${escapeHtml(province.displayLabel)}</td>
                <td>NA</td>
                <td class="delta-zero">Incomplete</td>
                <td>${formatNumber(province.totalVotes)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;
    }

    function renderMatrixLegend() {
      const allDiffs = provinceList.flatMap(province => province.candidateRows.map(row => row.difference).filter(value => value !== null));
      const maxAbs = Math.max(...allDiffs.map(value => Math.abs(value)), 1);
      elements.matrixLegend.innerHTML = `
        <span class="legend-chip"><span class="legend-swatch" style="background:${signedCellColor(maxAbs, maxAbs)};"></span>Ticket leads coalition</span>
        <span class="legend-chip"><span class="legend-swatch" style="background:${signedCellColor(0, maxAbs)};"></span>Near parity</span>
        <span class="legend-chip"><span class="legend-swatch" style="background:${signedCellColor(-maxAbs, maxAbs)};"></span>Coalition leads ticket</span>
      `;
    }

    function renderMatrixTable() {
      const rows = filteredProvinces(true);
      const allDiffs = rows.flatMap(province => province.candidateRows.map(row => row.difference).filter(value => value !== null));
      const maxAbs = Math.max(...allDiffs.map(value => Math.abs(value)), 1);
      const sortedRows = [...rows].sort((a, b) => {
        if (a.complete !== b.complete) return a.complete ? -1 : 1;
        if (state.sortMode === "candidate") {
          return (provinceCandidateRow(b, state.candidateKey).absDifference || 0) - (provinceCandidateRow(a, state.candidateKey).absDifference || 0) || a.displayLabel.localeCompare(b.displayLabel);
        }
        return (b.sumAbsDiff || -1) - (a.sumAbsDiff || -1) || a.displayLabel.localeCompare(b.displayLabel);
      });

      elements.matrixTable.innerHTML = `
        <table>
          <thead>
            <tr>
              <th>Province</th>
              ${candidates.map(candidate => `<th>${escapeHtml(candidate.shortLabel)}</th>`).join("")}
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            ${sortedRows.map(province => `
              <tr data-region="${escapeHtml(province.regionKey)}" class="${province.regionKey === state.provinceKey ? "active" : ""}">
                <td>${escapeHtml(province.displayLabel)}</td>
                ${province.candidateRows.map(row => `
                  <td style="background:${signedCellColor(row.difference, maxAbs)};">
                    <span class="${deltaClass(row.difference)}">${formatDelta(row.difference)}</span>
                  </td>
                `).join("")}
                <td>${formatPct(province.sumAbsDiff)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;
    }

    function renderMethodAndSources() {
      elements.methodGrid.innerHTML = payload.meta.methodology.map(item => `
        <article class="method-card">
          <h3>${escapeHtml(item.title)}</h3>
          <p>${escapeHtml(item.body)}</p>
        </article>
      `).join("");
      elements.sourceGrid.innerHTML = payload.meta.sources.map(item => `
        <article class="source-card">
          <h3>${escapeHtml(item.label)}</h3>
          <p>${escapeHtml(item.note || item.kind)}</p>
          <p class="small-note">Updated: ${escapeHtml(item.updatedAt)}</p>
          <code>${escapeHtml(item.path)}</code>
        </article>
      `).join("");
    }

    function renderAll() {
      renderControls();
      renderSummaryCards();
      renderScatter();
      renderProvinceDetail();
      renderRankingTable();
      renderMatrixLegend();
      renderMatrixTable();
      renderMethodAndSources();
    }

    elements.candidateControls.addEventListener("click", event => {
      const button = event.target.closest("[data-candidate]");
      if (!button) return;
      state.candidateKey = button.dataset.candidate;
      renderAll();
    });

    elements.provinceSearch.addEventListener("input", () => {
      state.query = elements.provinceSearch.value;
      renderScatter();
      renderRankingTable();
      renderMatrixTable();
    });

    elements.sortTotal.addEventListener("click", () => {
      state.sortMode = "total";
      renderRankingTable();
      renderMatrixTable();
    });

    elements.sortCandidate.addEventListener("click", () => {
      state.sortMode = "candidate";
      renderRankingTable();
      renderMatrixTable();
    });

    elements.clearRegion.addEventListener("click", () => {
      state.provinceKey = "";
      renderScatter();
      renderProvinceDetail();
      renderRankingTable();
      renderMatrixTable();
    });

    function bindRegionClick(container) {
      container.addEventListener("click", event => {
        const target = event.target.closest("[data-region]");
        if (!target) return;
        state.provinceKey = target.dataset.region;
        renderScatter();
        renderProvinceDetail();
        renderRankingTable();
        renderMatrixTable();
      });
    }

    bindRegionClick(elements.scatterChart);
    bindRegionClick(elements.rankingTable);
    bindRegionClick(elements.matrixTable);

    renderAll();
  </script>
</body>
</html>
"""
    return template.replace("__PAYLOAD__", safe_json(payload))


d