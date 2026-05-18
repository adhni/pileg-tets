#!/usr/bin/env python3
"""Exploratory DPRD province-seat analysis."""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter, defaultdict
from html import escape
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ROOT = BASE_DIR.parents[2]
PYTHON_DIR = ROOT / "analysis" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from common import ensure_dir, format_float, parse_float, parse_int, read_csv, write_csv


INPUT_DPRD_PROVINCE = BASE_DIR / "dprd_provincial_seats.csv"
INPUT_DPR_PARTY = ROOT / "analysis" / "python_outputs" / "dpr_estimated_winners" / "estimated_seats_by_party.csv"
INPUT_DPR_DISTRICT_PARTY = ROOT / "analysis" / "python_outputs" / "dpr_estimated_winners" / "estimated_seats_by_district_party.csv"
INPUT_DPR_SLATES = ROOT / "data" / "prepared" / "dpr_party_slates.csv"
INPUT_PILPRES = ROOT / "analysis" / "reference" / "pilpres_vs_pileg" / "election_results.csv"
INPUT_PARTY_LOOKUP = ROOT / "data" / "prepared" / "party_lookup.csv"

OUTPUT_DIR = BASE_DIR / "eda_outputs"
CHART_DIR = OUTPUT_DIR / "charts"

COALITIONS = [
    {
        "candidate": "Anies",
        "candidate_key": "anies",
        "parties": ["PKB", "PKS", "NasDem", "Ummat"],
        "color": "#2563eb",
    },
    {
        "candidate": "Prabowo",
        "candidate_key": "prabowo",
        "parties": ["Gerindra", "Golkar", "PAN", "Demokrat", "PSI", "Gelora", "Garuda"],
        "color": "#15803d",
    },
    {
        "candidate": "Ganjar",
        "candidate_key": "ganjar",
        "parties": ["PDIP", "PPP", "Hanura", "Perindo"],
        "color": "#dc2626",
    },
]

PROVINCE_ALIASES = {
    "Yogyakarta": "Daerah Istimewa Yogyakarta",
}


def pct(value: float) -> float:
    return value * 100


def canonical_province(value: str) -> str:
    return PROVINCE_ALIASES.get(value, value)


def sorted_parties(party_rows: dict[str, dict[str, object]]) -> list[str]:
    return sorted(
        party_rows,
        key=lambda code: (
            -int(party_rows[code].get("dprd_provincial_seats", 0)),
            -int(party_rows[code].get("dpr_estimated_seats", 0)),
            code,
        ),
    )


def make_chart_helpers():
    os.environ.setdefault("MPLCONFIGDIR", str(ensure_dir(OUTPUT_DIR / ".mplconfig")))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#cbd5e1",
            "axes.labelcolor": "#1f2937",
            "xtick.color": "#334155",
            "ytick.color": "#334155",
            "font.size": 10,
        }
    )
    return plt


def build_party_summary(dprd_rows: list[dict[str, str]], dpr_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    party_scope = {row["party_code"]: row["party_scope"] for row in read_csv(INPUT_PARTY_LOOKUP)}
    parties: dict[str, dict[str, object]] = {}
    dprd_total = sum(parse_int(row["provincial_seats"]) for row in dprd_rows)
    dpr_total = sum(parse_int(row["estimated_seats"]) for row in dpr_rows)

    for row in dprd_rows:
        party_code = row["party_code"]
        parties.setdefault(
            party_code,
            {
                "party_code": party_code,
                "party_name": row["party_name"],
                "dprd_provincial_seats": 0,
                "dpr_estimated_seats": 0,
                "dpr_national_vote_share": None,
                "party_scope": party_scope.get(party_code, "unknown"),
            },
        )
        parties[party_code]["dprd_provincial_seats"] = int(parties[party_code]["dprd_provincial_seats"]) + parse_int(
            row["provincial_seats"]
        )

    for row in dpr_rows:
        party_code = row["party_code"]
        parties.setdefault(
            party_code,
            {
                "party_code": party_code,
                "party_name": row["party_name"],
                "dprd_provincial_seats": 0,
                "dpr_estimated_seats": 0,
                "dpr_national_vote_share": None,
                "party_scope": party_scope.get(party_code, "unknown"),
            },
        )
        parties[party_code]["dpr_estimated_seats"] = parse_int(row["estimated_seats"])
        parties[party_code]["dpr_national_vote_share"] = parse_float(row["national_vote_share"])

    summary = []
    for party_code in sorted_parties(parties):
        row = parties[party_code]
        dprd_seats = int(row["dprd_provincial_seats"])
        dpr_seats = int(row["dpr_estimated_seats"])
        dprd_share = dprd_seats / dprd_total if dprd_total else 0
        dpr_share = dpr_seats / dpr_total if dpr_total else 0
        comparable_to_dpr = row["party_scope"] == "national"
        summary.append(
            {
                "party_code": party_code,
                "party_name": row["party_name"],
                "party_scope": row["party_scope"],
                "comparable_to_dpr": "true" if comparable_to_dpr else "false",
                "dprd_provincial_seats": dprd_seats,
                "dprd_provincial_seat_share": format_float(dprd_share),
                "dpr_estimated_seats": dpr_seats,
                "dpr_estimated_seat_share": format_float(dpr_share),
                "dprd_minus_dpr_seat_share": format_float(dprd_share - dpr_share) if comparable_to_dpr else "",
                "dpr_national_vote_share": format_float(row["dpr_national_vote_share"]) if comparable_to_dpr else "",
            }
        )
    return summary


def build_province_party_summary(
    dprd_rows: list[dict[str, str]],
    dpr_district_rows: list[dict[str, str]],
    dpr_slate_rows: list[dict[str, str]],
) -> list[dict[str, object]]:
    party_scope = {row["party_code"]: row["party_scope"] for row in read_csv(INPUT_PARTY_LOOKUP)}
    party_names = {row["party_code"]: row["party_name"] for row in dprd_rows}
    dprd_seats: Counter[tuple[str, str]] = Counter()
    dprd_province_totals: Counter[str] = Counter()
    for row in dprd_rows:
        key = (row["province"], row["party_code"])
        seats = parse_int(row["provincial_seats"])
        dprd_seats[key] += seats
        dprd_province_totals[row["province"]] += seats

    dpr_seats: Counter[tuple[str, str]] = Counter()
    dpr_province_seats: Counter[str] = Counter()
    for row in dpr_district_rows:
        key = (row["province"], row["party_code"])
        seats = parse_int(row["seats_won"])
        dpr_seats[key] += seats
        dpr_province_seats[row["province"]] += seats
        party_names.setdefault(row["party_code"], row["party_name"])

    dpr_votes: Counter[tuple[str, str]] = Counter()
    dpr_province_votes: Counter[str] = Counter()
    for row in dpr_slate_rows:
        key = (row["province"], row["party_code"])
        votes = parse_int(row["total_votes"])
        dpr_votes[key] += votes
        dpr_province_votes[row["province"]] += votes
        party_names.setdefault(row["party_code"], row["party_name"])

    rows = []
    for province, party_code in sorted(set(dprd_seats) | set(dpr_seats) | set(dpr_votes)):
        dprd_value = dprd_seats[(province, party_code)]
        dpr_seat_value = dpr_seats[(province, party_code)]
        dpr_vote_value = dpr_votes[(province, party_code)]
        dprd_share = dprd_value / dprd_province_totals[province] if dprd_province_totals[province] else 0
        dpr_seat_share = dpr_seat_value / dpr_province_seats[province] if dpr_province_seats[province] else 0
        dpr_vote_share = dpr_vote_value / dpr_province_votes[province] if dpr_province_votes[province] else 0
        comparable_to_dpr = party_scope.get(party_code, "unknown") == "national"
        rows.append(
            {
                "province": province,
                "party_code": party_code,
                "party_name": party_names.get(party_code, party_code),
                "party_scope": party_scope.get(party_code, "unknown"),
                "comparable_to_dpr": "true" if comparable_to_dpr else "false",
                "dprd_provincial_seats": dprd_value,
                "dprd_provincial_seat_share": format_float(dprd_share),
                "dpr_estimated_seats": dpr_seat_value,
                "dpr_estimated_seat_share": format_float(dpr_seat_share),
                "dpr_total_votes": dpr_vote_value,
                "dpr_vote_share": format_float(dpr_vote_share),
                "dprd_minus_dpr_vote_share": format_float(dprd_share - dpr_vote_share) if comparable_to_dpr else "",
                "dprd_minus_dpr_seat_share": format_float(dprd_share - dpr_seat_share) if comparable_to_dpr else "",
            }
        )
    rows.sort(key=lambda row: (row["province"], -int(row["dprd_provincial_seats"]), row["party_code"]))
    return rows


def build_province_leaders(province_party_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by_province: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for row in province_party_rows:
        if int(row["dprd_provincial_seats"]) > 0:
            by_province[str(row["province"])].append(row)

    leaders = []
    for province, rows in sorted(by_province.items()):
        ranked = sorted(rows, key=lambda row: (-int(row["dprd_provincial_seats"]), str(row["party_code"])))
        leader = ranked[0]
        runner = ranked[1] if len(ranked) > 1 else None
        leaders.append(
            {
                "province": province,
                "leading_party_code": leader["party_code"],
                "leading_party_name": leader["party_name"],
                "leading_party_seats": leader["dprd_provincial_seats"],
                "leading_party_seat_share": leader["dprd_provincial_seat_share"],
                "runner_up_party_code": runner["party_code"] if runner else "",
                "runner_up_party_name": runner["party_name"] if runner else "",
                "runner_up_party_seats": runner["dprd_provincial_seats"] if runner else 0,
                "seat_margin": int(leader["dprd_provincial_seats"]) - int(runner["dprd_provincial_seats"]) if runner else int(leader["dprd_provincial_seats"]),
            }
        )
    leaders.sort(key=lambda row: (-int(row["seat_margin"]), str(row["province"])))
    return leaders


def build_coalition_outputs(
    province_party_rows: list[dict[str, object]],
    pilpres_rows: list[dict[str, str]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    dprd_totals: Counter[str] = Counter()
    dpr_seat_totals: Counter[str] = Counter()
    by_province_party = {(str(row["province"]), str(row["party_code"])): row for row in province_party_rows}
    for row in province_party_rows:
        dprd_totals[str(row["province"])] += int(row["dprd_provincial_seats"])
        dpr_seat_totals[str(row["province"])] += int(row["dpr_estimated_seats"])

    pilpres_by_province = {canonical_province(row["Region"]): row for row in pilpres_rows}
    coalition_rows = []
    comparison_rows = []
    for province in sorted(dprd_totals):
        pilpres = pilpres_by_province.get(province, {})
        for coalition in COALITIONS:
            candidate = coalition["candidate"]
            dprd_seats = sum(int(by_province_party.get((province, party), {}).get("dprd_provincial_seats", 0)) for party in coalition["parties"])
            dpr_seats = sum(int(by_province_party.get((province, party), {}).get("dpr_estimated_seats", 0)) for party in coalition["parties"])
            dprd_share = dprd_seats / dprd_totals[province] if dprd_totals[province] else 0
            dpr_share = dpr_seats / dpr_seat_totals[province] if dpr_seat_totals[province] else 0
            pilpres_share = parse_float(pilpres.get(f"{candidate}_Pilpres", ""))
            row = {
                "province": province,
                "candidate": candidate,
                "coalition_parties": "|".join(coalition["parties"]),
                "dprd_provincial_seats": dprd_seats,
                "dprd_provincial_seat_share": format_float(dprd_share),
                "dpr_estimated_seats": dpr_seats,
                "dpr_estimated_seat_share": format_float(dpr_share),
                "pilpres_vote_share": format_float(pilpres_share / 100 if pilpres_share is not None else None),
                "pilpres_minus_dprd_seat_share": format_float((pilpres_share / 100 - dprd_share) if pilpres_share is not None else None),
            }
            coalition_rows.append(row)
            comparison_rows.append(row.copy())
    coalition_rows.sort(key=lambda row: (row["province"], row["candidate"]))
    comparison_rows.sort(key=lambda row: (row["candidate"], -abs(float(row["pilpres_minus_dprd_seat_share"] or 0)), row["province"]))
    return coalition_rows, comparison_rows


def top_strength_gaps(province_party_rows: list[dict[str, object]], limit: int = 20) -> list[dict[str, object]]:
    rows = [
        row
        for row in province_party_rows
        if int(row["dprd_provincial_seats"]) > 0
        and row["comparable_to_dpr"] == "true"
        and row["dpr_vote_share"] != ""
    ]
    rows.sort(key=lambda row: (-abs(float(row["dprd_minus_dpr_vote_share"])), str(row["province"]), str(row["party_code"])))
    return rows[:limit]


def write_summary_markdown(
    party_summary: list[dict[str, object]],
    province_leaders: list[dict[str, object]],
    dprd_vs_pilpres: list[dict[str, object]],
    strength_gaps: list[dict[str, object]],
    summary: dict[str, object],
) -> None:
    top_parties = party_summary[:8]
    top_leaders = province_leaders[:8]
    top_coalition_gaps = dprd_vs_pilpres[:8]

    lines = [
        "# DPRD Seat EDA Summary",
        "",
        "## Checks",
        "",
        f"- DPRD provincial seats: {summary['dprd_total_seats']:,}",
        f"- DPRD provinces: {summary['dprd_provinces']}",
        f"- DPRD parties with seats: {summary['dprd_parties_with_seats']}",
        f"- Aceh-local parties with seats: {summary['aceh_local_parties_with_seats']}",
        f"- Pilpres provinces joined: {summary['pilpres_joined_provinces']}",
        "- DPR comparison gaps exclude Aceh-local parties because they do not contest DPR nationally.",
        "",
        "## Top DPRD Provincial Parties",
        "",
    ]
    for row in top_parties:
        lines.append(
            f"- {row['party_code']}: {int(row['dprd_provincial_seats']):,} seats "
            f"({pct(float(row['dprd_provincial_seat_share'])):.1f}%)"
        )
    lines.extend(["", "## Largest Provincial Leader Margins", ""])
    for row in top_leaders:
        lines.append(
            f"- {row['province']}: {row['leading_party_code']} leads by {row['seat_margin']} seats"
        )
    lines.extend(["", "## Largest Pilpres vs DPRD Coalition Gaps", ""])
    for row in top_coalition_gaps:
        gap = float(row["pilpres_minus_dprd_seat_share"] or 0)
        lines.append(
            f"- {row['candidate']} in {row['province']}: Pilpres minus DPRD coalition seat share {pct(gap):+.1f} pts"
        )
    lines.extend(["", "## Largest DPRD vs DPR Vote Strength Gaps", ""])
    for row in strength_gaps[:8]:
        gap = float(row["dprd_minus_dpr_vote_share"])
        lines.append(
            f"- {row['province']} / {row['party_code']}: DPRD seat share minus DPR vote share {pct(gap):+.1f} pts"
        )

    (OUTPUT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def fmt_percent(value: object, signed: bool = False) -> str:
    if value in ("", None):
        return ""
    number = pct(float(value))
    return f"{number:+.1f}%" if signed else f"{number:.1f}%"


def table_rows(rows: list[dict[str, object]], columns: list[tuple[str, str]], limit: int | None = None) -> str:
    selected = rows[:limit] if limit else rows
    head = "".join(f"<th>{escape(label)}</th>" for _, label in columns)
    body = []
    for row in selected:
        cells = []
        for key, _ in columns:
            value = row.get(key, "")
            cells.append(f"<td>{escape(str(value))}</td>")
        body.append(f"<tr>{''.join(cells)}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def write_html_report(
    party_summary: list[dict[str, object]],
    province_leaders: list[dict[str, object]],
    dprd_vs_pilpres: list[dict[str, object]],
    strength_gaps: list[dict[str, object]],
    summary: dict[str, object],
) -> None:
    top_parties = [
        {
            "party_code": row["party_code"],
            "scope": row["party_scope"],
            "dprd_seats": row["dprd_provincial_seats"],
            "dprd_share": fmt_percent(row["dprd_provincial_seat_share"]),
            "dpr_share": fmt_percent(row["dpr_estimated_seat_share"]) if row["comparable_to_dpr"] == "true" else "",
            "gap": fmt_percent(row["dprd_minus_dpr_seat_share"], signed=True) if row["comparable_to_dpr"] == "true" else "",
        }
        for row in party_summary[:12]
    ]
    leader_rows = [
        {
            "province": row["province"],
            "leader": row["leading_party_code"],
            "seats": row["leading_party_seats"],
            "share": fmt_percent(row["leading_party_seat_share"]),
            "runner_up": row["runner_up_party_code"],
            "margin": row["seat_margin"],
        }
        for row in province_leaders[:12]
    ]
    coalition_rows = [
        {
            "province": row["province"],
            "candidate": row["candidate"],
            "dprd_share": fmt_percent(row["dprd_provincial_seat_share"]),
            "pilpres_share": fmt_percent(row["pilpres_vote_share"]),
            "gap": fmt_percent(row["pilpres_minus_dprd_seat_share"], signed=True),
        }
        for row in dprd_vs_pilpres[:15]
    ]
    gap_rows = [
        {
            "province": row["province"],
            "party": row["party_code"],
            "dprd_share": fmt_percent(row["dprd_provincial_seat_share"]),
            "dpr_vote_share": fmt_percent(row["dpr_vote_share"]),
            "gap": fmt_percent(row["dprd_minus_dpr_vote_share"], signed=True),
        }
        for row in strength_gaps[:15]
    ]

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>DPRD Seat EDA</title>
  <style>
    :root {{
      --paper: #f7f8fa;
      --surface: #ffffff;
      --ink: #17202a;
      --muted: #5f6b76;
      --line: #d8dee8;
      --accent: #0f766e;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: Inter, "Segoe UI", Arial, sans-serif;
      line-height: 1.5;
    }}
    .page {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 28px 20px 56px;
    }}
    header {{
      border-bottom: 1px solid var(--line);
      padding-bottom: 20px;
      margin-bottom: 24px;
    }}
    .eyebrow {{
      color: var(--accent);
      font-size: 0.8rem;
      font-weight: 800;
      text-transform: uppercase;
    }}
    h1 {{
      margin: 8px 0 10px;
      font-size: clamp(2rem, 5vw, 4rem);
      line-height: 1;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 0 0 14px;
      font-size: 1.15rem;
    }}
    p {{
      max-width: 76ch;
      color: var(--muted);
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin: 22px 0 0;
    }}
    .metric {{
      border: 1px solid var(--line);
      background: var(--surface);
      border-radius: 8px;
      padding: 14px;
    }}
    .metric span {{
      display: block;
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 700;
      text-transform: uppercase;
    }}
    .metric strong {{
      display: block;
      margin-top: 6px;
      font-size: 1.6rem;
    }}
    section {{
      margin-top: 28px;
    }}
    .chart-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }}
    figure {{
      margin: 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      padding: 12px;
    }}
    img {{
      display: block;
      width: 100%;
      height: auto;
      border-radius: 6px;
    }}
    figcaption {{
      margin-top: 8px;
      color: var(--muted);
      font-size: 0.88rem;
    }}
    .table-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }}
    .table-card {{
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      padding: 14px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.88rem;
      white-space: nowrap;
    }}
    th, td {{
      padding: 8px 10px;
      border-bottom: 1px solid var(--line);
      text-align: left;
    }}
    th {{
      color: var(--muted);
      font-size: 0.74rem;
      text-transform: uppercase;
    }}
    .note {{
      padding: 14px 16px;
      border-left: 4px solid var(--accent);
      background: #eef8f5;
      color: var(--ink);
      border-radius: 6px;
    }}
    @media (max-width: 820px) {{
      .metrics, .chart-grid, .table-grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <header>
      <div class="eyebrow">Exploratory analysis</div>
      <h1>DPRD Provincial Seats</h1>
      <p>Static visual readout comparing DPRD provincial seats with estimated DPR seats and Pilpres coalition vote share. This page is exploratory and not part of the public Render site.</p>
      <div class="metrics">
        <div class="metric"><span>DPRD Seats</span><strong>{summary['dprd_total_seats']:,}</strong></div>
        <div class="metric"><span>Provinces</span><strong>{summary['dprd_provinces']}</strong></div>
        <div class="metric"><span>Parties With Seats</span><strong>{summary['dprd_parties_with_seats']}</strong></div>
        <div class="metric"><span>Aceh Local Parties</span><strong>{summary['aceh_local_parties_with_seats']}</strong></div>
      </div>
    </header>

    <section>
      <p class="note">Aceh-local parties remain in DPRD totals and province leadership tables, but DPR comparison gaps exclude them because they do not contest DPR nationally.</p>
    </section>

    <section>
      <h2>Charts</h2>
      <div class="chart-grid">
        <figure><img src="charts/dprd_party_seats.png" alt="DPRD provincial seats by party"><figcaption>National DPRD provincial seats by party.</figcaption></figure>
        <figure><img src="charts/dprd_vs_dpr_party_share.png" alt="DPRD seat share versus DPR seat share"><figcaption>DPRD provincial seat share compared with estimated DPR seat share.</figcaption></figure>
        <figure><img src="charts/coalition_dprd_vs_pilpres.png" alt="Coalition DPRD share versus Pilpres vote share"><figcaption>Coalition DPRD seat share versus Pilpres vote share by province.</figcaption></figure>
        <figure><img src="charts/dprd_strength_gaps.png" alt="Largest DPRD strength gaps"><figcaption>Largest comparable DPRD seat-share gaps versus DPR vote share.</figcaption></figure>
      </div>
    </section>

    <section>
      <h2>Top Tables</h2>
      <div class="table-grid">
        <div class="table-card">
          <h2>Party Summary</h2>
          {table_rows(top_parties, [("party_code", "Party"), ("scope", "Scope"), ("dprd_seats", "DPRD Seats"), ("dprd_share", "DPRD Share"), ("dpr_share", "DPR Share"), ("gap", "Gap")])}
        </div>
        <div class="table-card">
          <h2>Province Leaders</h2>
          {table_rows(leader_rows, [("province", "Province"), ("leader", "Leader"), ("seats", "Seats"), ("share", "Share"), ("runner_up", "Runner Up"), ("margin", "Margin")])}
        </div>
        <div class="table-card">
          <h2>Pilpres Coalition Gaps</h2>
          {table_rows(coalition_rows, [("province", "Province"), ("candidate", "Candidate"), ("dprd_share", "DPRD Share"), ("pilpres_share", "Pilpres"), ("gap", "Gap")])}
        </div>
        <div class="table-card">
          <h2>DPRD vs DPR Vote Gaps</h2>
          {table_rows(gap_rows, [("province", "Province"), ("party", "Party"), ("dprd_share", "DPRD Share"), ("dpr_vote_share", "DPR Vote"), ("gap", "Gap")])}
        </div>
      </div>
    </section>
  </main>
</body>
</html>
"""
    (OUTPUT_DIR / "index.html").write_text(html, encoding="utf-8")


def plot_outputs(
    party_summary: list[dict[str, object]],
    dprd_vs_pilpres: list[dict[str, object]],
    strength_gaps: list[dict[str, object]],
) -> None:
    plt = make_chart_helpers()
    ensure_dir(CHART_DIR)

    top = party_summary[:12]
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.bar([str(row["party_code"]) for row in top], [int(row["dprd_provincial_seats"]) for row in top], color="#2563eb")
    ax.set_title("DPRD Provincial Seats by Party")
    ax.set_ylabel("Seats")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(CHART_DIR / "dprd_party_seats.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 7))
    for row in party_summary:
        x = pct(float(row["dpr_estimated_seat_share"] or 0))
        y = pct(float(row["dprd_provincial_seat_share"] or 0))
        ax.scatter(x, y, s=max(24, int(row["dprd_provincial_seats"]) / 3), color="#0f766e", alpha=0.75)
        if int(row["dprd_provincial_seats"]) >= 30 or int(row["dpr_estimated_seats"]) >= 10:
            ax.text(x + 0.1, y + 0.1, str(row["party_code"]), fontsize=8)
    max_axis = max(
        [pct(float(row["dpr_estimated_seat_share"] or 0)) for row in party_summary]
        + [pct(float(row["dprd_provincial_seat_share"] or 0)) for row in party_summary]
        + [1]
    )
    ax.plot([0, max_axis], [0, max_axis], color="#94a3b8", linestyle="--", linewidth=1)
    ax.set_title("DPRD Seat Share vs DPR Seat Share")
    ax.set_xlabel("DPR estimated seat share (%)")
    ax.set_ylabel("DPRD provincial seat share (%)")
    fig.tight_layout()
    fig.savefig(CHART_DIR / "dprd_vs_dpr_party_share.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 7))
    for coalition in COALITIONS:
        rows = [row for row in dprd_vs_pilpres if row["candidate"] == coalition["candidate"]]
        ax.scatter(
            [pct(float(row["dprd_provincial_seat_share"] or 0)) for row in rows],
            [pct(float(row["pilpres_vote_share"] or 0)) for row in rows],
            label=coalition["candidate"],
            color=coalition["color"],
            alpha=0.75,
        )
    ax.plot([0, 100], [0, 100], color="#94a3b8", linestyle="--", linewidth=1)
    ax.set_title("Coalition DPRD Share vs Pilpres Vote Share")
    ax.set_xlabel("Coalition DPRD provincial seat share (%)")
    ax.set_ylabel("Pilpres vote share (%)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(CHART_DIR / "coalition_dprd_vs_pilpres.png", dpi=160)
    plt.close(fig)

    gaps = strength_gaps[:12]
    labels = [f"{row['province']} / {row['party_code']}" for row in gaps]
    values = [pct(float(row["dprd_minus_dpr_vote_share"])) for row in gaps]
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.barh(labels[::-1], values[::-1], color=["#15803d" if value >= 0 else "#b91c1c" for value in values[::-1]])
    ax.axvline(0, color="#475569", linewidth=1)
    ax.set_title("Largest DPRD Seat Share Gaps vs DPR Vote Share")
    ax.set_xlabel("DPRD seat share minus DPR vote share (percentage points)")
    fig.tight_layout()
    fig.savefig(CHART_DIR / "dprd_strength_gaps.png", dpi=160)
    plt.close(fig)


def main() -> None:
    ensure_dir(OUTPUT_DIR)
    dprd_rows = read_csv(INPUT_DPRD_PROVINCE)
    dpr_party_rows = read_csv(INPUT_DPR_PARTY)
    dpr_district_rows = read_csv(INPUT_DPR_DISTRICT_PARTY)
    dpr_slate_rows = read_csv(INPUT_DPR_SLATES)
    pilpres_rows = read_csv(INPUT_PILPRES)

    party_summary = build_party_summary(dprd_rows, dpr_party_rows)
    province_party_summary = build_province_party_summary(dprd_rows, dpr_district_rows, dpr_slate_rows)
    province_leaders = build_province_leaders(province_party_summary)
    coalition_summary, dprd_vs_pilpres = build_coalition_outputs(province_party_summary, pilpres_rows)
    strength_gaps = top_strength_gaps(province_party_summary)

    dprd_total = sum(parse_int(row["provincial_seats"]) for row in dprd_rows)
    dprd_provinces = {row["province"] for row in dprd_rows}
    pilpres_provinces = {canonical_province(row["Region"]) for row in pilpres_rows}
    summary = {
        "dprd_total_seats": dprd_total,
        "dprd_provinces": len(dprd_provinces),
        "dprd_parties_with_seats": len({row["party_code"] for row in dprd_rows}),
        "aceh_local_parties_with_seats": len(
            {
                row["party_code"]
                for row in party_summary
                if row["party_scope"] == "local_aceh" and int(row["dprd_provincial_seats"]) > 0
            }
        ),
        "pilpres_provinces": len(pilpres_provinces),
        "pilpres_joined_provinces": len(dprd_provinces & pilpres_provinces),
        "missing_from_pilpres": sorted(dprd_provinces - pilpres_provinces),
        "missing_from_dprd": sorted(pilpres_provinces - dprd_provinces),
        "outputs": {
            "party_summary": "party_summary.csv",
            "province_party_summary": "province_party_summary.csv",
            "province_leaders": "province_leaders.csv",
            "coalition_summary": "coalition_summary.csv",
            "dprd_vs_pilpres": "dprd_vs_pilpres.csv",
            "summary_markdown": "summary.md",
            "html_report": "index.html",
        },
    }
    if dprd_total != 2372:
        raise AssertionError(f"Unexpected DPRD provincial seat total: {dprd_total}")
    if len(dprd_provinces) != 38:
        raise AssertionError(f"Unexpected DPRD province count: {len(dprd_provinces)}")
    if summary["missing_from_pilpres"] or summary["missing_from_dprd"]:
        raise AssertionError(f"Province mismatch: {summary}")

    write_csv(
        OUTPUT_DIR / "party_summary.csv",
        [
            "party_code",
            "party_name",
            "party_scope",
            "comparable_to_dpr",
            "dprd_provincial_seats",
            "dprd_provincial_seat_share",
            "dpr_estimated_seats",
            "dpr_estimated_seat_share",
            "dprd_minus_dpr_seat_share",
            "dpr_national_vote_share",
        ],
        party_summary,
    )
    write_csv(
        OUTPUT_DIR / "province_party_summary.csv",
        [
            "province",
            "party_code",
            "party_name",
            "party_scope",
            "comparable_to_dpr",
            "dprd_provincial_seats",
            "dprd_provincial_seat_share",
            "dpr_estimated_seats",
            "dpr_estimated_seat_share",
            "dpr_total_votes",
            "dpr_vote_share",
            "dprd_minus_dpr_vote_share",
            "dprd_minus_dpr_seat_share",
        ],
        province_party_summary,
    )
    write_csv(
        OUTPUT_DIR / "province_leaders.csv",
        [
            "province",
            "leading_party_code",
            "leading_party_name",
            "leading_party_seats",
            "leading_party_seat_share",
            "runner_up_party_code",
            "runner_up_party_name",
            "runner_up_party_seats",
            "seat_margin",
        ],
        province_leaders,
    )
    write_csv(
        OUTPUT_DIR / "coalition_summary.csv",
        [
            "province",
            "candidate",
            "coalition_parties",
            "dprd_provincial_seats",
            "dprd_provincial_seat_share",
            "dpr_estimated_seats",
            "dpr_estimated_seat_share",
            "pilpres_vote_share",
            "pilpres_minus_dprd_seat_share",
        ],
        coalition_summary,
    )
    write_csv(
        OUTPUT_DIR / "dprd_vs_pilpres.csv",
        [
            "province",
            "candidate",
            "coalition_parties",
            "dprd_provincial_seats",
            "dprd_provincial_seat_share",
            "dpr_estimated_seats",
            "dpr_estimated_seat_share",
            "pilpres_vote_share",
            "pilpres_minus_dprd_seat_share",
        ],
        dprd_vs_pilpres,
    )
    write_summary_markdown(party_summary, province_leaders, dprd_vs_pilpres, strength_gaps, summary)
    with (OUTPUT_DIR / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    plot_outputs(party_summary, dprd_vs_pilpres, strength_gaps)
    write_html_report(party_summary, province_leaders, dprd_vs_pilpres, strength_gaps, summary)

    print("Wrote DPRD EDA outputs to", OUTPUT_DIR)
    print("DPRD provincial seats:", dprd_total)
    print("Joined provinces:", summary["pilpres_joined_provinces"])


if __name__ == "__main__":
    main()
