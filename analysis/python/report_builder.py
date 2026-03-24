#!/usr/bin/env python3
"""Build a consolidated HTML and Markdown report from Python outputs."""
from __future__ import annotations

import csv
import json
from html import escape
from pathlib import Path
from typing import Iterable, Sequence

from common import PYTHON_OUTPUT_DIR


OUTPUT_DIR = PYTHON_OUTPUT_DIR / "report"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def html_table(rows: Sequence[dict[str, str]], columns: Sequence[str], max_rows: int = 10) -> str:
    body = []
    for row in rows[:max_rows]:
        cells = "".join(f"<td>{escape(str(row.get(column, '')))}</td>" for column in columns)
        body.append(f"<tr>{cells}</tr>")
    header = "".join(f"<th>{escape(column)}</th>" for column in columns)
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def markdown_table(rows: Sequence[dict[str, str]], columns: Sequence[str], max_rows: int = 10) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows[:max_rows]:
        lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join(lines)


def metric_card(title: str, value: str, note: str) -> str:
    return (
        '<div class="metric-card">'
        f'<div class="metric-title">{escape(title)}</div>'
        f'<div class="metric-value">{escape(value)}</div>'
        f'<div class="metric-note">{escape(note)}</div>'
        "</div>"
    )


def image_card(title: str, relative_path: str) -> str:
    return (
        '<div class="plot-card">'
        f"<h3>{escape(title)}</h3>"
        f'<img src="{escape(relative_path)}" alt="{escape(title)}" />'
        "</div>"
    )


def main() -> None:
    validation = read_json(PYTHON_OUTPUT_DIR / "validation" / "prepared_data_validation.json")
    vote_dynamics = read_json(PYTHON_OUTPUT_DIR / "dpr_vote_dynamics" / "summary.json")
    winners = read_json(PYTHON_OUTPUT_DIR / "dpr_estimated_winners" / "summary.json")
    coverage = read_json(PYTHON_OUTPUT_DIR / "data_coverage" / "summary.json")
    party_ratio = read_json(PYTHON_OUTPUT_DIR / "party_ratio_analysis" / "summary.json")
    representation = read_json(PYTHON_OUTPUT_DIR / "representation_gap" / "summary.json")

    seats_by_party = read_csv(PYTHON_OUTPUT_DIR / "dpr_estimated_winners" / "estimated_seats_by_party.csv")
    threshold_status = read_csv(PYTHON_OUTPUT_DIR / "dpr_estimated_winners" / "party_threshold_status.csv")
    threshold_impact = read_csv(PYTHON_OUTPUT_DIR / "dpr_estimated_winners" / "district_threshold_impact.csv")
    replacement_winners = read_csv(PYTHON_OUTPUT_DIR / "dpr_estimated_winners" / "replacement_winners.csv")
    displaced_winners = read_csv(PYTHON_OUTPUT_DIR / "dpr_estimated_winners" / "displaced_winners.csv")
    lowest_coverage = read_csv(PYTHON_OUTPUT_DIR / "representation_gap" / "lowest_coverage_districts.csv")
    party_distortion = read_csv(PYTHON_OUTPUT_DIR / "representation_gap" / "party_distortion.csv")
    top_candidate_dominance = read_csv(PYTHON_OUTPUT_DIR / "dpr_vote_dynamics" / "top_candidate_dominance.csv")
    party_ratio_table = read_csv(PYTHON_OUTPUT_DIR / "party_ratio_analysis" / "party_ratio_table.csv")
    psi_summary = read_csv(PYTHON_OUTPUT_DIR / "party_ratio_analysis" / "psi_province_summary.csv")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Python Election Report</title>
  <style>
    :root {{
      --bg: #f6f1e9;
      --panel: #fffdf8;
      --ink: #1f2933;
      --muted: #5b6773;
      --line: #ded6c8;
      --accent: #0f766e;
      --accent-2: #c2410c;
    }}
    body {{
      margin: 0;
      font-family: Georgia, "Iowan Old Style", "Times New Roman", serif;
      background: linear-gradient(180deg, #f6f1e9 0%, #fefcf7 100%);
      color: var(--ink);
    }}
    .wrap {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 32px 24px 80px;
    }}
    .hero {{
      background: linear-gradient(135deg, rgba(15,118,110,.96), rgba(21,128,61,.92));
      color: white;
      border-radius: 24px;
      padding: 28px 30px;
      box-shadow: 0 24px 50px rgba(0,0,0,.12);
      margin-bottom: 28px;
    }}
    .hero h1 {{
      margin: 0 0 8px;
      font-size: 2.2rem;
    }}
    .hero p {{
      margin: 0;
      font-size: 1.02rem;
      line-height: 1.6;
      max-width: 820px;
    }}
    .section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 22px 22px 18px;
      box-shadow: 0 10px 30px rgba(44,62,80,.05);
      margin-bottom: 20px;
    }}
    .section h2 {{
      margin: 0 0 12px;
      font-size: 1.35rem;
    }}
    .metric-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
      margin: 14px 0 8px;
    }}
    .metric-card {{
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
      background: #fff;
    }}
    .metric-title {{
      text-transform: uppercase;
      letter-spacing: .06em;
      font-size: .74rem;
      color: var(--muted);
      margin-bottom: 8px;
    }}
    .metric-value {{
      font-size: 1.8rem;
      font-weight: 700;
      color: var(--accent);
      margin-bottom: 4px;
    }}
    .metric-note {{
      color: var(--muted);
      font-size: .9rem;
      line-height: 1.45;
    }}
    .two-col {{
      display: grid;
      grid-template-columns: 1.2fr .8fr;
      gap: 18px;
    }}
    .plot-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 18px;
    }}
    .plot-card {{
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
      background: #fff;
    }}
    .plot-card h3 {{
      margin: 0 0 12px;
      font-size: 1rem;
      color: var(--accent-2);
    }}
    .plot-card img {{
      width: 100%;
      display: block;
      border-radius: 10px;
      border: 1px solid var(--line);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: .94rem;
    }}
    th, td {{
      padding: 9px 10px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }}
    th {{
      font-size: .8rem;
      text-transform: uppercase;
      letter-spacing: .04em;
      color: var(--muted);
    }}
    ul {{
      margin: 0;
      padding-left: 18px;
    }}
    li {{
      margin: 8px 0;
    }}
    code {{
      background: #f3ece0;
      padding: 2px 5px;
      border-radius: 6px;
      font-size: .92em;
    }}
    @media (max-width: 820px) {{
      .two-col {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>Python Election Report</h1>
      <p>This report consolidates the Python migration layer for the repo: prepared data validation, DPR vote dynamics, party-vs-candidate ratios, estimated winners, representation coverage, and quick static plots. It is fully regenerated by <code>python3 analysis/python/run_all.py</code>.</p>
    </section>

    <section class="section">
      <h2>Pipeline Status</h2>
      <div class="metric-grid">
        {metric_card("Prepared Rows", str(validation["checks"]["dpr_candidate_rows"]), "Candidate-level DPR rows validated")}
        {metric_card("Dapil Seats", str(validation["checks"]["total_dapil_seats"]), "Explicit seat counts used in Python seat allocation")}
        {metric_card("Expected DPD Gap", ", ".join(coverage["dpd_missing_from_dpr"]), "Expected source coverage")}
        {metric_card("Expected DPRD2 Gap", ", ".join(coverage["dprd_kabkot_missing_from_dpr"]), "Expected source coverage")}
      </div>
      <ul>
        {''.join(f'<li>{escape(note)}</li>' for note in validation["notes"])}
      </ul>
    </section>

    <section class="section">
      <h2>DPR Vote Dynamics</h2>
      <div class="metric-grid">
        {metric_card("Provinces", str(vote_dynamics["provinces_covered"]), "Covered in the standardized DPR slate table")}
        {metric_card("Districts", str(vote_dynamics["districts_covered"]), "Unique DPR dapil")}
        {metric_card("Median Top Share", str(vote_dynamics["median_top_candidate_vote_share"]), "Top candidate share of candidate votes")}
        {metric_card("Median Party Share", str(vote_dynamics["median_party_vote_share"]), "Party-only vote share of total slate votes")}
      </div>
      <div class="two-col">
        <div>
          <h3>Most Dominant Slates</h3>
          {html_table(top_candidate_dominance, ["province", "district", "party_code", "top_candidate_name", "top_candidate_vote_share"], 8)}
        </div>
        <div>
          {image_card("Top candidate share distribution", "../plots/dpr_top_candidate_share_hist.png")}
        </div>
      </div>
    </section>

    <section class="section">
      <h2>Party Ratio Analysis</h2>
      <div class="metric-grid">
        {metric_card("Top Ratio Party", str(party_ratio["highest_party_ratio_party"]), str(party_ratio["highest_party_ratio_value"]))}
        {metric_card("Top Ratio Province", str(party_ratio["highest_province_ratio"]), str(party_ratio["highest_province_ratio_value"]))}
        {metric_card("PSI Top Province", str(party_ratio["psi_top_province_by_share"]), str(party_ratio["psi_top_share"]))}
        {metric_card("Parties", str(party_ratio["parties"]), "National parties in the DPR candidate file")}
      </div>
      <div class="two-col">
        <div>
          <h3>National Party Ratios</h3>
          {html_table(party_ratio_table, ["party_code", "party_to_candidate_ratio", "party_vote_share_of_total"], 8)}
          <h3>PSI Provincial Outliers</h3>
          {html_table(psi_summary, ["province", "party_to_candidate_ratio", "party_vote_share_of_total"], 6)}
        </div>
        <div class="plot-grid">
          {image_card("Party-vote reliance by party", "../plots/party_vote_ratio_by_party.png")}
          {image_card("PSI party vs candidate votes", "../plots/psi_party_vs_candidate_votes.png")}
        </div>
      </div>
    </section>

    <section class="section">
      <h2>Parliamentary Threshold</h2>
      <p>For <strong>DPR 2024</strong>, parties below <strong>{escape(str(float(winners["threshold_percent"]) * 100).rstrip("0").rstrip("."))}%</strong> of valid national DPR votes are excluded from DPR seat allocation. This rule applies to DPR only, not DPRD.</p>
      <div class="metric-grid">
        {metric_card("Qualified Parties", str(winners["qualified_parties"]), "Parties above the national DPR threshold")}
        {metric_card("Disqualified Parties", str(winners["disqualified_parties"]), "Visible in votes, excluded from DPR seat allocation")}
        {metric_card("Excluded Vote Share", str(winners["excluded_vote_share"]), "Share of national DPR-valid votes cast for sub-threshold parties")}
        {metric_card("Affected Districts", str(winners["affected_districts"]), "Districts where the legal threshold changed the winner set")}
      </div>
      <div class="two-col">
        <div>
          <h3>National Party Threshold Status</h3>
          {html_table(threshold_status, ["party_code", "national_vote_share", "passes_dpr_threshold"], 12)}
          <h3>Most Affected Districts</h3>
          {html_table(threshold_impact, ["province", "district", "disqualified_vote_share", "raw_seats_lost_to_threshold", "replacement_winners"], 10)}
        </div>
        <div class="plot-grid">
          {image_card("National vote share vs threshold", "../plots/dpr_threshold_vote_share.png")}
        </div>
      </div>
      <div class="two-col" style="margin-top:18px;">
        <div>
          <h3>Replacement Winners</h3>
          {html_table(replacement_winners, ["province", "district", "party_code", "candidate_name", "candidate_vote"], 8)}
        </div>
        <div>
          <h3>Displaced Winners</h3>
          {html_table(displaced_winners, ["province", "district", "party_code", "candidate_name", "candidate_vote"], 8)}
        </div>
      </div>
    </section>

    <section class="section">
      <h2>Estimated Winners And Representation</h2>
      <p>These seat and winner outputs use the <strong>threshold-adjusted legal DPR model</strong> by default. Raw all-party simulation outputs are retained separately for comparison.</p>
      <div class="metric-grid">
        {metric_card("Estimated Seats", str(winners["total_seats"]), "Total seats allocated after applying the DPR threshold")}
        {metric_card("Winning Parties", str(winners["threshold_adjusted"]["parties_winning_seats"]), "Parties winning at least one threshold-adjusted DPR seat")}
        {metric_card("Average Coverage", str(representation["avg_coverage"]), "Winning-candidate share of total district votes")}
        {metric_card("Median Coverage", str(representation["median_coverage"]), "Median district-level coverage")}
      </div>
      <div class="two-col">
        <div>
          <h3>Threshold-Adjusted Seats By Party</h3>
          {html_table(seats_by_party, ["party_code", "estimated_seats", "estimated_seats_raw", "seat_delta"], 10)}
          <h3>Lowest Coverage Districts</h3>
          {html_table(lowest_coverage, ["province", "district", "coverage", "residual"], 8)}
          <h3>Seat Minus Vote Leaders</h3>
          {html_table(party_distortion, ["party_code", "seat_share", "vote_share", "seat_minus_vote"], 8)}
        </div>
        <div class="plot-grid">
          {image_card("Estimated seats by party", "../plots/estimated_seats_by_party.png")}
          {image_card("Coverage histogram", "../plots/representation_coverage_hist.png")}
          {image_card("Seat minus vote by party", "../plots/seat_minus_vote_by_party.png")}
        </div>
      </div>
    </section>
  </div>
</body>
</html>
"""

    markdown = "\n\n".join(
        [
            "# Python Election Report",
            "This report is generated by `analysis/python/report_builder.py` and rebuilt by `python3 analysis/python/run_all.py`.",
            "## Pipeline Status",
            f"- Prepared DPR candidate rows: {validation['checks']['dpr_candidate_rows']}",
            f"- Total dapil seats: {validation['checks']['total_dapil_seats']}",
            f"- Expected DPD gap: {', '.join(coverage['dpd_missing_from_dpr'])}",
            f"- Expected DPRD kabupaten/kota gap: {', '.join(coverage['dprd_kabkot_missing_from_dpr'])}",
            "## DPR Vote Dynamics",
            f"- Provinces: {vote_dynamics['provinces_covered']}",
            f"- Districts: {vote_dynamics['districts_covered']}",
            f"- Median top candidate share: {vote_dynamics['median_top_candidate_vote_share']}",
            f"- Median party vote share: {vote_dynamics['median_party_vote_share']}",
            markdown_table(top_candidate_dominance, ["province", "district", "party_code", "top_candidate_name", "top_candidate_vote_share"], 8),
            "## Party Ratio Analysis",
            f"- Highest party ratio party: {party_ratio['highest_party_ratio_party']} ({party_ratio['highest_party_ratio_value']})",
            f"- Highest province ratio: {party_ratio['highest_province_ratio']} ({party_ratio['highest_province_ratio_value']})",
            f"- PSI top province by share: {party_ratio['psi_top_province_by_share']} ({party_ratio['psi_top_share']})",
            markdown_table(party_ratio_table, ["party_code", "party_to_candidate_ratio", "party_vote_share_of_total"], 8),
            "## Parliamentary Threshold",
            f"- DPR threshold: {float(winners['threshold_percent']) * 100:.1f}%",
            f"- Qualified parties: {winners['qualified_parties']}",
            f"- Disqualified parties: {winners['disqualified_parties']}",
            f"- Excluded vote share: {winners['excluded_vote_share']}",
            f"- Affected districts: {winners['affected_districts']}",
            markdown_table(threshold_status, ["party_code", "national_vote_share", "passes_dpr_threshold"], 12),
            markdown_table(threshold_impact, ["province", "district", "disqualified_vote_share", "raw_seats_lost_to_threshold", "replacement_winners"], 8),
            "## Estimated Winners And Representation",
            f"- Total seats: {winners['total_seats']}",
            f"- Winning parties (threshold-adjusted): {winners['threshold_adjusted']['parties_winning_seats']}",
            f"- Average coverage: {representation['avg_coverage']}",
            f"- Median coverage: {representation['median_coverage']}",
            markdown_table(lowest_coverage, ["province", "district", "coverage", "residual"], 8),
        ]
    )

    (OUTPUT_DIR / "index.html").write_text(html, encoding="utf-8")
    (OUTPUT_DIR / "index.md").write_text(markdown + "\n", encoding="utf-8")
    print("Wrote consolidated report to", OUTPUT_DIR / "index.html")


if __name__ == "__main__":
    main()
