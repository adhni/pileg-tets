#!/usr/bin/env python3
"""Build a standalone interactive HTML dashboard for the DPR D'Hondt counterfactual."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from common import PYTHON_OUTPUT_DIR, ROOT, ensure_dir, read_csv


OUTPUT_DIR = ensure_dir(PYTHON_OUTPUT_DIR / "dpr_dhondt_dashboard")
INPUT_DIR = PYTHON_OUTPUT_DIR / "dpr_dhondt_method"

PARTY_COLORS = {
    "PKB": "#0f766e",
    "Gerindra": "#b45309",
    "PDIP": "#b91c1c",
    "Golkar": "#ca8a04",
    "NasDem": "#1d4ed8",
    "PKS": "#ea580c",
    "PAN": "#2563eb",
    "Demokrat": "#1e40af",
}

METHODOLOGY = [
    {
        "title": "Same Votes, Different Divisors",
        "body": (
            "This dashboard keeps the same DPR 2024 vote totals, candidate rankings, dapil seat counts, and 4% national threshold. "
            "The only change is the district seat-allocation formula: Sainte-Lague becomes D'Hondt."
        ),
    },
    {
        "title": "D'Hondt Logic",
        "body": (
            "For each party in a dapil, votes are divided by 1, 2, 3, 4, and so on. The highest quotients take the available seats. "
            "Compared with Sainte-Lague's 1, 3, 5, 7 sequence, this favors larger parties more strongly."
        ),
    },
    {
        "title": "Candidate Winners",
        "body": (
            "After a party's seat count changes, the seats still go to the top personal-vote candidates within that party slate. "
            "So winner changes in this dashboard come only from party seat changes, not from any new candidate ranking rule."
        ),
    },
]


def safe_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def iso_timestamp(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")


def source_entry(path: Path, label: str, kind: str) -> dict[str, str]:
    return {
        "label": label,
        "kind": kind,
        "path": path.relative_to(ROOT).as_posix(),
        "updatedAt": iso_timestamp(path),
    }


def load_rows(filename: str) -> list[dict[str, str]]:
    path = INPUT_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Missing required input file {path.relative_to(ROOT)}. Run analysis/python/dpr_dhondt_method.py first."
        )
    return read_csv(path)


def load_payload() -> dict:
    national_rows = load_rows("national_party_summary.csv")
    district_rows = load_rows("district_party_comparison.csv")
    dhondt_winners = load_rows("dhondt_winners.csv")
    sainte_winners = load_rows("sainte_lague_winners.csv")

    national_parties = []
    threshold_parties = []
    for row in national_rows:
        party = {
            "partyCode": row["party_code"],
            "partyName": row["party_name"],
            "partyNumber": int(row["party_number"]),
            "nationalVotes": int(row["national_valid_votes"]),
            "voteShare": float(row["national_vote_share"]) if row["national_vote_share"] else 0.0,
            "passesThreshold": row["passes_dpr_threshold"] == "true",
            "sainteSeats": int(row["seats_sainte_lague"]),
            "dhondtSeats": int(row["seats_dhondt"]),
            "delta": int(row["seat_delta"]),
            "color": PARTY_COLORS.get(row["party_code"], "#475569"),
        }
        national_parties.append(party)
        if party["passesThreshold"]:
            threshold_parties.append(party)

    national_parties.sort(key=lambda item: (-item["dhondtSeats"], -item["nationalVotes"], item["partyNumber"], item["partyCode"]))
    threshold_parties.sort(key=lambda item: (-item["dhondtSeats"], -item["nationalVotes"], item["partyNumber"], item["partyCode"]))

    district_meta: dict[tuple[str, str], dict[str, object]] = {}
    for row in district_rows:
        key = (row["province"], row["district"])
        district_meta.setdefault(
            key,
            {
                "province": row["province"],
                "district": row["district"],
                "seatCount": int(row["seat_count"]),
                "districtTotalVotes": int(row["district_total_votes"]),
                "partyRows": [],
            },
        )
        district_meta[key]["partyRows"].append(
            {
                "partyCode": row["party_code"],
                "partyName": row["party_name"],
                "partyNumber": int(row["party_number"]),
                "totalVotes": int(row["total_votes"]),
                "voteShare": float(row["vote_share"]) if row["vote_share"] else 0.0,
                "sainteSeats": int(row["seats_sainte_lague"]),
                "dhondtSeats": int(row["seats_dhondt"]),
                "delta": int(row["seat_delta"]),
                "color": PARTY_COLORS.get(row["party_code"], "#475569"),
            }
        )

    sainte_lookup = defaultdict(list)
    dhondt_lookup = defaultdict(list)
    for row in sainte_winners:
        key = (row["province"], row["district"])
        sainte_lookup[key].append(
            {
                "partyCode": row["party_code"],
                "partyName": row["party_name"],
                "candidateName": row["candidate_name"],
                "candidateVote": int(row["candidate_vote"]),
                "candidateNumber": int(row["candidate_number"]),
            }
        )
    for row in dhondt_winners:
        key = (row["province"], row["district"])
        dhondt_lookup[key].append(
            {
                "partyCode": row["party_code"],
                "partyName": row["party_name"],
                "candidateName": row["candidate_name"],
                "candidateVote": int(row["candidate_vote"]),
                "candidateNumber": int(row["candidate_number"]),
            }
        )

    districts = []
    winner_change_count = 0
    for key, district in district_meta.items():
        district["partyRows"].sort(
            key=lambda item: (-item["dhondtSeats"], -item["sainteSeats"], -item["totalVotes"], item["partyNumber"], item["partyCode"])
        )
        changed_rows = [row for row in district["partyRows"] if row["delta"] != 0]
        district["changed"] = bool(changed_rows)
        district["changedPartyCount"] = len(changed_rows)
        district["netSeatMovement"] = sum(abs(row["delta"]) for row in changed_rows) // 2

        sainte_set = {
            (row["partyCode"], row["candidateName"], row["candidateNumber"])
            for row in sainte_lookup.get(key, [])
        }
        dhondt_set = {
            (row["partyCode"], row["candidateName"], row["candidateNumber"])
            for row in dhondt_lookup.get(key, [])
        }
        entrants = sorted(dhondt_set - sainte_set)
        exits = sorted(sainte_set - dhondt_set)
        winner_change_count += max(len(entrants), len(exits))
        district["winnerEntrants"] = [
            {"partyCode": party_code, "candidateName": candidate_name, "candidateNumber": candidate_number}
            for party_code, candidate_name, candidate_number in entrants
        ]
        district["winnerExits"] = [
            {"partyCode": party_code, "candidateName": candidate_name, "candidateNumber": candidate_number}
            for party_code, candidate_name, candidate_number in exits
        ]
        districts.append(district)

    districts.sort(
        key=lambda item: (
            not item["changed"],
            -item["netSeatMovement"],
            -item["seatCount"],
            item["province"],
            item["district"],
        )
    )

    top_gainers = [row for row in threshold_parties if row["delta"] > 0]
    top_losers = [row for row in threshold_parties if row["delta"] < 0]
    top_gainers.sort(key=lambda item: (-item["delta"], -item["dhondtSeats"], item["partyNumber"], item["partyCode"]))
    top_losers.sort(key=lambda item: (item["delta"], -item["dhondtSeats"], item["partyNumber"], item["partyCode"]))

    total_changed_districts = sum(1 for district in districts if district["changed"])

    return {
        "meta": {
            "title": "DPR 2024 Under D'Hondt",
            "subtitle": "A local counterfactual dashboard replacing Sainte-Lague with D'Hondt",
            "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
            "changedDistrictCount": total_changed_districts,
            "districtCount": len(districts),
            "winnerChangeCount": winner_change_count,
            "methodology": METHODOLOGY,
            "sources": [
                source_entry(INPUT_DIR / "national_party_summary.csv", "National party comparison", "csv"),
                source_entry(INPUT_DIR / "district_party_comparison.csv", "District party comparison", "csv"),
                source_entry(INPUT_DIR / "dhondt_winners.csv", "D'Hondt winners", "csv"),
                source_entry(INPUT_DIR / "sainte_lague_winners.csv", "Sainte-Lague winners", "csv"),
            ],
        },
        "summary": {
            "topGainers": top_gainers[:5],
            "topLosers": top_losers[:5],
            "thresholdParties": threshold_parties,
        },
        "districts": districts,
    }


def render_dashboard(payload: dict) -> str:
    template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DPR 2024 Under D'Hondt</title>
  <style>
    :root {
      --paper: #f4efe4;
      --paper-strong: #efe4cf;
      --ink: #1f2937;
      --muted: #6b7280;
      --accent: #8c2f20;
      --accent-soft: rgba(140, 47, 32, 0.12);
      --line: rgba(31, 41, 55, 0.12);
      --card: rgba(255, 251, 243, 0.86);
      --shadow: 0 24px 80px rgba(76, 49, 28, 0.12);
      --gain: #166534;
      --loss: #b91c1c;
    }

    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      font-family: "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(140, 47, 32, 0.18), transparent 28%),
        radial-gradient(circle at top right, rgba(202, 138, 4, 0.18), transparent 30%),
        linear-gradient(180deg, #f9f5ec 0%, var(--paper) 52%, #efe6d4 100%);
      min-height: 100vh;
    }

    .shell {
      width: min(1240px, calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0 64px;
    }

    .hero {
      position: relative;
      overflow: hidden;
      padding: 32px;
      border: 1px solid rgba(255, 255, 255, 0.55);
      border-radius: 32px;
      background:
        linear-gradient(135deg, rgba(255, 250, 242, 0.9), rgba(248, 239, 221, 0.78)),
        var(--card);
      box-shadow: var(--shadow);
    }

    .hero::after {
      content: "";
      position: absolute;
      inset: auto -80px -120px auto;
      width: 260px;
      height: 260px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(140, 47, 32, 0.18), transparent 70%);
      pointer-events: none;
    }

    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--accent);
      font-weight: 700;
      padding: 8px 12px;
      border-radius: 999px;
      background: var(--accent-soft);
    }

    h1, h2, h3 {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      font-weight: 700;
      letter-spacing: -0.03em;
    }

    h1 {
      margin-top: 18px;
      font-size: clamp(2.5rem, 5vw, 4.7rem);
      line-height: 0.92;
      max-width: 760px;
    }

    .hero p {
      max-width: 720px;
      font-size: 1.02rem;
      line-height: 1.65;
      color: rgba(31, 41, 55, 0.82);
      margin: 16px 0 0;
    }

    .hero-grid,
    .metrics,
    .national-panels,
    .method-grid,
    .source-grid,
    .district-layout {
      display: grid;
      gap: 18px;
    }

    .hero-grid {
      grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.8fr);
      margin-top: 24px;
      align-items: end;
    }

    .metrics {
      grid-template-columns: repeat(3, minmax(0, 1fr));
      margin-top: 26px;
    }

    .metric,
    .panel,
    .method-card,
    .source-card,
    .district-card,
    .winner-card {
      border: 1px solid var(--line);
      background: rgba(255, 252, 246, 0.88);
      border-radius: 22px;
      box-shadow: 0 12px 32px rgba(91, 63, 40, 0.08);
    }

    .metric {
      padding: 18px 20px;
    }

    .metric-label {
      color: var(--muted);
      font-size: 0.84rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .metric-value {
      margin-top: 10px;
      font-size: clamp(2rem, 3vw, 3rem);
      font-weight: 700;
      line-height: 1;
    }

    .metric-note {
      margin-top: 10px;
      color: var(--muted);
      font-size: 0.94rem;
    }

    .section {
      margin-top: 26px;
    }

    .section-head {
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 16px;
      margin-bottom: 14px;
    }

    .section-head p {
      margin: 0;
      color: var(--muted);
      max-width: 760px;
      line-height: 1.6;
    }

    .national-panels {
      grid-template-columns: minmax(0, 1.3fr) minmax(290px, 0.7fr);
    }

    .panel {
      padding: 22px;
    }

    .party-bars {
      display: grid;
      gap: 14px;
    }

    .party-bar {
      display: grid;
      grid-template-columns: 116px minmax(0, 1fr) 110px;
      align-items: center;
      gap: 12px;
    }

    .party-label {
      font-weight: 700;
    }

    .bar-track {
      position: relative;
      height: 16px;
      border-radius: 999px;
      overflow: hidden;
      background: rgba(31, 41, 55, 0.09);
    }

    .bar-before,
    .bar-after {
      position: absolute;
      inset: 0 auto 0 0;
      border-radius: 999px;
    }

    .bar-before {
      opacity: 0.28;
      filter: saturate(0.5);
    }

    .bar-after {
      opacity: 0.9;
    }

    .bar-values {
      text-align: right;
      font-variant-numeric: tabular-nums;
      font-weight: 700;
      white-space: nowrap;
    }

    .delta {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 56px;
      padding: 4px 8px;
      border-radius: 999px;
      font-size: 0.82rem;
      font-weight: 700;
      margin-left: 8px;
      background: rgba(31, 41, 55, 0.06);
    }

    .delta.gain { color: var(--gain); background: rgba(22, 101, 52, 0.12); }
    .delta.loss { color: var(--loss); background: rgba(185, 28, 28, 0.1); }

    .swing-list {
      display: grid;
      gap: 10px;
    }

    .swing-row {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: baseline;
      padding: 12px 0;
      border-bottom: 1px solid var(--line);
    }

    .swing-row:last-child { border-bottom: 0; padding-bottom: 0; }

    .swing-name {
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .swatch {
      width: 11px;
      height: 11px;
      border-radius: 999px;
      flex: 0 0 auto;
    }

    .swing-meta {
      color: var(--muted);
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }

    .method-grid,
    .source-grid {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .method-card,
    .source-card {
      padding: 18px;
    }

    .method-card p,
    .source-card p {
      margin: 10px 0 0;
      color: var(--muted);
      line-height: 1.65;
    }

    .district-layout {
      grid-template-columns: minmax(300px, 360px) minmax(0, 1fr);
      align-items: start;
    }

    .filters {
      position: sticky;
      top: 18px;
      padding: 20px;
    }

    .filters label {
      display: block;
      margin-bottom: 10px;
      font-size: 0.82rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      font-weight: 700;
    }

    .filters input,
    .filters select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px 14px;
      font: inherit;
      background: rgba(255, 255, 255, 0.72);
      color: var(--ink);
    }

    .filter-stack {
      display: grid;
      gap: 14px;
    }

    .chip-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 2px;
    }

    .chip {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 8px 12px;
      font: inherit;
      background: rgba(255, 252, 246, 0.9);
      cursor: pointer;
    }

    .chip.active {
      background: var(--ink);
      color: white;
      border-color: var(--ink);
    }

    .district-list {
      display: grid;
      gap: 14px;
    }

    .district-card {
      padding: 20px;
      cursor: pointer;
      transition: transform 140ms ease, border-color 140ms ease, box-shadow 140ms ease;
    }

    .district-card:hover,
    .district-card.active {
      transform: translateY(-2px);
      border-color: rgba(140, 47, 32, 0.35);
      box-shadow: 0 18px 40px rgba(91, 63, 40, 0.12);
    }

    .district-card h3 {
      font-size: 1.24rem;
    }

    .district-meta {
      margin-top: 6px;
      color: var(--muted);
      font-size: 0.94rem;
    }

    .district-badges {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 14px;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 7px 11px;
      border-radius: 999px;
      font-size: 0.82rem;
      background: rgba(31, 41, 55, 0.06);
      color: var(--ink);
    }

    .badge.gain { background: rgba(22, 101, 52, 0.12); color: var(--gain); }
    .badge.loss { background: rgba(185, 28, 28, 0.1); color: var(--loss); }

    .detail-shell {
      display: grid;
      gap: 16px;
    }

    .party-grid {
      display: grid;
      gap: 12px;
    }

    .party-row {
      display: grid;
      grid-template-columns: minmax(120px, 160px) minmax(0, 1fr) 110px;
      gap: 12px;
      align-items: center;
      padding: 12px 0;
      border-bottom: 1px solid var(--line);
    }

    .party-row:last-child { border-bottom: 0; }

    .mini-track {
      position: relative;
      height: 12px;
      background: rgba(31, 41, 55, 0.08);
      border-radius: 999px;
      overflow: hidden;
    }

    .mini-track > span {
      position: absolute;
      inset: 0 auto 0 0;
      border-radius: 999px;
      opacity: 0.92;
    }

    .winner-layout {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }

    .winner-card {
      padding: 18px;
    }

    .winner-card h3 {
      font-size: 1.06rem;
      margin-bottom: 12px;
    }

    .winner-list {
      display: grid;
      gap: 10px;
    }

    .winner-item {
      padding: 12px;
      border-radius: 16px;
      background: rgba(31, 41, 55, 0.05);
    }

    .winner-party {
      color: var(--muted);
      font-size: 0.84rem;
      margin-top: 4px;
    }

    .empty {
      padding: 18px;
      border-radius: 18px;
      background: rgba(31, 41, 55, 0.04);
      color: var(--muted);
      line-height: 1.6;
    }

    .small-note {
      color: var(--muted);
      font-size: 0.9rem;
      line-height: 1.6;
    }

    @media (max-width: 1024px) {
      .hero-grid,
      .national-panels,
      .district-layout,
      .method-grid,
      .source-grid,
      .winner-layout {
        grid-template-columns: 1fr;
      }

      .filters {
        position: static;
      }
    }

    @media (max-width: 720px) {
      .shell {
        width: min(100% - 20px, 1240px);
        padding-top: 16px;
      }

      .hero,
      .panel,
      .method-card,
      .source-card,
      .district-card,
      .winner-card {
        padding: 18px;
      }

      .metrics {
        grid-template-columns: 1fr;
      }

      .party-bar,
      .party-row {
        grid-template-columns: 1fr;
      }

      .bar-values {
        text-align: left;
      }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <span class="eyebrow">Counterfactual Seat Map</span>
      <div class="hero-grid">
        <div>
          <h1>DPR 2024 if Indonesia used D'Hondt instead of Sainte-Lague</h1>
          <p id="hero-subtitle"></p>
        </div>
        <div class="small-note">
          <strong>What changed:</strong> the divisor sequence only. District votes, 4% national threshold, dapil seat counts, and in-party candidate ranking all stay the same. This makes the page a clean test of how a more majoritarian seat formula would reshape the chamber.
        </div>
      </div>
      <div class="metrics">
        <div class="metric">
          <div class="metric-label">Changed Districts</div>
          <div class="metric-value" id="changed-districts"></div>
          <div class="metric-note">How many of the 84 DPR dapils move at least one seat.</div>
        </div>
        <div class="metric">
          <div class="metric-label">Winner Swaps</div>
          <div class="metric-value" id="winner-swaps"></div>
          <div class="metric-note">Approximate number of candidate entries or exits caused by party seat shifts.</div>
        </div>
        <div class="metric">
          <div class="metric-label">Threshold Parties</div>
          <div class="metric-value" id="threshold-parties"></div>
          <div class="metric-note">Parties that still compete after the national 4% DPR threshold.</div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <div>
          <h2>National Seat Shift</h2>
          <p>D'Hondt rewards parties whose vote totals are already large enough to keep claiming second and third seats. The bars below compare the current Sainte-Lague seat total with the D'Hondt counterfactual.</p>
        </div>
      </div>
      <div class="national-panels">
        <div class="panel">
          <div class="party-bars" id="party-bars"></div>
        </div>
        <div class="panel">
          <h3>Biggest Winners</h3>
          <div class="swing-list" id="top-gainers"></div>
          <div style="height:16px"></div>
          <h3>Biggest Losers</h3>
          <div class="swing-list" id="top-losers"></div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <div>
          <h2>District Explorer</h2>
          <p>Search by province or dapil, or focus only on districts that move. Pick a district to inspect the party seat swap and the candidate-level winner changes.</p>
        </div>
      </div>
      <div class="district-layout">
        <div class="panel filters">
          <div class="filter-stack">
            <div>
              <label for="district-search">Search district</label>
              <input id="district-search" type="text" placeholder="Banten I, Jawa Tengah, Aceh...">
            </div>
            <div>
              <label for="province-filter">Province</label>
              <select id="province-filter"></select>
            </div>
            <div>
              <label>Scope</label>
              <div class="chip-row">
                <button class="chip active" data-scope="all">All districts</button>
                <button class="chip" data-scope="changed">Changed only</button>
              </div>
            </div>
            <div class="small-note" id="district-count-note"></div>
          </div>
        </div>
        <div class="detail-shell">
          <div class="district-list" id="district-list"></div>
          <div class="panel" id="district-detail"></div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <div>
          <h2>Method Notes</h2>
          <p>This page uses the D'Hondt comparison outputs already generated in the repo.</p>
        </div>
      </div>
      <div class="method-grid" id="method-grid"></div>
    </section>

    <section class="section">
      <div class="section-head">
        <div>
          <h2>Source Files</h2>
          <p>These are the local files powering the dashboard.</p>
        </div>
      </div>
      <div class="source-grid" id="source-grid"></div>
    </section>
  </div>

  <script>
    const payload = __PAYLOAD__;
    const state = {
      scope: 'all',
      search: '',
      province: 'all',
      selectedKey: '',
    };

    const districts = payload.districts.map((district) => ({
      ...district,
      key: `${district.province}__${district.district}`,
    }));

    function formatNumber(value) {
      return new Intl.NumberFormat('en-US').format(value);
    }

    function formatPct(value) {
      return `${(value * 100).toFixed(1)}%`;
    }

    function deltaClass(value) {
      if (value > 0) return 'gain';
      if (value < 0) return 'loss';
      return '';
    }

    function deltaLabel(value) {
      if (value > 0) return `+${value}`;
      return `${value}`;
    }

    function byId(id) {
      return document.getElementById(id);
    }

    function renderHero() {
      byId('hero-subtitle').textContent = `Generated ${new Date(payload.meta.generatedAt).toLocaleString()} using the existing DPR 2024 vote tables. D'Hondt changes ${payload.meta.changedDistrictCount} districts and reassigns roughly ${payload.meta.winnerChangeCount} candidate seats.`;
      byId('changed-districts').textContent = formatNumber(payload.meta.changedDistrictCount);
      byId('winner-swaps').textContent = formatNumber(payload.meta.winnerChangeCount);
      byId('threshold-parties').textContent = formatNumber(payload.summary.thresholdParties.length);
    }

    function renderNational() {
      const maxSeats = Math.max(...payload.summary.thresholdParties.map((party) => Math.max(party.sainteSeats, party.dhondtSeats)));
      byId('party-bars').innerHTML = payload.summary.thresholdParties.map((party) => {
        const beforeWidth = `${(party.sainteSeats / maxSeats) * 100}%`;
        const afterWidth = `${(party.dhondtSeats / maxSeats) * 100}%`;
        const delta = deltaLabel(party.delta);
        return `
          <div class="party-bar">
            <div class="party-label">${party.partyCode}</div>
            <div class="bar-track">
              <span class="bar-before" style="width:${beforeWidth}; background:${party.color};"></span>
              <span class="bar-after" style="width:${afterWidth}; background:${party.color};"></span>
            </div>
            <div class="bar-values">${party.sainteSeats} → ${party.dhondtSeats}<span class="delta ${deltaClass(party.delta)}">${delta}</span></div>
          </div>
        `;
      }).join('');

      const renderSwingList = (rows, target) => {
        byId(target).innerHTML = rows.map((party) => `
          <div class="swing-row">
            <div class="swing-name"><span class="swatch" style="background:${party.color}"></span>${party.partyCode}</div>
            <div class="swing-meta">${party.sainteSeats} → ${party.dhondtSeats} <span class="delta ${deltaClass(party.delta)}">${deltaLabel(party.delta)}</span></div>
          </div>
        `).join('');
      };

      renderSwingList(payload.summary.topGainers, 'top-gainers');
      renderSwingList(payload.summary.topLosers, 'top-losers');
    }

    function renderMethodAndSources() {
      byId('method-grid').innerHTML = payload.meta.methodology.map((item) => `
        <article class="method-card">
          <h3>${item.title}</h3>
          <p>${item.body}</p>
        </article>
      `).join('');

      byId('source-grid').innerHTML = payload.meta.sources.map((source) => `
        <article class="source-card">
          <h3>${source.label}</h3>
          <p><strong>${source.kind.toUpperCase()}</strong><br>${source.path}<br>Updated ${new Date(source.updatedAt).toLocaleString()}</p>
        </article>
      `).join('');
    }

    function filteredDistricts() {
      return districts.filter((district) => {
        if (state.scope === 'changed' && !district.changed) return false;
        if (state.province !== 'all' && district.province !== state.province) return false;
        if (!state.search) return true;
        const haystack = `${district.province} ${district.district}`.toLowerCase();
        return haystack.includes(state.search.toLowerCase());
      });
    }

    function ensureSelection(rows) {
      if (!rows.length) {
        state.selectedKey = '';
        return;
      }
      if (!rows.some((row) => row.key === state.selectedKey)) {
        state.selectedKey = rows[0].key;
      }
    }

    function renderDistrictList() {
      const rows = filteredDistricts();
      ensureSelection(rows);
      byId('district-count-note').textContent = `${rows.length} district${rows.length === 1 ? '' : 's'} in view`;
      byId('district-list').innerHTML = rows.map((district) => `
        <article class="district-card ${district.key === state.selectedKey ? 'active' : ''}" data-key="${district.key}">
          <h3>${district.district}</h3>
          <div class="district-meta">${district.province} · ${district.seatCount} seats · ${formatNumber(district.districtTotalVotes)} valid votes</div>
          <div class="district-badges">
            <span class="badge ${district.changed ? 'gain' : ''}">${district.changed ? `${district.netSeatMovement} seat swap` : 'No seat change'}</span>
            <span class="badge">${district.changedPartyCount} party${district.changedPartyCount === 1 ? '' : 'ies'} moved</span>
            <span class="badge">${district.winnerEntrants.length + district.winnerExits.length} winner flips</span>
          </div>
        </article>
      `).join('');

      document.querySelectorAll('.district-card').forEach((card) => {
        card.addEventListener('click', () => {
          state.selectedKey = card.dataset.key;
          renderDistrictList();
          renderDistrictDetail();
        });
      });
    }

    function renderDistrictDetail() {
      const district = districts.find((item) => item.key === state.selectedKey);
      if (!district) {
        byId('district-detail').innerHTML = `<div class="empty">No district matches the current filters.</div>`;
        return;
      }

      const maxVotes = Math.max(...district.partyRows.map((row) => row.totalVotes));
      const partyRowsHtml = district.partyRows.map((row) => `
        <div class="party-row">
          <div>
            <strong>${row.partyCode}</strong><br>
            <span class="small-note">${formatPct(row.voteShare)} vote share</span>
          </div>
          <div class="mini-track"><span style="width:${(row.totalVotes / maxVotes) * 100}%; background:${row.color};"></span></div>
          <div class="bar-values">${row.sainteSeats} → ${row.dhondtSeats}<span class="delta ${deltaClass(row.delta)}">${deltaLabel(row.delta)}</span></div>
        </div>
      `).join('');

      const renderWinnerList = (rows, emptyMessage) => {
        if (!rows.length) {
          return `<div class="empty">${emptyMessage}</div>`;
        }
        return `<div class="winner-list">${rows.map((row) => `
          <div class="winner-item">
            <strong>${row.candidateName}</strong>
            <div class="winner-party">${row.partyCode} · candidate #${row.candidateNumber}</div>
          </div>
        `).join('')}</div>`;
      };

      byId('district-detail').innerHTML = `
        <div class="section-head">
          <div>
            <h2>${district.district}</h2>
            <p>${district.province} · ${district.seatCount} seats · ${formatNumber(district.districtTotalVotes)} valid votes</p>
          </div>
        </div>
        <div class="panel" style="padding:22px;">
          <h3>Party seat comparison</h3>
          <div class="party-grid">${partyRowsHtml}</div>
        </div>
        <div class="winner-layout">
          <div class="winner-card">
            <h3>New winners under D'Hondt</h3>
            ${renderWinnerList(district.winnerEntrants, 'No candidates enter in this district.')}
          </div>
          <div class="winner-card">
            <h3>Winners lost from Sainte-Lague</h3>
            ${renderWinnerList(district.winnerExits, 'No candidates drop out in this district.')}
          </div>
        </div>
      `;
    }

    function initFilters() {
      const provinceSelect = byId('province-filter');
      const provinces = [...new Set(districts.map((district) => district.province))].sort((a, b) => a.localeCompare(b));
      provinceSelect.innerHTML = ['<option value="all">All provinces</option>'].concat(
        provinces.map((province) => `<option value="${province}">${province}</option>`)
      ).join('');

      byId('district-search').addEventListener('input', (event) => {
        state.search = event.target.value.trim();
        renderDistrictList();
        renderDistrictDetail();
      });

      provinceSelect.addEventListener('change', (event) => {
        state.province = event.target.value;
        renderDistrictList();
        renderDistrictDetail();
      });

      document.querySelectorAll('.chip').forEach((chip) => {
        chip.addEventListener('click', () => {
          state.scope = chip.dataset.scope;
          document.querySelectorAll('.chip').forEach((item) => item.classList.remove('active'));
          chip.classList.add('active');
          renderDistrictList();
          renderDistrictDetail();
        });
      });
    }

    renderHero();
    renderNational();
    renderMethodAndSources();
    initFilters();
    renderDistrictList();
    renderDistrictDetail();
  </script>
</body>
</html>
"""
    return template.replace("__PAYLOAD__", safe_json(payload))


def main() -> None:
    payload = load_payload()
    html = render_dashboard(payload)
    output_path = OUTPUT_DIR / "index.html"
    output_path.write_text(html, encoding="utf-8")
    (OUTPUT_DIR / "dashboard_metadata.json").write_text(
        json.dumps(
            {
                "title": payload["meta"]["title"],
                "generatedAt": payload["meta"]["generatedAt"],
                "output": output_path.relative_to(ROOT).as_posix(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "README.txt").write_text(
        "Open index.html in a browser after running analysis/python/dpr_dhondt_method.py and analysis/python/build_dhondt_dashboard.py.\n",
        encoding="utf-8",
    )
    print("Built D'Hondt dashboard at", output_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
