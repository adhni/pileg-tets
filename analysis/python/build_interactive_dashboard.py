#!/usr/bin/env python3
"""Build a standalone interactive HTML dashboard for DPR candidate and party votes."""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

from common import PREPARED_DATA_DIR, PYTHON_OUTPUT_DIR, ROOT, read_csv


OUTPUT_DIR = PYTHON_OUTPUT_DIR / "dashboard"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
    "Hanura": "#b91c1c",
    "Garuda": "#475569",
    "PAN": "#2563eb",
    "PBB": "#15803d",
    "Demokrat": "#1e40af",
    "PSI": "#dc2626",
    "Perindo": "#0f766e",
    "PPP": "#166534",
    "Ummat": "#111827",
}

METHODOLOGY = [
    {
        "title": "Official Inputs, Estimated Outputs",
        "body": (
            "Candidate votes, party-only votes, provinces, districts, and party identities come from the prepared election tables in this repo. "
            "The dashboard then estimates district-party seats and likely winners in Python. Those estimated seats and winner lists are analytical outputs, not official KPU certification."
        ),
    },
    {
        "title": "What Counts As Party Votes",
        "body": (
            "Party votes are the party-only ballots recorded for a district-party slate. Candidate votes are the personal votes won by individual names on that same slate. "
            "Party vote share is the party-only portion of total visible support for the slate."
        ),
    },
    {
        "title": "How Estimated Winners Are Produced",
        "body": (
            "Seat estimates are allocated with the Sainte-Lague highest-quotient method using explicit dapil seat counts. "
            "Once a party is estimated to win seats in a district, the highest-vote candidates inside that party's slate are treated as the likely winners."
        ),
    },
    {
        "title": "How To Read District Labels",
        "body": (
            "A party-led district means party-only ballots carry an unusually large share of support. "
            "A candidate-led district means support is concentrated more heavily in standout personal vote-getters. "
            "Mixed means both effects matter."
        ),
    },
    {
        "title": "Expected Coverage Gaps",
        "body": (
            "Some source gaps are expected and documented rather than treated as failures. "
            "In the current source set, Papua Barat Daya is absent from the DPD file, and DKI Jakarta is absent from the DPRD kabupaten/kota file."
        ),
    },
]

GLOSSARY = [
    {
        "term": "Dapil",
        "definition": "An electoral district. DPR seats are allocated within each dapil, not at the national total alone.",
    },
    {
        "term": "Party Vote",
        "definition": "A vote cast for the party slate rather than for a named candidate on that slate.",
    },
    {
        "term": "Candidate Vote",
        "definition": "A personal vote won by an individual candidate within a party slate.",
    },
    {
        "term": "Party-Led District",
        "definition": "A district where party-only ballots make up a relatively large share of support and no single candidate dominates as strongly.",
    },
    {
        "term": "Candidate-Led District",
        "definition": "A district where personal vote-getters dominate more strongly and party-only ballots play a smaller role.",
    },
    {
        "term": "Estimated Winner",
        "definition": "A candidate treated as a likely winner by the Python seat-allocation model. This is not an official certified winner list.",
    },
]


def to_int(value: str) -> int:
    return int(value)


def to_float(value: str) -> float | None:
    if value == "":
        return None
    return float(value)


def iso_timestamp(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")


def source_entry(path: Path, label: str, kind: str, row_count: int | None = None, note: str = "") -> dict:
    relative_path = path.relative_to(ROOT).as_posix()
    entry = {
        "label": label,
        "kind": kind,
        "path": relative_path,
        "updatedAt": iso_timestamp(path),
        "note": note,
    }
    if row_count is not None:
        entry["rowCount"] = row_count
    return entry


def make_payload() -> dict:
    candidate_path = PREPARED_DATA_DIR / "dpr_candidates_standardized.csv"
    slate_path = PREPARED_DATA_DIR / "dpr_party_slates.csv"
    winners_path = PYTHON_OUTPUT_DIR / "dpr_estimated_winners" / "estimated_winners.csv"
    seats_path = PYTHON_OUTPUT_DIR / "dpr_estimated_winners" / "estimated_seats_by_district_party.csv"
    validation_path = PYTHON_OUTPUT_DIR / "validation" / "prepared_data_validation.json"
    vote_summary_path = PYTHON_OUTPUT_DIR / "dpr_vote_dynamics" / "summary.json"
    ratio_summary_path = PYTHON_OUTPUT_DIR / "party_ratio_analysis" / "summary.json"
    representation_summary_path = PYTHON_OUTPUT_DIR / "representation_gap" / "summary.json"
    coverage_summary_path = PYTHON_OUTPUT_DIR / "data_coverage" / "summary.json"

    candidates = []
    for row in read_csv(candidate_path):
        candidates.append(
            {
                "province": row["province"],
                "district": row["district"],
                "partyCode": row["party_code"],
                "partyName": row["party_name"],
                "partyNumber": to_int(row["party_number"]),
                "partyVote": to_int(row["party_vote"]),
                "candidateNumber": to_int(row["candidate_number"]),
                "candidateName": row["candidate_name"],
                "candidateVote": to_int(row["candidate_vote"]),
                "candidateRank": to_int(row["candidate_rank"]),
            }
        )

    slates = []
    for row in read_csv(slate_path):
        slates.append(
            {
                "province": row["province"],
                "district": row["district"],
                "partyCode": row["party_code"],
                "partyName": row["party_name"],
                "partyNumber": to_int(row["party_number"]),
                "partyVote": to_int(row["party_vote"]),
                "candidateCount": to_int(row["candidate_count"]),
                "candidateVoteTotal": to_int(row["candidate_vote_total"]),
                "totalVotes": to_int(row["total_votes"]),
                "topCandidateName": row["top_candidate_name"],
                "topCandidateVote": to_int(row["top_candidate_vote"]),
                "topShare": to_float(row["top_candidate_vote_share"]),
                "partyShare": to_float(row["party_vote_share"]),
            }
        )

    seats = []
    for row in read_csv(seats_path):
        seats.append(
            {
                "province": row["province"],
                "district": row["district"],
                "partyCode": row["party_code"],
                "partyName": row["party_name"],
                "seatsWon": to_int(row["seats_won"]),
                "seatCount": to_int(row["seat_count"]),
                "totalVotes": to_int(row["total_votes"]),
            }
        )

    winners = []
    for row in read_csv(winners_path):
        winners.append(
            {
                "province": row["province"],
                "district": row["district"],
                "seatCount": to_int(row["seat_count"]),
                "partyCode": row["party_code"],
                "partyName": row["party_name"],
                "partyNumber": to_int(row["party_number"]),
                "partyVote": to_int(row["party_vote"]),
                "totalVotes": to_int(row["total_votes"]),
                "candidateNumber": to_int(row["candidate_number"]),
                "candidateName": row["candidate_name"],
                "candidateVote": to_int(row["candidate_vote"]),
                "listPosition": to_int(row["list_position"]),
                "candidateVoteShareOfPartyTotal": to_float(row["candidate_vote_share_of_party_total"]),
            }
        )

    party_lookup = []
    for row in read_csv(PREPARED_DATA_DIR / "party_lookup.csv"):
        logo_path = row["logo_path"]
        if logo_path:
            logo_path = "../../../" + logo_path
        party_lookup.append(
            {
                "partyCode": row["party_code"],
                "partyName": row["party_name"],
                "logoPath": logo_path,
                "color": PARTY_COLORS.get(row["party_code"], "#334155"),
            }
        )

    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    vote_summary = json.loads(vote_summary_path.read_text(encoding="utf-8"))
    ratio_summary = json.loads(ratio_summary_path.read_text(encoding="utf-8"))
    representation_summary = json.loads(representation_summary_path.read_text(encoding="utf-8"))
    coverage_summary = json.loads(coverage_summary_path.read_text(encoding="utf-8"))

    sources = [
        source_entry(
            candidate_path,
            "Prepared DPR candidate table",
            "Prepared data",
            row_count=len(candidates),
            note="Candidate-level vote counts by province, district, party, and candidate.",
        ),
        source_entry(
            slate_path,
            "Prepared DPR slate summary table",
            "Prepared data",
            row_count=len(slates),
            note="One row per district-party slate with party votes, candidate totals, and concentration metrics.",
        ),
        source_entry(
            winners_path,
            "Estimated DPR winners table",
            "Derived output",
            row_count=len(winners),
            note="Python-estimated winners derived from seat allocation and within-party ranking.",
        ),
        source_entry(
            validation_path,
            "Prepared-data validation report",
            "Quality check",
            note="Schema checks, row counts, seat totals, and expected gap handling.",
        ),
        source_entry(
            coverage_summary_path,
            "Coverage summary",
            "Quality check",
            note="Province-level coverage notes and expected source gaps.",
        ),
    ]
    freshest_source_at = datetime.fromtimestamp(
        max(
            candidate_path.stat().st_mtime,
            slate_path.stat().st_mtime,
            winners_path.stat().st_mtime,
            validation_path.stat().st_mtime,
            coverage_summary_path.stat().st_mtime,
        )
    ).astimezone().isoformat(timespec="seconds")
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")

    return {
        "candidates": candidates,
        "slates": slates,
        "seats": seats,
        "winners": winners,
        "partyLookup": party_lookup,
        "summary": {
            "validation": validation,
            "voteDynamics": vote_summary,
            "partyRatio": ratio_summary,
            "representation": representation_summary,
        },
        "meta": {
            "generatedAt": generated_at,
            "freshestSourceAt": freshest_source_at,
            "validationStatus": validation["status"],
            "status": {
                "headline": "Official vote counts, estimated seat outcomes",
                "officialInputs": "Vote counts and district-party slate inputs come from prepared source tables in this repo.",
                "estimatedOutputs": "Estimated seats and winner lists are generated in Python and are not official certified results.",
                "caution": "Use this dashboard to understand local vote patterns and likely outcomes, not as a legal declaration of final seats.",
                "seatMethod": "Sainte-Lague highest quotient with explicit dapil seat counts, then highest-vote candidates inside winning party slates.",
            },
            "coverageNotes": coverage_summary["notes"],
            "methodology": METHODOLOGY,
            "glossary": GLOSSARY,
            "sources": sources,
        },
        "notes": [
            "Logic is inspired by the party-ratio analysis: party-only votes versus candidate votes, party vote share, and top-candidate concentration.",
            "Metrics react to province, district, and party filters. Candidate search narrows candidate views but leaves scope-level vote metrics anchored to the selected geography and party.",
            "Expected source gaps are documented separately and are not treated as data failures: Papua Barat Daya is absent from DPD, and DKI Jakarta is absent from DPRD kabupaten/kota.",
        ],
    }


def safe_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def build_html(payload: dict) -> str:
    template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Interactive DPR Vote Dashboard</title>
  <style>
    :root {
      --paper: #f3efe5;
      --ink: #1c2733;
      --muted: #5f6b76;
      --line: rgba(28, 39, 51, 0.12);
      --panel: rgba(255,255,255,0.85);
      --shadow: 0 18px 40px rgba(28,39,51,0.08);
      --accent: #0f766e;
      --accent-2: #b45309;
      --accent-3: #9f1239;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--ink);
      font-family: "Avenir Next", "Trebuchet MS", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(15,118,110,0.16), transparent 32%),
        radial-gradient(circle at top right, rgba(180,83,9,0.14), transparent 26%),
        linear-gradient(180deg, #f6f1e8 0%, #fbf8f2 52%, #f5efe3 100%);
      min-height: 100vh;
    }
    .skip-link {
      position: absolute;
      left: 14px;
      top: -48px;
      z-index: 2000;
      padding: 10px 14px;
      border-radius: 999px;
      background: #ffffff;
      color: var(--ink);
      text-decoration: none;
      box-shadow: 0 10px 20px rgba(28,39,51,.16);
    }
    .skip-link:focus {
      top: 14px;
    }
    .app {
      max-width: 1480px;
      margin: 0 auto;
      padding: 26px 20px 72px;
    }
    .sr-only {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
    }
    .hero {
      position: relative;
      overflow: hidden;
      background: linear-gradient(135deg, rgba(15,118,110,.96), rgba(17,94,89,.92) 54%, rgba(180,83,9,.88));
      color: white;
      border-radius: 28px;
      padding: 30px 30px 28px;
      box-shadow: 0 26px 54px rgba(0,0,0,.14);
      margin-bottom: 18px;
    }
    .hero::after {
      content: "";
      position: absolute;
      inset: auto -90px -100px auto;
      width: 300px;
      height: 300px;
      border-radius: 50%;
      background: rgba(255,255,255,.08);
    }
    .hero h1 {
      margin: 0 0 8px;
      font-size: clamp(2rem, 4vw, 3.1rem);
      line-height: 1.03;
      max-width: 820px;
    }
    .hero p {
      margin: 0;
      max-width: 820px;
      line-height: 1.6;
      font-size: 1rem;
      color: rgba(255,255,255,.92);
    }
    .hero-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 16px;
    }
    .finder-shell {
      margin-top: 22px;
      padding: 16px;
      border-radius: 18px;
      background: rgba(255,255,255,.12);
      border: 1px solid rgba(255,255,255,.15);
      backdrop-filter: blur(8px);
    }
    .finder-grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
      gap: 12px;
      align-items: end;
    }
    .finder-actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    .finder-note {
      margin: 10px 0 0;
      font-size: .86rem;
      color: rgba(255,255,255,.82);
      line-height: 1.5;
    }
    .finder-support {
      display: grid;
      gap: 12px;
      margin-top: 14px;
    }
    .finder-panel {
      border-radius: 18px;
      border: 1px solid rgba(255,255,255,.16);
      background: rgba(255,255,255,.10);
      padding: 14px 16px;
      backdrop-filter: blur(10px);
    }
    .finder-panel h2,
    .finder-panel h3 {
      margin: 0 0 8px;
      font-size: 1rem;
      color: white;
    }
    .finder-panel p {
      margin: 0;
      color: rgba(255,255,255,.88);
      font-size: .9rem;
      line-height: 1.55;
    }
    .finder-panel .small-note {
      color: rgba(255,255,255,.8);
    }
    .finder-suggestion-grid {
      display: grid;
      gap: 10px;
      margin-top: 10px;
    }
    .finder-suggestion {
      appearance: none;
      border: 1px solid rgba(255,255,255,.16);
      border-radius: 16px;
      background: rgba(255,255,255,.12);
      color: white;
      padding: 12px 14px;
      text-align: left;
      cursor: pointer;
    }
    .finder-suggestion strong {
      display: block;
      font-size: .95rem;
      line-height: 1.3;
    }
    .finder-suggestion span {
      display: block;
      margin-top: 4px;
      color: rgba(255,255,255,.82);
      font-size: .82rem;
      line-height: 1.45;
    }
    .finder-chip {
      appearance: none;
      border: 1px solid rgba(255,255,255,.16);
      border-radius: 999px;
      background: rgba(255,255,255,.12);
      color: white;
      padding: 8px 12px;
      font-size: .84rem;
      font-weight: 700;
    }
    .finder-chip:hover,
    .finder-suggestion:hover {
      background: rgba(255,255,255,.18);
    }
    .hero-pill {
      padding: 8px 12px;
      border: 1px solid rgba(255,255,255,.18);
      border-radius: 999px;
      background: rgba(255,255,255,.09);
      font-size: .86rem;
    }
    .status-banner {
      margin-bottom: 18px;
      background: linear-gradient(180deg, rgba(255,255,255,.96), rgba(249,246,241,.92));
    }
    .status-actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
    }
    .status-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
    }
    .status-card {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
      background: rgba(255,255,255,.88);
    }
    .status-card h3 {
      margin: 0 0 8px;
      font-size: 1rem;
      color: var(--accent-2);
    }
    .status-card p {
      margin: 0;
      color: var(--muted);
      line-height: 1.6;
      font-size: .9rem;
    }
    .trust-list {
      display: grid;
      gap: 10px;
      margin-top: 8px;
    }
    .trust-item {
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px;
      background: rgba(255,255,255,.78);
    }
    .trust-item strong {
      display: block;
      margin-bottom: 4px;
      color: var(--ink);
    }
    .source-list {
      display: grid;
      gap: 12px;
    }
    .source-item {
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 12px;
      background: rgba(255,255,255,.92);
    }
    .source-item strong {
      display: block;
      margin-bottom: 4px;
    }
    .source-meta {
      color: var(--muted);
      font-size: .84rem;
      line-height: 1.55;
    }
    .inline-note {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(159,18,57,.08);
      border: 1px solid rgba(159,18,57,.16);
      color: var(--ink);
      font-size: .84rem;
    }
    .layout {
      display: grid;
      grid-template-columns: 320px minmax(0, 1fr);
      gap: 18px;
      align-items: start;
    }
    .quick-jump {
      margin-bottom: 18px;
    }
    .jump-links {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }
    .jump-link {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 9px 12px;
      border-radius: 999px;
      border: 1px solid rgba(15,118,110,.16);
      background: rgba(15,118,110,.08);
      color: var(--ink);
      text-decoration: none;
      font-size: .86rem;
    }
    .jump-link:hover {
      text-decoration: underline;
    }
    .sidebar {
      position: sticky;
      top: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .panel {
      background: var(--panel);
      backdrop-filter: blur(12px);
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: var(--shadow);
    }
    .panel.pad {
      padding: 18px;
    }
    .panel h2, .panel h3 {
      margin: 0 0 12px;
      font-family: "Iowan Old Style", "Palatino Linotype", Georgia, serif;
    }
    .control-grid {
      display: grid;
      gap: 12px;
    }
    label {
      display: block;
      font-size: .82rem;
      text-transform: uppercase;
      letter-spacing: .08em;
      color: var(--muted);
      margin-bottom: 5px;
    }
    select, input[type="text"] {
      width: 100%;
      border-radius: 14px;
      border: 1px solid rgba(28,39,51,.16);
      padding: 11px 12px;
      background: rgba(255,255,255,.92);
      color: var(--ink);
      font-size: .95rem;
    }
    input[type="range"] {
      width: 100%;
    }
    .small-note {
      color: var(--muted);
      font-size: .84rem;
      line-height: 1.5;
    }
    .button-row {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 4px;
    }
    button {
      appearance: none;
      border: 0;
      cursor: pointer;
      border-radius: 999px;
      padding: 10px 14px;
      font-weight: 700;
      letter-spacing: .02em;
    }
    button[disabled] {
      opacity: .56;
      cursor: not-allowed;
    }
    button:focus-visible,
    .link-button:focus-visible,
    .sort-button:focus-visible,
    .party-card:focus-visible,
    select:focus-visible,
    input[type="text"]:focus-visible,
    input[type="range"]:focus-visible {
      outline: 3px solid rgba(15,118,110,.34);
      outline-offset: 2px;
    }
    .btn-primary {
      background: var(--accent);
      color: white;
    }
    .btn-secondary {
      background: rgba(28,39,51,.08);
      color: var(--ink);
    }
    .content {
      display: grid;
      gap: 18px;
    }
    .metric-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 14px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 15px;
      background: rgba(255,255,255,.9);
    }
    .summary-shell {
      display: grid;
      gap: 16px;
    }
    .summary-hero {
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 18px;
      background: linear-gradient(180deg, rgba(255,255,255,.96), rgba(247,244,238,.92));
    }
    .summary-hero h3 {
      margin: 0 0 8px;
      font-size: 1.5rem;
    }
    .summary-copy {
      color: var(--muted);
      line-height: 1.65;
      font-size: .98rem;
      max-width: 900px;
    }
    .summary-badges {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 14px;
    }
    .summary-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 9px 12px;
      border-radius: 999px;
      background: rgba(15,118,110,.08);
      border: 1px solid rgba(15,118,110,.16);
      font-size: .86rem;
      color: var(--ink);
    }
    .summary-badge strong {
      font-size: .84rem;
      text-transform: uppercase;
      letter-spacing: .05em;
      color: var(--muted);
    }
    .summary-note-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 14px;
    }
    .summary-note-card {
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
      background: rgba(255,255,255,.92);
    }
    .summary-note-card h4 {
      margin: 0 0 8px;
      color: var(--accent-2);
      font-size: 1rem;
    }
    .compare-shell {
      display: grid;
      gap: 16px;
    }
    .compare-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }
    .compare-card {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
      background: rgba(255,255,255,.92);
    }
    .compare-card h3 {
      margin: 0 0 8px;
      font-size: 1.1rem;
    }
    .metric-title {
      font-size: .77rem;
      text-transform: uppercase;
      letter-spacing: .08em;
      color: var(--muted);
      margin-bottom: 8px;
    }
    .metric-value {
      font-size: 1.72rem;
      font-weight: 800;
      color: var(--accent);
      line-height: 1;
    }
    .metric-note {
      font-size: .86rem;
      color: var(--muted);
      margin-top: 6px;
      line-height: 1.4;
    }
    .section-head {
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 14px;
    }
    .section-head p {
      margin: 0;
      color: var(--muted);
      font-size: .92rem;
      max-width: 760px;
      line-height: 1.55;
    }
    .section-actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      justify-content: end;
      align-items: center;
    }
    .split-2 {
      display: grid;
      grid-template-columns: minmax(0, 1.06fr) minmax(0, .94fr);
      gap: 16px;
    }
    .split-3 {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
    }
    .subpanel {
      border: 1px solid var(--line);
      border-radius: 18px;
      background: rgba(255,255,255,.92);
      padding: 14px;
    }
    .subpanel h3 {
      font-size: 1rem;
      color: var(--accent-2);
      margin-bottom: 10px;
    }
    .bar-list {
      display: grid;
      gap: 10px;
    }
    .bar-row {
      display: grid;
      grid-template-columns: minmax(0, 168px) minmax(0, 1fr) 88px;
      gap: 10px;
      align-items: center;
    }
    .bar-label {
      font-size: .9rem;
      line-height: 1.3;
    }
    .bar-label strong {
      display: block;
      color: var(--ink);
    }
    .bar-label span {
      color: var(--muted);
      font-size: .82rem;
    }
    .bar-track {
      position: relative;
      height: 14px;
      border-radius: 999px;
      background: rgba(28,39,51,.08);
      overflow: hidden;
    }
    .bar-fill {
      height: 100%;
      border-radius: 999px;
    }
    .bar-value {
      text-align: right;
      font-feature-settings: "tnum" 1;
      font-variant-numeric: tabular-nums;
      font-size: .9rem;
      color: var(--muted);
    }
    .scatter-shell {
      position: relative;
    }
    .scatter-summary {
      margin-top: 12px;
    }
    .scatter-svg {
      width: 100%;
      height: 360px;
      display: block;
      background: linear-gradient(180deg, rgba(255,255,255,.98), rgba(244,248,248,.94));
      border-radius: 16px;
      border: 1px solid var(--line);
    }
    .axis-label {
      fill: var(--muted);
      font-size: 12px;
    }
    .axis-line {
      stroke: rgba(28,39,51,.18);
      stroke-width: 1;
    }
    .grid-line {
      stroke: rgba(28,39,51,.08);
      stroke-width: 1;
    }
    .point {
      cursor: pointer;
      opacity: .86;
      transition: r .14s ease, opacity .14s ease;
    }
    .point:hover {
      opacity: 1;
    }
    .tooltip {
      position: fixed;
      display: none;
      pointer-events: none;
      background: rgba(16,24,40,.96);
      color: white;
      border-radius: 12px;
      padding: 10px 12px;
      font-size: .86rem;
      line-height: 1.45;
      max-width: 260px;
      z-index: 1000;
      box-shadow: 0 16px 34px rgba(0,0,0,.22);
    }
    .link-button {
      appearance: none;
      border: 0;
      background: transparent;
      padding: 0;
      margin: 0;
      color: inherit;
      font: inherit;
      text-align: left;
      cursor: pointer;
    }
    .link-button:hover {
      text-decoration: underline;
    }
    .party-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 14px;
    }
    .party-card {
      border: 1px solid var(--line);
      border-radius: 20px;
      background: rgba(255,255,255,.94);
      overflow: hidden;
    }
    .party-head {
      display: flex;
      gap: 12px;
      align-items: center;
      padding: 14px 14px 10px;
      border-bottom: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(255,255,255,.94), rgba(244,244,240,.9));
    }
    .party-logo {
      width: 42px;
      height: 42px;
      object-fit: contain;
      border-radius: 10px;
      background: white;
      border: 1px solid rgba(28,39,51,.08);
      padding: 5px;
      flex: 0 0 42px;
    }
    .party-title {
      min-width: 0;
    }
    .party-title strong {
      display: block;
      font-size: 1rem;
      line-height: 1.2;
    }
    .party-title span {
      color: var(--muted);
      font-size: .84rem;
    }
    .party-body {
      padding: 12px 14px 14px;
    }
    .party-meta {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 12px;
    }
    .party-meta div {
      border: 1px solid rgba(28,39,51,.08);
      border-radius: 14px;
      padding: 10px 11px;
      background: rgba(246,247,243,.84);
    }
    .party-meta label {
      margin: 0 0 4px;
      font-size: .68rem;
    }
    .party-meta strong {
      font-size: 1rem;
      display: block;
      line-height: 1.15;
    }
    .mini-table {
      width: 100%;
      border-collapse: collapse;
      font-size: .88rem;
    }
    .mini-table th, .mini-table td {
      padding: 7px 0;
      border-bottom: 1px solid rgba(28,39,51,.08);
      text-align: left;
      vertical-align: top;
    }
    .mini-table th {
      font-size: .7rem;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: .06em;
    }
    .candidate-table-wrap {
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: rgba(255,255,255,.94);
    }
    .mobile-candidate-list {
      display: none;
      gap: 12px;
    }
    .mobile-candidate-card {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
      background: rgba(255,255,255,.94);
    }
    .mobile-candidate-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: start;
      margin-bottom: 8px;
    }
    .mobile-candidate-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-top: 12px;
    }
    .mobile-candidate-metric {
      border: 1px solid rgba(28,39,51,.08);
      border-radius: 14px;
      padding: 10px 11px;
      background: rgba(246,247,243,.84);
    }
    .mobile-candidate-metric strong {
      display: block;
      margin-top: 4px;
      font-size: 1rem;
      line-height: 1.2;
    }
    .candidate-table-pager {
      margin-top: 12px;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      color: var(--muted);
      font-size: .9rem;
    }
    .pager-buttons {
      display: flex;
      gap: 10px;
    }
    .sort-button {
      appearance: none;
      background: transparent;
      border: 0;
      padding: 0;
      color: inherit;
      font: inherit;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    table.data-table {
      width: 100%;
      border-collapse: collapse;
      min-width: 980px;
      font-size: .91rem;
    }
    .data-table th, .data-table td {
      padding: 10px 12px;
      border-bottom: 1px solid rgba(28,39,51,.08);
      text-align: left;
      vertical-align: top;
    }
    .data-table th {
      position: sticky;
      top: 0;
      z-index: 1;
      background: rgba(246,244,239,.98);
      color: var(--muted);
      font-size: .72rem;
      text-transform: uppercase;
      letter-spacing: .08em;
    }
    .tag-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }
    .tag {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 7px 11px;
      border-radius: 999px;
      background: rgba(15,118,110,.08);
      border: 1px solid rgba(15,118,110,.14);
      color: var(--ink);
      font-size: .82rem;
    }
    .tag.validation-pass {
      background: rgba(22,163,74,.10);
      border-color: rgba(22,163,74,.18);
    }
    .tag.validation-warn {
      background: rgba(180,83,9,.10);
      border-color: rgba(180,83,9,.18);
    }
    .tag-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--accent);
    }
    .empty-state {
      padding: 22px;
      text-align: center;
      color: var(--muted);
      border: 1px dashed rgba(28,39,51,.14);
      border-radius: 16px;
      background: rgba(255,255,255,.72);
    }
    .foot-notes ul {
      margin: 0;
      padding-left: 18px;
    }
    .foot-notes li {
      margin: 8px 0;
      color: var(--muted);
    }
    .drawer-overlay {
      position: fixed;
      inset: 0;
      display: none;
      z-index: 1200;
    }
    .drawer-overlay.open {
      display: block;
    }
    .drawer-backdrop {
      position: absolute;
      inset: 0;
      background: rgba(15,23,42,.42);
      backdrop-filter: blur(3px);
    }
    .drawer-panel {
      position: absolute;
      top: 0;
      right: 0;
      width: min(580px, 100vw);
      height: 100%;
      background: linear-gradient(180deg, #fdfcf8, #f6f1e7);
      box-shadow: -20px 0 40px rgba(15,23,42,.18);
      display: flex;
      flex-direction: column;
    }
    .drawer-head {
      display: flex;
      justify-content: space-between;
      gap: 14px;
      align-items: start;
      padding: 20px 20px 14px;
      border-bottom: 1px solid var(--line);
    }
    .drawer-kicker {
      text-transform: uppercase;
      letter-spacing: .08em;
      color: var(--muted);
      font-size: .75rem;
      margin-bottom: 5px;
    }
    .drawer-head h2 {
      margin: 0;
      font-size: 1.5rem;
    }
    .drawer-close {
      appearance: none;
      border: 0;
      background: rgba(28,39,51,.08);
      width: 38px;
      height: 38px;
      border-radius: 999px;
      font-size: 1.4rem;
      cursor: pointer;
    }
    .drawer-body {
      padding: 18px 20px 28px;
      overflow: auto;
      display: grid;
      gap: 16px;
    }
    .drawer-section {
      border: 1px solid var(--line);
      border-radius: 18px;
      background: rgba(255,255,255,.92);
      padding: 14px;
    }
    .drawer-section h3 {
      margin: 0 0 10px;
      font-size: 1rem;
      color: var(--accent-2);
    }
    [id$="Section"] {
      scroll-margin-top: 22px;
    }
    @media (prefers-reduced-motion: reduce) {
      .point,
      .link-button,
      .jump-link,
      button {
        transition: none !important;
      }
      html {
        scroll-behavior: auto;
      }
    }
    @media (max-width: 1180px) {
      .layout {
        grid-template-columns: 1fr;
      }
      .sidebar {
        position: static;
        order: 2;
      }
      .content {
        order: 1;
      }
      .split-2 {
        grid-template-columns: 1fr;
      }
      .finder-grid {
        grid-template-columns: 1fr;
      }
      .compare-grid {
        grid-template-columns: 1fr;
      }
    }
    @media (max-width: 820px) {
      .app {
        padding: 18px 14px 48px;
      }
      .section-head {
        flex-direction: column;
        align-items: start;
      }
      .hero {
        padding: 24px 20px 22px;
      }
      .status-actions {
        width: 100%;
      }
      .status-grid {
        grid-template-columns: 1fr;
      }
      .jump-links {
        flex-wrap: nowrap;
        overflow-x: auto;
        padding-bottom: 4px;
      }
      .split-3 {
        grid-template-columns: 1fr;
      }
      .bar-row {
        grid-template-columns: 1fr;
      }
      .bar-value {
        text-align: left;
      }
      .party-meta {
        grid-template-columns: 1fr;
      }
      table.data-table {
        display: none;
      }
      .candidate-table-wrap {
        overflow: visible;
        border: 0;
        background: transparent;
      }
      .mobile-candidate-list {
        display: grid;
      }
      .mobile-candidate-grid {
        grid-template-columns: 1fr;
      }
      .drawer-panel {
        width: 100vw;
      }
      .finder-actions {
        width: 100%;
      }
      .finder-actions button {
        width: 100%;
      }
      .section-actions {
        width: 100%;
        justify-content: start;
      }
    }
  </style>
</head>
<body>
  <a class="skip-link" href="#mainContent">Skip to main content</a>
  <div class="app">
    <section class="hero">
      <h1>Interactive DPR Vote Dashboard</h1>
      <p>Built for the general public first: start with your district, see who won, who nearly won, and whether the result was driven more by party labels or by standout candidates. The deeper analysis tools are still here, but the first question is now local.</p>
      <div class="hero-meta" id="heroMeta"></div>
      <div class="finder-shell">
        <div class="finder-grid">
          <div>
            <label for="districtFinderInput">Start With Your District</label>
            <input id="districtFinderInput" type="text" list="districtFinderList" placeholder="Type district, province, or candidate name" />
            <datalist id="districtFinderList"></datalist>
          </div>
          <div>
            <label for="compareFinderInput">Compare To Another District</label>
            <input id="compareFinderInput" type="text" list="districtFinderList" placeholder="Optional second district for comparison" />
          </div>
          <div class="finder-actions">
            <button class="btn-primary" id="districtFinderBtn">Go To District</button>
            <button class="btn-secondary" id="clearCompareBtn">Clear Compare</button>
          </div>
        </div>
        <p class="finder-note">Type a district, province, or even a candidate name. District matches jump directly into the local result; candidate matches suggest the district where that person is competing.</p>
      </div>
      <div class="finder-support">
        <section class="finder-panel" aria-live="polite">
          <h2>Start Here</h2>
          <div id="finderGuidance"></div>
          <div class="tag-row" id="recentDistricts"></div>
          <div class="finder-suggestion-grid" id="finderSuggestions"></div>
        </section>
      </div>
    </section>

    <section class="panel pad status-banner" role="status" aria-live="polite">
      <div class="section-head">
        <div>
          <h2>Result Status</h2>
          <p id="statusSummary"></p>
        </div>
        <div class="status-actions">
          <button class="btn-primary" id="shareViewBtn">Copy View Link</button>
          <button class="btn-secondary" id="shareDistrictBtn">Copy District Link</button>
          <button class="btn-secondary" id="downloadMethodBtn">Download Method Note</button>
          <button class="btn-secondary" id="methodologyBtn">How This Works</button>
          <button class="btn-secondary" id="glossaryBtn">Glossary</button>
          <button class="btn-secondary" id="sourcesBtn">Sources</button>
        </div>
      </div>
      <div class="status-grid" id="statusMeta"></div>
    </section>

    <nav class="panel pad quick-jump" aria-label="Quick jump">
      <div class="jump-links">
        <a class="jump-link" href="#districtSummarySection">District Summary</a>
        <a class="jump-link" href="#winnersSection">Winners</a>
        <a class="jump-link" href="#voteStructureSection">Vote Structure</a>
        <a class="jump-link" href="#partyRatioSection">Party Ratio</a>
        <a class="jump-link" href="#partyInspectorSection">Party Inspector</a>
        <a class="jump-link" href="#candidateTableSection">Candidate Table</a>
      </div>
    </nav>

    <div class="layout">
      <aside class="sidebar">
        <section class="panel pad">
          <h2>Filters</h2>
          <div class="control-grid">
            <div>
              <label for="provinceSelect">Province</label>
              <select id="provinceSelect"></select>
            </div>
            <div>
              <label for="districtSelect">District</label>
              <select id="districtSelect"></select>
            </div>
            <div>
              <label for="partySelect">Party</label>
              <select id="partySelect"></select>
            </div>
            <div>
              <label for="candidateSearch">Candidate Search</label>
              <input id="candidateSearch" type="text" placeholder="Search candidate name" />
            </div>
            <div>
              <label for="ratioMetric">Party Chart Metric</label>
              <select id="ratioMetric">
                <option value="partyShare">Party vote share of total support</option>
                <option value="ratio">Party vote / candidate vote ratio</option>
                <option value="seats">Estimated seats in scope</option>
              </select>
            </div>
            <div>
              <label for="topNRange">Top Candidates In Leaderboard: <span id="topNValue">18</span></label>
              <input id="topNRange" type="range" min="8" max="40" step="1" value="18" />
            </div>
            <div>
              <label for="pageSizeSelect">Candidate Table Rows</label>
              <select id="pageSizeSelect">
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
              </select>
            </div>
          </div>
          <div class="button-row">
            <button class="btn-primary" id="applyScopeBtn">Refresh Dashboard</button>
            <button class="btn-secondary" id="resetBtn">Reset Filters</button>
          </div>
          <p class="small-note">District-first users should start above with the district finder. These controls are for narrowing inside that district or for broader exploratory analysis.</p>
          <div class="tag-row" id="activeTags"></div>
        </section>

        <section class="panel pad">
          <h3>How To Read This</h3>
          <div id="storyGuide" class="small-note"></div>
        </section>

        <section class="panel pad">
          <h3>Trust And Method</h3>
          <div id="trustSummary" class="small-note"></div>
          <div class="tag-row" id="sourceSummary"></div>
        </section>

        <section class="panel pad">
          <h3>Downloads</h3>
          <p class="small-note">Export the current public view as CSV. District-specific files unlock after you select a district.</p>
          <div class="control-grid">
            <button class="btn-secondary" id="downloadWinnersBtn">Download Winners CSV</button>
            <button class="btn-secondary" id="downloadContendersBtn">Download Contenders CSV</button>
            <button class="btn-secondary" id="downloadCandidatesBtn">Download Candidate Table CSV</button>
            <button class="btn-secondary" id="downloadPartiesBtn">Download Party Summary CSV</button>
          </div>
        </section>

        <section class="panel pad foot-notes">
          <h3>Notes</h3>
          <ul id="notesList"></ul>
        </section>
      </aside>

      <main class="content" id="mainContent">
        <section class="panel pad" id="districtSummarySection">
          <div class="section-head">
            <div>
              <h2>District Summary</h2>
              <p>This is the new public-facing entry point. When a district is selected, the dashboard explains what happened there in plain language before dropping into deeper charts and tables.</p>
            </div>
          </div>
          <div id="districtSummary" aria-live="polite"></div>
        </section>

        <section class="panel pad" id="districtComparePanel">
          <div class="section-head">
            <div>
              <h2>Compare Districts</h2>
              <p>Use the optional comparison finder to see how one district differs from another on turnout proxies, party-vote reliance, candidate concentration, and estimated winners.</p>
            </div>
          </div>
          <div id="districtCompare" aria-live="polite"></div>
        </section>

        <section class="panel pad" id="scopeOverviewSection">
          <div class="section-head">
            <div>
              <h2>Scope Overview</h2>
              <p>These metrics summarize the current filter scope. Party-only votes are deduplicated at the slate level, while candidate totals sum the visible scope.</p>
            </div>
          </div>
          <div class="metric-grid" id="metricGrid"></div>
        </section>

        <section class="panel pad" id="winnersSection">
          <div class="section-head">
            <div>
              <h2>Who Won And Who Nearly Won</h2>
              <p>The left panel lists estimated elected candidates in the selected district. The right panel surfaces strong candidates who missed out, either because their party missed a seat or because they were outranked within their own party list.</p>
            </div>
          </div>
          <div class="inline-note">These winners are Python estimates, not official certified seat declarations.</div>
          <div class="split-2">
            <div class="subpanel">
              <h3>Estimated Winners</h3>
              <div id="districtWinners" aria-live="polite"></div>
            </div>
            <div class="subpanel">
              <h3>Closest Contenders</h3>
              <div id="districtContenders" aria-live="polite"></div>
            </div>
          </div>
        </section>

        <section class="panel pad" id="voteStructureSection">
          <div class="section-head">
            <div>
              <h2>Vote Structure</h2>
              <p>The left panel ranks candidates by raw vote count inside the current scope. The scatter on the right compares party-ballot share and top-candidate dominance for each slate in the selected scope.</p>
            </div>
          </div>
          <div class="split-2">
            <div class="subpanel">
              <h3>Candidate Leaderboard</h3>
              <div id="candidateLeaderboard"></div>
            </div>
            <div class="subpanel">
              <h3 id="scatterHeading">Slate Scatter: Top Candidate Share vs Party Vote Share</h3>
              <div class="scatter-shell">
                <svg class="scatter-svg" id="scatterSvg" viewBox="0 0 620 360" preserveAspectRatio="none" role="img" aria-labelledby="scatterHeading" aria-describedby="scatterSummary"></svg>
              </div>
              <div id="scatterSummary" class="small-note scatter-summary"></div>
            </div>
          </div>
        </section>

        <section class="panel pad" id="partyRatioSection">
          <div class="section-head">
            <div>
              <h2>Party Ratio Drilldown</h2>
              <p>Inspired directly by the party-ratio notebook: how much of each party’s support comes from party-only ballots versus candidate votes, and which parties convert that support into estimated seats in the current scope.</p>
            </div>
          </div>
          <div class="split-2">
            <div class="subpanel">
              <h3>Party Comparison</h3>
              <div id="partyRatioBars"></div>
            </div>
            <div class="subpanel">
              <h3>District Vs Province Context</h3>
              <div id="scopeHighlights"></div>
            </div>
          </div>
        </section>

        <section class="panel pad" id="partyInspectorSection">
          <div class="section-head">
            <div>
              <h2>Party Inspector</h2>
              <p>Each card shows a party’s current-scope totals, party-ratio metrics, estimated seats, and the candidates driving its performance. Click a party card to open a deeper side drawer.</p>
            </div>
          </div>
          <div class="party-grid" id="partyInspector"></div>
        </section>

        <section class="panel pad" id="candidateTableSection">
          <div class="section-head">
            <div>
              <h2>Candidate Table</h2>
              <p>This table now supports clickable column sorting and pagination. Click any candidate name to open a detail drawer.</p>
            </div>
            <div class="section-actions">
              <button class="btn-secondary" id="downloadCandidatesInlineBtn">Download Visible Candidate Table</button>
            </div>
          </div>
          <div class="candidate-table-wrap" id="candidateTableWrap"></div>
          <div id="candidateTablePager"></div>
        </section>
      </main>
    </div>
  </div>

  <div class="tooltip" id="tooltip" role="tooltip" aria-hidden="true"></div>
  <div class="drawer-overlay" id="drawerOverlay" aria-hidden="true">
    <div class="drawer-backdrop" id="drawerBackdrop"></div>
    <aside class="drawer-panel" role="dialog" aria-modal="true" aria-labelledby="drawerTitle">
      <div class="drawer-head">
        <div>
          <div class="drawer-kicker" id="drawerKicker"></div>
          <h2 id="drawerTitle"></h2>
        </div>
        <button class="drawer-close" id="drawerCloseBtn" aria-label="Close details">×</button>
      </div>
      <div class="drawer-body" id="drawerBody"></div>
    </aside>
  </div>

  <script>
    const DASHBOARD_DATA = __PAYLOAD__;

    const ALL_LABEL = "All";

    const state = {
      province: ALL_LABEL,
      district: ALL_LABEL,
      party: ALL_LABEL,
      search: "",
      topN: 18,
      ratioMetric: "partyShare",
      compareProvince: "",
      compareDistrict: "",
      pageSize: 25,
      candidatePage: 1,
      candidateSortKey: "candidateVote",
      candidateSortDir: "desc",
      drawerType: "",
      drawerValue: "",
    };

    const elements = {
      tooltip: document.getElementById("tooltip"),
      statusSummary: document.getElementById("statusSummary"),
      statusMeta: document.getElementById("statusMeta"),
      shareViewBtn: document.getElementById("shareViewBtn"),
      shareDistrictBtn: document.getElementById("shareDistrictBtn"),
      downloadMethodBtn: document.getElementById("downloadMethodBtn"),
      methodologyBtn: document.getElementById("methodologyBtn"),
      glossaryBtn: document.getElementById("glossaryBtn"),
      sourcesBtn: document.getElementById("sourcesBtn"),
      provinceSelect: document.getElementById("provinceSelect"),
      districtSelect: document.getElementById("districtSelect"),
      partySelect: document.getElementById("partySelect"),
      candidateSearch: document.getElementById("candidateSearch"),
      topNRange: document.getElementById("topNRange"),
      topNValue: document.getElementById("topNValue"),
      ratioMetric: document.getElementById("ratioMetric"),
      pageSizeSelect: document.getElementById("pageSizeSelect"),
      districtFinderInput: document.getElementById("districtFinderInput"),
      districtFinderList: document.getElementById("districtFinderList"),
      finderGuidance: document.getElementById("finderGuidance"),
      recentDistricts: document.getElementById("recentDistricts"),
      finderSuggestions: document.getElementById("finderSuggestions"),
      compareFinderInput: document.getElementById("compareFinderInput"),
      districtFinderBtn: document.getElementById("districtFinderBtn"),
      clearCompareBtn: document.getElementById("clearCompareBtn"),
      applyScopeBtn: document.getElementById("applyScopeBtn"),
      resetBtn: document.getElementById("resetBtn"),
      activeTags: document.getElementById("activeTags"),
      storyGuide: document.getElementById("storyGuide"),
      trustSummary: document.getElementById("trustSummary"),
      sourceSummary: document.getElementById("sourceSummary"),
      heroMeta: document.getElementById("heroMeta"),
      notesList: document.getElementById("notesList"),
      districtSummary: document.getElementById("districtSummary"),
      districtComparePanel: document.getElementById("districtComparePanel"),
      districtCompare: document.getElementById("districtCompare"),
      metricGrid: document.getElementById("metricGrid"),
      districtWinners: document.getElementById("districtWinners"),
      districtContenders: document.getElementById("districtContenders"),
      candidateLeaderboard: document.getElementById("candidateLeaderboard"),
      scatterSvg: document.getElementById("scatterSvg"),
      scatterSummary: document.getElementById("scatterSummary"),
      partyRatioBars: document.getElementById("partyRatioBars"),
      scopeHighlights: document.getElementById("scopeHighlights"),
      partyInspector: document.getElementById("partyInspector"),
      candidateTableWrap: document.getElementById("candidateTableWrap"),
      candidateTablePager: document.getElementById("candidateTablePager"),
      downloadWinnersBtn: document.getElementById("downloadWinnersBtn"),
      downloadContendersBtn: document.getElementById("downloadContendersBtn"),
      downloadCandidatesBtn: document.getElementById("downloadCandidatesBtn"),
      downloadCandidatesInlineBtn: document.getElementById("downloadCandidatesInlineBtn"),
      downloadPartiesBtn: document.getElementById("downloadPartiesBtn"),
      drawerOverlay: document.getElementById("drawerOverlay"),
      drawerBackdrop: document.getElementById("drawerBackdrop"),
      drawerKicker: document.getElementById("drawerKicker"),
      drawerTitle: document.getElementById("drawerTitle"),
      drawerBody: document.getElementById("drawerBody"),
      drawerCloseBtn: document.getElementById("drawerCloseBtn"),
    };

    const partyLookup = Object.fromEntries(DASHBOARD_DATA.partyLookup.map(item => [item.partyCode, item]));
    const candidateLookup = new Map();
    const slateLookup = new Map(DASHBOARD_DATA.slates.map(row => [slateKey(row), row]));

    for (const row of DASHBOARD_DATA.candidates) {
      candidateLookup.set(candidateKey(row), row);
    }

    const districtRecords = buildDistrictRecords();
    const districtDisplayLookup = new Map(districtRecords.map(record => [normalizeText(record.display), record]));
    const districtNameLookup = new Map();

    for (const record of districtRecords) {
      const key = normalizeText(record.district);
      if (!districtNameLookup.has(key)) {
        districtNameLookup.set(key, record);
      } else {
        districtNameLookup.set(key, null);
      }
    }

    const districtIndex = buildDistrictIndex();
    const provinceSummaryIndex = buildProvinceSummaryIndex();
    const validProvinces = new Set(DASHBOARD_DATA.slates.map(row => row.province));
    const validParties = new Set(DASHBOARD_DATA.slates.map(row => row.partyCode));

    let currentView = {
      scopedCandidates: [],
      candidateRows: [],
      scopedSlates: [],
      scopedSeats: [],
      metrics: null,
      partyRowsFull: [],
      partyRowsVisible: [],
      partyRowsFullMap: new Map(),
      primaryDistrictCtx: null,
    };
    const RECENT_DISTRICTS_STORAGE_KEY = "interactive_dpr_dashboard_recent_districts_v1";
    const MAX_RECENT_DISTRICTS = 6;
    const candidateDerivedCache = new Map();
    let recentDistrictKeys = loadRecentDistrictKeys();
    let candidateSearchDebounce = null;
    let lastFocusedElement = null;

    function partyColor(code) {
      return (partyLookup[code] && partyLookup[code].color) || "#334155";
    }

    function formatNumber(value) {
      return new Intl.NumberFormat("en-US").format(value);
    }

    function formatDecimal(value, digits = 3) {
      if (value === null || value === undefined || Number.isNaN(value)) return "—";
      return Number(value).toFixed(digits);
    }

    function formatPercent(value, digits = 1) {
      if (value === null || value === undefined || Number.isNaN(value)) return "—";
      return `${(Number(value) * 100).toFixed(digits)}%`;
    }

    function formatPercentDelta(value, baseline, digits = 1) {
      if (value === null || baseline === null || value === undefined || baseline === undefined) return "—";
      const delta = Number(value) - Number(baseline);
      const prefix = delta > 0 ? "+" : "";
      return `${prefix}${(delta * 100).toFixed(digits)} pp`;
    }

    function formatDateTime(value) {
      if (!value) return "—";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return "—";
      return new Intl.DateTimeFormat("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
        timeZoneName: "short",
      }).format(date);
    }

    function sortAria(key) {
      if (state.candidateSortKey !== key) return "none";
      return state.candidateSortDir === "asc" ? "ascending" : "descending";
    }

    function updateDocumentTitle() {
      const base = "Interactive DPR Vote Dashboard";
      if (state.drawerType === "candidate" && candidateLookup.has(state.drawerValue)) {
        const row = candidateLookup.get(state.drawerValue);
        document.title = `${row.candidateName} | ${row.district} | ${base}`;
        return;
      }
      if (state.drawerType === "party" && state.drawerValue) {
        const partyName = (partyLookup[state.drawerValue] && partyLookup[state.drawerValue].partyName) || state.drawerValue;
        const districtLabel = state.district !== ALL_LABEL ? ` | ${state.district}` : "";
        document.title = `${partyName}${districtLabel} | ${base}`;
        return;
      }
      if (state.district !== ALL_LABEL) {
        const compareLabel = state.compareDistrict ? ` vs ${state.compareDistrict}` : "";
        document.title = `${state.district}${compareLabel} | ${base}`;
        return;
      }
      if (state.province !== ALL_LABEL) {
        document.title = `${state.province} | ${base}`;
        return;
      }
      document.title = base;
    }

    function flashButton(button, defaultLabel, nextLabel = "Copied") {
      const original = defaultLabel;
      button.textContent = nextLabel;
      window.setTimeout(() => {
        button.textContent = original;
      }, 1600);
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
    }

    function normalizeText(value) {
      return String(value || "").trim().toLowerCase();
    }

    function districtKey(province, district) {
      return `${province}||${district}`;
    }

    function candidateKey(row) {
      return `${row.province}||${row.district}||${row.partyCode}||${row.candidateNumber}||${row.candidateName}`;
    }

    function slateKey(row) {
      return `${row.province}||${row.district}||${row.partyCode}`;
    }

    function districtDisplay(row) {
      return `${row.district} — ${row.province}`;
    }

    function sortAlpha(values) {
      return [...values].sort((a, b) => a.localeCompare(b));
    }

    function mean(values) {
      if (!values.length) return null;
      return values.reduce((sum, value) => sum + value, 0) / values.length;
    }

    function clamp(value, minValue, maxValue) {
      return Math.max(minValue, Math.min(maxValue, value));
    }

    function pluralize(count, singular, plural = singular + "s") {
      return count === 1 ? singular : plural;
    }

    function hasExplorationScope() {
      return state.province !== ALL_LABEL || state.district !== ALL_LABEL || state.party !== ALL_LABEL || Boolean(state.search);
    }

    function slugify(value) {
      return String(value || "")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "") || "export";
    }

    function buildDistrictRecords() {
      const seen = new Set();
      const records = [];
      for (const row of DASHBOARD_DATA.slates) {
        const key = districtKey(row.province, row.district);
        if (seen.has(key)) continue;
        seen.add(key);
        records.push({
          province: row.province,
          district: row.district,
          key,
          display: districtDisplay(row),
        });
      }
      return records.sort((a, b) => a.display.localeCompare(b.display));
    }

    function loadRecentDistrictKeys() {
      try {
        const raw = window.localStorage.getItem(RECENT_DISTRICTS_STORAGE_KEY);
        if (!raw) return [];
        const parsed = JSON.parse(raw);
        if (!Array.isArray(parsed)) return [];
        return parsed.filter(key => districtIndex.has(key)).slice(0, MAX_RECENT_DISTRICTS);
      } catch (error) {
        return [];
      }
    }

    function persistRecentDistrictKeys() {
      try {
        window.localStorage.setItem(RECENT_DISTRICTS_STORAGE_KEY, JSON.stringify(recentDistrictKeys.slice(0, MAX_RECENT_DISTRICTS)));
      } catch (error) {
        return;
      }
    }

    function rememberRecentDistrict(record) {
      if (!record || !record.key) return;
      recentDistrictKeys = [record.key, ...recentDistrictKeys.filter(key => key !== record.key)].slice(0, MAX_RECENT_DISTRICTS);
      persistRecentDistrictKeys();
    }

    function getRecentDistrictRecords() {
      return recentDistrictKeys
        .map(key => districtIndex.get(key))
        .filter(Boolean)
        .map(ctx => ({
          province: ctx.province,
          district: ctx.district,
          key: ctx.key,
          display: districtDisplay(ctx),
          totalVotes: ctx.metrics.totalVotes,
        }));
    }

    function getExampleDistrictRecords(limit = 4) {
      return [...districtIndex.values()]
        .sort((a, b) => b.metrics.totalVotes - a.metrics.totalVotes || a.district.localeCompare(b.district))
        .slice(0, limit)
        .map(ctx => ({
          province: ctx.province,
          district: ctx.district,
          key: ctx.key,
          display: districtDisplay(ctx),
          totalVotes: ctx.metrics.totalVotes,
        }));
    }

    function populateDistrictFinder() {
      elements.districtFinderList.innerHTML = districtRecords
        .map(record => `<option value="${escapeHtml(record.display)}"></option>`)
        .join("");
    }

    function findDistrictRecord(query) {
      const normalized = normalizeText(query);
      if (!normalized) return null;
      if (districtDisplayLookup.has(normalized)) return districtDisplayLookup.get(normalized);

      const exactDistrict = districtNameLookup.get(normalized);
      if (exactDistrict) return exactDistrict;

      const startsWithMatch = districtRecords.find(record =>
        normalizeText(record.display).startsWith(normalized)
        || normalizeText(record.district).startsWith(normalized)
      );
      if (startsWithMatch) return startsWithMatch;

      return districtRecords.find(record =>
        normalizeText(record.display).includes(normalized)
        || normalizeText(record.district).includes(normalized)
        || normalizeText(record.province).includes(normalized)
      ) || null;
    }

    function populateSelect(selectEl, values, selected, allLabel) {
      const normalized = [allLabel, ...values];
      selectEl.innerHTML = normalized.map(value => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("");
      selectEl.value = normalized.includes(selected) ? selected : allLabel;
      return selectEl.value;
    }

    function updateFilterOptions() {
      const provinces = sortAlpha([...new Set(DASHBOARD_DATA.slates.map(row => row.province))]);
      state.province = populateSelect(elements.provinceSelect, provinces, state.province, ALL_LABEL);

      const districts = sortAlpha(
        [...new Set(
          DASHBOARD_DATA.slates
            .filter(row => state.province === ALL_LABEL || row.province === state.province)
            .map(row => row.district)
        )]
      );
      state.district = populateSelect(elements.districtSelect, districts, state.district, ALL_LABEL);

      const parties = sortAlpha(
        [...new Set(
          DASHBOARD_DATA.slates
            .filter(row =>
              (state.province === ALL_LABEL || row.province === state.province)
              && (state.district === ALL_LABEL || row.district === state.district)
            )
            .map(row => row.partyCode)
        )]
      );
      state.party = populateSelect(elements.partySelect, parties, state.party, ALL_LABEL);
    }

    function applyStateToInputs() {
      elements.provinceSelect.value = state.province;
      elements.districtSelect.value = state.district;
      elements.partySelect.value = state.party;
      elements.candidateSearch.value = state.search;
      elements.ratioMetric.value = state.ratioMetric;
      elements.topNRange.value = String(state.topN);
      elements.topNValue.textContent = String(state.topN);
      elements.pageSizeSelect.value = String(state.pageSize);
      elements.districtFinderInput.value = state.district !== ALL_LABEL ? `${state.district} — ${state.province}` : "";
      elements.compareFinderInput.value = state.compareDistrict ? `${state.compareDistrict} — ${state.compareProvince}` : "";
    }

    function hydrateStateFromUrl() {
      const params = new URLSearchParams(window.location.search);
      const province = params.get("province");
      const district = params.get("district");
      const party = params.get("party");
      const search = params.get("q");
      const ratio = params.get("ratio");
      const compareProvince = params.get("compareProvince");
      const compareDistrict = params.get("compareDistrict");
      const topN = Number(params.get("topN"));
      const pageSize = Number(params.get("pageSize"));
      const page = Number(params.get("page"));
      const sort = params.get("sort");
      const dir = params.get("dir");
      const candidateDetail = params.get("candidate");
      const partyDetail = params.get("partyDetail");

      if (province && validProvinces.has(province)) state.province = province;
      if (district) {
        const record = findDistrictRecord(province ? `${district} — ${province}` : district);
        if (record) {
          state.province = record.province;
          state.district = record.district;
        }
      }
      if (party && validParties.has(party)) state.party = party;
      if (typeof search === "string") state.search = search;
      if (ratio && ["partyShare", "ratio", "seats"].includes(ratio)) state.ratioMetric = ratio;
      if (Number.isFinite(topN) && topN >= 8 && topN <= 40) state.topN = topN;
      if ([25, 50, 100].includes(pageSize)) state.pageSize = pageSize;
      if (Number.isFinite(page) && page >= 1) state.candidatePage = page;
      if (sort && ["candidateName", "partyCode", "province", "district", "candidateVote", "candidateRank", "shareOfPartyCandidates", "shareOfTotalSupport"].includes(sort)) {
        state.candidateSortKey = sort;
      }
      if (dir && ["asc", "desc"].includes(dir)) state.candidateSortDir = dir;

      if (compareDistrict) {
        const compareRecord = findDistrictRecord(compareProvince ? `${compareDistrict} — ${compareProvince}` : compareDistrict);
        if (compareRecord) {
          state.compareProvince = compareRecord.province;
          state.compareDistrict = compareRecord.district;
        }
      }
      if (candidateDetail && candidateLookup.has(candidateDetail)) {
        state.drawerType = "candidate";
        state.drawerValue = candidateDetail;
      } else if (partyDetail && validParties.has(partyDetail)) {
        state.drawerType = "party";
        state.drawerValue = partyDetail;
      }
    }

    function syncUrl() {
      const params = new URLSearchParams();
      if (state.province !== ALL_LABEL) params.set("province", state.province);
      if (state.district !== ALL_LABEL) params.set("district", state.district);
      if (state.party !== ALL_LABEL) params.set("party", state.party);
      if (state.search) params.set("q", state.search);
      if (state.ratioMetric !== "partyShare") params.set("ratio", state.ratioMetric);
      if (state.topN !== 18) params.set("topN", String(state.topN));
      if (state.pageSize !== 25) params.set("pageSize", String(state.pageSize));
      if (state.candidatePage !== 1) params.set("page", String(state.candidatePage));
      if (state.candidateSortKey !== "candidateVote") params.set("sort", state.candidateSortKey);
      if (state.candidateSortDir !== "desc") params.set("dir", state.candidateSortDir);
      if (state.compareDistrict) {
        params.set("compareProvince", state.compareProvince);
        params.set("compareDistrict", state.compareDistrict);
      }
      if (state.drawerType === "candidate" && state.drawerValue) {
        params.set("candidate", state.drawerValue);
      } else if (state.drawerType === "party" && state.drawerValue) {
        params.set("partyDetail", state.drawerValue);
      }
      const query = params.toString();
      const nextUrl = query ? `${window.location.pathname}?${query}` : window.location.pathname;
      window.history.replaceState({}, "", nextUrl);
    }

    function matchesScope(row) {
      return (state.province === ALL_LABEL || row.province === state.province)
        && (state.district === ALL_LABEL || row.district === state.district)
        && (state.party === ALL_LABEL || row.partyCode === state.party);
    }

    function getScopedCandidates() {
      return DASHBOARD_DATA.candidates.filter(matchesScope);
    }

    function getScopedSlates() {
      return DASHBOARD_DATA.slates.filter(matchesScope);
    }

    function getScopedSeats() {
      return DASHBOARD_DATA.seats.filter(matchesScope);
    }

    function getCandidateQueryRows(scopedCandidates) {
      const query = normalizeText(state.search);
      if (!query) return scopedCandidates;
      return scopedCandidates.filter(row => normalizeText(row.candidateName).includes(query));
    }

    function aggregateByParty(scopedCandidates, scopedSlates, scopedSeats, candidateRowsForLists) {
      const byParty = new Map();
      const seatMap = new Map(scopedSeats.map(row => [slateKey(row), row.seatsWon]));

      for (const slate of scopedSlates) {
        if (!byParty.has(slate.partyCode)) {
          byParty.set(slate.partyCode, {
            partyCode: slate.partyCode,
            partyName: slate.partyName,
            partyNumber: slate.partyNumber,
            partyVoteTotal: 0,
            candidateVoteTotal: 0,
            totalVotes: 0,
            seatsWon: 0,
            slates: 0,
            topSlate: null,
            candidates: [],
          });
        }
        const target = byParty.get(slate.partyCode);
        target.partyVoteTotal += slate.partyVote;
        target.candidateVoteTotal += slate.candidateVoteTotal;
        target.totalVotes += slate.totalVotes;
        target.slates += 1;
        target.seatsWon += seatMap.get(slateKey(slate)) || 0;
        if (!target.topSlate || slate.totalVotes > target.topSlate.totalVotes) {
          target.topSlate = slate;
        }
      }

      for (const row of candidateRowsForLists) {
        if (!byParty.has(row.partyCode)) {
          byParty.set(row.partyCode, {
            partyCode: row.partyCode,
            partyName: row.partyName,
            partyNumber: row.partyNumber,
            partyVoteTotal: 0,
            candidateVoteTotal: 0,
            totalVotes: 0,
            seatsWon: 0,
            slates: 0,
            topSlate: null,
            candidates: [],
          });
        }
        byParty.get(row.partyCode).candidates.push(row);
      }

      const result = [...byParty.values()].map(item => {
        item.candidates.sort((a, b) => b.candidateVote - a.candidateVote || a.candidateName.localeCompare(b.candidateName));
        item.topCandidate = item.candidates[0] || null;
        item.ratio = item.candidateVoteTotal > 0 ? item.partyVoteTotal / item.candidateVoteTotal : null;
        item.partyShare = item.totalVotes > 0 ? item.partyVoteTotal / item.totalVotes : null;
        return item;
      });

      result.sort((a, b) => b.totalVotes - a.totalVotes || a.partyNumber - b.partyNumber);
      return result;
    }

    function computeMetrics(scopedCandidates, scopedSlates, scopedSeats) {
      const candidateVotes = scopedCandidates.reduce((sum, row) => sum + row.candidateVote, 0);
      const partyVotes = scopedSlates.reduce((sum, row) => sum + row.partyVote, 0);
      const totalVotes = candidateVotes + partyVotes;
      const uniqueDistricts = new Set(scopedSlates.map(row => districtKey(row.province, row.district))).size;
      const topShares = scopedSlates.map(row => row.topShare).filter(value => value !== null && value !== undefined);
      const partyShares = scopedSlates.map(row => row.partyShare).filter(value => value !== null && value !== undefined);
      return {
        candidateRows: scopedCandidates.length,
        slates: scopedSlates.length,
        parties: new Set(scopedSlates.map(row => row.partyCode)).size,
        districts: uniqueDistricts,
        candidateVotes,
        partyVotes,
        totalVotes,
        ratio: candidateVotes > 0 ? partyVotes / candidateVotes : null,
        partyShare: totalVotes > 0 ? partyVotes / totalVotes : null,
        seatsWon: scopedSeats.reduce((sum, row) => sum + row.seatsWon, 0),
        avgTopShare: topShares.length ? mean(topShares) : null,
        avgPartyShare: partyShares.length ? mean(partyShares) : null,
      };
    }

    function classifyDistrict(metrics) {
      const partyShare = metrics.partyShare || 0;
      const topShare = metrics.avgTopShare || 0;

      if (partyShare >= 0.30 && topShare <= 0.44) {
        return {
          label: "Party-led",
          summary: "Party labels carried an above-average share of the vote, and support was not dominated by only one or two candidates.",
        };
      }
      if (partyShare <= 0.19 || topShare >= 0.52) {
        return {
          label: "Candidate-led",
          summary: "Personal vote-getters drove most of the support. Candidate names mattered more than party ballots here.",
        };
      }
      return {
        label: "Mixed",
        summary: "Both party brands and candidate personalities mattered. Voters split attention between logos and standout names.",
      };
    }

    function buildDistrictIndex() {
      const grouped = new Map();

      function ensure(province, district) {
        const key = districtKey(province, district);
        if (!grouped.has(key)) {
          grouped.set(key, {
            key,
            province,
            district,
            candidates: [],
            slates: [],
            seats: [],
            winners: [],
          });
        }
        return grouped.get(key);
      }

      for (const row of DASHBOARD_DATA.candidates) ensure(row.province, row.district).candidates.push(row);
      for (const row of DASHBOARD_DATA.slates) ensure(row.province, row.district).slates.push(row);
      for (const row of DASHBOARD_DATA.seats) ensure(row.province, row.district).seats.push(row);
      for (const row of DASHBOARD_DATA.winners) ensure(row.province, row.district).winners.push(row);

      for (const ctx of grouped.values()) {
        ctx.metrics = computeMetrics(ctx.candidates, ctx.slates, ctx.seats);
        ctx.partyRowsFull = aggregateByParty(ctx.candidates, ctx.slates, ctx.seats, ctx.candidates);
        ctx.partySeatMap = new Map(ctx.seats.map(row => [row.partyCode, row.seatsWon]));
        ctx.seatCount = ctx.seats[0]?.seatCount || ctx.winners[0]?.seatCount || 0;
        ctx.leadingParty = ctx.partyRowsFull[0] || null;
        ctx.winningPartyCount = new Set(ctx.winners.map(row => row.partyCode)).size;
        ctx.classification = classifyDistrict(ctx.metrics);
        ctx.winnerKeySet = new Set(ctx.winners.map(row => candidateKey(row)));
        ctx.districtRankMap = new Map(
          [...ctx.candidates]
            .sort((a, b) => b.candidateVote - a.candidateVote || a.candidateName.localeCompare(b.candidateName))
            .map((row, index) => [candidateKey(row), index + 1])
        );
        ctx.partyRankMap = new Map();
        const byParty = new Map();
        for (const row of ctx.candidates) {
          if (!byParty.has(row.partyCode)) byParty.set(row.partyCode, []);
          byParty.get(row.partyCode).push(row);
        }
        for (const [partyCode, rows] of byParty.entries()) {
          rows
            .sort((a, b) => b.candidateVote - a.candidateVote || a.candidateName.localeCompare(b.candidateName))
            .forEach((row, index) => ctx.partyRankMap.set(`${partyCode}||${candidateKey(row)}`, index + 1));
        }
      }

      return grouped;
    }

    function buildProvinceSummaryIndex() {
      const byProvince = new Map();
      for (const ctx of districtIndex.values()) {
        if (!byProvince.has(ctx.province)) byProvince.set(ctx.province, []);
        byProvince.get(ctx.province).push(ctx);
      }

      const summary = new Map();
      for (const [province, districts] of byProvince.entries()) {
        summary.set(province, {
          province,
          districtCount: districts.length,
          avgPartyShare: mean(districts.map(ctx => ctx.metrics.partyShare).filter(value => value !== null)),
          avgTopShare: mean(districts.map(ctx => ctx.metrics.avgTopShare).filter(value => value !== null)),
          avgWinningPartyCount: mean(districts.map(ctx => ctx.winningPartyCount)),
          avgTotalVotes: mean(districts.map(ctx => ctx.metrics.totalVotes)),
        });
      }
      return summary;
    }

    function getPrimaryDistrictContext() {
      if (state.district === ALL_LABEL || state.province === ALL_LABEL) return null;
      return districtIndex.get(districtKey(state.province, state.district)) || null;
    }

    function getCompareDistrictContext() {
      if (!state.compareDistrict || !state.compareProvince) return null;
      return districtIndex.get(districtKey(state.compareProvince, state.compareDistrict)) || null;
    }

    function getCandidateDerivedMetrics(row) {
      const cacheKey = candidateKey(row);
      if (candidateDerivedCache.has(cacheKey)) return candidateDerivedCache.get(cacheKey);
      const slate = slateLookup.get(slateKey(row));
      const derived = {
        shareOfPartyCandidates: slate && slate.candidateVoteTotal ? row.candidateVote / slate.candidateVoteTotal : null,
        shareOfTotalSupport: slate && slate.totalVotes ? row.candidateVote / slate.totalVotes : null,
      };
      candidateDerivedCache.set(cacheKey, derived);
      return derived;
    }

    function getTopContenders(ctx, limit = 8) {
      if (!ctx) return [];
      return [...ctx.candidates]
        .filter(row => !ctx.winnerKeySet.has(candidateKey(row)))
        .sort((a, b) => b.candidateVote - a.candidateVote || a.candidateName.localeCompare(b.candidateName))
        .slice(0, limit)
        .map(row => {
          const partySeats = ctx.partySeatMap.get(row.partyCode) || 0;
          const partyRank = ctx.partyRankMap.get(`${row.partyCode}||${candidateKey(row)}`) || null;
          const reason = partySeats === 0
            ? `${row.partyCode} did not reach a seat in this district.`
            : `${row.partyCode} won ${partySeats} ${pluralize(partySeats, "seat")}, but this candidate finished #${partyRank} inside the party race.`;
          return { row, partySeats, partyRank, reason };
        });
    }

    function districtMatchScore(record, query) {
      const display = normalizeText(record.display);
      const district = normalizeText(record.district);
      const province = normalizeText(record.province);
      if (!query) return 999;
      if (display === query || district === query) return 0;
      if (display.startsWith(query) || district.startsWith(query)) return 1;
      if (province.startsWith(query)) return 2;
      if (display.includes(query) || district.includes(query)) return 3;
      if (province.includes(query)) return 4;
      return 999;
    }

    function getDistrictSuggestions(query, limit = 6) {
      if (!query) return [];
      return districtRecords
        .map(record => ({ record, score: districtMatchScore(record, query) }))
        .filter(item => item.score < 999)
        .sort((a, b) => {
          if (a.score !== b.score) return a.score - b.score;
          const ctxA = districtIndex.get(a.record.key);
          const ctxB = districtIndex.get(b.record.key);
          return (ctxB?.metrics.totalVotes || 0) - (ctxA?.metrics.totalVotes || 0) || a.record.display.localeCompare(b.record.display);
        })
        .slice(0, limit)
        .map(item => item.record);
    }

    function getCandidateFinderSuggestions(query, limit = 4) {
      if (!query || query.length < 3) return [];
      return [...DASHBOARD_DATA.candidates]
        .filter(row => normalizeText(row.candidateName).includes(query))
        .sort((a, b) => b.candidateVote - a.candidateVote || a.candidateName.localeCompare(b.candidateName))
        .slice(0, limit);
    }

    function renderFinderAssist() {
      const query = normalizeText(elements.districtFinderInput.value);
      const recent = getRecentDistrictRecords();
      const examples = getExampleDistrictRecords(4);
      const districtSuggestions = getDistrictSuggestions(query, 6);
      const candidateSuggestions = getCandidateFinderSuggestions(query, 4);

      if (!query) {
        const activeLabel = state.district !== ALL_LABEL ? `${state.district} — ${state.province}` : "No district selected yet";
        const intro = state.district !== ALL_LABEL
          ? `You are currently reading <strong>${escapeHtml(activeLabel)}</strong>. Use the chips below to jump to a recent district or explore one of the larger districts in the dataset.`
          : "Type your district name first. After that, read the district summary, then check the estimated winners and the strongest near-miss candidates.";
        const follow = state.compareDistrict
          ? `A comparison district is active too: <strong>${escapeHtml(state.compareDistrict)} — ${escapeHtml(state.compareProvince)}</strong>.`
          : "You can optionally add a second district in the comparison box for side-by-side reading.";
        elements.finderGuidance.innerHTML = `
          <p>${intro}</p>
          <p class="small-note" style="margin-top:8px;">${follow}</p>
        `;

        elements.recentDistricts.innerHTML = [
          ...recent.map(record => `<button class="finder-chip" data-action="finder-district" data-record="${escapeHtml(record.display)}">Recent: ${escapeHtml(record.district)}</button>`),
          ...examples
            .filter(record => !recent.some(item => item.key === record.key))
            .map(record => `<button class="finder-chip" data-action="finder-district" data-record="${escapeHtml(record.display)}">Try: ${escapeHtml(record.district)}</button>`),
        ].join("");

        elements.finderSuggestions.innerHTML = `
          <button class="finder-suggestion" data-action="finder-district" data-record="${escapeHtml(examples[0]?.display || "")}" ${examples[0] ? "" : "disabled"}>
            <strong>${escapeHtml(examples[0] ? examples[0].district : "Start with a district")}</strong>
            <span>${escapeHtml(examples[0] ? `${examples[0].province} • ${formatNumber(examples[0].totalVotes)} total visible support` : "No district examples available")}</span>
          </button>
          <button class="finder-suggestion" data-action="finder-district" data-record="${escapeHtml(examples[1]?.display || "")}" ${examples[1] ? "" : "disabled"}>
            <strong>${escapeHtml(examples[1] ? examples[1].district : "Explore another district")}</strong>
            <span>${escapeHtml(examples[1] ? `${examples[1].province} • ${formatNumber(examples[1].totalVotes)} total visible support` : "Type any district or province name above")}</span>
          </button>
        `;
        return;
      }

      const districtButtons = districtSuggestions.map(record => {
        const ctx = districtIndex.get(record.key);
        return `
          <button class="finder-suggestion" data-action="finder-district" data-record="${escapeHtml(record.display)}">
            <strong>${escapeHtml(record.district)}</strong>
            <span>${escapeHtml(record.province)} • ${escapeHtml(formatNumber(ctx?.seatCount || 0))} seats • ${escapeHtml(formatNumber(ctx?.metrics.totalVotes || 0))} total visible support</span>
          </button>
        `;
      }).join("");

      const candidateButtons = candidateSuggestions.map(row => `
        <button class="finder-suggestion" data-action="finder-candidate" data-key="${escapeHtml(candidateKey(row))}">
          <strong>${escapeHtml(row.candidateName)}</strong>
          <span>${escapeHtml(row.partyCode)} in ${escapeHtml(row.district)} — ${escapeHtml(row.province)} • ${escapeHtml(formatNumber(row.candidateVote))} votes</span>
        </button>
      `).join("");

      const totalMatches = districtSuggestions.length + candidateSuggestions.length;
      elements.finderGuidance.innerHTML = `
        <p>${totalMatches ? `Pick a match below. District matches jump into the local result; candidate matches open that person's district and focus the dashboard on them.` : "No direct match yet. Try the district name, province name, or a longer candidate name."}</p>
        <p class="small-note" style="margin-top:8px;">District matches are prioritized first because the dashboard is district-first by design.</p>
      `;
      elements.recentDistricts.innerHTML = recent.map(record => `
        <button class="finder-chip" data-action="finder-district" data-record="${escapeHtml(record.display)}">Recent: ${escapeHtml(record.district)}</button>
      `).join("");
      elements.finderSuggestions.innerHTML = districtButtons + candidateButtons || `
        <div class="small-note">Try a province plus roman numeral, such as “Jawa Barat VII”, or type a candidate name to jump to their district.</div>
      `;
    }

    function csvEscape(value) {
      const stringValue = value === null || value === undefined ? "" : String(value);
      return /[",\\n]/.test(stringValue) ? `"${stringValue.replaceAll('"', '""')}"` : stringValue;
    }

    function buildCsv(columns, rows) {
      const header = columns.map(column => csvEscape(column.label)).join(",");
      const body = rows.map(row => columns.map(column => csvEscape(row[column.key])).join(",")).join("\\n");
      return `${header}\\n${body}\\n`;
    }

    function downloadText(filename, content, mimeType = "text/plain;charset=utf-8") {
      const blob = new Blob([content], { type: mimeType });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.setTimeout(() => URL.revokeObjectURL(url), 0);
    }

    function currentScopeFileBase(suffix) {
      const label = state.district !== ALL_LABEL
        ? `${state.district}-${state.province}`
        : state.province !== ALL_LABEL
          ? state.province
          : "all-districts";
      return `${slugify(label)}-${suffix}`;
    }

    function buildMethodologyNote() {
      const meta = DASHBOARD_DATA.meta;
      const sections = [
        meta.status.headline,
        "",
        `Official inputs: ${meta.status.officialInputs}`,
        `Estimated outputs: ${meta.status.estimatedOutputs}`,
        `Seat method: ${meta.status.seatMethod}`,
        `Caution: ${meta.status.caution}`,
        "",
        "Methodology",
        ...meta.methodology.flatMap(item => [`- ${item.title}: ${item.body}`]),
        "",
        `Validation status: ${meta.validationStatus.toUpperCase()}`,
        `Generated at: ${formatDateTime(meta.generatedAt)}`,
        `Freshest tracked source: ${formatDateTime(meta.freshestSourceAt)}`,
        "",
        "Coverage notes",
        ...meta.coverageNotes.map(note => `- ${note}`),
      ];
      return sections.join("\\n");
    }

    function downloadCurrentViewCsv(kind) {
      const primaryCtx = currentView.primaryDistrictCtx;

      if (kind === "winners") {
        if (!primaryCtx || !primaryCtx.winners.length) return;
        downloadText(
          `${currentScopeFileBase("estimated-winners")}.csv`,
          buildCsv(
            [
              { key: "province", label: "province" },
              { key: "district", label: "district" },
              { key: "seatCount", label: "seat_count" },
              { key: "partyCode", label: "party_code" },
              { key: "partyName", label: "party_name" },
              { key: "candidateNumber", label: "candidate_number" },
              { key: "candidateName", label: "candidate_name" },
              { key: "candidateVote", label: "candidate_vote" },
              { key: "partyVote", label: "party_vote" },
              { key: "candidateVoteShareOfPartyTotal", label: "candidate_vote_share_of_party_total" },
            ],
            [...primaryCtx.winners]
              .sort((a, b) => b.candidateVote - a.candidateVote || a.candidateName.localeCompare(b.candidateName))
              .map(row => ({
                province: row.province,
                district: row.district,
                seatCount: row.seatCount,
                partyCode: row.partyCode,
                partyName: row.partyName,
                candidateNumber: row.candidateNumber,
                candidateName: row.candidateName,
                candidateVote: row.candidateVote,
                partyVote: row.partyVote,
                candidateVoteShareOfPartyTotal: row.candidateVoteShareOfPartyTotal,
              }))
          ),
          "text/csv;charset=utf-8"
        );
        return;
      }

      if (kind === "contenders") {
        if (!primaryCtx) return;
        const contenders = getTopContenders(primaryCtx, primaryCtx.candidates.length);
        downloadText(
          `${currentScopeFileBase("closest-contenders")}.csv`,
          buildCsv(
            [
              { key: "province", label: "province" },
              { key: "district", label: "district" },
              { key: "partyCode", label: "party_code" },
              { key: "candidateNumber", label: "candidate_number" },
              { key: "candidateName", label: "candidate_name" },
              { key: "candidateVote", label: "candidate_vote" },
              { key: "districtRank", label: "district_rank" },
              { key: "partyRank", label: "party_rank" },
              { key: "partySeats", label: "party_seats" },
              { key: "reason", label: "reason" },
            ],
            contenders.map(item => ({
              province: item.row.province,
              district: item.row.district,
              partyCode: item.row.partyCode,
              candidateNumber: item.row.candidateNumber,
              candidateName: item.row.candidateName,
              candidateVote: item.row.candidateVote,
              districtRank: primaryCtx.districtRankMap.get(candidateKey(item.row)) || "",
              partyRank: item.partyRank || "",
              partySeats: item.partySeats,
              reason: item.reason,
            }))
          ),
          "text/csv;charset=utf-8"
        );
        return;
      }

      if (kind === "candidates") {
        const rows = getSortedCandidateRows(currentView.candidateRows);
        if (!rows.length) return;
        downloadText(
          `${currentScopeFileBase("candidate-table")}.csv`,
          buildCsv(
            [
              { key: "province", label: "province" },
              { key: "district", label: "district" },
              { key: "partyCode", label: "party_code" },
              { key: "partyName", label: "party_name" },
              { key: "candidateNumber", label: "candidate_number" },
              { key: "candidateName", label: "candidate_name" },
              { key: "candidateVote", label: "candidate_vote" },
              { key: "candidateRank", label: "candidate_rank" },
              { key: "shareOfPartyCandidates", label: "share_of_party_candidate_votes" },
              { key: "shareOfTotalSupport", label: "share_of_total_slate_support" },
              { key: "estimatedWinner", label: "estimated_winner" },
            ],
            rows.map(row => {
              const derived = getCandidateDerivedMetrics(row);
              const ctx = districtIndex.get(districtKey(row.province, row.district));
              return {
                province: row.province,
                district: row.district,
                partyCode: row.partyCode,
                partyName: row.partyName,
                candidateNumber: row.candidateNumber,
                candidateName: row.candidateName,
                candidateVote: row.candidateVote,
                candidateRank: row.candidateRank,
                shareOfPartyCandidates: derived.shareOfPartyCandidates,
                shareOfTotalSupport: derived.shareOfTotalSupport,
                estimatedWinner: ctx ? ctx.winnerKeySet.has(candidateKey(row)) : false,
              };
            })
          ),
          "text/csv;charset=utf-8"
        );
        return;
      }

      if (kind === "parties") {
        if (!currentView.partyRowsFull.length) return;
        downloadText(
          `${currentScopeFileBase("party-summary")}.csv`,
          buildCsv(
            [
              { key: "partyCode", label: "party_code" },
              { key: "partyName", label: "party_name" },
              { key: "partyNumber", label: "party_number" },
              { key: "slates", label: "slates_in_scope" },
              { key: "partyVoteTotal", label: "party_vote_total" },
              { key: "candidateVoteTotal", label: "candidate_vote_total" },
              { key: "totalVotes", label: "total_support" },
              { key: "ratio", label: "party_vote_to_candidate_vote_ratio" },
              { key: "partyShare", label: "party_vote_share_of_total_support" },
              { key: "seatsWon", label: "estimated_seats" },
              { key: "topCandidate", label: "top_visible_candidate" },
            ],
            currentView.partyRowsFull.map(row => ({
              partyCode: row.partyCode,
              partyName: row.partyName,
              partyNumber: row.partyNumber,
              slates: row.slates,
              partyVoteTotal: row.partyVoteTotal,
              candidateVoteTotal: row.candidateVoteTotal,
              totalVotes: row.totalVotes,
              ratio: row.ratio,
              partyShare: row.partyShare,
              seatsWon: row.seatsWon,
              topCandidate: row.topCandidate ? row.topCandidate.candidateName : "",
            }))
          ),
          "text/csv;charset=utf-8"
        );
      }
    }

    function updateDownloadButtons(primaryCtx) {
      elements.downloadWinnersBtn.disabled = !primaryCtx || !primaryCtx.winners.length;
      elements.downloadContendersBtn.disabled = !primaryCtx;
      elements.downloadCandidatesBtn.disabled = !currentView.candidateRows.length;
      elements.downloadCandidatesInlineBtn.disabled = !currentView.candidateRows.length;
      elements.downloadPartiesBtn.disabled = !currentView.partyRowsFull.length;
    }

    function renderHeroMeta() {
      const summary = DASHBOARD_DATA.summary;
      const pills = [
        `${summary.validation.checks.dpr_candidate_rows} candidate rows`,
        `${summary.validation.checks.total_dapil_seats} total dapil seats`,
        `${summary.voteDynamics.party_slates} party slates`,
        `Median top-share ${summary.voteDynamics.median_top_candidate_vote_share}`,
        `Validation ${DASHBOARD_DATA.meta.validationStatus.toUpperCase()}`,
      ];
      elements.heroMeta.innerHTML = pills.map(item => `<span class="hero-pill">${escapeHtml(item)}</span>`).join("");
    }

    function renderNotes() {
      elements.notesList.innerHTML = DASHBOARD_DATA.notes.map(note => `<li>${escapeHtml(note)}</li>`).join("");
    }

    function renderTrustLayer(primaryCtx) {
      const meta = DASHBOARD_DATA.meta;
      const districtLabel = primaryCtx ? `${primaryCtx.district} — ${primaryCtx.province}` : "the current dashboard";
      const validationClass = meta.validationStatus === "pass" ? "validation-pass" : "validation-warn";
      elements.shareDistrictBtn.disabled = !primaryCtx;
      elements.statusSummary.innerHTML = `
        ${escapeHtml(meta.status.officialInputs)} ${escapeHtml(meta.status.estimatedOutputs)}
        <strong>${escapeHtml(districtLabel)}</strong> is shown with official vote inputs and analytical seat estimates.
      `;

      elements.statusMeta.innerHTML = `
        <div class="status-card">
          <h3>Official Inputs</h3>
          <p>${escapeHtml(meta.status.officialInputs)}</p>
        </div>
        <div class="status-card">
          <h3>Estimated Outputs</h3>
          <p>${escapeHtml(meta.status.estimatedOutputs)}</p>
        </div>
        <div class="status-card">
          <h3>Dashboard Build</h3>
          <p>Generated ${escapeHtml(formatDateTime(meta.generatedAt))}. Freshest source updated ${escapeHtml(formatDateTime(meta.freshestSourceAt))}.</p>
        </div>
        <div class="status-card">
          <h3>Known Limits</h3>
          <p>${escapeHtml(meta.status.caution)}</p>
        </div>
      `;

      elements.trustSummary.innerHTML = `
        <p><strong>Validation status:</strong> ${escapeHtml(meta.validationStatus.toUpperCase())}.</p>
        <p><strong>Seat method:</strong> ${escapeHtml(meta.status.seatMethod)}</p>
        <p><strong>Freshest source:</strong> ${escapeHtml(formatDateTime(meta.freshestSourceAt))}</p>
        <p><strong>Public reading note:</strong> ${primaryCtx ? `The district story for ${escapeHtml(primaryCtx.district)} is always district-wide, even if you narrow the party or candidate filters below.` : "Choose a district to unlock the public-facing explanation, winner list, and near-miss list."}</p>
      `;

      elements.sourceSummary.innerHTML = [
        `<span class="tag ${validationClass}"><span class="tag-dot"></span>Validation ${escapeHtml(meta.validationStatus.toUpperCase())}</span>`,
        `<span class="tag"><span class="tag-dot"></span>${escapeHtml(DASHBOARD_DATA.meta.sources.length.toString())} tracked source files</span>`,
        `<span class="tag"><span class="tag-dot"></span>${escapeHtml(formatDateTime(meta.generatedAt))}</span>`,
        ...meta.coverageNotes.slice(0, 2).map(note => `<span class="tag"><span class="tag-dot"></span>${escapeHtml(note)}</span>`),
      ].join("");
    }

    function openMethodologyDrawer() {
      const meta = DASHBOARD_DATA.meta;
      state.drawerType = "";
      state.drawerValue = "";
      updateDocumentTitle();
      syncUrl();
      openDrawer(
        "How This Works",
        "Methodology",
        `
          <section class="drawer-section">
            <h3>${escapeHtml(meta.status.headline)}</h3>
            <p class="small-note">${escapeHtml(meta.status.officialInputs)}</p>
            <p class="small-note">${escapeHtml(meta.status.estimatedOutputs)}</p>
            <p class="small-note">${escapeHtml(meta.status.caution)}</p>
          </section>
          ${meta.methodology.map(item => `
            <section class="drawer-section">
              <h3>${escapeHtml(item.title)}</h3>
              <p class="small-note">${escapeHtml(item.body)}</p>
            </section>
          `).join("")}
        `
      );
    }

    function openGlossaryDrawer() {
      const glossaryRows = DASHBOARD_DATA.meta.glossary.map(item => `
        <div class="trust-item">
          <strong>${escapeHtml(item.term)}</strong>
          <div class="small-note">${escapeHtml(item.definition)}</div>
        </div>
      `).join("");

      state.drawerType = "";
      state.drawerValue = "";
      updateDocumentTitle();
      syncUrl();
      openDrawer(
        "Public Guide",
        "Glossary",
        `
          <section class="drawer-section">
            <h3>Election Terms Used In This Dashboard</h3>
            <div class="trust-list">${glossaryRows}</div>
          </section>
        `
      );
    }

    function openSourcesDrawer() {
      const meta = DASHBOARD_DATA.meta;
      state.drawerType = "";
      state.drawerValue = "";
      updateDocumentTitle();
      syncUrl();
      openDrawer(
        "Data Provenance",
        "Sources And Freshness",
        `
          <section class="drawer-section">
            <h3>Build Metadata</h3>
            <p class="small-note">Dashboard generated ${escapeHtml(formatDateTime(meta.generatedAt))}. Freshest tracked source updated ${escapeHtml(formatDateTime(meta.freshestSourceAt))}.</p>
            <p class="small-note">Validation status: ${escapeHtml(meta.validationStatus.toUpperCase())}.</p>
          </section>
          <section class="drawer-section">
            <h3>Tracked Sources</h3>
            <div class="source-list">
              ${meta.sources.map(source => `
                <div class="source-item">
                  <strong>${escapeHtml(source.label)}</strong>
                  <div class="source-meta">
                    <div>Kind: ${escapeHtml(source.kind)}</div>
                    <div>Path: ${escapeHtml(source.path)}</div>
                    <div>Updated: ${escapeHtml(formatDateTime(source.updatedAt))}</div>
                    ${source.rowCount !== undefined ? `<div>Rows: ${escapeHtml(formatNumber(source.rowCount))}</div>` : ""}
                    <div>${escapeHtml(source.note)}</div>
                  </div>
                </div>
              `).join("")}
            </div>
          </section>
          <section class="drawer-section">
            <h3>Coverage Notes</h3>
            <div class="trust-list">
              ${meta.coverageNotes.map(note => `
                <div class="trust-item">
                  <div class="small-note">${escapeHtml(note)}</div>
                </div>
              `).join("")}
            </div>
          </section>
        `
      );
    }

    function buildShareUrl(mode) {
      const url = new URL(window.location.href);
      const params = new URLSearchParams();

      if (mode === "district") {
        if (state.province !== ALL_LABEL) params.set("province", state.province);
        if (state.district !== ALL_LABEL) params.set("district", state.district);
      } else if (mode === "candidate" && state.drawerType === "candidate" && state.drawerValue) {
        const row = candidateLookup.get(state.drawerValue);
        if (row) {
          params.set("province", row.province);
          params.set("district", row.district);
        }
        params.set("candidate", state.drawerValue);
      } else if (mode === "party" && state.drawerType === "party" && state.drawerValue) {
        if (state.province !== ALL_LABEL) params.set("province", state.province);
        if (state.district !== ALL_LABEL) params.set("district", state.district);
        params.set("partyDetail", state.drawerValue);
      } else {
        if (state.province !== ALL_LABEL) params.set("province", state.province);
        if (state.district !== ALL_LABEL) params.set("district", state.district);
        if (state.party !== ALL_LABEL) params.set("party", state.party);
        if (state.search) params.set("q", state.search);
        if (state.ratioMetric !== "partyShare") params.set("ratio", state.ratioMetric);
        if (state.topN !== 18) params.set("topN", String(state.topN));
        if (state.pageSize !== 25) params.set("pageSize", String(state.pageSize));
        if (state.candidatePage !== 1) params.set("page", String(state.candidatePage));
        if (state.candidateSortKey !== "candidateVote") params.set("sort", state.candidateSortKey);
        if (state.candidateSortDir !== "desc") params.set("dir", state.candidateSortDir);
        if (state.compareDistrict) {
          params.set("compareProvince", state.compareProvince);
          params.set("compareDistrict", state.compareDistrict);
        }
        if (state.drawerType === "candidate" && state.drawerValue) {
          params.set("candidate", state.drawerValue);
        } else if (state.drawerType === "party" && state.drawerValue) {
          params.set("partyDetail", state.drawerValue);
        }
      }

      url.search = params.toString();
      url.hash = "";
      return url.toString();
    }

    async function copyShareUrl(mode, button, defaultLabel) {
      const text = buildShareUrl(mode);
      try {
        await navigator.clipboard.writeText(text);
        flashButton(button, defaultLabel);
      } catch (error) {
        window.prompt("Copy this link", text);
        flashButton(button, defaultLabel, "Ready to copy");
      }
    }

    function renderStoryGuide(primaryCtx) {
      if (!primaryCtx) {
        elements.storyGuide.innerHTML = `
          <p>Start with the district finder at the top. This dashboard is designed to answer one public question first: what happened in my district?</p>
          <p>After choosing a district, read the summary, then check who won, who nearly won, and whether the district behaved more like a party-led contest or a candidate-led contest.</p>
          <p>The sidebar filters narrow the exploratory charts and the large candidate table below.</p>
        `;
        return;
      }

      elements.storyGuide.innerHTML = `
        <p><strong>${escapeHtml(primaryCtx.district)}</strong> is now the anchor. The district summary, winners, and contenders stay district-wide so the public story does not disappear when you narrow the charts.</p>
        <p>Use the party filter to zoom into one party, and use candidate search to find a person. The deep charts and table respond to those filters; the district story above does not.</p>
        <p>${state.compareDistrict ? "The comparison panel is active, so you can read this district against another district directly." : "Add a second district in the comparison finder if you want a side-by-side view."}</p>
      `;
    }

    function renderActiveTags() {
      const tags = [
        { label: "Province", value: state.province },
        { label: "District", value: state.district },
        { label: "Party", value: state.party },
        { label: "Search", value: state.search || "—" },
      ];

      if (state.compareDistrict) {
        tags.push({ label: "Compare", value: `${state.compareDistrict} — ${state.compareProvince}` });
      }

      elements.activeTags.innerHTML = tags.map(tag => `
        <span class="tag">
          <span class="tag-dot"></span>
          <strong>${escapeHtml(tag.label)}:</strong>&nbsp;${escapeHtml(tag.value)}
        </span>
      `).join("");
    }

    function renderMetrics(metrics) {
      const cards = [
        ["Candidate Rows", formatNumber(metrics.candidateRows), "Rows in the current exploratory scope"],
        ["Party Slates", formatNumber(metrics.slates), "Unique district-party slates"],
        ["Candidate Votes", formatNumber(metrics.candidateVotes), "Sum of visible candidate votes"],
        ["Party Votes", formatNumber(metrics.partyVotes), "Deduplicated party-only ballots"],
        ["Party/Candidate Ratio", formatDecimal(metrics.ratio, 3), "Party votes divided by candidate votes"],
        ["Party Vote Share", formatPercent(metrics.partyShare, 1), "Party-only votes as share of total support"],
        ["Estimated Seats", formatNumber(metrics.seatsWon), "Seats in the current scope"],
        ["Avg Top Share", formatPercent(metrics.avgTopShare, 1), "Average top-candidate dominance"],
      ];
      elements.metricGrid.innerHTML = cards.map(([title, value, note]) => `
        <div class="metric">
          <div class="metric-title">${escapeHtml(title)}</div>
          <div class="metric-value">${escapeHtml(value)}</div>
          <div class="metric-note">${escapeHtml(note)}</div>
        </div>
      `).join("");
    }

    function renderDistrictSummary(primaryCtx) {
      if (!primaryCtx) {
        const examples = getExampleDistrictRecords(3);
        elements.districtSummary.innerHTML = `
          <div class="empty-state">
            <strong>Start with your district.</strong><br>
            Pick a district above to unlock the public-facing summary, winners, contenders, and district comparisons.
            <div class="tag-row" style="justify-content:center; margin-top:14px;">
              ${examples.map(record => `<button class="btn-secondary" data-action="finder-district" data-record="${escapeHtml(record.display)}">Try ${escapeHtml(record.district)}</button>`).join("")}
            </div>
          </div>
        `;
        return;
      }

      const provinceSummary = provinceSummaryIndex.get(primaryCtx.province);
      const seatRows = [...primaryCtx.seats].filter(row => row.seatsWon > 0).sort((a, b) => b.seatsWon - a.seatsWon || b.totalVotes - a.totalVotes);
      const topContender = getTopContenders(primaryCtx, 1)[0] || null;
      const leadingParty = primaryCtx.leadingParty;
      const meta = DASHBOARD_DATA.meta;

      elements.districtSummary.innerHTML = `
        <div class="summary-shell">
          <div class="summary-hero">
            <h3>${escapeHtml(primaryCtx.district)}</h3>
            <div class="summary-copy">
              ${escapeHtml(primaryCtx.classification.summary)}
              ${leadingParty ? ` The largest party by total support was ${leadingParty.partyCode}, while party-only ballots made up ${formatPercent(primaryCtx.metrics.partyShare, 1)} of all visible support in the district.` : ""}
            </div>
            <div class="summary-badges">
              <span class="summary-badge"><strong>Province</strong> ${escapeHtml(primaryCtx.province)}</span>
              <span class="summary-badge"><strong>Seats</strong> ${escapeHtml(formatNumber(primaryCtx.seatCount))}</span>
              <span class="summary-badge"><strong>Total Support</strong> ${escapeHtml(formatNumber(primaryCtx.metrics.totalVotes))}</span>
              <span class="summary-badge"><strong>District Type</strong> ${escapeHtml(primaryCtx.classification.label)}</span>
              <span class="summary-badge"><strong>Winning Parties</strong> ${escapeHtml(formatNumber(primaryCtx.winningPartyCount))}</span>
            </div>
          </div>
          <div class="summary-note-grid">
            <div class="summary-note-card">
              <h4>What Drove The Result</h4>
              <p class="small-note">Party ballots accounted for <strong>${escapeHtml(formatPercent(primaryCtx.metrics.partyShare, 1))}</strong> of support here. The province-wide district average is <strong>${escapeHtml(formatPercent(provinceSummary?.avgPartyShare, 1))}</strong>.</p>
              <p class="small-note">The average top-candidate share in this district was <strong>${escapeHtml(formatPercent(primaryCtx.metrics.avgTopShare, 1))}</strong>, compared with <strong>${escapeHtml(formatPercent(provinceSummary?.avgTopShare, 1))}</strong> across the province.</p>
            </div>
            <div class="summary-note-card">
              <h4>Seat Distribution</h4>
              <p class="small-note">${seatRows.length ? seatRows.map(row => `${row.partyCode} ${row.seatsWon}`).join(", ") : "No estimated seat distribution available."}</p>
              <p class="small-note">${leadingParty ? `${leadingParty.partyCode} led the district with ${formatNumber(leadingParty.totalVotes)} total support.` : "No leading party available."}</p>
            </div>
            <div class="summary-note-card">
              <h4>Closest Pressure Point</h4>
              <p class="small-note">${topContender ? `<strong>${escapeHtml(topContender.row.candidateName)}</strong> was the strongest non-winning candidate with ${escapeHtml(formatNumber(topContender.row.candidateVote))} votes. ${escapeHtml(topContender.reason)}` : "No contender summary is available for this district."}</p>
              <p class="small-note">${state.party !== ALL_LABEL ? `Exploratory charts below are currently narrowed to ${escapeHtml(state.party)}, but this district summary remains district-wide.` : "Exploratory charts below are unfiltered at the party level unless you narrow them in the sidebar."}</p>
            </div>
            <div class="summary-note-card">
              <h4>Data And Method</h4>
              <p class="small-note">Built ${escapeHtml(formatDateTime(meta.generatedAt))}. Freshest tracked source updated ${escapeHtml(formatDateTime(meta.freshestSourceAt))}.</p>
              <p class="small-note">${escapeHtml(meta.status.officialInputs)} ${escapeHtml(meta.status.estimatedOutputs)}</p>
              <p class="small-note">${escapeHtml(meta.status.seatMethod)}</p>
              <p class="small-note"><strong>Validation:</strong> ${escapeHtml(meta.validationStatus.toUpperCase())}. ${escapeHtml(meta.coverageNotes[0] || "")}</p>
            </div>
          </div>
        </div>
      `;
    }

    function renderDistrictCompare(primaryCtx) {
      if (!primaryCtx) {
        elements.districtComparePanel.style.display = "none";
        return;
      }

      elements.districtComparePanel.style.display = "";
      const compareCtx = getCompareDistrictContext();

      if (!compareCtx) {
        elements.districtCompare.innerHTML = `
          <div class="empty-state">
            Add a second district in the comparison finder to compare seat count, total support, party-vote reliance, and candidate concentration.
          </div>
        `;
        return;
      }

      const compareCards = [primaryCtx, compareCtx].map(ctx => `
        <div class="compare-card">
          <h3>${escapeHtml(ctx.district)}</h3>
          <p class="small-note" style="margin-top:0;">${escapeHtml(ctx.province)} • ${escapeHtml(formatNumber(ctx.seatCount))} seats • ${escapeHtml(ctx.classification.label)}</p>
          <div class="metric-grid" style="grid-template-columns:repeat(2,minmax(0,1fr));">
            <div class="metric">
              <div class="metric-title">Total Support</div>
              <div class="metric-value" style="font-size:1.2rem;">${escapeHtml(formatNumber(ctx.metrics.totalVotes))}</div>
              <div class="metric-note">Party votes + candidate votes</div>
            </div>
            <div class="metric">
              <div class="metric-title">Winning Parties</div>
              <div class="metric-value" style="font-size:1.2rem;">${escapeHtml(formatNumber(ctx.winningPartyCount))}</div>
              <div class="metric-note">Parties with at least one seat</div>
            </div>
            <div class="metric">
              <div class="metric-title">Party Vote Share</div>
              <div class="metric-value" style="font-size:1.2rem;">${escapeHtml(formatPercent(ctx.metrics.partyShare, 1))}</div>
              <div class="metric-note">Share of all visible support</div>
            </div>
            <div class="metric">
              <div class="metric-title">Avg Top Share</div>
              <div class="metric-value" style="font-size:1.2rem;">${escapeHtml(formatPercent(ctx.metrics.avgTopShare, 1))}</div>
              <div class="metric-note">Average top-candidate dominance</div>
            </div>
          </div>
        </div>
      `).join("");

      const differences = [
        `Party-vote reliance differs by ${formatPercent(Math.abs((primaryCtx.metrics.partyShare || 0) - (compareCtx.metrics.partyShare || 0)), 1)}.`,
        `Top-candidate concentration differs by ${formatPercent(Math.abs((primaryCtx.metrics.avgTopShare || 0) - (compareCtx.metrics.avgTopShare || 0)), 1)}.`,
        `${primaryCtx.leadingParty ? primaryCtx.leadingParty.partyCode : "No party"} leads ${escapeHtml(primaryCtx.district)}, while ${compareCtx.leadingParty ? compareCtx.leadingParty.partyCode : "no party"} leads ${escapeHtml(compareCtx.district)}.`,
      ];

      elements.districtCompare.innerHTML = `
        <div class="compare-shell">
          <div class="compare-grid">${compareCards}</div>
          <div class="tag-row">
            ${differences.map(text => `<span class="tag"><span class="tag-dot"></span>${text}</span>`).join("")}
          </div>
        </div>
      `;
    }

    function renderDistrictWinners(primaryCtx) {
      if (!primaryCtx) {
        elements.districtWinners.innerHTML = `<div class="empty-state">Pick a district to see estimated winners.</div>`;
        return;
      }

      if (!primaryCtx.winners.length) {
        elements.districtWinners.innerHTML = `<div class="empty-state">No estimated winners are available for this district.</div>`;
        return;
      }

      const rows = [...primaryCtx.winners].sort((a, b) => b.candidateVote - a.candidateVote || a.candidateName.localeCompare(b.candidateName));
      elements.districtWinners.innerHTML = `
        <div class="summary-note-grid">
          ${rows.map(row => `
            <div class="summary-note-card">
              <h4>
                <button class="link-button" data-action="candidate" data-key="${escapeHtml(candidateKey(row))}">
                  ${escapeHtml(row.candidateName)}
                </button>
              </h4>
              <p class="small-note" style="margin-top:0;">${escapeHtml(row.partyCode)} • ${escapeHtml(formatNumber(row.candidateVote))} votes • ${escapeHtml(formatPercent(row.candidateVoteShareOfPartyTotal, 1))} of party candidate votes</p>
              <p class="small-note">Party votes: ${escapeHtml(formatNumber(row.partyVote))}. Estimated seat winner in ${escapeHtml(primaryCtx.district)}.</p>
            </div>
          `).join("")}
        </div>
      `;
    }

    function renderDistrictContenders(primaryCtx) {
      if (!primaryCtx) {
        elements.districtContenders.innerHTML = `<div class="empty-state">Pick a district to see the strongest non-winning candidates.</div>`;
        return;
      }

      const contenders = getTopContenders(primaryCtx, 8);
      if (!contenders.length) {
        elements.districtContenders.innerHTML = `<div class="empty-state">No contender list is available for this district.</div>`;
        return;
      }

      elements.districtContenders.innerHTML = `
        <div class="summary-note-grid">
          ${contenders.map(item => `
            <div class="summary-note-card">
              <h4>
                <button class="link-button" data-action="candidate" data-key="${escapeHtml(candidateKey(item.row))}">
                  ${escapeHtml(item.row.candidateName)}
                </button>
              </h4>
              <p class="small-note" style="margin-top:0;">${escapeHtml(item.row.partyCode)} • ${escapeHtml(formatNumber(item.row.candidateVote))} votes • district rank #${escapeHtml(formatNumber(primaryCtx.districtRankMap.get(candidateKey(item.row)) || 0))}</p>
              <p class="small-note">${escapeHtml(item.reason)}</p>
            </div>
          `).join("")}
        </div>
      `;
    }

    function renderCandidateLeaderboard(candidateRows) {
      if (!hasExplorationScope() && !currentView.primaryDistrictCtx) {
        elements.candidateLeaderboard.innerHTML = `<div class="empty-state">Pick a district, province, party, or candidate name to populate the leaderboard.</div>`;
        return;
      }
      if (!candidateRows.length) {
        elements.candidateLeaderboard.innerHTML = `<div class="empty-state">No candidates match the current scope.</div>`;
        return;
      }

      const rows = [...candidateRows]
        .sort((a, b) => b.candidateVote - a.candidateVote || a.candidateName.localeCompare(b.candidateName))
        .slice(0, state.topN);

      const maxValue = Math.max(...rows.map(row => row.candidateVote), 1);
      elements.candidateLeaderboard.innerHTML = `
        <div class="bar-list">
          ${rows.map(row => `
            <div class="bar-row">
              <div class="bar-label">
                <strong>
                  <button class="link-button" data-action="candidate" data-key="${escapeHtml(candidateKey(row))}">
                    ${escapeHtml(row.candidateName)}
                  </button>
                </strong>
                <span>${escapeHtml(row.partyCode)} • ${escapeHtml(row.district)}</span>
              </div>
              <div class="bar-track">
                <div class="bar-fill" style="width:${(row.candidateVote / maxValue) * 100}%; background:${escapeHtml(partyColor(row.partyCode))};"></div>
              </div>
              <div class="bar-value">${escapeHtml(formatNumber(row.candidateVote))}</div>
            </div>
          `).join("")}
        </div>
      `;
    }

    function renderPartyRatioBars(partyRows) {
      const metricLabel = {
        partyShare: "Party vote share of total support",
        ratio: "Party vote / candidate vote ratio",
        seats: "Estimated seats in current scope",
      }[state.ratioMetric];

      if (!hasExplorationScope() && !currentView.primaryDistrictCtx) {
        elements.partyRatioBars.innerHTML = `<p class="small-note" style="margin-top:0; margin-bottom:12px;">Current metric: ${escapeHtml(metricLabel)}</p><div class="empty-state">Choose a district or province first. The public dashboard starts locally, then opens deeper party-ratio analysis.</div>`;
        return;
      }

      if (!partyRows.length) {
        elements.partyRatioBars.innerHTML = `<p class="small-note" style="margin-top:0; margin-bottom:12px;">Current metric: ${escapeHtml(metricLabel)}</p><div class="empty-state">No party data available for the current scope.</div>`;
        return;
      }

      const rows = [...partyRows]
        .map(row => ({
          source: row,
          label: row.partyCode,
          subtitle: `${row.slates} slates • ${formatNumber(row.totalVotes)} total support`,
          metricValue: state.ratioMetric === "partyShare" ? (row.partyShare || 0) : state.ratioMetric === "ratio" ? (row.ratio || 0) : row.seatsWon,
          color: partyColor(row.partyCode),
        }))
        .sort((a, b) => b.metricValue - a.metricValue);

      const maxValue = Math.max(...rows.map(row => row.metricValue), 1);
      elements.partyRatioBars.innerHTML = `
        <p class="small-note" style="margin-top:0; margin-bottom:12px;">Current metric: ${escapeHtml(metricLabel)}</p>
        <div class="bar-list">
          ${rows.map(row => `
            <div class="bar-row">
              <div class="bar-label">
                <strong>
                  <button class="link-button" data-action="party" data-party="${escapeHtml(row.source.partyCode)}">
                    ${escapeHtml(row.label)}
                  </button>
                </strong>
                <span>${escapeHtml(row.subtitle)}</span>
              </div>
              <div class="bar-track">
                <div class="bar-fill" style="width:${(row.metricValue / maxValue) * 100}%; background:${escapeHtml(row.color)};"></div>
              </div>
              <div class="bar-value">${
                state.ratioMetric === "partyShare"
                  ? escapeHtml(formatPercent(row.metricValue, 1))
                  : state.ratioMetric === "ratio"
                    ? escapeHtml(formatDecimal(row.metricValue, 3))
                    : escapeHtml(formatNumber(row.metricValue))
              }</div>
            </div>
          `).join("")}
        </div>
      `;
    }

    function renderScopeHighlights(metrics, partyRows, scopedSlates, primaryCtx) {
      if (primaryCtx) {
        const provinceSummary = provinceSummaryIndex.get(primaryCtx.province);
        elements.scopeHighlights.innerHTML = `
          <div class="split-3">
            <div class="metric">
              <div class="metric-title">Party Vote Share vs Province</div>
              <div class="metric-value" style="font-size:1.2rem;">${escapeHtml(formatPercent(primaryCtx.metrics.partyShare, 1))}</div>
              <div class="metric-note">${escapeHtml(formatPercentDelta(primaryCtx.metrics.partyShare, provinceSummary?.avgPartyShare, 1))} against province district average</div>
            </div>
            <div class="metric">
              <div class="metric-title">Top Candidate Share vs Province</div>
              <div class="metric-value" style="font-size:1.2rem;">${escapeHtml(formatPercent(primaryCtx.metrics.avgTopShare, 1))}</div>
              <div class="metric-note">${escapeHtml(formatPercentDelta(primaryCtx.metrics.avgTopShare, provinceSummary?.avgTopShare, 1))} against province district average</div>
            </div>
            <div class="metric">
              <div class="metric-title">Winning Parties vs Province</div>
              <div class="metric-value" style="font-size:1.2rem;">${escapeHtml(formatNumber(primaryCtx.winningPartyCount))}</div>
              <div class="metric-note">${primaryCtx.winningPartyCount >= (provinceSummary?.avgWinningPartyCount || 0) ? "More fragmented winner spread than province average" : "More concentrated winner spread than province average"}</div>
            </div>
          </div>
          <div class="tag-row">
            <span class="tag"><span class="tag-dot"></span>${escapeHtml(primaryCtx.district)} has ${escapeHtml(formatNumber(primaryCtx.metrics.totalVotes))} total visible support.</span>
            <span class="tag"><span class="tag-dot"></span>Province district average total support: ${escapeHtml(formatNumber(Math.round(provinceSummary?.avgTotalVotes || 0)))}.</span>
            <span class="tag"><span class="tag-dot"></span>${escapeHtml(primaryCtx.classification.label)} district based on party-vote share and top-candidate concentration.</span>
          </div>
        `;
        return;
      }

      if (!hasExplorationScope()) {
        elements.scopeHighlights.innerHTML = `<div class="empty-state">The district summary above is the main public entry point. If you want broader exploration, pick a province or use candidate search.</div>`;
        return;
      }

      if (!partyRows.length || !scopedSlates.length) {
        elements.scopeHighlights.innerHTML = `<div class="empty-state">Select a broader scope to see highlights.</div>`;
        return;
      }

      const topPartyByVotes = [...partyRows].sort((a, b) => b.totalVotes - a.totalVotes)[0];
      const topPartyByShare = [...partyRows].filter(row => row.partyShare !== null).sort((a, b) => (b.partyShare || 0) - (a.partyShare || 0))[0];
      const topSlate = [...scopedSlates].sort((a, b) => b.totalVotes - a.totalVotes)[0];
      const mostDominantSlate = [...scopedSlates].filter(row => row.topShare !== null).sort((a, b) => (b.topShare || 0) - (a.topShare || 0))[0];
      elements.scopeHighlights.innerHTML = `
        <div class="split-3">
          <div class="metric">
            <div class="metric-title">Largest Party In Scope</div>
            <div class="metric-value" style="font-size:1.35rem;">${escapeHtml(topPartyByVotes.partyCode)}</div>
            <div class="metric-note">${escapeHtml(formatNumber(topPartyByVotes.totalVotes))} total support</div>
          </div>
          <div class="metric">
            <div class="metric-title">Highest Party Vote Share</div>
            <div class="metric-value" style="font-size:1.35rem;">${escapeHtml(topPartyByShare.partyCode)}</div>
            <div class="metric-note">${escapeHtml(formatPercent(topPartyByShare.partyShare, 1))} of visible support</div>
          </div>
          <div class="metric">
            <div class="metric-title">Most Dominant Top Candidate</div>
            <div class="metric-value" style="font-size:1.18rem;">${escapeHtml(mostDominantSlate.topCandidateName)}</div>
            <div class="metric-note">${escapeHtml(mostDominantSlate.partyCode)} • ${escapeHtml(formatPercent(mostDominantSlate.topShare, 1))}</div>
          </div>
        </div>
        <div class="tag-row">
          <span class="tag"><span class="tag-dot"></span>Top slate: ${escapeHtml(topSlate.partyCode)} in ${escapeHtml(topSlate.district)} with ${escapeHtml(formatNumber(topSlate.totalVotes))} total votes</span>
          <span class="tag"><span class="tag-dot"></span>Average party vote share in scope: ${escapeHtml(formatPercent(metrics.avgPartyShare, 1))}</span>
          <span class="tag"><span class="tag-dot"></span>Average top-candidate share in scope: ${escapeHtml(formatPercent(metrics.avgTopShare, 1))}</span>
        </div>
      `;
    }

    function renderScatter(scopedSlates) {
      const svg = elements.scatterSvg;
      if (!hasExplorationScope() && !currentView.primaryDistrictCtx) {
        svg.innerHTML = `<text x="50%" y="50%" text-anchor="middle" fill="#5f6b76" font-size="16">Pick a district or province to draw the scatter</text>`;
        svg.setAttribute("aria-label", "Pick a district or province to draw the scatter.");
        elements.scatterSummary.textContent = "The scatter activates after you choose a district, province, party, or candidate search.";
        return;
      }
      if (!scopedSlates.length) {
        svg.innerHTML = `<text x="50%" y="50%" text-anchor="middle" fill="#5f6b76" font-size="16">No slates in current scope</text>`;
        svg.setAttribute("aria-label", "No slates in the current scope.");
        elements.scatterSummary.textContent = "No slates are available in the current scope.";
        return;
      }

      const width = 620;
      const height = 360;
      const margin = { top: 20, right: 20, bottom: 46, left: 52 };
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;
      const xScale = value => margin.left + value * innerWidth;
      const yScale = value => margin.top + (1 - value) * innerHeight;
      const ticks = [0, 0.25, 0.5, 0.75, 1];

      const grid = ticks.map(tick => `
        <line class="grid-line" x1="${xScale(tick)}" x2="${xScale(tick)}" y1="${margin.top}" y2="${height - margin.bottom}"></line>
        <line class="grid-line" x1="${margin.left}" x2="${width - margin.right}" y1="${yScale(tick)}" y2="${yScale(tick)}"></line>
        <text class="axis-label" x="${xScale(tick)}" y="${height - margin.bottom + 20}" text-anchor="middle">${Math.round(tick * 100)}%</text>
        <text class="axis-label" x="${margin.left - 12}" y="${yScale(tick) + 4}" text-anchor="end">${Math.round(tick * 100)}%</text>
      `).join("");

      const points = scopedSlates.map(row => {
        const cx = xScale(row.topShare || 0);
        const cy = yScale(row.partyShare || 0);
        const radius = 4 + Math.min(12, Math.sqrt(row.totalVotes) / 55);
        const payload = [
          `${row.partyCode} • ${row.district}`,
          `Top candidate: ${row.topCandidateName}`,
          `Top-share: ${formatPercent(row.topShare, 1)}`,
          `Party vote share: ${formatPercent(row.partyShare, 1)}`,
          `Party votes: ${formatNumber(row.partyVote)}`,
          `Candidate votes: ${formatNumber(row.candidateVoteTotal)}`,
        ].join(" | ");
        return `<circle class="point" data-tip="${escapeHtml(payload)}" cx="${cx}" cy="${cy}" r="${radius}" fill="${escapeHtml(partyColor(row.partyCode))}" stroke="rgba(255,255,255,.95)" stroke-width="1.4"></circle>`;
      }).join("");

      svg.innerHTML = `
        <line class="axis-line" x1="${margin.left}" x2="${width - margin.right}" y1="${height - margin.bottom}" y2="${height - margin.bottom}"></line>
        <line class="axis-line" x1="${margin.left}" x2="${margin.left}" y1="${margin.top}" y2="${height - margin.bottom}"></line>
        ${grid}
        ${points}
        <text class="axis-label" x="${width / 2}" y="${height - 10}" text-anchor="middle">Top candidate share of candidate votes</text>
        <text class="axis-label" x="18" y="${height / 2}" text-anchor="middle" transform="rotate(-90 18 ${height / 2})">Party vote share of total support</text>
      `;

      const topSlate = [...scopedSlates].sort((a, b) => b.totalVotes - a.totalVotes)[0];
      const topPartyShareSlate = [...scopedSlates].filter(row => row.partyShare !== null).sort((a, b) => (b.partyShare || 0) - (a.partyShare || 0))[0];
      const topCandidateShareSlate = [...scopedSlates].filter(row => row.topShare !== null).sort((a, b) => (b.topShare || 0) - (a.topShare || 0))[0];
      const scatterSummary = [
        `Largest visible slate: ${topSlate.partyCode} in ${topSlate.district} with ${formatNumber(topSlate.totalVotes)} total support.`,
        topPartyShareSlate ? `Highest party-vote share: ${topPartyShareSlate.partyCode} in ${topPartyShareSlate.district} at ${formatPercent(topPartyShareSlate.partyShare, 1)}.` : "",
        topCandidateShareSlate ? `Strongest top-candidate concentration: ${topCandidateShareSlate.topCandidateName} on ${topCandidateShareSlate.partyCode} in ${topCandidateShareSlate.district} at ${formatPercent(topCandidateShareSlate.topShare, 1)}.` : "",
      ].filter(Boolean).join(" ");
      elements.scatterSummary.textContent = scatterSummary;
      svg.setAttribute("aria-label", scatterSummary);

      svg.querySelectorAll(".point").forEach(point => {
        point.addEventListener("mouseenter", () => {
          elements.tooltip.style.display = "block";
          elements.tooltip.textContent = point.dataset.tip;
          elements.tooltip.setAttribute("aria-hidden", "false");
        });
        point.addEventListener("mousemove", event => {
          elements.tooltip.style.left = `${event.clientX + 14}px`;
          elements.tooltip.style.top = `${event.clientY + 14}px`;
        });
        point.addEventListener("mouseleave", () => {
          elements.tooltip.style.display = "none";
          elements.tooltip.setAttribute("aria-hidden", "true");
        });
      });
    }

    function renderPartyInspector(visiblePartyRows) {
      if (!hasExplorationScope() && !currentView.primaryDistrictCtx) {
        elements.partyInspector.innerHTML = `<div class="empty-state">Party cards appear after you select a district, province, party, or candidate search.</div>`;
        return;
      }
      if (!visiblePartyRows.length) {
        elements.partyInspector.innerHTML = `<div class="empty-state">No party cards available for the current scope.</div>`;
        return;
      }

      elements.partyInspector.innerHTML = visiblePartyRows.map(row => {
        const lookup = partyLookup[row.partyCode] || {};
        const candidateRows = row.candidates.slice(0, 8).map(candidate => {
          const derived = getCandidateDerivedMetrics(candidate);
          return `
            <tr>
              <td>
                <strong>
                  <button class="link-button" data-action="candidate" data-key="${escapeHtml(candidateKey(candidate))}">
                    ${escapeHtml(candidate.candidateName)}
                  </button>
                </strong>
                <br><span style="color:#5f6b76; font-size:.8rem;">${escapeHtml(candidate.district)}</span>
              </td>
              <td>${escapeHtml(formatNumber(candidate.candidateVote))}</td>
              <td>${escapeHtml(formatPercent(derived.shareOfPartyCandidates, 1))}</td>
              <td>${escapeHtml(formatPercent(derived.shareOfTotalSupport, 1))}</td>
            </tr>
          `;
        }).join("");

        return `
          <article class="party-card" data-action="party" data-party="${escapeHtml(row.partyCode)}" tabindex="0" role="button" aria-haspopup="dialog" aria-label="Open party details for ${escapeHtml(row.partyName)}" style="cursor:pointer;">
            <div class="party-head">
              ${lookup.logoPath ? `<img class="party-logo" src="${escapeHtml(lookup.logoPath)}" alt="${escapeHtml(row.partyName)} logo" />` : `<div class="party-logo"></div>`}
              <div class="party-title">
                <strong>${escapeHtml(row.partyName)}</strong>
                <span>${escapeHtml(row.partyCode)} • ${escapeHtml(formatNumber(row.slates))} slates in scope</span>
              </div>
            </div>
            <div class="party-body">
              <div class="party-meta">
                <div><label>Party Votes</label><strong>${escapeHtml(formatNumber(row.partyVoteTotal))}</strong></div>
                <div><label>Candidate Votes</label><strong>${escapeHtml(formatNumber(row.candidateVoteTotal))}</strong></div>
                <div><label>Party/Candidate Ratio</label><strong>${escapeHtml(formatDecimal(row.ratio, 3))}</strong></div>
                <div><label>Estimated Seats</label><strong>${escapeHtml(formatNumber(row.seatsWon))}</strong></div>
              </div>
              <div class="small-note" style="margin-bottom:10px;">
                ${row.topCandidate ? `Top visible candidate: <strong>${escapeHtml(row.topCandidate.candidateName)}</strong> with ${escapeHtml(formatNumber(row.topCandidate.candidateVote))} votes.` : "No visible candidates after search filter."}
              </div>
              <table class="mini-table">
                <thead>
                  <tr>
                    <th>Candidate</th>
                    <th>Votes</th>
                    <th>Share Of Party Candidates</th>
                    <th>Share Of Total Support</th>
                  </tr>
                </thead>
                <tbody>
                  ${candidateRows || `<tr><td colspan="4" style="color:#5f6b76;">No visible candidates after search filter.</td></tr>`}
                </tbody>
              </table>
            </div>
          </article>
        `;
      }).join("");
    }

    function getSortedCandidateRows(rows) {
      const direction = state.candidateSortDir === "asc" ? 1 : -1;
      return [...rows].sort((a, b) => {
        const derivedA = getCandidateDerivedMetrics(a);
        const derivedB = getCandidateDerivedMetrics(b);

        const values = {
          candidateName: [a.candidateName, b.candidateName, "text"],
          partyCode: [a.partyCode, b.partyCode, "text"],
          province: [a.province, b.province, "text"],
          district: [a.district, b.district, "text"],
          candidateVote: [a.candidateVote, b.candidateVote, "number"],
          candidateRank: [a.candidateRank, b.candidateRank, "number"],
          shareOfPartyCandidates: [derivedA.shareOfPartyCandidates || 0, derivedB.shareOfPartyCandidates || 0, "number"],
          shareOfTotalSupport: [derivedA.shareOfTotalSupport || 0, derivedB.shareOfTotalSupport || 0, "number"],
        };

        const [valueA, valueB, kind] = values[state.candidateSortKey] || values.candidateVote;
        let comparison = 0;
        if (kind === "text") {
          comparison = String(valueA).localeCompare(String(valueB));
        } else {
          comparison = Number(valueA) - Number(valueB);
        }

        if (comparison !== 0) return comparison * direction;
        return (b.candidateVote - a.candidateVote) || a.candidateName.localeCompare(b.candidateName);
      });
    }

    function sortIndicator(key) {
      if (state.candidateSortKey !== key) return "-";
      return state.candidateSortDir === "asc" ? "^" : "v";
    }

    function renderCandidateTable(scopeCandidates, candidateRows) {
      if (!hasExplorationScope() && !currentView.primaryDistrictCtx) {
        elements.candidateTableWrap.innerHTML = `<div class="empty-state">The large table stays hidden until you choose a district, province, party, or candidate search. This keeps the first-load experience focused on the local story.</div>`;
        elements.candidateTablePager.innerHTML = "";
        return;
      }
      if (!scopeCandidates.length) {
        elements.candidateTableWrap.innerHTML = `<div class="empty-state">No candidates in the current scope.</div>`;
        elements.candidateTablePager.innerHTML = "";
        return;
      }

      if (!candidateRows.length) {
        elements.candidateTableWrap.innerHTML = `<div class="empty-state">No candidates match the current search.</div>`;
        elements.candidateTablePager.innerHTML = "";
        return;
      }

      const sortedRows = getSortedCandidateRows(candidateRows);
      const totalPages = Math.max(1, Math.ceil(sortedRows.length / state.pageSize));
      state.candidatePage = clamp(state.candidatePage, 1, totalPages);

      const start = (state.candidatePage - 1) * state.pageSize;
      const rowsOnPage = sortedRows.slice(start, start + state.pageSize);

      const makeHeader = (label, key) => `
        <button class="sort-button" data-action="sort" data-sort-key="${escapeHtml(key)}">
          ${escapeHtml(label)} <span>${escapeHtml(sortIndicator(key))}</span>
        </button>
      `;

      elements.candidateTableWrap.innerHTML = `
        <table class="data-table">
          <caption class="sr-only">Candidate results in the current scope with sortable columns for candidate, party, district, votes, rank, and slate shares.</caption>
          <thead>
            <tr>
              <th aria-sort="${sortAria("candidateName")}">${makeHeader("Candidate", "candidateName")}</th>
              <th aria-sort="${sortAria("partyCode")}">${makeHeader("Party", "partyCode")}</th>
              <th aria-sort="${sortAria("province")}">${makeHeader("Province", "province")}</th>
              <th aria-sort="${sortAria("district")}">${makeHeader("District", "district")}</th>
              <th aria-sort="${sortAria("candidateVote")}">${makeHeader("Candidate Votes", "candidateVote")}</th>
              <th aria-sort="${sortAria("candidateRank")}">${makeHeader("Candidate Rank", "candidateRank")}</th>
              <th aria-sort="${sortAria("shareOfPartyCandidates")}">${makeHeader("Share Of Party Candidate Votes", "shareOfPartyCandidates")}</th>
              <th aria-sort="${sortAria("shareOfTotalSupport")}">${makeHeader("Share Of Total Slate Support", "shareOfTotalSupport")}</th>
            </tr>
          </thead>
          <tbody>
            ${rowsOnPage.map(row => {
              const derived = getCandidateDerivedMetrics(row);
              return `
                <tr>
                  <td>
                    <strong>
                      <button class="link-button" data-action="candidate" data-key="${escapeHtml(candidateKey(row))}">
                        ${escapeHtml(row.candidateName)}
                      </button>
                    </strong>
                    <br><span style="color:#5f6b76; font-size:.82rem;">No. ${escapeHtml(row.candidateNumber)}</span>
                  </td>
                  <td>${escapeHtml(row.partyCode)}</td>
                  <td>${escapeHtml(row.province)}</td>
                  <td>${escapeHtml(row.district)}</td>
                  <td>${escapeHtml(formatNumber(row.candidateVote))}</td>
                  <td>${escapeHtml(formatNumber(row.candidateRank))}</td>
                  <td>${escapeHtml(formatPercent(derived.shareOfPartyCandidates, 1))}</td>
                  <td>${escapeHtml(formatPercent(derived.shareOfTotalSupport, 1))}</td>
                </tr>
              `;
            }).join("")}
          </tbody>
        </table>
        <div class="mobile-candidate-list">
          ${rowsOnPage.map(row => {
            const derived = getCandidateDerivedMetrics(row);
            const ctx = districtIndex.get(districtKey(row.province, row.district));
            const isWinner = ctx ? ctx.winnerKeySet.has(candidateKey(row)) : false;
            return `
              <article class="mobile-candidate-card">
                <div class="mobile-candidate-head">
                  <div>
                    <strong>
                      <button class="link-button" data-action="candidate" data-key="${escapeHtml(candidateKey(row))}">
                        ${escapeHtml(row.candidateName)}
                      </button>
                    </strong>
                    <div class="small-note">No. ${escapeHtml(row.candidateNumber)} • ${escapeHtml(row.partyCode)} • ${escapeHtml(row.district)}</div>
                    <div class="small-note">${escapeHtml(row.province)}</div>
                  </div>
                  <span class="tag"><span class="tag-dot"></span>${isWinner ? "Estimated winner" : "Not in winner set"}</span>
                </div>
                <div class="mobile-candidate-grid">
                  <div class="mobile-candidate-metric">
                    <div class="metric-title">Candidate Votes</div>
                    <strong>${escapeHtml(formatNumber(row.candidateVote))}</strong>
                  </div>
                  <div class="mobile-candidate-metric">
                    <div class="metric-title">Candidate Rank</div>
                    <strong>${escapeHtml(formatNumber(row.candidateRank))}</strong>
                  </div>
                  <div class="mobile-candidate-metric">
                    <div class="metric-title">Share Of Party Candidate Votes</div>
                    <strong>${escapeHtml(formatPercent(derived.shareOfPartyCandidates, 1))}</strong>
                  </div>
                  <div class="mobile-candidate-metric">
                    <div class="metric-title">Share Of Total Slate Support</div>
                    <strong>${escapeHtml(formatPercent(derived.shareOfTotalSupport, 1))}</strong>
                  </div>
                </div>
              </article>
            `;
          }).join("")}
        </div>
      `;

      elements.candidateTablePager.innerHTML = `
        <div class="candidate-table-pager">
          <div>Showing ${escapeHtml(formatNumber(start + 1))}-${escapeHtml(formatNumber(start + rowsOnPage.length))} of ${escapeHtml(formatNumber(sortedRows.length))} visible candidates</div>
          <div class="pager-buttons">
            <button class="btn-secondary" data-action="page" data-page="prev" ${state.candidatePage === 1 ? "disabled" : ""}>Prev</button>
            <button class="btn-secondary" data-action="page" data-page="next" ${state.candidatePage === totalPages ? "disabled" : ""}>Next</button>
          </div>
          <div>Page ${escapeHtml(formatNumber(state.candidatePage))} of ${escapeHtml(formatNumber(totalPages))}</div>
        </div>
      `;
    }

    function openDrawer(kicker, title, bodyHtml) {
      lastFocusedElement = document.activeElement;
      elements.drawerKicker.textContent = kicker;
      elements.drawerTitle.textContent = title;
      elements.drawerBody.innerHTML = bodyHtml;
      elements.drawerOverlay.classList.add("open");
      elements.drawerOverlay.setAttribute("aria-hidden", "false");
      window.setTimeout(() => elements.drawerCloseBtn.focus(), 0);
    }

    function closeDrawer() {
      elements.drawerOverlay.classList.remove("open");
      elements.drawerOverlay.setAttribute("aria-hidden", "true");
      state.drawerType = "";
      state.drawerValue = "";
      updateDocumentTitle();
      syncUrl();
      if (lastFocusedElement && typeof lastFocusedElement.focus === "function") {
        lastFocusedElement.focus();
      }
    }

    function trapDrawerFocus(event) {
      if (!elements.drawerOverlay.classList.contains("open") || event.key !== "Tab") return;
      const focusable = [...elements.drawerOverlay.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')]
        .filter(node => !node.hasAttribute("disabled"));
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
        return;
      }
      if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    function openCandidateDrawer(key) {
      const row = candidateLookup.get(key);
      if (!row) return;

      const ctx = districtIndex.get(districtKey(row.province, row.district));
      if (!ctx) return;

      const partyRow = ctx.partyRowsFull.find(item => item.partyCode === row.partyCode) || null;
      const districtRank = ctx.districtRankMap.get(candidateKey(row)) || null;
      const partyRank = ctx.partyRankMap.get(`${row.partyCode}||${candidateKey(row)}`) || null;
      const isWinner = ctx.winnerKeySet.has(candidateKey(row));
      const partySeats = ctx.partySeatMap.get(row.partyCode) || 0;
      const peerRows = [...ctx.candidates]
        .filter(candidate => candidate.partyCode === row.partyCode)
        .sort((a, b) => b.candidateVote - a.candidateVote || a.candidateName.localeCompare(b.candidateName))
        .slice(0, 8);
      const derived = partyRow
        ? {
            shareOfPartyCandidates: partyRow.candidateVoteTotal ? row.candidateVote / partyRow.candidateVoteTotal : null,
            shareOfTotalSupport: partyRow.totalVotes ? row.candidateVote / partyRow.totalVotes : null,
          }
        : { shareOfPartyCandidates: null, shareOfTotalSupport: null };
      state.drawerType = "candidate";
      state.drawerValue = key;
      updateDocumentTitle();
      syncUrl();

      openDrawer(
        "Candidate Detail",
        row.candidateName,
        `
          <section class="drawer-section">
            <div class="metric-grid">
              <div class="metric">
                <div class="metric-title">Candidate Votes</div>
                <div class="metric-value" style="font-size:1.2rem;">${escapeHtml(formatNumber(row.candidateVote))}</div>
                <div class="metric-note">${escapeHtml(row.partyCode)} in ${escapeHtml(row.district)}</div>
              </div>
              <div class="metric">
                <div class="metric-title">District Rank</div>
                <div class="metric-value" style="font-size:1.2rem;">#${escapeHtml(formatNumber(districtRank || 0))}</div>
                <div class="metric-note">Among all candidates in the district</div>
              </div>
              <div class="metric">
                <div class="metric-title">Party Rank</div>
                <div class="metric-value" style="font-size:1.2rem;">#${escapeHtml(formatNumber(partyRank || 0))}</div>
                <div class="metric-note">Inside ${escapeHtml(row.partyCode)}</div>
              </div>
              <div class="metric">
                <div class="metric-title">Estimated Winner</div>
                <div class="metric-value" style="font-size:1.2rem;">${isWinner ? "Yes" : "No"}</div>
                <div class="metric-note">${isWinner ? "Part of the estimated winner set" : `Party won ${partySeats} ${pluralize(partySeats, "seat")} in this district`}</div>
              </div>
            </div>
          </section>
          <section class="drawer-section">
            <h3>How This Candidate Fits The Result</h3>
            <p class="small-note">${isWinner ? `${escapeHtml(row.candidateName)} is in the estimated winning set for ${escapeHtml(row.district)}.` : `${escapeHtml(row.candidateName)} did not make the estimated winner set for ${escapeHtml(row.district)}.`}</p>
            <p class="small-note">This candidate accounts for <strong>${escapeHtml(formatPercent(derived.shareOfPartyCandidates, 1))}</strong> of visible candidate votes inside ${escapeHtml(row.partyCode)}, and <strong>${escapeHtml(formatPercent(derived.shareOfTotalSupport, 1))}</strong> of the party's total support.</p>
            <div class="button-row">
              <button class="btn-secondary" data-action="share-candidate">Copy Candidate Link</button>
            </div>
          </section>
          <section class="drawer-section">
            <h3>Party Slate Context</h3>
            <p class="small-note">${partyRow ? `${escapeHtml(row.partyCode)} recorded ${escapeHtml(formatNumber(partyRow.partyVoteTotal))} party votes and ${escapeHtml(formatNumber(partyRow.candidateVoteTotal))} candidate votes in this district scope.` : "No party context available."}</p>
            <p class="small-note">${partySeats === 0 ? `${escapeHtml(row.partyCode)} did not win a seat here.` : `${escapeHtml(row.partyCode)} won ${partySeats} ${pluralize(partySeats, "seat")} here, so only its top ${partySeats} vote-getter${partySeats === 1 ? "" : "s"} were estimated to win.`}</p>
          </section>
          <section class="drawer-section">
            <h3>Top Candidates In ${escapeHtml(row.partyCode)}</h3>
            <table class="mini-table">
              <thead>
                <tr>
                  <th>Candidate</th>
                  <th>Votes</th>
                  <th>Party Rank</th>
                </tr>
              </thead>
              <tbody>
                ${peerRows.map(candidate => `
                  <tr>
                    <td>${candidateKey(candidate) === key ? `<strong>${escapeHtml(candidate.candidateName)}</strong>` : `<button class="link-button" data-action="candidate" data-key="${escapeHtml(candidateKey(candidate))}">${escapeHtml(candidate.candidateName)}</button>`}</td>
                    <td>${escapeHtml(formatNumber(candidate.candidateVote))}</td>
                    <td>#${escapeHtml(formatNumber(ctx.partyRankMap.get(`${candidate.partyCode}||${candidateKey(candidate)}`) || 0))}</td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </section>
        `
      );
    }

    function openPartyDrawer(code) {
      const row = currentView.partyRowsFullMap.get(code);
      if (!row) return;

      const scopedSlates = currentView.scopedSlates.filter(item => item.partyCode === code).sort((a, b) => b.totalVotes - a.totalVotes);
      const candidates = [...currentView.scopedCandidates]
        .filter(item => item.partyCode === code)
        .sort((a, b) => b.candidateVote - a.candidateVote || a.candidateName.localeCompare(b.candidateName))
        .slice(0, 12);
      state.drawerType = "party";
      state.drawerValue = code;
      updateDocumentTitle();
      syncUrl();

      openDrawer(
        "Party Detail",
        `${row.partyName} (${row.partyCode})`,
        `
          <section class="drawer-section">
            <div class="metric-grid">
              <div class="metric">
                <div class="metric-title">Party Votes</div>
                <div class="metric-value" style="font-size:1.2rem;">${escapeHtml(formatNumber(row.partyVoteTotal))}</div>
                <div class="metric-note">Party-only ballots in current scope</div>
              </div>
              <div class="metric">
                <div class="metric-title">Candidate Votes</div>
                <div class="metric-value" style="font-size:1.2rem;">${escapeHtml(formatNumber(row.candidateVoteTotal))}</div>
                <div class="metric-note">Sum of candidate votes in current scope</div>
              </div>
              <div class="metric">
                <div class="metric-title">Party/Candidate Ratio</div>
                <div class="metric-value" style="font-size:1.2rem;">${escapeHtml(formatDecimal(row.ratio, 3))}</div>
                <div class="metric-note">Party votes divided by candidate votes</div>
              </div>
              <div class="metric">
                <div class="metric-title">Estimated Seats</div>
                <div class="metric-value" style="font-size:1.2rem;">${escapeHtml(formatNumber(row.seatsWon))}</div>
                <div class="metric-note">Seats in current scope</div>
              </div>
            </div>
          </section>
          <section class="drawer-section">
            <h3>How This Party Performs In Scope</h3>
            <p class="small-note">${escapeHtml(row.partyCode)} accounts for <strong>${escapeHtml(formatPercent(row.partyShare, 1))}</strong> of its own visible support as party-only ballots. The party appears in <strong>${escapeHtml(formatNumber(row.slates))}</strong> slate${row.slates === 1 ? "" : "s"} in the current scope.</p>
            <p class="small-note">${row.topSlate ? `Its biggest visible slate is ${escapeHtml(row.topSlate.district)} with ${escapeHtml(formatNumber(row.topSlate.totalVotes))} total support.` : "No slate detail is available."}</p>
            <div class="button-row">
              <button class="btn-secondary" data-action="share-party">Copy Party Link</button>
            </div>
          </section>
          <section class="drawer-section">
            <h3>Top District Slates</h3>
            <table class="mini-table">
              <thead>
                <tr>
                  <th>District</th>
                  <th>Total Support</th>
                  <th>Party Share</th>
                </tr>
              </thead>
              <tbody>
                ${scopedSlates.slice(0, 8).map(item => `
                  <tr>
                    <td>${escapeHtml(item.district)}<br><span style="color:#5f6b76; font-size:.8rem;">${escapeHtml(item.province)}</span></td>
                    <td>${escapeHtml(formatNumber(item.totalVotes))}</td>
                    <td>${escapeHtml(formatPercent(item.partyShare, 1))}</td>
                  </tr>
                `).join("") || `<tr><td colspan="3" style="color:#5f6b76;">No district slates in current scope.</td></tr>`}
              </tbody>
            </table>
          </section>
          <section class="drawer-section">
            <h3>Top Candidates In Scope</h3>
            <table class="mini-table">
              <thead>
                <tr>
                  <th>Candidate</th>
                  <th>Votes</th>
                  <th>District</th>
                </tr>
              </thead>
              <tbody>
                ${candidates.map(candidate => `
                  <tr>
                    <td><button class="link-button" data-action="candidate" data-key="${escapeHtml(candidateKey(candidate))}">${escapeHtml(candidate.candidateName)}</button></td>
                    <td>${escapeHtml(formatNumber(candidate.candidateVote))}</td>
                    <td>${escapeHtml(candidate.district)}</td>
                  </tr>
                `).join("") || `<tr><td colspan="3" style="color:#5f6b76;">No candidates available in current scope.</td></tr>`}
              </tbody>
            </table>
          </section>
        `
      );
    }

    function refreshDashboard() {
      updateFilterOptions();
      applyStateToInputs();
      renderFinderAssist();

      const scopedCandidates = getScopedCandidates();
      const scopedSlates = getScopedSlates();
      const scopedSeats = getScopedSeats();
      const candidateRows = getCandidateQueryRows(scopedCandidates);
      const partyRowsFull = aggregateByParty(scopedCandidates, scopedSlates, scopedSeats, scopedCandidates);
      const partyRowsVisible = aggregateByParty(scopedCandidates, scopedSlates, scopedSeats, state.search ? candidateRows : scopedCandidates);
      const metrics = computeMetrics(scopedCandidates, scopedSlates, scopedSeats);
      const primaryCtx = getPrimaryDistrictContext();

      currentView = {
        scopedCandidates,
        candidateRows,
        scopedSlates,
        scopedSeats,
        metrics,
        partyRowsFull,
        partyRowsVisible,
        partyRowsFullMap: new Map(partyRowsFull.map(row => [row.partyCode, row])),
        primaryDistrictCtx: primaryCtx,
      };

      renderTrustLayer(primaryCtx);
      updateDownloadButtons(primaryCtx);
      renderActiveTags();
      renderStoryGuide(primaryCtx);
      renderDistrictSummary(primaryCtx);
      renderDistrictCompare(primaryCtx);
      renderMetrics(metrics);
      renderDistrictWinners(primaryCtx);
      renderDistrictContenders(primaryCtx);
      renderCandidateLeaderboard(candidateRows);
      renderPartyRatioBars(partyRowsFull);
      renderScopeHighlights(metrics, partyRowsFull, scopedSlates, primaryCtx);
      renderScatter(scopedSlates);
      renderPartyInspector(partyRowsVisible);
      renderCandidateTable(scopedCandidates, candidateRows);
      if (state.drawerType === "candidate" && state.drawerValue && candidateLookup.has(state.drawerValue)) {
        openCandidateDrawer(state.drawerValue);
        return;
      }
      if (state.drawerType === "party" && state.drawerValue && currentView.partyRowsFullMap.has(state.drawerValue)) {
        openPartyDrawer(state.drawerValue);
        return;
      }
      updateDocumentTitle();
      syncUrl();
    }

    function applyDistrictRecord(record, mode, options = {}) {
      if (!record) return;
      window.clearTimeout(candidateSearchDebounce);

      if (mode === "compare") {
        if (record.province === state.province && record.district === state.district) {
          state.compareProvince = "";
          state.compareDistrict = "";
        } else {
          state.compareProvince = record.province;
          state.compareDistrict = record.district;
        }
        refreshDashboard();
        return;
      }

      state.province = record.province;
      state.district = record.district;
      state.party = ALL_LABEL;
      state.search = Object.prototype.hasOwnProperty.call(options, "search") ? options.search : "";
      state.candidatePage = 1;
      if (options.openCandidateKey) {
        state.drawerType = "candidate";
        state.drawerValue = options.openCandidateKey;
      } else if (!options.keepDrawer) {
        state.drawerType = "";
        state.drawerValue = "";
      }
      if (state.compareProvince === record.province && state.compareDistrict === record.district) {
        state.compareProvince = "";
        state.compareDistrict = "";
      }
      rememberRecentDistrict(record);
      refreshDashboard();
    }

    function applyFinderValue(value, mode) {
      const record = findDistrictRecord(value);
      if (!record) return;
      applyDistrictRecord(record, mode);
    }

    function resetDashboard() {
      window.clearTimeout(candidateSearchDebounce);
      state.province = ALL_LABEL;
      state.district = ALL_LABEL;
      state.party = ALL_LABEL;
      state.search = "";
      state.topN = 18;
      state.ratioMetric = "partyShare";
      state.compareProvince = "";
      state.compareDistrict = "";
      state.pageSize = 25;
      state.candidatePage = 1;
      state.candidateSortKey = "candidateVote";
      state.candidateSortDir = "desc";
      elements.districtFinderInput.value = "";
      elements.compareFinderInput.value = "";
      closeDrawer();
      refreshDashboard();
    }

    elements.applyScopeBtn.addEventListener("click", () => {
      state.province = elements.provinceSelect.value;
      state.district = elements.districtSelect.value;
      state.party = elements.partySelect.value;
      state.search = elements.candidateSearch.value.trim();
      state.ratioMetric = elements.ratioMetric.value;
      state.pageSize = Number(elements.pageSizeSelect.value);
      state.topN = Number(elements.topNRange.value);
      state.candidatePage = 1;
      refreshDashboard();
    });

    elements.provinceSelect.addEventListener("change", () => {
      state.province = elements.provinceSelect.value;
      state.district = ALL_LABEL;
      state.party = ALL_LABEL;
      state.candidatePage = 1;
      refreshDashboard();
    });

    elements.districtSelect.addEventListener("change", () => {
      state.district = elements.districtSelect.value;
      state.party = ALL_LABEL;
      state.candidatePage = 1;
      refreshDashboard();
    });

    elements.partySelect.addEventListener("change", () => {
      state.party = elements.partySelect.value;
      state.candidatePage = 1;
      refreshDashboard();
    });

    elements.candidateSearch.addEventListener("input", () => {
      window.clearTimeout(candidateSearchDebounce);
      candidateSearchDebounce = window.setTimeout(() => {
        state.search = elements.candidateSearch.value.trim();
        state.candidatePage = 1;
        refreshDashboard();
      }, 120);
    });

    elements.ratioMetric.addEventListener("change", () => {
      state.ratioMetric = elements.ratioMetric.value;
      refreshDashboard();
    });

    elements.topNRange.addEventListener("input", () => {
      state.topN = Number(elements.topNRange.value);
      elements.topNValue.textContent = elements.topNRange.value;
      refreshDashboard();
    });

    elements.pageSizeSelect.addEventListener("change", () => {
      state.pageSize = Number(elements.pageSizeSelect.value);
      state.candidatePage = 1;
      refreshDashboard();
    });

    elements.districtFinderBtn.addEventListener("click", () => {
      applyFinderValue(elements.districtFinderInput.value, "primary");
      if (elements.compareFinderInput.value.trim()) {
        applyFinderValue(elements.compareFinderInput.value, "compare");
      }
    });

    elements.districtFinderInput.addEventListener("keydown", event => {
      if (event.key === "Enter") {
        event.preventDefault();
        applyFinderValue(elements.districtFinderInput.value, "primary");
      }
    });
    elements.districtFinderInput.addEventListener("input", renderFinderAssist);

    elements.compareFinderInput.addEventListener("keydown", event => {
      if (event.key === "Enter") {
        event.preventDefault();
        applyFinderValue(elements.compareFinderInput.value, "compare");
      }
    });

    elements.clearCompareBtn.addEventListener("click", () => {
      state.compareProvince = "";
      state.compareDistrict = "";
      refreshDashboard();
    });

    elements.shareViewBtn.addEventListener("click", () => {
      copyShareUrl("view", elements.shareViewBtn, "Copy View Link");
    });
    elements.shareDistrictBtn.addEventListener("click", () => {
      copyShareUrl("district", elements.shareDistrictBtn, "Copy District Link");
    });
    elements.downloadMethodBtn.addEventListener("click", () => {
      downloadText("dpr-dashboard-method-note.txt", buildMethodologyNote());
      flashButton(elements.downloadMethodBtn, "Download Method Note", "Downloaded");
    });
    elements.methodologyBtn.addEventListener("click", openMethodologyDrawer);
    elements.glossaryBtn.addEventListener("click", openGlossaryDrawer);
    elements.sourcesBtn.addEventListener("click", openSourcesDrawer);
    elements.downloadWinnersBtn.addEventListener("click", () => {
      downloadCurrentViewCsv("winners");
      flashButton(elements.downloadWinnersBtn, "Download Winners CSV", "Downloaded");
    });
    elements.downloadContendersBtn.addEventListener("click", () => {
      downloadCurrentViewCsv("contenders");
      flashButton(elements.downloadContendersBtn, "Download Contenders CSV", "Downloaded");
    });
    elements.downloadCandidatesBtn.addEventListener("click", () => {
      downloadCurrentViewCsv("candidates");
      flashButton(elements.downloadCandidatesBtn, "Download Candidate Table CSV", "Downloaded");
    });
    elements.downloadCandidatesInlineBtn.addEventListener("click", () => {
      downloadCurrentViewCsv("candidates");
      flashButton(elements.downloadCandidatesInlineBtn, "Download Visible Candidate Table", "Downloaded");
    });
    elements.downloadPartiesBtn.addEventListener("click", () => {
      downloadCurrentViewCsv("parties");
      flashButton(elements.downloadPartiesBtn, "Download Party Summary CSV", "Downloaded");
    });
    elements.resetBtn.addEventListener("click", resetDashboard);

    elements.drawerBackdrop.addEventListener("click", closeDrawer);
    elements.drawerCloseBtn.addEventListener("click", closeDrawer);
    document.addEventListener("keydown", event => {
      trapDrawerFocus(event);
      if (event.key === "Escape") {
        closeDrawer();
        return;
      }

      const actionEl = event.target.closest("[data-action]");
      if (!actionEl) return;
      if (!["Enter", " "].includes(event.key)) return;

      const action = actionEl.dataset.action;
      if (action === "party") {
        event.preventDefault();
        openPartyDrawer(actionEl.dataset.party);
      }
    });

    document.addEventListener("click", event => {
      const actionEl = event.target.closest("[data-action]");
      if (!actionEl) return;

      const action = actionEl.dataset.action;
      if (action === "candidate") {
        event.preventDefault();
        openCandidateDrawer(actionEl.dataset.key);
        return;
      }
      if (action === "finder-district") {
        event.preventDefault();
        applyFinderValue(actionEl.dataset.record, "primary");
        return;
      }
      if (action === "finder-candidate") {
        event.preventDefault();
        const row = candidateLookup.get(actionEl.dataset.key);
        if (!row) return;
        applyDistrictRecord(
          {
            province: row.province,
            district: row.district,
            key: districtKey(row.province, row.district),
            display: districtDisplay(row),
          },
          "primary",
          { search: row.candidateName, openCandidateKey: actionEl.dataset.key }
        );
        return;
      }
      if (action === "party") {
        event.preventDefault();
        openPartyDrawer(actionEl.dataset.party);
        return;
      }
      if (action === "sort") {
        event.preventDefault();
        const nextKey = actionEl.dataset.sortKey;
        if (state.candidateSortKey === nextKey) {
          state.candidateSortDir = state.candidateSortDir === "asc" ? "desc" : "asc";
        } else {
          state.candidateSortKey = nextKey;
          state.candidateSortDir = ["candidateName", "partyCode", "province", "district"].includes(nextKey) ? "asc" : "desc";
        }
        state.candidatePage = 1;
        refreshDashboard();
        return;
      }
      if (action === "page") {
        event.preventDefault();
        state.candidatePage += actionEl.dataset.page === "next" ? 1 : -1;
        refreshDashboard();
        return;
      }
      if (action === "share-candidate") {
        event.preventDefault();
        copyShareUrl("candidate", actionEl, "Copy Candidate Link");
        return;
      }
      if (action === "share-party") {
        event.preventDefault();
        copyShareUrl("party", actionEl, "Copy Party Link");
      }
    });

    hydrateStateFromUrl();
    populateDistrictFinder();
    renderHeroMeta();
    renderNotes();
    refreshDashboard();
  </script>
</body>
</html>
"""
    return template.replace("__PAYLOAD__", safe_json(payload))


def main() -> None:
    payload = make_payload()
    html = build_html(payload)
    output_path = OUTPUT_DIR / "index.html"
    output_path.write_text(html, encoding="utf-8")
    (OUTPUT_DIR / "dashboard_metadata.json").write_text(
        json.dumps(payload["meta"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (OUTPUT_DIR / "README.txt").write_text(
        "Open index.html in a browser. This dashboard is generated by analysis/python/build_interactive_dashboard.py and now includes deep links, CSV exports, and public-facing onboarding helpers.\n",
        encoding="utf-8",
    )
    print("Wrote interactive dashboard to", output_path)


if __name__ == "__main__":
    main()
