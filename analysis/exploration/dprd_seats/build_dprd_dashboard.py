#!/usr/bin/env python3
"""Build a local interactive DPRD province-seat dashboard."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ROOT = BASE_DIR.parents[2]
PYTHON_DIR = ROOT / "analysis" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from common import ensure_dir, parse_float, parse_int, read_csv
from dapil_map import DAPIL_GEOJSON_PATH, DAPIL_LOOKUP_PATH, _bounds_for_features, _geometry_to_path


OUTPUT_DIR = ensure_dir(BASE_DIR / "dashboard")
EDA_DIR = BASE_DIR / "eda_outputs"

PARTY_COLORS = {
    "PKB": "#0f766e",
    "Gerindra": "#b45309",
    "PDIP": "#b91c1c",
    "Golkar": "#ca8a04",
    "NasDem": "#1d4ed8",
    "Buruh": "#c2410c",
    "Gelora": "#0891b2",
    "PKS": "#ea580c",
    "PKN": "#6d28d9",
    "Hanura": "#ef4444",
    "Garuda": "#475569",
    "PAN": "#2563eb",
    "PBB": "#15803d",
    "Demokrat": "#1e40af",
    "PSI": "#e11d48",
    "Perindo": "#0f766e",
    "PPP": "#166534",
    "Ummat": "#111827",
    "PA": "#64748b",
    "PASA": "#7c3aed",
    "PDA": "#0f172a",
    "PNA": "#0369a1",
}

GADM_PROVINCE_ALIASES = {
    "BangkaBelitung": "Kepulauan Bangka Belitung",
    "JakartaRaya": "DKI Jakarta",
    "JawaBarat": "Jawa Barat",
    "JawaTengah": "Jawa Tengah",
    "JawaTimur": "Jawa Timur",
    "KalimantanBarat": "Kalimantan Barat",
    "KalimantanSelatan": "Kalimantan Selatan",
    "KalimantanTengah": "Kalimantan Tengah",
    "KalimantanTimur": "Kalimantan Timur",
    "KalimantanUtara": "Kalimantan Utara",
    "KepulauanRiau": "Kepulauan Riau",
    "MalukuUtara": "Maluku Utara",
    "NusaTenggaraBarat": "Nusa Tenggara Barat",
    "NusaTenggaraTimur": "Nusa Tenggara Timur",
    "PapuaBarat": "Papua Barat",
    "SulawesiBarat": "Sulawesi Barat",
    "SulawesiSelatan": "Sulawesi Selatan",
    "SulawesiTengah": "Sulawesi Tengah",
    "SulawesiTenggara": "Sulawesi Tenggara",
    "SulawesiUtara": "Sulawesi Utara",
    "SumateraBarat": "Sumatera Barat",
    "SumateraSelatan": "Sumatera Selatan",
    "SumateraUtara": "Sumatera Utara",
    "North Sumatra": "Sumatera Utara",
    "West Sumatra": "Sumatera Barat",
    "Riau Islands": "Kepulauan Riau",
    "South Sumatra": "Sumatera Selatan",
    "Bangka Belitung": "Kepulauan Bangka Belitung",
    "Jakarta": "DKI Jakarta",
    "West Java": "Jawa Barat",
    "Central Java": "Jawa Tengah",
    "Yogyakarta": "Daerah Istimewa Yogyakarta",
    "East Java": "Jawa Timur",
    "West Nusa Tenggara": "Nusa Tenggara Barat",
    "East Nusa Tenggara": "Nusa Tenggara Timur",
    "West Kalimantan": "Kalimantan Barat",
    "Central Kalimantan": "Kalimantan Tengah",
    "South Kalimantan": "Kalimantan Selatan",
    "East Kalimantan": "Kalimantan Timur",
    "North Kalimantan": "Kalimantan Utara",
    "North Sulawesi": "Sulawesi Utara",
    "Central Sulawesi": "Sulawesi Tengah",
    "South Sulawesi": "Sulawesi Selatan",
    "West Sulawesi": "Sulawesi Barat",
    "Southeast Sulawesi": "Sulawesi Tenggara",
    "North Maluku": "Maluku Utara",
    "West Papua": "Papua Barat",
    "South Papua": "Papua Selatan",
    "Central Papua": "Papua Tengah",
    "Highland Papua": "Papua Pegunungan",
    "Southwest Papua": "Papua Barat Daya",
}

COALITION_ORDER = ["Anies", "Prabowo", "Ganjar"]


def to_float(value: str) -> float | None:
    return parse_float(value)


def row_float(row: dict[str, str], key: str) -> float | None:
    return to_float(row.get(key, ""))


def safe_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def canonical_province(value: str) -> str:
    return GADM_PROVINCE_ALIASES.get(value, value)


def build_province_map_payload(provinces_with_data: set[str], width: float = 960.0, padding: float = 20.0) -> dict:
    gid_to_split_province = {
        row["GID_2"]: row["DAPIL"]
        for row in read_csv(DAPIL_LOOKUP_PATH)
        if row.get("DAPIL") in provinces_with_data
    }

    def feature_province(feature: dict) -> str:
        gid = feature.get("properties", {}).get("GID_2", "")
        if gid in gid_to_split_province:
            return gid_to_split_province[gid]
        return canonical_province(feature.get("properties", {}).get("NAME_1", ""))

    geojson = json.loads(DAPIL_GEOJSON_PATH.read_text(encoding="utf-8"))
    features = [
        feature
        for feature in geojson.get("features", [])
        if feature.get("properties", {}).get("TYPE_2") != "WaterBody"
    ]
    mapped_provinces = {feature_province(feature) for feature in features}
    missing_provinces = sorted(provinces_with_data - mapped_provinces)
    if missing_provinces:
        raise ValueError(f"Province map is missing geometry for: {', '.join(missing_provinces)}")
    min_lon, min_lat, max_lon, max_lat = _bounds_for_features(features)
    lon_span = max(max_lon - min_lon, 1e-6)
    lat_span = max(max_lat - min_lat, 1e-6)
    usable_width = max(width - (padding * 2.0), 1.0)
    scale = usable_width / lon_span
    height = (lat_span * scale) + (padding * 2.0)

    def project(lon: float, lat: float) -> tuple[float, float]:
        return (padding + ((lon - min_lon) * scale), padding + ((max_lat - lat) * scale))

    province_entries: dict[str, dict[str, object]] = {}
    for feature in features:
        province = feature_province(feature)
        if province not in provinces_with_data:
            continue
        path = _geometry_to_path(feature.get("geometry", {}), project)
        if not path:
            continue
        entry = province_entries.setdefault(province, {"province": province, "paths": []})
        entry["paths"].append(path)

    return {
        "viewBox": f"0 0 {width:.1f} {height:.1f}",
        "provinces": sorted(province_entries.values(), key=lambda item: item["province"]),
    }


def make_payload() -> dict:
    party_summary = []
    for row in read_csv(EDA_DIR / "party_summary.csv"):
        party_summary.append(
            {
                "partyCode": row["party_code"],
                "partyName": row["party_name"],
                "partyScope": row["party_scope"],
                "comparableToDpr": row["comparable_to_dpr"] == "true",
                "dprdSeats": parse_int(row["dprd_provincial_seats"]),
                "dprdShare": row_float(row, "dprd_provincial_seat_share"),
                "dprSeats": parse_int(row["dpr_estimated_seats"]),
                "dprShare": row_float(row, "dpr_estimated_seat_share"),
                "seatShareGap": row_float(row, "dprd_minus_dpr_seat_share"),
                "dprVoteShare": row_float(row, "dpr_national_vote_share"),
                "color": PARTY_COLORS.get(row["party_code"], "#334155"),
            }
        )

    province_party_rows = []
    province_totals: Counter[str] = Counter()
    province_party_counts: Counter[str] = Counter()
    for row in read_csv(EDA_DIR / "province_party_summary.csv"):
        seats = parse_int(row["dprd_provincial_seats"])
        province_totals[row["province"]] += seats
        if seats > 0:
            province_party_counts[row["province"]] += 1
        province_party_rows.append(
            {
                "province": row["province"],
                "partyCode": row["party_code"],
                "partyName": row["party_name"],
                "partyScope": row["party_scope"],
                "comparableToDpr": row["comparable_to_dpr"] == "true",
                "dprdSeats": seats,
                "dprdShare": row_float(row, "dprd_provincial_seat_share"),
                "dprSeats": parse_int(row["dpr_estimated_seats"]),
                "dprShare": row_float(row, "dpr_estimated_seat_share"),
                "dprVotes": parse_int(row["dpr_total_votes"]),
                "dprVoteShare": row_float(row, "dpr_vote_share"),
                "dprdMinusDprVoteShare": row_float(row, "dprd_minus_dpr_vote_share"),
                "dprdMinusDprSeatShare": row_float(row, "dprd_minus_dpr_seat_share"),
                "color": PARTY_COLORS.get(row["party_code"], "#334155"),
            }
        )

    leader_by_province = {}
    province_leaders = []
    for row in read_csv(EDA_DIR / "province_leaders.csv"):
        entry = {
            "province": row["province"],
            "leaderCode": row["leading_party_code"],
            "leaderName": row["leading_party_name"],
            "leaderSeats": parse_int(row["leading_party_seats"]),
            "leaderShare": row_float(row, "leading_party_seat_share"),
            "runnerUpCode": row["runner_up_party_code"],
            "runnerUpName": row["runner_up_party_name"],
            "runnerUpSeats": parse_int(row["runner_up_party_seats"]),
            "seatMargin": parse_int(row["seat_margin"]),
            "color": PARTY_COLORS.get(row["leading_party_code"], "#334155"),
        }
        leader_by_province[row["province"]] = entry
        province_leaders.append(entry)

    coalition_rows = []
    coalition_by_province: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for row in read_csv(EDA_DIR / "dprd_vs_pilpres.csv"):
        entry = {
            "province": row["province"],
            "candidate": row["candidate"],
            "coalitionParties": row["coalition_parties"].split("|") if row["coalition_parties"] else [],
            "dprdSeats": parse_int(row["dprd_provincial_seats"]),
            "dprdShare": row_float(row, "dprd_provincial_seat_share"),
            "dprSeats": parse_int(row["dpr_estimated_seats"]),
            "dprShare": row_float(row, "dpr_estimated_seat_share"),
            "pilpresShare": row_float(row, "pilpres_vote_share"),
            "pilpresMinusDprdShare": row_float(row, "pilpres_minus_dprd_seat_share"),
        }
        coalition_rows.append(entry)
        coalition_by_province[row["province"]].append(entry)

    provinces = []
    for province in sorted(province_totals):
        leader = leader_by_province.get(province)
        coalitions = sorted(coalition_by_province[province], key=lambda row: COALITION_ORDER.index(str(row["candidate"])))
        provinces.append(
            {
                "province": province,
                "totalSeats": province_totals[province],
                "partiesWithSeats": province_party_counts[province],
                "leader": leader,
                "coalitions": coalitions,
            }
        )

    summary = json.loads((EDA_DIR / "summary.json").read_text(encoding="utf-8"))
    sources = [
        {
            "label": "DPRD provincial seats",
            "path": (BASE_DIR / "dprd_provincial_seats.csv").relative_to(ROOT).as_posix(),
            "rows": len(read_csv(BASE_DIR / "dprd_provincial_seats.csv")),
        },
        {
            "label": "DPRD EDA party summary",
            "path": (EDA_DIR / "party_summary.csv").relative_to(ROOT).as_posix(),
            "rows": len(party_summary),
        },
        {
            "label": "DPRD vs Pilpres summary",
            "path": (EDA_DIR / "dprd_vs_pilpres.csv").relative_to(ROOT).as_posix(),
            "rows": len(coalition_rows),
        },
    ]

    return {
        "summary": summary,
        "partySummary": party_summary,
        "provincePartyRows": province_party_rows,
        "provinceLeaders": province_leaders,
        "coalitionRows": coalition_rows,
        "provinces": provinces,
        "provinceMap": build_province_map_payload(set(province_totals)),
        "meta": {
            "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
            "sources": sources,
            "notes": [
                "This is a local exploratory DPRD dashboard, not part of the public Render site.",
                "Aceh-local parties are included in DPRD totals and leadership, but excluded from DPR comparison gaps.",
                "DPR seats are model estimates from the existing threshold-adjusted DPR workflow.",
                "Pilpres comparison uses fixed coalition party groupings from the existing Pilpres-vs-Pileg workflow.",
            ],
        },
    }


def build_html(payload: dict) -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>DPRD Provincial Seats Dashboard</title>
  <style>
    :root {
      --paper: #f7f8fa;
      --panel: #ffffff;
      --ink: #1c2733;
      --muted: #5f6b76;
      --line: rgba(28,39,51,.13);
      --accent: #0f766e;
      --accent-soft: #e8f6f1;
      --danger: #b91c1c;
      --good: #15803d;
      --shadow: 0 16px 34px rgba(28,39,51,.08);
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: Inter, "Avenir Next", "Segoe UI", Arial, sans-serif;
      line-height: 1.5;
    }
    .app { max-width: 1440px; margin: 0 auto; padding: 18px 18px 48px; }
    .site-nav {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 8px 0 16px;
      border-bottom: 1px solid var(--line);
    }
    .site-brand { color: var(--ink); font-weight: 900; text-decoration: none; }
    .site-links { display: flex; flex-wrap: wrap; gap: 12px; }
    .site-links a { color: var(--muted); font-weight: 800; text-decoration: none; }
    .site-links a.active { color: var(--accent); }
    .glossary-strip {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 16px 0;
    }
    .glossary-chip {
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--panel);
      color: var(--muted);
      padding: 7px 10px;
      font-size: .82rem;
    }
    .hero {
      display: grid;
      grid-template-columns: minmax(0,1.15fr) minmax(320px,.85fr);
      gap: 18px;
      padding: 26px 0 24px;
    }
    h1, h2, h3 { margin: 0; letter-spacing: 0; }
    h1 { max-width: 12ch; font-size: clamp(2.5rem,7vw,5.4rem); line-height: .94; }
    h2 { font-size: 1.12rem; }
    h3 { font-size: .98rem; }
    p { color: var(--muted); }
    .hero p { max-width: 72ch; font-size: 1.03rem; }
    .eyebrow { color: var(--accent); font-weight: 900; font-size: .82rem; text-transform: uppercase; }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }
    .pad { padding: 16px; }
    .hero-card { align-self: end; }
    .metric-grid {
      display: grid;
      grid-template-columns: repeat(2,minmax(0,1fr));
      gap: 10px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: #fbfcfd;
    }
    .metric-title { color: var(--muted); font-size: .76rem; font-weight: 900; text-transform: uppercase; }
    .metric-value { margin-top: 6px; font-size: 1.55rem; font-weight: 900; }
    .metric-note { color: var(--muted); font-size: .83rem; }
    .layout {
      display: grid;
      grid-template-columns: 320px minmax(0,1fr);
      gap: 18px;
      align-items: start;
    }
    .sidebar { position: sticky; top: 12px; display: grid; gap: 14px; }
    .content { display: grid; gap: 18px; min-width: 0; }
    label { display: grid; gap: 6px; color: var(--muted); font-size: .76rem; font-weight: 900; text-transform: uppercase; }
    select, input {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: white;
      color: var(--ink);
      padding: 10px 11px;
      font: inherit;
    }
    .control-grid { display: grid; gap: 12px; }
    .tag-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
    .tag { display: inline-flex; align-items: center; gap: 6px; border: 1px solid var(--line); border-radius: 999px; padding: 6px 9px; color: var(--muted); font-size: .82rem; background: white; }
    .section-head { display: flex; justify-content: space-between; gap: 16px; align-items: start; margin-bottom: 12px; }
    .map-shell { display: grid; gap: 10px; }
    .map-stage { min-height: 520px; border: 1px solid var(--line); border-radius: 8px; background: #eef2f6; overflow: hidden; }
    #provinceMap { width: 100%; height: 100%; min-height: 520px; display: block; }
    .province-shape { stroke: #fff; stroke-width: .7; cursor: pointer; opacity: .88; transition: opacity .15s, stroke-width .15s; }
    .province-group:hover .province-shape, .province-group.selected .province-shape { opacity: 1; stroke: #111827; stroke-width: 1.6; }
    .province-group.dimmed .province-shape { opacity: .24; }
    .legend { display: flex; flex-wrap: wrap; gap: 8px; color: var(--muted); font-size: .82rem; }
    .swatch { width: 12px; height: 12px; border-radius: 3px; display: inline-block; }
    .split { display: grid; grid-template-columns: minmax(0,1fr) minmax(0,1fr); gap: 14px; }
    .bar-list { display: grid; gap: 8px; }
    .bar-row { display: grid; grid-template-columns: 92px minmax(0,1fr) 62px; gap: 10px; align-items: center; font-size: .9rem; }
    .bar-track { height: 12px; border-radius: 999px; background: #e6ebf1; overflow: hidden; }
    .bar-fill { height: 100%; border-radius: inherit; }
    table { width: 100%; border-collapse: collapse; font-size: .88rem; white-space: nowrap; }
    th, td { padding: 8px 9px; border-bottom: 1px solid var(--line); text-align: left; }
    th { color: var(--muted); font-size: .72rem; text-transform: uppercase; }
    .table-wrap { overflow: auto; }
    .notice { background: var(--accent-soft); border-left: 4px solid var(--accent); border-radius: 6px; padding: 12px 14px; color: var(--ink); }
    .small-note { color: var(--muted); font-size: .9rem; }
    .button-row { display: flex; gap: 8px; flex-wrap: wrap; }
    button {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: white;
      color: var(--ink);
      padding: 9px 11px;
      font: inherit;
      font-weight: 800;
      cursor: pointer;
    }
    button.primary { background: var(--accent); color: white; border-color: var(--accent); }
    @media (max-width: 980px) {
      .hero, .layout, .split { grid-template-columns: 1fr; }
      .sidebar { position: static; }
      .metric-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="app">
    <header class="site-nav">
      <a class="site-brand" href="../../../../README.md">Pileg Reports</a>
      <nav class="site-links" aria-label="Exploration navigation">
        <a class="active" href="#">DPRD Province</a>
        <a href="../eda_outputs/index.html">EDA Output</a>
        <a href="../README.md">DPRD Notes</a>
      </nav>
    </header>

    <section class="glossary-strip" aria-label="Election glossary">
      <span class="glossary-chip"><strong>DPRD Provinsi</strong>: provincial legislature</span>
      <span class="glossary-chip"><strong>DPR</strong>: national legislature</span>
      <span class="glossary-chip"><strong>Pilpres</strong>: presidential election</span>
      <span class="glossary-chip"><strong>Aceh local parties</strong>: DPRD-only comparison caveat</span>
    </section>

    <section class="hero">
      <div>
        <div class="eyebrow">Exploratory dashboard</div>
        <h1>DPRD Provincial Seats</h1>
        <p>Inspect party strength across provincial DPRD seats, compare it with estimated DPR outcomes, and test presidential coalition alignment by province.</p>
        <p class="small-note">This dashboard is local exploratory work and is not connected to the public Render site.</p>
      </div>
      <section class="panel pad hero-card">
        <div class="metric-grid" id="heroMetrics"></div>
      </section>
    </section>

    <div class="layout">
      <aside class="sidebar">
        <section class="panel pad">
          <h2>Filters</h2>
          <div class="control-grid">
            <label>Province <select id="provinceSelect"></select></label>
            <label>Party <select id="partySelect"></select></label>
            <label>Coalition <select id="coalitionSelect"></select></label>
            <label>Map Metric <select id="mapMetricSelect">
              <option value="leader">Leading DPRD party</option>
              <option value="coalitionShare">Coalition DPRD seat share</option>
              <option value="coalitionGap">Pilpres minus DPRD coalition share</option>
              <option value="dprGap">Selected party DPRD minus DPR vote share</option>
            </select></label>
          </div>
          <div class="button-row" style="margin-top:12px;">
            <button class="primary" id="resetBtn">Reset</button>
          </div>
          <div class="tag-row" id="activeTags"></div>
        </section>

        <section class="panel pad">
          <h3>Data Notes</h3>
          <div id="dataNotes" class="small-note"></div>
        </section>
      </aside>

      <main class="content">
        <section class="panel pad">
          <div class="section-head">
            <div>
              <h2>Province Map</h2>
              <p class="small-note" id="mapSummary"></p>
            </div>
            <div class="legend" id="mapLegend"></div>
          </div>
          <div class="map-shell">
            <div class="map-stage">
              <svg id="provinceMap" role="img" preserveAspectRatio="xMidYMid meet"></svg>
            </div>
          </div>
        </section>

        <section class="panel pad">
          <div class="section-head">
            <div>
              <h2 id="provinceTitle">Province Summary</h2>
              <p class="small-note" id="provinceSummary"></p>
            </div>
          </div>
          <div class="metric-grid" id="provinceMetrics"></div>
          <div class="split" style="margin-top:14px;">
            <div>
              <h3>Party Seat Distribution</h3>
              <div class="bar-list" id="partyBars"></div>
            </div>
            <div>
              <h3>Coalition Comparison</h3>
              <div class="bar-list" id="coalitionBars"></div>
            </div>
          </div>
        </section>

        <section class="panel pad">
          <div class="section-head">
            <div>
              <h2>Province Party Table</h2>
              <p class="small-note">DPR comparison gaps are blank for Aceh-local parties.</p>
            </div>
          </div>
          <div class="table-wrap" id="provincePartyTable"></div>
        </section>

        <section class="panel pad">
          <h2>National Party Overview</h2>
          <div class="table-wrap" id="nationalPartyTable"></div>
        </section>

        <section class="panel pad">
          <h2>Sources</h2>
          <div class="table-wrap" id="sourceTable"></div>
        </section>
      </main>
    </div>
  </div>

  <script id="dashboardPayload" type="application/json">__PAYLOAD__</script>
  <script>
    const DATA = JSON.parse(document.getElementById("dashboardPayload").textContent);
    const ALL = "All";
    const state = { province: "All", party: "All", coalition: "Anies", mapMetric: "leader" };
    const elements = {
      heroMetrics: document.getElementById("heroMetrics"),
      provinceSelect: document.getElementById("provinceSelect"),
      partySelect: document.getElementById("partySelect"),
      coalitionSelect: document.getElementById("coalitionSelect"),
      mapMetricSelect: document.getElementById("mapMetricSelect"),
      resetBtn: document.getElementById("resetBtn"),
      activeTags: document.getElementById("activeTags"),
      dataNotes: document.getElementById("dataNotes"),
      provinceMap: document.getElementById("provinceMap"),
      mapSummary: document.getElementById("mapSummary"),
      mapLegend: document.getElementById("mapLegend"),
      provinceTitle: document.getElementById("provinceTitle"),
      provinceSummary: document.getElementById("provinceSummary"),
      provinceMetrics: document.getElementById("provinceMetrics"),
      partyBars: document.getElementById("partyBars"),
      coalitionBars: document.getElementById("coalitionBars"),
      provincePartyTable: document.getElementById("provincePartyTable"),
      nationalPartyTable: document.getElementById("nationalPartyTable"),
      sourceTable: document.getElementById("sourceTable"),
    };
    const provinceByName = new Map(DATA.provinces.map(row => [row.province, row]));
    const rowsByProvince = new Map();
    for (const row of DATA.provincePartyRows) {
      if (!rowsByProvince.has(row.province)) rowsByProvince.set(row.province, []);
      rowsByProvince.get(row.province).push(row);
    }
    const coalitionsByProvince = new Map();
    for (const row of DATA.coalitionRows) {
      if (!coalitionsByProvince.has(row.province)) coalitionsByProvince.set(row.province, []);
      coalitionsByProvince.get(row.province).push(row);
    }
    const partyByCode = new Map(DATA.partySummary.map(row => [row.partyCode, row]));

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
    }
    function fmtNumber(value) { return Number(value || 0).toLocaleString("en-US"); }
    function fmtPct(value, signed = false) {
      if (value === null || value === undefined || value === "") return "";
      const pct = Number(value) * 100;
      return `${signed && pct > 0 ? "+" : ""}${pct.toFixed(1)}%`;
    }
    function metric(title, value, note = "") {
      return `<div class="metric"><div class="metric-title">${escapeHtml(title)}</div><div class="metric-value">${escapeHtml(value)}</div><div class="metric-note">${escapeHtml(note)}</div></div>`;
    }
    function table(rows, columns) {
      const head = columns.map(col => `<th>${escapeHtml(col.label)}</th>`).join("");
      const body = rows.map(row => `<tr>${columns.map(col => `<td>${escapeHtml(col.format ? col.format(row[col.key], row) : row[col.key])}</td>`).join("")}</tr>`).join("");
      return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
    }
    function partyColor(code) { return (partyByCode.get(code) || {}).color || "#64748b"; }
    function gapColor(value) {
      if (value === null || value === undefined || value === "") return "#cbd5e1";
      const v = Number(value);
      if (v > 0.08) return "#166534";
      if (v > 0.03) return "#65a30d";
      if (v < -0.08) return "#991b1b";
      if (v < -0.03) return "#dc2626";
      return "#94a3b8";
    }
    function shareColor(value) {
      const v = Number(value || 0);
      if (v >= .6) return "#065f46";
      if (v >= .45) return "#0f766e";
      if (v >= .3) return "#14b8a6";
      if (v >= .15) return "#67e8f9";
      return "#cbd5e1";
    }
    function getSelectedProvinceRows() {
      if (state.province === ALL) return DATA.provincePartyRows;
      return rowsByProvince.get(state.province) || [];
    }
    function getProvinceCoalition(province) {
      return (coalitionsByProvince.get(province) || []).find(row => row.candidate === state.coalition) || null;
    }
    function renderControls() {
      const provinces = [ALL, ...DATA.provinces.map(row => row.province)];
      const parties = [ALL, ...DATA.partySummary.map(row => row.partyCode)];
      const coalitions = [...new Set(DATA.coalitionRows.map(row => row.candidate))];
      elements.provinceSelect.innerHTML = provinces.map(value => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("");
      elements.partySelect.innerHTML = parties.map(value => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("");
      elements.coalitionSelect.innerHTML = coalitions.map(value => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("");
      elements.provinceSelect.value = state.province;
      elements.partySelect.value = state.party;
      elements.coalitionSelect.value = state.coalition;
      elements.mapMetricSelect.value = state.mapMetric;
    }
    function renderHero() {
      elements.heroMetrics.innerHTML = [
        metric("DPRD Seats", fmtNumber(DATA.summary.dprd_total_seats), "Provincial seats"),
        metric("Provinces", fmtNumber(DATA.summary.dprd_provinces), "Joined to Pilpres"),
        metric("Parties With Seats", fmtNumber(DATA.summary.dprd_parties_with_seats), "Includes Aceh local"),
        metric("Aceh Local Parties", fmtNumber(DATA.summary.aceh_local_parties_with_seats), "Excluded from DPR gaps"),
      ].join("");
      elements.dataNotes.innerHTML = DATA.meta.notes.map(note => `<p>${escapeHtml(note)}</p>`).join("");
    }
    function renderTags() {
      elements.activeTags.innerHTML = [
        ["Province", state.province],
        ["Party", state.party],
        ["Coalition", state.coalition],
        ["Map", elements.mapMetricSelect.options[elements.mapMetricSelect.selectedIndex].text],
      ].map(([label, value]) => `<span class="tag"><strong>${escapeHtml(label)}:</strong> ${escapeHtml(value)}</span>`).join("");
    }
    function mapFill(province) {
      const record = provinceByName.get(province);
      if (!record) return "#cbd5e1";
      const leader = record.leader || {};
      const coalition = getProvinceCoalition(province);
      if (state.mapMetric === "leader") return partyColor(leader.leaderCode);
      if (state.mapMetric === "coalitionShare") return shareColor(coalition && coalition.dprdShare);
      if (state.mapMetric === "coalitionGap") return gapColor(coalition && coalition.pilpresMinusDprdShare);
      if (state.mapMetric === "dprGap" && state.party !== ALL) {
        const row = (rowsByProvince.get(province) || []).find(item => item.partyCode === state.party);
        return row ? gapColor(row.dprdMinusDprVoteShare) : "#cbd5e1";
      }
      return "#cbd5e1";
    }
    function mapTooltip(province) {
      const record = provinceByName.get(province);
      const coalition = getProvinceCoalition(province);
      if (!record) return province;
      const leader = record.leader || {};
      const parts = [
        province,
        `Leader: ${leader.leaderCode || ""} (${fmtNumber(leader.leaderSeats)} seats)`,
        `${state.coalition}: ${coalition ? fmtPct(coalition.dprdShare) : ""} DPRD / ${coalition ? fmtPct(coalition.pilpresShare) : ""} Pilpres`,
      ];
      if (state.party !== ALL) {
        const row = (rowsByProvince.get(province) || []).find(item => item.partyCode === state.party);
        if (row) parts.push(`${state.party}: ${fmtPct(row.dprdShare)} DPRD, gap ${fmtPct(row.dprdMinusDprVoteShare, true)}`);
      }
      return parts.join(" | ");
    }
    function renderMap() {
      elements.provinceMap.setAttribute("viewBox", DATA.provinceMap.viewBox);
      elements.provinceMap.innerHTML = DATA.provinceMap.provinces.map(item => {
        const selected = state.province === item.province;
        const dimmed = state.province !== ALL && !selected;
        return `<g class="province-group${selected ? " selected" : ""}${dimmed ? " dimmed" : ""}" data-province="${escapeHtml(item.province)}" tabindex="0" role="button" aria-label="${escapeHtml(mapTooltip(item.province))}">
          <title>${escapeHtml(mapTooltip(item.province))}</title>
          ${item.paths.map(path => `<path class="province-shape" d="${path}" fill="${escapeHtml(mapFill(item.province))}"></path>`).join("")}
        </g>`;
      }).join("");
      elements.provinceMap.querySelectorAll(".province-group").forEach(group => {
        group.addEventListener("click", () => {
          state.province = group.dataset.province;
          elements.provinceSelect.value = state.province;
          render();
        });
        group.addEventListener("keydown", event => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            state.province = group.dataset.province;
            elements.provinceSelect.value = state.province;
            render();
          }
        });
      });
      const metricLabel = elements.mapMetricSelect.options[elements.mapMetricSelect.selectedIndex].text;
      elements.mapSummary.textContent = `${metricLabel}. Click a province to lock the detail panels.`;
      const leaderCounts = new Map();
      for (const record of DATA.provinces) {
        if (record.leader) leaderCounts.set(record.leader.leaderCode, (leaderCounts.get(record.leader.leaderCode) || 0) + 1);
      }
      elements.mapLegend.innerHTML = [...leaderCounts.entries()]
        .sort((a,b) => b[1] - a[1] || a[0].localeCompare(b[0]))
        .slice(0, 8)
        .map(([party, count]) => `<span class="tag"><span class="swatch" style="background:${escapeHtml(partyColor(party))}"></span>${escapeHtml(party)} leads ${fmtNumber(count)}</span>`)
        .join("");
    }
    function renderProvinceSummary() {
      const province = state.province === ALL ? "Indonesia" : state.province;
      elements.provinceTitle.textContent = `${province} Summary`;
      const rows = getSelectedProvinceRows()
        .filter(row => state.party === ALL || row.partyCode === state.party)
        .sort((a,b) => b.dprdSeats - a.dprdSeats || a.partyCode.localeCompare(b.partyCode));
      const totalSeats = state.province === ALL ? DATA.summary.dprd_total_seats : (provinceByName.get(state.province) || {}).totalSeats || 0;
      const leader = state.province === ALL ? DATA.partySummary[0] : (provinceByName.get(state.province) || {}).leader;
      const coalition = state.province === ALL ? null : getProvinceCoalition(state.province);
      const partiesWithSeats = new Set(rows.filter(row => row.dprdSeats > 0).map(row => row.partyCode)).size;
      elements.provinceSummary.textContent = state.province === ALL
        ? "National view across all DPRD provincial seats."
        : `Province-level view for ${state.province}.`;
      elements.provinceMetrics.innerHTML = [
        metric("Seats", fmtNumber(totalSeats), "DPRD provincial"),
        metric("Parties", fmtNumber(partiesWithSeats), "Current filter"),
        metric("Leader", leader ? (leader.leaderCode || leader.partyCode) : "", leader ? `${fmtNumber(leader.leaderSeats || leader.dprdSeats)} seats` : ""),
        metric(`${state.coalition} Gap`, coalition ? fmtPct(coalition.pilpresMinusDprdShare, true) : "—", "Pilpres minus DPRD coalition share"),
      ].join("");
      const topRows = rows.filter(row => row.dprdSeats > 0).slice(0, 14);
      const maxSeats = Math.max(1, ...topRows.map(row => row.dprdSeats));
      elements.partyBars.innerHTML = topRows.map(row => `
        <div class="bar-row">
          <strong>${escapeHtml(row.partyCode)}</strong>
          <div class="bar-track"><div class="bar-fill" style="width:${Math.max(2, row.dprdSeats / maxSeats * 100).toFixed(1)}%; background:${escapeHtml(row.color)}"></div></div>
          <span>${fmtNumber(row.dprdSeats)}</span>
        </div>
      `).join("");
      const coalitionRows = state.province === ALL
        ? DATA.coalitionRows.filter(row => row.province === "Aceh").slice(0, 0)
        : (coalitionsByProvince.get(state.province) || []);
      const maxShare = Math.max(0.01, ...coalitionRows.map(row => Number(row.dprdShare || 0)));
      elements.coalitionBars.innerHTML = coalitionRows.map(row => `
        <div class="bar-row">
          <strong>${escapeHtml(row.candidate)}</strong>
          <div class="bar-track"><div class="bar-fill" style="width:${Math.max(2, Number(row.dprdShare || 0) / maxShare * 100).toFixed(1)}%; background:${row.candidate === "Anies" ? "#2563eb" : row.candidate === "Prabowo" ? "#15803d" : "#dc2626"}"></div></div>
          <span>${fmtPct(row.dprdShare)}</span>
        </div>
      `).join("") || `<p class="small-note">Choose a province to compare coalitions.</p>`;
    }
    function renderTables() {
      const provinceRows = getSelectedProvinceRows()
        .filter(row => state.party === ALL || row.partyCode === state.party)
        .sort((a,b) => b.dprdSeats - a.dprdSeats || a.partyCode.localeCompare(b.partyCode))
        .slice(0, 40);
      elements.provincePartyTable.innerHTML = table(provinceRows, [
        { key: "partyCode", label: "Party" },
        { key: "partyScope", label: "Scope" },
        { key: "dprdSeats", label: "DPRD", format: fmtNumber },
        { key: "dprdShare", label: "DPRD %", format: fmtPct },
        { key: "dprVoteShare", label: "DPR Vote %", format: fmtPct },
        { key: "dprdMinusDprVoteShare", label: "Gap", format: value => fmtPct(value, true) },
      ]);
      elements.nationalPartyTable.innerHTML = table(DATA.partySummary, [
        { key: "partyCode", label: "Party" },
        { key: "partyScope", label: "Scope" },
        { key: "dprdSeats", label: "DPRD", format: fmtNumber },
        { key: "dprdShare", label: "DPRD %" , format: fmtPct },
        { key: "dprSeats", label: "DPR", format: fmtNumber },
        { key: "dprShare", label: "DPR %", format: fmtPct },
        { key: "seatShareGap", label: "Gap", format: value => fmtPct(value, true) },
      ]);
      elements.sourceTable.innerHTML = table(DATA.meta.sources, [
        { key: "label", label: "Source" },
        { key: "path", label: "Path" },
        { key: "rows", label: "Rows", format: fmtNumber },
      ]);
    }
    function render() {
      renderTags();
      renderMap();
      renderProvinceSummary();
      renderTables();
    }
    renderControls();
    renderHero();
    render();
    elements.provinceSelect.addEventListener("change", event => { state.province = event.target.value; render(); });
    elements.partySelect.addEventListener("change", event => { state.party = event.target.value; render(); });
    elements.coalitionSelect.addEventListener("change", event => { state.coalition = event.target.value; render(); });
    elements.mapMetricSelect.addEventListener("change", event => { state.mapMetric = event.target.value; render(); });
    elements.resetBtn.addEventListener("click", () => {
      state.province = ALL;
      state.party = ALL;
      state.coalition = "Anies";
      state.mapMetric = "leader";
      renderControls();
      render();
    });
  </script>
</body>
</html>
""".replace("__PAYLOAD__", safe_json(payload))


def main() -> None:
    payload = make_payload()
    output_path = OUTPUT_DIR / "index.html"
    output_path.write_text(build_html(payload), encoding="utf-8")
    print("Wrote DPRD dashboard to", output_path)


if __name__ == "__main__":
    main()
