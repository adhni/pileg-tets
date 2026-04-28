#!/usr/bin/env python3
"""Build a standalone interactive dashboard for DPR seat-adjustment scenarios."""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from common import PREPARED_DATA_DIR, PYTHON_OUTPUT_DIR, ROOT, ensure_dir, read_csv
from dapil_map import DAPIL_GEOJSON_PATH, DAPIL_LOOKUP_PATH, build_dapil_map_payload, normalize_district_name


OUTPUT_DIR = ensure_dir(PYTHON_OUTPUT_DIR / "pileg_dashboard")
PARLIAMENTARY_THRESHOLD = 0.04
BASE_FACTOR_KEY = "1"

FACTOR_DEFS = [
    {
        "value": 0.125,
        "shortLabel": "x8",
        "headline": "Multiply seats by 8",
        "description": "Every dapil seat count becomes ceiling(base seats / 0.125).",
    },
    {
        "value": 0.25,
        "shortLabel": "x4",
        "headline": "Multiply seats by 4",
        "description": "Every dapil seat count becomes ceiling(base seats / 0.25).",
    },
    {
        "value": 0.5,
        "shortLabel": "x2",
        "headline": "Multiply seats by 2",
        "description": "Every dapil seat count becomes ceiling(base seats / 0.5).",
    },
    {
        "value": 1.0,
        "shortLabel": "Base",
        "headline": "Status quo",
        "description": "Current dapil seat counts with no adjustment.",
    },
    {
        "value": 2.0,
        "shortLabel": "/2",
        "headline": "Divide seats by 2",
        "description": "Every dapil seat count becomes ceiling(base seats / 2).",
    },
    {
        "value": 4.0,
        "shortLabel": "/4",
        "headline": "Divide seats by 4",
        "description": "Every dapil seat count becomes ceiling(base seats / 4).",
    },
    {
        "value": 8.0,
        "shortLabel": "/8",
        "headline": "Divide seats by 8",
        "description": "Every dapil seat count becomes ceiling(base seats / 8).",
    },
]

LENSES = [
    {
        "key": "legal",
        "label": "Legal DPR Lens",
        "shortLabel": "Threshold",
        "description": "Applies the legal 4% national DPR parliamentary threshold before seats are allocated.",
    },
    {
        "key": "raw",
        "label": "All Parties Lens",
        "shortLabel": "All Parties",
        "description": "Allocates seats using every party in the vote table, without applying the DPR threshold.",
    },
]

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
}

METHODOLOGY = [
    {
        "title": "Repo Data Only",
        "body": (
            "National and dapil vote totals come from the prepared DPR slate table in this repo, and baseline seat counts come "
            "from the tracked dapil seat file. The Quarto note is used only as design inspiration for the scenario framing."
        ),
    },
    {
        "title": "Seat Adjustment Rule",
        "body": (
            "Each scenario changes seats with ceiling(base seats / factor). Factors below 1 expand the chamber, while factors "
            "above 1 shrink it."
        ),
    },
    {
        "title": "Seat Allocation Method",
        "body": (
            "After seat counts change, seats are reallocated using the same Sainte-Lague method already used in the Python DPR "
            "workflow. This keeps the scenario engine aligned with the repo's main seat model."
        ),
    },
    {
        "title": "Two Analytical Lenses",
        "body": (
            "The legal lens applies the 4% national DPR threshold before allocating seats. The raw lens keeps all parties in the "
            "allocation so you can see how seat inflation changes the opening for smaller parties."
        ),
    },
]


def to_int(value: str) -> int:
    return int(value)


def factor_key(value: float) -> str:
    return f"{value:g}"


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


def safe_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def allocate_sainte_lague(party_rows: list[dict[str, object]], seat_count: int) -> dict[str, int]:
    quotients: list[tuple[float, int, str]] = []
    for row in party_rows:
        total_votes = int(row["totalVotes"])
        if total_votes <= 0:
            continue
        for divisor in range(1, 2 * seat_count, 2):
            quotients.append((total_votes / divisor, int(row["partyNumber"]), str(row["partyCode"])))
    quotients.sort(key=lambda item: (-item[0], item[1], item[2]))
    winners = quotients[:seat_count]
    return dict(Counter(item[2] for item in winners))


def make_payload() -> dict:
    slates_path = PREPARED_DATA_DIR / "dpr_party_slates.csv"
    seats_path = PREPARED_DATA_DIR / "dapil_seats.csv"
    dapil_map_payload = build_dapil_map_payload()

    district_meta: dict[str, dict[str, object]] = {}
    for row in read_csv(seats_path):
        district_key = normalize_district_name(row["district"])
        district_meta[district_key] = {
            "districtKey": district_key,
            "label": row["district_label"],
            "province": row["province"],
            "baseSeats": to_int(row["seat_count"]),
            "totalVotes": 0,
            "partyRows": [],
            "seatByFactor": {},
        }

    party_rows_by_district: dict[str, list[dict[str, object]]] = defaultdict(list)
    national_votes_by_party: Counter[str] = Counter()
    parties_by_code: dict[str, dict[str, object]] = {}

    slate_rows = read_csv(slates_path)
    for row in slate_rows:
        district_key = normalize_district_name(row["district"])
        if district_key not in district_meta:
            raise KeyError(f"Missing seat metadata for district {row['district']}")
        record = {
            "districtKey": district_key,
            "province": row["province"],
            "district": row["district"],
            "partyCode": row["party_code"],
            "partyName": row["party_name"],
            "partyNumber": to_int(row["party_number"]),
            "partyVote": to_int(row["party_vote"]),
            "candidateVoteTotal": to_int(row["candidate_vote_total"]),
            "candidateCount": to_int(row["candidate_count"]),
            "totalVotes": to_int(row["total_votes"]),
            "topCandidateName": row["top_candidate_name"],
            "topCandidateVote": to_int(row["top_candidate_vote"]),
        }
        party_rows_by_district[district_key].append(record)
        district_meta[district_key]["totalVotes"] = int(district_meta[district_key]["totalVotes"]) + int(record["totalVotes"])
        national_votes_by_party[str(record["partyCode"])] += int(record["totalVotes"])
        parties_by_code.setdefault(
            str(record["partyCode"]),
            {
                "partyCode": str(record["partyCode"]),
                "partyName": str(record["partyName"]),
                "partyNumber": int(record["partyNumber"]),
                "color": PARTY_COLORS.get(str(record["partyCode"]), "#334155"),
            },
        )

    dashboard_map_districts = set(district_meta.keys())
    geometry_map_districts = {item["districtKey"] for item in dapil_map_payload["districts"]}
    missing_from_geometry = sorted(dashboard_map_districts - geometry_map_districts)
    missing_from_dashboard = sorted(geometry_map_districts - dashboard_map_districts)
    if missing_from_geometry or missing_from_dashboard:
        message_parts = []
        if missing_from_geometry:
            message_parts.append(f"missing from geometry: {', '.join(missing_from_geometry)}")
        if missing_from_dashboard:
            message_parts.append(f"missing from dashboard: {', '.join(missing_from_dashboard)}")
        raise ValueError(f"DAPIL map join mismatch: {'; '.join(message_parts)}")

    total_national_valid_votes = sum(national_votes_by_party.values())
    parties: list[dict[str, object]] = []
    qualified_party_codes: set[str] = set()
    for party in sorted(parties_by_code.values(), key=lambda item: (int(item["partyNumber"]), str(item["partyCode"]))):
        code = str(party["partyCode"])
        national_votes = int(national_votes_by_party[code])
        share = national_votes / total_national_valid_votes if total_national_valid_votes else 0.0
        passes_threshold = share >= PARLIAMENTARY_THRESHOLD
        if passes_threshold:
            qualified_party_codes.add(code)
        parties.append(
            {
                **party,
                "nationalVotes": national_votes,
                "nationalVoteShare": share,
                "passesThreshold": passes_threshold,
            }
        )

    party_meta_by_code = {str(item["partyCode"]): item for item in parties}

    for district_key, rows in party_rows_by_district.items():
        district_total_votes = int(district_meta[district_key]["totalVotes"])
        district_meta[district_key]["partyRows"] = sorted(
            [
                {
                    "partyCode": str(row["partyCode"]),
                    "partyName": str(row["partyName"]),
                    "partyNumber": int(row["partyNumber"]),
                    "color": PARTY_COLORS.get(str(row["partyCode"]), "#334155"),
                    "totalVotes": int(row["totalVotes"]),
                    "voteShare": int(row["totalVotes"]) / district_total_votes if district_total_votes else 0.0,
                    "partyVote": int(row["partyVote"]),
                    "partyVoteShareOfSlate": int(row["partyVote"]) / int(row["totalVotes"]) if int(row["totalVotes"]) else 0.0,
                    "candidateVoteTotal": int(row["candidateVoteTotal"]),
                    "candidateCount": int(row["candidateCount"]),
                    "topCandidateName": str(row["topCandidateName"]),
                    "topCandidateVote": int(row["topCandidateVote"]),
                }
                for row in rows
            ],
            key=lambda item: (-int(item["totalVotes"]), int(item["partyNumber"]), str(item["partyCode"])),
        )

    scenarios: dict[str, dict[str, dict[str, object]]] = {lens["key"]: {} for lens in LENSES}
    for factor in FACTOR_DEFS:
        factor["key"] = factor_key(float(factor["value"]))
        factor_total_seats = 0
        for meta in district_meta.values():
            adjusted = math.ceil(int(meta["baseSeats"]) / float(factor["value"]))
            meta["seatByFactor"][str(factor["key"])] = adjusted
            factor_total_seats += adjusted
        factor["totalSeats"] = factor_total_seats

        for lens in LENSES:
            lens_key = str(lens["key"])
            national_seats: Counter[str] = Counter()
            district_summaries: dict[str, dict[str, object]] = {}

            for district_key, meta in sorted(district_meta.items(), key=lambda item: str(item[1]["label"])):
                rows = party_rows_by_district[district_key]
                eligible_rows = (
                    rows
                    if lens_key == "raw"
                    else [row for row in rows if str(row["partyCode"]) in qualified_party_codes]
                )
                seat_count = int(meta["seatByFactor"][str(factor["key"])])
                allocation = allocate_sainte_lague(eligible_rows, seat_count)
                party_seat_rows = []
                for row in sorted(rows, key=lambda item: (int(item["partyNumber"]), str(item["partyCode"]))):
                    party_code = str(row["partyCode"])
                    seats_won = allocation.get(party_code, 0)
                    national_seats[party_code] += seats_won
                    party_seat_rows.append(
                        {
                            "partyCode": party_code,
                            "partyName": str(row["partyName"]),
                            "partyNumber": int(row["partyNumber"]),
                            "color": PARTY_COLORS.get(party_code, "#334155"),
                            "totalVotes": int(row["totalVotes"]),
                            "voteShare": int(row["totalVotes"]) / int(meta["totalVotes"]) if int(meta["totalVotes"]) else 0.0,
                            "partyVote": int(row["partyVote"]),
                            "candidateVoteTotal": int(row["candidateVoteTotal"]),
                            "seats": seats_won,
                            "seatShare": seats_won / seat_count if seat_count else 0.0,
                            "passesThreshold": bool(party_meta_by_code[party_code]["passesThreshold"]),
                        }
                    )

                ranked_seat_rows = sorted(
                    party_seat_rows,
                    key=lambda item: (-int(item["seats"]), -int(item["totalVotes"]), int(item["partyNumber"]), str(item["partyCode"])),
                )
                leading_party_code = ranked_seat_rows[0]["partyCode"] if ranked_seat_rows and int(ranked_seat_rows[0]["seats"]) > 0 else ""
                district_summaries[district_key] = {
                    "districtKey": district_key,
                    "label": meta["label"],
                    "province": meta["province"],
                    "seatCount": seat_count,
                    "partiesWithSeats": sum(1 for row in party_seat_rows if int(row["seats"]) > 0),
                    "leadingPartyCode": leading_party_code,
                    "partySeatRows": party_seat_rows,
                }

            national_parties = []
            for party in parties:
                party_code = str(party["partyCode"])
                seats_won = int(national_seats.get(party_code, 0))
                national_parties.append(
                    {
                        "partyCode": party_code,
                        "partyName": str(party["partyName"]),
                        "partyNumber": int(party["partyNumber"]),
                        "color": str(party["color"]),
                        "nationalVotes": int(party["nationalVotes"]),
                        "nationalVoteShare": float(party["nationalVoteShare"]),
                        "passesThreshold": bool(party["passesThreshold"]),
                        "seats": seats_won,
                        "seatShare": seats_won / int(factor["totalSeats"]) if int(factor["totalSeats"]) else 0.0,
                    }
                )
            national_parties.sort(
                key=lambda item: (-int(item["seats"]), -int(item["nationalVotes"]), int(item["partyNumber"]), str(item["partyCode"]))
            )

            scenarios[lens_key][str(factor["key"])] = {
                "factorKey": str(factor["key"]),
                "factorValue": float(factor["value"]),
                "factorTotalSeats": int(factor["totalSeats"]),
                "nationalParties": national_parties,
                "districts": district_summaries,
            }

    base_national_by_lens: dict[str, dict[str, dict[str, float]]] = {}
    base_district_party_by_lens: dict[str, dict[str, dict[str, dict[str, float]]]] = {}
    base_district_disproportionality_by_lens: dict[str, dict[str, float]] = {}
    for lens in LENSES:
        lens_key = str(lens["key"])
        base_scenario = scenarios[lens_key][BASE_FACTOR_KEY]
        base_national_by_lens[lens_key] = {
            str(row["partyCode"]): {
                "seats": int(row["seats"]),
                "seatShare": float(row["seatShare"]),
            }
            for row in base_scenario["nationalParties"]
        }
        base_district_party_by_lens[lens_key] = {
            district_key: {
                str(row["partyCode"]): {
                    "seats": int(row["seats"]),
                    "seatShare": float(row["seatShare"]),
                }
                for row in summary["partySeatRows"]
            }
            for district_key, summary in base_scenario["districts"].items()
        }
        base_district_disproportionality_by_lens[lens_key] = {
            district_key: 0.5 * sum(abs(float(row["seatShare"]) - float(row["voteShare"])) for row in summary["partySeatRows"])
            for district_key, summary in base_scenario["districts"].items()
        }

    for lens in LENSES:
        lens_key = str(lens["key"])
        for factor in FACTOR_DEFS:
            scenario = scenarios[lens_key][str(factor["key"])]
            for row in scenario["nationalParties"]:
                base_party = base_national_by_lens[lens_key].get(str(row["partyCode"]), {"seats": 0, "seatShare": 0.0})
                row["delta"] = int(row["seats"]) - int(base_party["seats"])
                row["seatShareDelta"] = float(row["seatShare"]) - float(base_party["seatShare"])
                row["seatPremium"] = float(row["seatShare"]) - float(row["nationalVoteShare"])

            scenario["nationalDisproportionality"] = 0.5 * sum(
                abs(float(row["seatPremium"])) for row in scenario["nationalParties"]
            )
            overrepresented = sorted(
                [row for row in scenario["nationalParties"] if float(row["seatPremium"]) > 0],
                key=lambda item: (-float(item["seatPremium"]), -int(item["seats"]), int(item["partyNumber"]), str(item["partyCode"])),
            )
            underrepresented = sorted(
                [row for row in scenario["nationalParties"] if float(row["seatPremium"]) < 0],
                key=lambda item: (float(item["seatPremium"]), -int(item["nationalVotes"]), int(item["partyNumber"]), str(item["partyCode"])),
            )
            scenario["topOverrepresented"] = [
                {
                    "partyCode": str(row["partyCode"]),
                    "partyName": str(row["partyName"]),
                    "seatPremium": float(row["seatPremium"]),
                    "seatShare": float(row["seatShare"]),
                    "voteShare": float(row["nationalVoteShare"]),
                }
                for row in overrepresented[:5]
            ]
            scenario["topUnderrepresented"] = [
                {
                    "partyCode": str(row["partyCode"]),
                    "partyName": str(row["partyName"]),
                    "seatPremium": float(row["seatPremium"]),
                    "seatShare": float(row["seatShare"]),
                    "voteShare": float(row["nationalVoteShare"]),
                }
                for row in underrepresented[:5]
            ]

            gainers = sorted(
                [row for row in scenario["nationalParties"] if int(row["delta"]) > 0],
                key=lambda item: (-int(item["delta"]), -int(item["seats"]), int(item["partyNumber"]), str(item["partyCode"])),
            )
            losers = sorted(
                [row for row in scenario["nationalParties"] if int(row["delta"]) < 0],
                key=lambda item: (int(item["delta"]), -int(item["seats"]), int(item["partyNumber"]), str(item["partyCode"])),
            )
            scenario["topGainers"] = [
                {
                    "partyCode": str(row["partyCode"]),
                    "partyName": str(row["partyName"]),
                    "delta": int(row["delta"]),
                    "seats": int(row["seats"]),
                }
                for row in gainers[:5]
            ]
            scenario["topLosers"] = [
                {
                    "partyCode": str(row["partyCode"]),
                    "partyName": str(row["partyName"]),
                    "delta": int(row["delta"]),
                    "seats": int(row["seats"]),
                }
                for row in losers[:5]
            ]

            for district_key, summary in scenario["districts"].items():
                summary["seatDelta"] = int(summary["seatCount"]) - int(district_meta[district_key]["baseSeats"])
                for row in summary["partySeatRows"]:
                    base_party = base_district_party_by_lens[lens_key][district_key].get(
                        str(row["partyCode"]),
                        {"seats": 0, "seatShare": 0.0},
                    )
                    base_seats = int(base_party["seats"])
                    row["baseSeats"] = base_seats
                    row["delta"] = int(row["seats"]) - base_seats
                    row["baseSeatShare"] = float(base_party["seatShare"])
                    row["seatShareDelta"] = float(row["seatShare"]) - float(base_party["seatShare"])
                    row["seatPremium"] = float(row["seatShare"]) - float(row["voteShare"])
                summary["districtDisproportionality"] = 0.5 * sum(
                    abs(float(row["seatPremium"])) for row in summary["partySeatRows"]
                )
                summary["districtDisproportionalityDelta"] = float(summary["districtDisproportionality"]) - float(
                    base_district_disproportionality_by_lens[lens_key][district_key]
                )
                positive = sorted(
                    [row for row in summary["partySeatRows"] if int(row["delta"]) > 0],
                    key=lambda item: (-int(item["delta"]), -int(item["totalVotes"]), int(item["partyNumber"]), str(item["partyCode"])),
                )
                negative = sorted(
                    [row for row in summary["partySeatRows"] if int(row["delta"]) < 0],
                    key=lambda item: (int(item["delta"]), -int(item["totalVotes"]), int(item["partyNumber"]), str(item["partyCode"])),
                )
                premium_positive = sorted(
                    [row for row in summary["partySeatRows"] if float(row["seatPremium"]) > 0],
                    key=lambda item: (-float(item["seatPremium"]), -int(item["seats"]), -int(item["totalVotes"]), int(item["partyNumber"]), str(item["partyCode"])),
                )
                premium_negative = sorted(
                    [row for row in summary["partySeatRows"] if float(row["seatPremium"]) < 0],
                    key=lambda item: (float(item["seatPremium"]), -int(item["totalVotes"]), int(item["partyNumber"]), str(item["partyCode"])),
                )
                summary["largestPositivePartyCode"] = str(positive[0]["partyCode"]) if positive else ""
                summary["largestNegativePartyCode"] = str(negative[0]["partyCode"]) if negative else ""
                summary["largestSeatPremiumPartyCode"] = str(premium_positive[0]["partyCode"]) if premium_positive else ""
                summary["largestSeatPenaltyPartyCode"] = str(premium_negative[0]["partyCode"]) if premium_negative else ""
                summary["leadingPartySeatPremium"] = next(
                    (float(row["seatPremium"]) for row in summary["partySeatRows"] if str(row["partyCode"]) == str(summary["leadingPartyCode"])),
                    0.0,
                )

    ordered_districts = sorted(district_meta.values(), key=lambda item: str(item["label"]))
    payload = {
        "meta": {
            "title": "Seat Adjustment Scenario Dashboard",
            "subtitle": "DPR 2024 seat-count scenarios using existing repo data",
            "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
            "baseTotalSeats": int(sum(int(item["baseSeats"]) for item in ordered_districts)),
            "thresholdPercent": PARLIAMENTARY_THRESHOLD * 100,
            "methodology": METHODOLOGY,
            "sources": [
                source_entry(
                    slates_path,
                    "Prepared DPR Party Slates",
                    "prepared_csv",
                    row_count=len(slate_rows),
                    note="Provides district-party total votes, party votes, and candidate totals.",
                ),
                source_entry(
                    seats_path,
                    "Prepared DPR Dapil Seats",
                    "prepared_csv",
                    row_count=len(read_csv(seats_path)),
                    note="Provides the baseline seat count used before factor adjustments.",
                ),
                source_entry(
                    DAPIL_GEOJSON_PATH,
                    "DAPIL Geometry",
                    "geojson",
                    row_count=len(dapil_map_payload["districts"]),
                    note="Used only to render the clickable dapil map.",
                ),
                source_entry(
                    DAPIL_LOOKUP_PATH,
                    "DAPIL Geometry Lookup",
                    "reference_csv",
                    row_count=len(read_csv(DAPIL_LOOKUP_PATH)),
                    note="Maps level-2 geometry rows to DPR dapil labels.",
                ),
            ],
        },
        "factors": FACTOR_DEFS,
        "lenses": LENSES,
        "parties": parties,
        "districts": ordered_districts,
        "map": dapil_map_payload,
        "scenarios": scenarios,
    }
    return payload


def build_html(payload: dict) -> str:
    template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Seat Adjustment Scenario Dashboard</title>
  <style>
    :root {
      --paper: #f4efe5;
      --paper-2: #fbf8f2;
      --ink: #1f2933;
      --muted: #5f6c78;
      --line: rgba(31, 41, 51, 0.12);
      --panel: rgba(255, 255, 255, 0.86);
      --panel-strong: rgba(255, 255, 255, 0.94);
      --accent: #0f766e;
      --accent-2: #b45309;
      --danger: #b91c1c;
      --shadow: 0 22px 50px rgba(31, 41, 51, 0.10);
      --radius: 24px;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--ink);
      font-family: "Avenir Next", "Trebuchet MS", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(15, 118, 110, 0.18), transparent 30%),
        radial-gradient(circle at top right, rgba(180, 83, 9, 0.16), transparent 28%),
        linear-gradient(180deg, #f8f3ea 0%, #fbf8f2 52%, #f2ebdf 100%);
      min-height: 100vh;
    }
    .skip-link {
      position: absolute;
      left: 16px;
      top: -48px;
      z-index: 50;
      padding: 10px 14px;
      border-radius: 999px;
      background: #fff;
      color: var(--ink);
      text-decoration: none;
      box-shadow: 0 12px 24px rgba(31,41,51,0.14);
    }
    .skip-link:focus { top: 16px; }
    .app {
      max-width: 1520px;
      margin: 0 auto;
      padding: 28px 20px 72px;
    }
    .site-nav {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 16px;
      padding-bottom: 14px;
      border-bottom: 1px solid var(--line);
      color: var(--muted);
      font-size: 0.92rem;
    }
    .site-brand {
      color: var(--ink);
      font-weight: 800;
      text-decoration: none;
    }
    .site-links {
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 10px 14px;
    }
    .site-links a {
      color: var(--muted);
      font-weight: 700;
      text-decoration: none;
    }
    .site-links a.active,
    .site-links a:hover {
      color: var(--accent-2);
    }
    .glossary-strip {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 16px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(255,255,255,0.82);
      color: var(--muted);
      font-size: 0.88rem;
      line-height: 1.4;
    }
    .glossary-strip strong {
      color: var(--ink);
    }
    .glossary-chip {
      padding: 6px 8px;
      border: 1px solid rgba(31,41,51,0.10);
      border-radius: 999px;
      background: rgba(255,255,255,0.72);
    }
    .hero {
      padding: 30px;
      border-radius: 34px;
      background:
        linear-gradient(135deg, rgba(255,255,255,0.88), rgba(255,255,255,0.75)),
        linear-gradient(135deg, rgba(15,118,110,0.12), rgba(180,83,9,0.10));
      box-shadow: var(--shadow);
      border: 1px solid rgba(255,255,255,0.55);
    }
    .hero-grid {
      display: grid;
      grid-template-columns: 1.45fr 1fr;
      gap: 22px;
      align-items: start;
    }
    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 7px 12px;
      border-radius: 999px;
      background: rgba(15,118,110,0.10);
      color: var(--accent);
      font-size: 0.82rem;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }
    h1, h2, h3 {
      margin: 0;
      font-family: "Baskerville", "Iowan Old Style", "Georgia", serif;
      letter-spacing: -0.02em;
    }
    h1 {
      margin-top: 16px;
      font-size: clamp(2.3rem, 4.8vw, 4.5rem);
      line-height: 0.95;
      max-width: 12ch;
    }
    .hero p {
      margin: 14px 0 0;
      max-width: 68ch;
      color: var(--muted);
      font-size: 1rem;
      line-height: 1.55;
    }
    .hero-side {
      display: grid;
      gap: 14px;
    }
    .control-card, .summary-card, .panel {
      background: var(--panel);
      backdrop-filter: blur(14px);
      border-radius: var(--radius);
      border: 1px solid rgba(255,255,255,0.6);
      box-shadow: var(--shadow);
    }
    .control-card {
      padding: 18px;
      display: grid;
      gap: 14px;
    }
    .control-label {
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
    }
    .segmented {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .segment-btn {
      border: 1px solid rgba(31,41,51,0.10);
      background: rgba(255,255,255,0.72);
      color: var(--ink);
      padding: 10px 12px;
      border-radius: 14px;
      font: inherit;
      font-size: 0.93rem;
      font-weight: 700;
      cursor: pointer;
      transition: transform 140ms ease, border-color 140ms ease, background 140ms ease;
    }
    .segment-btn:hover,
    .segment-btn:focus-visible {
      transform: translateY(-1px);
      border-color: rgba(15,118,110,0.35);
      outline: none;
    }
    .segment-btn.active {
      background: linear-gradient(135deg, rgba(15,118,110,0.18), rgba(15,118,110,0.08));
      border-color: rgba(15,118,110,0.45);
      color: var(--accent);
    }
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 14px;
      margin-top: 20px;
    }
    .summary-card {
      padding: 18px;
      min-height: 120px;
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
      font-size: 1.7rem;
      font-weight: 800;
      letter-spacing: -0.04em;
    }
    .summary-card .note {
      color: var(--muted);
      font-size: 0.9rem;
      line-height: 1.4;
    }
    .current-view {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      margin-top: 16px;
      padding: 12px 14px;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(255,255,255,0.82);
      color: var(--muted);
      font-size: 0.92rem;
    }
    .current-view strong {
      color: var(--ink);
    }
    .current-chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 7px 10px;
      border: 1px solid rgba(31,41,51,0.10);
      border-radius: 999px;
      background: rgba(255,255,255,0.82);
    }
    main {
      display: grid;
      gap: 22px;
      margin-top: 22px;
    }
    .panel {
      padding: 22px;
    }
    .section-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: end;
      margin-bottom: 18px;
    }
    .section-head p {
      margin: 8px 0 0;
      color: var(--muted);
      max-width: 72ch;
      line-height: 1.5;
    }
    .national-grid {
      display: grid;
      grid-template-columns: 1.25fr 1fr;
      gap: 20px;
      align-items: start;
    }
    .subpanel {
      border-radius: 20px;
      background: rgba(255,255,255,0.74);
      border: 1px solid rgba(31,41,51,0.08);
      padding: 16px;
    }
    .chart-note, .small-note {
      color: var(--muted);
      font-size: 0.9rem;
      line-height: 1.45;
    }
    .search-row, .map-toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      margin-bottom: 12px;
    }
    input[type="search"], select {
      appearance: none;
      width: 100%;
      border: 1px solid rgba(31,41,51,0.10);
      background: rgba(255,255,255,0.84);
      border-radius: 14px;
      padding: 12px 14px;
      color: var(--ink);
      font: inherit;
    }
    input[type="search"] { flex: 1 1 220px; }
    select { flex: 1 1 280px; }
    .btn {
      border: 1px solid rgba(31,41,51,0.10);
      background: rgba(255,255,255,0.84);
      color: var(--ink);
      border-radius: 14px;
      padding: 11px 14px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }
    .party-table-wrap, .district-table-wrap {
      overflow: auto;
      border-radius: 16px;
      border: 1px solid rgba(31,41,51,0.08);
      background: rgba(255,255,255,0.72);
      max-height: 620px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 640px;
    }
    th, td {
      padding: 11px 12px;
      border-bottom: 1px solid rgba(31,41,51,0.08);
      text-align: left;
      font-size: 0.92rem;
      white-space: nowrap;
    }
    th {
      position: sticky;
      top: 0;
      z-index: 1;
      background: rgba(250,248,244,0.96);
      color: var(--muted);
      font-size: 0.76rem;
      text-transform: uppercase;
      letter-spacing: 0.07em;
    }
    tr[data-party], tr[data-district-row] { cursor: pointer; }
    tr:hover td, tr:focus-within td { background: rgba(15,118,110,0.05); }
    tr.active td { background: rgba(15,118,110,0.10); }
    .party-pill {
      display: inline-flex;
      align-items: center;
      gap: 9px;
      font-weight: 700;
    }
    .party-swatch {
      width: 10px;
      height: 10px;
      border-radius: 999px;
      flex: 0 0 auto;
    }
    .delta-pos { color: #0f766e; font-weight: 700; }
    .delta-neg { color: #b91c1c; font-weight: 700; }
    .delta-zero { color: var(--muted); font-weight: 700; }
    .map-grid {
      display: grid;
      grid-template-columns: 1.15fr 0.95fr;
      gap: 20px;
      align-items: start;
    }
    .map-shell {
      display: grid;
      gap: 12px;
    }
    .map-wrap {
      position: relative;
      border-radius: 22px;
      overflow: hidden;
      background:
        radial-gradient(circle at top, rgba(15,118,110,0.08), transparent 30%),
        linear-gradient(180deg, #f8fbfb 0%, #eef5f5 100%);
      border: 1px solid rgba(31,41,51,0.08);
      min-height: 620px;
    }
    .map-wrap svg {
      display: block;
      width: 100%;
      height: auto;
    }
    .map-district {
      cursor: pointer;
      transition: opacity 140ms ease;
    }
    .map-district:hover path,
    .map-district:focus path {
      stroke: rgba(17,24,39,0.9);
      stroke-width: 1.8;
    }
    .map-district.active path {
      stroke: #111827;
      stroke-width: 2.2;
    }
    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 10px 16px;
      align-items: center;
      color: var(--muted);
      font-size: 0.9rem;
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
      border: 1px solid rgba(17,24,39,0.08);
    }
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
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }
    .metric {
      padding: 16px;
      border-radius: 18px;
      background: rgba(255,255,255,0.72);
      border: 1px solid rgba(31,41,51,0.08);
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
      font-size: 1.45rem;
      font-weight: 800;
      letter-spacing: -0.04em;
    }
    .factor-strip {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .factor-chip {
      border: 1px solid rgba(31,41,51,0.08);
      background: rgba(255,255,255,0.82);
      color: var(--ink);
      padding: 10px 12px;
      border-radius: 14px;
      font: inherit;
      cursor: pointer;
      min-width: 96px;
      text-align: left;
    }
    .factor-chip.active {
      border-color: rgba(15,118,110,0.45);
      background: rgba(15,118,110,0.10);
      color: var(--accent);
    }
    .factor-chip strong {
      display: block;
      font-size: 0.98rem;
    }
    .factor-chip span {
      display: block;
      margin-top: 2px;
      font-size: 0.82rem;
      color: inherit;
      opacity: 0.85;
    }
    .ranking-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }
    .ranking-card {
      border-radius: 18px;
      border: 1px solid rgba(31,41,51,0.08);
      background: rgba(255,255,255,0.72);
      padding: 14px;
    }
    .ranking-card ol {
      margin: 10px 0 0;
      padding-left: 18px;
      color: var(--muted);
      line-height: 1.6;
    }
    .ranking-card li strong { color: var(--ink); }
    .method-grid, .source-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
    }
    .method-card, .source-card {
      padding: 16px;
      border-radius: 18px;
      background: rgba(255,255,255,0.72);
      border: 1px solid rgba(31,41,51,0.08);
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
      color: var(--accent);
    }
    .tooltip {
      position: fixed;
      z-index: 40;
      max-width: 260px;
      padding: 12px 14px;
      border-radius: 14px;
      background: rgba(17,24,39,0.94);
      color: #f8fafc;
      box-shadow: 0 18px 36px rgba(0,0,0,0.22);
      font-size: 0.88rem;
      line-height: 1.45;
      pointer-events: none;
      opacity: 0;
      transform: translateY(4px);
      transition: opacity 100ms ease, transform 100ms ease;
    }
    .tooltip.open {
      opacity: 1;
      transform: translateY(0);
    }
    @media (max-width: 1180px) {
      .hero-grid,
      .national-grid,
      .map-grid {
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
      .site-nav {
        align-items: start;
        flex-direction: column;
      }
      .site-links {
        justify-content: flex-start;
      }
      .hero, .panel { padding: 18px; }
      .summary-grid,
      .detail-metrics,
      .ranking-grid,
      .method-grid,
      .source-grid {
        grid-template-columns: 1fr;
      }
      .map-wrap { min-height: 440px; }
      h1 { font-size: 2.4rem; }
    }
  </style>
</head>
<body>
  <a class="skip-link" href="#main-content">Skip to dashboard</a>
  <div class="app">
    <header class="site-nav">
      <a class="site-brand" href="/">Pileg Reports</a>
      <nav class="site-links" aria-label="Report navigation">
        <a href="/dpr/">Legislative Results</a>
        <a class="active" href="/pileg-seats/">Seat Scenarios</a>
        <a href="/pilpres-vs-pileg/">Presidential Alignment</a>
      </nav>
    </header>
    <section class="glossary-strip" aria-label="Election glossary">
      <span class="glossary-chip"><strong>Pileg</strong>: legislative election</span>
      <span class="glossary-chip"><strong>Pilpres</strong>: presidential election</span>
      <span class="glossary-chip"><strong>DPR</strong>: national House of Representatives</span>
      <span class="glossary-chip"><strong>Dapil</strong>: electoral district</span>
      <span class="glossary-chip"><strong>Parliamentary threshold</strong>: parties below 4% national DPR vote do not receive DPR seats</span>
    </section>
    <header class="hero">
      <div class="hero-grid">
        <div>
          <div class="eyebrow">Seat Proportion Explorer</div>
          <h1>How Does Party Balance Change When Dapil Seat Counts Move?</h1>
          <p>
            Start here: what would happen if district seat counts were larger or smaller? This dashboard tests 2024 DPR seat-count scenarios using only the live repo data. Pick a chamber size,
            choose whether to apply the 4% DPR threshold, then inspect how vote share turns into seat share at both
            the national and dapil level.
          </p>
          <p id="hero-meta" class="small-note"></p>
        </div>
        <div class="hero-side">
          <section class="control-card">
            <div>
              <div class="control-label">Chamber Size Scenario</div>
              <div id="factor-controls" class="segmented"></div>
            </div>
            <div>
              <div class="control-label">Threshold Rule</div>
              <div id="lens-controls" class="segmented"></div>
            </div>
            <div class="small-note" id="lens-note"></div>
          </section>
        </div>
      </div>
      <div id="current-view" class="current-view" aria-live="polite"></div>
      <div id="summary-cards" class="summary-grid"></div>
    </header>

    <main id="main-content">
      <section class="panel">
        <div class="section-head">
          <div>
            <h2>National Proportionality</h2>
            <p>
              The selected table and chart share the same factor and lens. Click a line or a party row to focus it and trace how that
              party's seat share changes across the full scenario ladder.
            </p>
          </div>
        </div>
        <div class="national-grid">
          <div class="subpanel">
            <div id="party-chart"></div>
            <p class="chart-note">Line chart uses national seat share. Factor labels still show chamber size so you can see whether proportional shifts are happening in a larger or smaller seat pool.</p>
          </div>
          <div class="subpanel">
            <div class="search-row">
              <input id="party-search" type="search" placeholder="Filter parties by code or name" />
              <button id="clear-party-focus" class="btn" type="button">Clear Focus</button>
            </div>
            <div id="party-table" class="party-table-wrap"></div>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="section-head">
          <div>
            <h2>Dapil Proportionality And District Detail</h2>
            <p>
              The map color shows how disproportional each dapil becomes under the selected scenario. Click any dapil to inspect how
              party vote share translates into seat share inside that district.
            </p>
          </div>
        </div>
        <div class="map-grid">
          <div class="map-shell">
            <div class="map-toolbar">
              <select id="district-select" aria-label="Jump to district"></select>
              <button id="clear-district" class="btn" type="button">Show national view</button>
            </div>
            <div id="map-legend" class="legend"></div>
            <div id="map-wrap" class="map-wrap"></div>
            <div class="small-note">Map color reflects the district disproportionality index: the gap between vote share and seat share after allocation. The legal/raw lens changes that distribution directly.</div>
          </div>
          <div class="detail-shell">
            <div id="district-detail" class="subpanel"></div>
            <div id="district-rankings" class="ranking-grid"></div>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="section-head">
          <div>
            <h2>Method And Sources</h2>
            <p>
              This scenario dashboard is a separate analytical surface. It leaves the current DPR dashboard untouched and keeps the
              seat-scaling idea explicit so you can inspect the consequences directly.
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
    const factorList = payload.factors;
    const lensList = payload.lenses;
    const districtList = payload.districts;
    const partyList = payload.parties;
    const districtIndex = new Map(districtList.map(item => [item.districtKey, item]));
    const partyIndex = new Map(partyList.map(item => [item.partyCode, item]));
    const state = {
      factorKey: "1",
      lens: "legal",
      districtKey: "",
      partyQuery: "",
      partyFocus: "",
    };

    const elements = {
      heroMeta: document.getElementById("hero-meta"),
      factorControls: document.getElementById("factor-controls"),
      lensControls: document.getElementById("lens-controls"),
      lensNote: document.getElementById("lens-note"),
      currentView: document.getElementById("current-view"),
      summaryCards: document.getElementById("summary-cards"),
      partyChart: document.getElementById("party-chart"),
      partySearch: document.getElementById("party-search"),
      clearPartyFocus: document.getElementById("clear-party-focus"),
      partyTable: document.getElementById("party-table"),
      districtSelect: document.getElementById("district-select"),
      clearDistrict: document.getElementById("clear-district"),
      mapLegend: document.getElementById("map-legend"),
      mapWrap: document.getElementById("map-wrap"),
      districtDetail: document.getElementById("district-detail"),
      districtRankings: document.getElementById("district-rankings"),
      methodGrid: document.getElementById("method-grid"),
      sourceGrid: document.getElementById("source-grid"),
      tooltip: document.getElementById("tooltip"),
    };

    function formatNumber(value) {
      return new Intl.NumberFormat("en-US").format(value);
    }

    function formatPercent(value, digits = 1) {
      return `${(Number(value || 0) * 100).toFixed(digits)}%`;
    }

    function formatPointDelta(value, digits = 1) {
      const num = Number(value || 0) * 100;
      if (num > 0) return `+${num.toFixed(digits)} pp`;
      if (num < 0) return `${num.toFixed(digits)} pp`;
      return `0.0 pp`;
    }

    function formatDelta(value) {
      const num = Number(value || 0);
      if (num > 0) return `+${formatNumber(num)}`;
      if (num < 0) return `-${formatNumber(Math.abs(num))}`;
      return "0";
    }

    function escapeHtml(value) {
      return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }

    function currentFactor() {
      return factorList.find(item => item.key === state.factorKey) || factorList.find(item => item.key === "1");
    }

    function currentLens() {
      return lensList.find(item => item.key === state.lens) || lensList[0];
    }

    function currentScenario() {
      return payload.scenarios[state.lens][state.factorKey];
    }

    function nationalRowFor(partyCode, factorKey) {
      return payload.scenarios[state.lens][factorKey].nationalParties.find(row => row.partyCode === partyCode) || null;
    }

    function currentDistrictSummary(districtKey) {
      return currentScenario().districts[districtKey] || null;
    }

    function movementClass(value) {
      if (value > 0) return "delta-pos";
      if (value < 0) return "delta-neg";
      return "delta-zero";
    }

    function disproportionalityColor(value, maxValue) {
      const safeMax = Math.max(maxValue, 0.0001);
      const ratio = Math.min(Math.max(value, 0) / safeMax, 1);
      const lightness = 96 - (ratio * 48);
      return `hsl(197 72% ${lightness}%)`;
    }

    function seatChangeByDistrict(districtKey) {
      const district = districtIndex.get(districtKey);
      if (!district) return 0;
      return Number(district.seatByFactor[state.factorKey] || 0) - Number(district.baseSeats || 0);
    }

    function disproportionalityByDistrict(districtKey) {
      const summary = currentDistrictSummary(districtKey);
      return summary ? Number(summary.districtDisproportionality || 0) : 0;
    }

    function currentDistrictRows() {
      return districtList
        .map(district => {
          const summary = currentDistrictSummary(district.districtKey);
          return {
            districtKey: district.districtKey,
            label: district.label,
            province: district.province,
            baseSeats: district.baseSeats,
            seatCount: district.seatByFactor[state.factorKey],
            seatDelta: seatChangeByDistrict(district.districtKey),
            districtDisproportionality: summary ? Number(summary.districtDisproportionality || 0) : 0,
            districtDisproportionalityDelta: summary ? Number(summary.districtDisproportionalityDelta || 0) : 0,
            partiesWithSeats: summary ? summary.partiesWithSeats : 0,
            leadingPartyCode: summary ? summary.leadingPartyCode : "",
            leadingPartySeatPremium: summary ? Number(summary.leadingPartySeatPremium || 0) : 0,
          };
        })
        .sort((a, b) => b.districtDisproportionality - a.districtDisproportionality || Math.abs(b.leadingPartySeatPremium) - Math.abs(a.leadingPartySeatPremium) || a.label.localeCompare(b.label));
    }

    function renderControls() {
      elements.factorControls.innerHTML = factorList.map(item => `
        <button class="segment-btn ${item.key === state.factorKey ? "active" : ""}" data-factor="${escapeHtml(item.key)}" type="button" title="${escapeHtml(item.headline)}: ${escapeHtml(formatNumber(item.totalSeats))} seats">
          ${escapeHtml(item.shortLabel)} · ${escapeHtml(formatNumber(item.totalSeats))}
        </button>
      `).join("");
      elements.lensControls.innerHTML = lensList.map(item => `
        <button class="segment-btn ${item.key === state.lens ? "active" : ""}" data-lens="${escapeHtml(item.key)}" type="button">
          ${escapeHtml(item.shortLabel)}
        </button>
      `).join("");
      elements.lensNote.textContent = currentLens().description;
      const factor = currentFactor();
      const seatDelta = factor.totalSeats - payload.meta.baseTotalSeats;
      const chamberNote = seatDelta === 0
        ? `This is the status quo chamber size of ${formatNumber(payload.meta.baseTotalSeats)} seats.`
        : `This scenario changes the chamber from ${formatNumber(payload.meta.baseTotalSeats)} to ${formatNumber(factor.totalSeats)} seats (${formatDelta(seatDelta)}).`;
      const disproportionality = currentScenario().nationalDisproportionality || 0;
      elements.heroMeta.textContent = `${factor.headline}. ${chamberNote} National disproportionality in the current lens is ${formatPercent(disproportionality)}.`;
    }

    function renderCurrentView() {
      const factor = currentFactor();
      const lens = currentLens();
      const district = state.districtKey ? districtIndex.get(state.districtKey) : null;
      const party = state.partyFocus ? partyIndex.get(state.partyFocus) : null;
      const districtLabel = district ? `${district.label}, ${district.province}` : "National view";
      const partyLabel = party ? `${party.partyCode} focus` : "All parties";
      elements.currentView.innerHTML = `
        <strong>Current view</strong>
        <span class="current-chip">Scenario: ${escapeHtml(factor.shortLabel)} / ${escapeHtml(formatNumber(factor.totalSeats))} seats</span>
        <span class="current-chip">Rule: ${escapeHtml(lens.shortLabel)}</span>
        <span class="current-chip">Scope: ${escapeHtml(districtLabel)}</span>
        <span class="current-chip">Party: ${escapeHtml(partyLabel)}</span>
      `;
    }

    function renderSummaryCards() {
      const scenario = currentScenario();
      const factor = currentFactor();
      const activeParties = scenario.nationalParties.filter(row => row.seats > 0).length;
      const topOverrepresented = scenario.topOverrepresented[0] || null;
      const topUnderrepresented = scenario.topUnderrepresented[0] || null;
      const biggestDistrict = currentDistrictRows()[0] || null;
      const mostBalancedDistrict = [...currentDistrictRows()].sort((a, b) => a.districtDisproportionality - b.districtDisproportionality || a.label.localeCompare(b.label))[0] || null;

      const cards = [
        {
          label: "National Disproportionality",
          value: formatPercent(scenario.nationalDisproportionality),
          note: `Loosemore-Hanby style mismatch between national vote share and seat share under ${escapeHtml(factor.shortLabel)}.`,
        },
        {
          label: "Most Overrepresented Party",
          value: topOverrepresented ? escapeHtml(topOverrepresented.partyCode) : "None",
          note: topOverrepresented ? `${formatPointDelta(topOverrepresented.seatPremium)} seat premium over vote share.` : "No party is overrepresented under this scenario.",
        },
        {
          label: "Parties With Seats",
          value: formatNumber(activeParties),
          note: state.lens === "legal"
            ? "Counted after applying the 4% national DPR threshold."
            : "Counted with all parties included in the allocation.",
        },
        {
          label: "Most Underrepresented Party",
          value: topUnderrepresented ? escapeHtml(topUnderrepresented.partyCode) : "None",
          note: topUnderrepresented ? `${formatPointDelta(topUnderrepresented.seatPremium)} seat penalty versus vote share.` : "No party is underrepresented under this scenario.",
        },
        {
          label: "Most Disproportionate Dapil",
          value: biggestDistrict ? escapeHtml(biggestDistrict.label) : "None",
          note: biggestDistrict
            ? `${formatPercent(biggestDistrict.districtDisproportionality)} mismatch. Most balanced: ${escapeHtml(mostBalancedDistrict.label)} at ${formatPercent(mostBalancedDistrict.districtDisproportionality)}.`
            : "No district comparison available.",
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

    function renderPartyChart() {
      const query = state.partyQuery.trim().toLowerCase();
      const series = partyList
        .map(party => ({
          partyCode: party.partyCode,
          partyName: party.partyName,
          color: party.color,
          voteShare: party.nationalVoteShare,
          points: factorList.map(factor => {
            const row = nationalRowFor(party.partyCode, factor.key);
            return {
              factorKey: factor.key,
              factorLabel: factor.shortLabel,
              totalSeats: factor.totalSeats,
              seats: row ? row.seats : 0,
              seatShare: row ? row.seatShare : 0,
              seatPremium: row ? row.seatPremium : 0,
            };
          }),
        }))
        .filter(seriesItem => {
          if (!query) return true;
          return `${seriesItem.partyCode} ${seriesItem.partyName}`.toLowerCase().includes(query);
        });

      const maxShare = Math.max(0.01, ...series.flatMap(item => item.points.map(point => point.seatShare)), ...series.map(item => item.voteShare));
      const width = 840;
      const height = 360;
      const margin = { top: 18, right: 22, bottom: 70, left: 54 };
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;

      const xForIndex = index => margin.left + (index / Math.max(factorList.length - 1, 1)) * innerWidth;
      const yForShare = share => margin.top + innerHeight - ((share / maxShare) * innerHeight);
      const tickValues = [0, maxShare / 2, maxShare];

      const lineMarkup = series.map(item => {
        const isFocused = state.partyFocus === item.partyCode;
        const isMuted = state.partyFocus && !isFocused;
        const points = item.points.map((point, index) => `${xForIndex(index).toFixed(1)},${yForShare(point.seatShare).toFixed(1)}`).join(" ");
        const opacity = isFocused ? 0.98 : (isMuted ? 0.08 : 0.58);
        const strokeWidth = isFocused ? 3.4 : 1.7;
        const baselineY = yForShare(item.voteShare);
        const circles = item.points.map((point, index) => `
          <circle
            cx="${xForIndex(index).toFixed(1)}"
            cy="${yForShare(point.seatShare).toFixed(1)}"
            r="${isFocused ? 4.3 : 3.2}"
            fill="${item.color}"
            data-party="${escapeHtml(item.partyCode)}"
            style="cursor:pointer;opacity:${opacity};"
          >
            <title>${escapeHtml(item.partyCode)} | ${escapeHtml(point.factorLabel)} | ${formatPercent(point.seatShare)} seat share | ${formatPointDelta(point.seatPremium)} premium over vote share | ${formatNumber(point.seats)} seats</title>
          </circle>
        `).join("");
        return `
          <g>
            ${isFocused ? `<line x1="${margin.left}" y1="${baselineY.toFixed(1)}" x2="${width - margin.right}" y2="${baselineY.toFixed(1)}" stroke="${item.color}" stroke-opacity="0.55" stroke-width="1.2" stroke-dasharray="5 5"></line>` : ""}
            <polyline
              fill="none"
              stroke="${item.color}"
              stroke-width="${strokeWidth}"
              points="${points}"
              data-party="${escapeHtml(item.partyCode)}"
              style="cursor:pointer;opacity:${opacity};"
            >
              <title>${escapeHtml(item.partyCode)} (${escapeHtml(item.partyName)})</title>
            </polyline>
            ${circles}
          </g>
        `;
      }).join("");

      elements.partyChart.innerHTML = `
        <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Party seat trajectories across factors">
          <rect x="0" y="0" width="${width}" height="${height}" fill="transparent"></rect>
          ${tickValues.map(value => `
            <g>
              <line x1="${margin.left}" y1="${yForShare(value)}" x2="${width - margin.right}" y2="${yForShare(value)}" stroke="rgba(31,41,51,0.08)"></line>
              <text x="${margin.left - 10}" y="${yForShare(value) + 4}" text-anchor="end" font-size="12" fill="#5f6c78">${formatPercent(value)}</text>
            </g>
          `).join("")}
          ${factorList.map((factor, index) => `
            <g>
              <line x1="${xForIndex(index)}" y1="${margin.top}" x2="${xForIndex(index)}" y2="${margin.top + innerHeight}" stroke="rgba(31,41,51,0.05)"></line>
              <text x="${xForIndex(index)}" y="${height - 34}" text-anchor="middle" font-size="12" fill="#1f2933" font-weight="700">${escapeHtml(factor.shortLabel)}</text>
              <text x="${xForIndex(index)}" y="${height - 18}" text-anchor="middle" font-size="11" fill="#5f6c78">${formatNumber(factor.totalSeats)}</text>
            </g>
          `).join("")}
          <text x="${margin.left}" y="14" font-size="12" fill="#5f6c78">National seat share</text>
          <text x="${width - margin.right}" y="${height - 50}" text-anchor="end" font-size="12" fill="#5f6c78">Factor / chamber size</text>
          ${lineMarkup}
        </svg>
      `;
    }

    function renderPartyTable() {
      const rows = currentScenario().nationalParties
        .filter(row => {
          const query = state.partyQuery.trim().toLowerCase();
          if (!query) return true;
          return `${row.partyCode} ${row.partyName}`.toLowerCase().includes(query);
        })
        .sort((a, b) => b.seatPremium - a.seatPremium || b.seatShare - a.seatShare || b.nationalVotes - a.nationalVotes || a.partyNumber - b.partyNumber);

      elements.partyTable.innerHTML = `
        <table>
          <thead>
            <tr>
              <th>Party</th>
              <th>Vote Share</th>
              <th>Seat Share</th>
              <th>Premium</th>
              <th>Share vs Base</th>
              <th>Seats</th>
            </tr>
          </thead>
          <tbody>
            ${rows.map(row => `
              <tr data-party="${escapeHtml(row.partyCode)}" class="${state.partyFocus === row.partyCode ? "active" : ""}">
                <td>
                  <span class="party-pill">
                    <span class="party-swatch" style="background:${row.color};"></span>
                    ${escapeHtml(row.partyCode)}
                  </span>
                </td>
                <td>${formatPercent(row.nationalVoteShare)}</td>
                <td>${formatPercent(row.seatShare)}</td>
                <td class="${movementClass(row.seatPremium)}">${formatPointDelta(row.seatPremium)}</td>
                <td class="${movementClass(row.seatShareDelta)}">${formatPointDelta(row.seatShareDelta)}</td>
                <td>${formatNumber(row.seats)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;
    }

    function renderMapLegend() {
      const maxValue = Math.max(...districtList.map(item => disproportionalityByDistrict(item.districtKey)), 0);
      elements.mapLegend.innerHTML = `
        <span class="legend-chip"><span class="legend-swatch" style="background:${disproportionalityColor(0, Math.max(maxValue, 0.0001))};"></span>Low mismatch</span>
        <span class="legend-chip"><span class="legend-swatch" style="background:${disproportionalityColor(Math.max(maxValue, 0.0001) / 2, Math.max(maxValue, 0.0001))};"></span>Medium mismatch</span>
        <span class="legend-chip"><span class="legend-swatch" style="background:${disproportionalityColor(Math.max(maxValue, 0.0001), Math.max(maxValue, 0.0001))};"></span>High mismatch (${formatPercent(maxValue)})</span>
      `;
    }

    function renderMap() {
      const maxValue = Math.max(...districtList.map(item => disproportionalityByDistrict(item.districtKey)), 0.0001);
      const svg = `
        <svg viewBox="${payload.map.viewBox}" role="img" aria-label="Indonesia dapil map">
          ${payload.map.districts.map(item => {
            const district = districtIndex.get(item.districtKey);
            const summary = currentDistrictSummary(item.districtKey);
            const disproportionality = disproportionalityByDistrict(item.districtKey);
            const fill = disproportionalityColor(disproportionality, maxValue);
            const active = item.districtKey === state.districtKey;
            const title = [
              district.label,
              district.province,
              `${formatPercent(disproportionality)} disproportionality`,
              summary ? `${formatPointDelta(summary.leadingPartySeatPremium || 0)} winner premium` : "",
              `${district.baseSeats} → ${district.seatByFactor[state.factorKey]} seats`,
            ].filter(Boolean).join(" | ");
            return `
              <g class="map-district ${active ? "active" : ""}" tabindex="0" role="button" data-district="${escapeHtml(item.districtKey)}" aria-label="${escapeHtml(title)}">
                ${item.paths.map(pathData => `<path d="${pathData}" fill="${fill}" stroke="rgba(17,24,39,0.25)" stroke-width="0.7"></path>`).join("")}
                <title>${escapeHtml(title)}</title>
              </g>
            `;
          }).join("")}
        </svg>
      `;
      elements.mapWrap.innerHTML = svg;
    }

    function renderDistrictDetail() {
      if (!state.districtKey || !districtIndex.has(state.districtKey)) {
        const factor = currentFactor();
        elements.districtDetail.innerHTML = `
          <div class="detail-header">
            <h3>Pick a Dapil</h3>
            <p>Use the map or the district selector to inspect one district. Right now the dashboard is showing the national proportionality effect of <strong>${escapeHtml(factor.headline)}</strong>.</p>
          </div>
          <div class="small-note">Tip: watch how vote share and seat share separate as you move away from the base factor.</div>
        `;
        return;
      }

      const district = districtIndex.get(state.districtKey);
      const summary = currentDistrictSummary(state.districtKey);
      const leadingParty = summary.leadingPartyCode ? partyIndex.get(summary.leadingPartyCode) : null;
      const largestPositive = summary.largestSeatPremiumPartyCode ? partyIndex.get(summary.largestSeatPremiumPartyCode) : null;
      const largestNegative = summary.largestSeatPenaltyPartyCode ? partyIndex.get(summary.largestSeatPenaltyPartyCode) : null;
      const rankedRows = [...summary.partySeatRows].sort(
        (a, b) => b.seatPremium - a.seatPremium || b.seatShare - a.seatShare || b.totalVotes - a.totalVotes || a.partyNumber - b.partyNumber
      );

      elements.districtDetail.innerHTML = `
        <div class="detail-header">
          <h3>${escapeHtml(district.label)}</h3>
          <p>${escapeHtml(district.province)}. Under the <strong>${escapeHtml(currentLens().label)}</strong>, this dapil moves from <strong>${formatNumber(district.baseSeats)}</strong> seats to <strong>${formatNumber(summary.seatCount)}</strong> seats at the current factor. The main question here is how far seat share pulls away from vote share.</p>
        </div>
        <div class="detail-metrics">
          <div class="metric">
            <div class="label">Disproportionality</div>
            <div class="value">${formatPercent(summary.districtDisproportionality)}</div>
          </div>
          <div class="metric">
            <div class="label">Vs Base Factor</div>
            <div class="value ${movementClass(summary.districtDisproportionalityDelta)}">${formatPointDelta(summary.districtDisproportionalityDelta)}</div>
          </div>
          <div class="metric">
            <div class="label">Winner Premium</div>
            <div class="value ${movementClass(summary.leadingPartySeatPremium)}">${formatPointDelta(summary.leadingPartySeatPremium)}</div>
          </div>
          <div class="metric">
            <div class="label">Scenario Seats</div>
            <div class="value">${formatNumber(summary.seatCount)}</div>
          </div>
        </div>
        <div class="factor-strip">
          ${factorList.map(factor => `
            <button class="factor-chip ${factor.key === state.factorKey ? "active" : ""}" data-factor="${escapeHtml(factor.key)}" type="button">
              <strong>${escapeHtml(factor.shortLabel)}</strong>
              <span>${formatNumber(district.seatByFactor[factor.key])} seats</span>
            </button>
          `).join("")}
        </div>
        <p class="small-note">
          ${leadingParty ? `${escapeHtml(leadingParty.partyCode)} leads this dapil.` : "No party leads this dapil."}
          ${largestPositive ? ` ${escapeHtml(largestPositive.partyCode)} is the most overrepresented relative to vote share.` : ""}
          ${largestNegative ? ` ${escapeHtml(largestNegative.partyCode)} is the most underrepresented.` : ""}
        </p>
        <div class="district-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Party</th>
                <th>Vote Share</th>
                <th>Seat Share</th>
                <th>Premium</th>
                <th>Share vs Base</th>
                <th>Seats</th>
              </tr>
            </thead>
            <tbody>
              ${rankedRows.map(row => `
                <tr data-party="${escapeHtml(row.partyCode)}" class="${state.partyFocus === row.partyCode ? "active" : ""}">
                  <td>
                    <span class="party-pill">
                      <span class="party-swatch" style="background:${row.color};"></span>
                      ${escapeHtml(row.partyCode)}
                    </span>
                  </td>
                  <td>${formatPercent(row.voteShare)}</td>
                  <td>${formatPercent(row.seatShare)}</td>
                  <td class="${movementClass(row.seatPremium)}">${formatPointDelta(row.seatPremium)}</td>
                  <td class="${movementClass(row.seatShareDelta)}">${formatPointDelta(row.seatShareDelta)}</td>
                  <td>${formatNumber(row.seats)}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      `;
    }

    function renderDistrictRankings() {
      const ranked = currentDistrictRows();
      const balanced = [...ranked].sort((a, b) => a.districtDisproportionality - b.districtDisproportionality || a.label.localeCompare(b.label)).slice(0, 6);
      const strongestWinnerPremium = [...ranked].sort((a, b) => b.leadingPartySeatPremium - a.leadingPartySeatPremium || a.label.localeCompare(b.label)).slice(0, 6);
      const active = ranked.filter(item => item.partiesWithSeats > 0).sort((a, b) => b.partiesWithSeats - a.partiesWithSeats).slice(0, 6);

      elements.districtRankings.innerHTML = `
        <section class="ranking-card">
          <h3>Most Disproportionate</h3>
          <ol>
            ${ranked.slice(0, 6).map(item => `
              <li data-district-row="${escapeHtml(item.districtKey)}"><strong>${escapeHtml(item.label)}</strong> <span>${formatPercent(item.districtDisproportionality)}</span></li>
            `).join("")}
          </ol>
        </section>
        <section class="ranking-card">
          <h3>Most Balanced</h3>
          <ol>
            ${balanced.map(item => `
              <li data-district-row="${escapeHtml(item.districtKey)}"><strong>${escapeHtml(item.label)}</strong> <span>${formatPercent(item.districtDisproportionality)}</span></li>
            `).join("")}
          </ol>
        </section>
        <section class="ranking-card">
          <h3>Strongest Winner Premium</h3>
          <ol>
            ${strongestWinnerPremium.map(item => `
              <li data-district-row="${escapeHtml(item.districtKey)}"><strong>${escapeHtml(item.label)}</strong> <span class="${movementClass(item.leadingPartySeatPremium)}">${formatPointDelta(item.leadingPartySeatPremium)}</span></li>
            `).join("")}
          </ol>
        </section>
        <section class="ranking-card">
          <h3>Current Scenario Note</h3>
          <p class="small-note" style="margin:10px 0 0;">
            <strong>${escapeHtml(currentFactor().headline)}</strong> under the <strong>${escapeHtml(currentLens().label)}</strong>.
            Total chamber size is <strong>${formatNumber(currentFactor().totalSeats)}</strong>, but the ranking here is driven by proportionality, not by chamber size alone.
          </p>
        </section>
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

    function renderDistrictSelect() {
      elements.districtSelect.innerHTML = `
        <option value="">Jump to a dapil</option>
        ${districtList.map(item => `
          <option value="${escapeHtml(item.districtKey)}" ${item.districtKey === state.districtKey ? "selected" : ""}>
            ${escapeHtml(item.label)} (${escapeHtml(item.province)})
          </option>
        `).join("")}
      `;
    }

    function showTooltip(event, districtKey) {
      const district = districtIndex.get(districtKey);
      const summary = currentDistrictSummary(districtKey);
      if (!district) return;
      elements.tooltip.innerHTML = `
        <strong>${escapeHtml(district.label)}</strong><br>
        ${escapeHtml(district.province)}<br>
        ${formatPercent(disproportionalityByDistrict(districtKey))} disproportionality<br>
        ${summary ? `<span class="${movementClass(summary.leadingPartySeatPremium || 0)}">${formatPointDelta(summary.leadingPartySeatPremium || 0)}</span> winner premium<br>` : ""}
        ${formatNumber(district.baseSeats)} → ${formatNumber(district.seatByFactor[state.factorKey])} seats
      `;
      elements.tooltip.style.left = `${event.clientX + 16}px`;
      elements.tooltip.style.top = `${event.clientY + 16}px`;
      elements.tooltip.classList.add("open");
      elements.tooltip.setAttribute("aria-hidden", "false");
    }

    function hideTooltip() {
      elements.tooltip.classList.remove("open");
      elements.tooltip.setAttribute("aria-hidden", "true");
    }

    function renderAll() {
      renderControls();
      renderCurrentView();
      renderSummaryCards();
      renderPartyChart();
      renderPartyTable();
      renderDistrictSelect();
      renderMapLegend();
      renderMap();
      renderDistrictDetail();
      renderDistrictRankings();
      renderMethodAndSources();
    }

    elements.factorControls.addEventListener("click", event => {
      const button = event.target.closest("[data-factor]");
      if (!button) return;
      state.factorKey = button.dataset.factor;
      renderAll();
    });

    elements.lensControls.addEventListener("click", event => {
      const button = event.target.closest("[data-lens]");
      if (!button) return;
      state.lens = button.dataset.lens;
      renderAll();
    });

    elements.partySearch.addEventListener("input", () => {
      state.partyQuery = elements.partySearch.value;
      renderPartyChart();
      renderPartyTable();
    });

    elements.clearPartyFocus.addEventListener("click", () => {
      state.partyFocus = "";
      renderPartyChart();
      renderPartyTable();
      renderDistrictDetail();
    });

    elements.partyTable.addEventListener("click", event => {
      const row = event.target.closest("[data-party]");
      if (!row) return;
      state.partyFocus = state.partyFocus === row.dataset.party ? "" : row.dataset.party;
      renderPartyChart();
      renderPartyTable();
      renderDistrictDetail();
    });

    elements.partyChart.addEventListener("click", event => {
      const target = event.target.closest("[data-party]");
      if (!target) return;
      state.partyFocus = state.partyFocus === target.dataset.party ? "" : target.dataset.party;
      renderPartyChart();
      renderPartyTable();
      renderDistrictDetail();
    });

    elements.districtSelect.addEventListener("change", () => {
      state.districtKey = elements.districtSelect.value;
      renderAll();
    });

    elements.clearDistrict.addEventListener("click", () => {
      state.districtKey = "";
      renderAll();
    });

    elements.mapWrap.addEventListener("click", event => {
      const district = event.target.closest("[data-district]");
      if (!district) return;
      state.districtKey = district.dataset.district;
      renderAll();
    });

    elements.mapWrap.addEventListener("keydown", event => {
      const district = event.target.closest("[data-district]");
      if (!district) return;
      if (!["Enter", " "].includes(event.key)) return;
      event.preventDefault();
      state.districtKey = district.dataset.district;
      renderAll();
    });

    elements.mapWrap.addEventListener("mousemove", event => {
      const district = event.target.closest("[data-district]");
      if (!district) {
        hideTooltip();
        return;
      }
      showTooltip(event, district.dataset.district);
    });

    elements.mapWrap.addEventListener("mouseleave", hideTooltip);
    elements.mapWrap.addEventListener("focusout", hideTooltip);

    elements.districtDetail.addEventListener("click", event => {
      const factorButton = event.target.closest("[data-factor]");
      if (factorButton) {
        state.factorKey = factorButton.dataset.factor;
        renderAll();
        return;
      }
      const partyRow = event.target.closest("[data-party]");
      if (partyRow) {
        state.partyFocus = state.partyFocus === partyRow.dataset.party ? "" : partyRow.dataset.party;
        renderPartyChart();
        renderPartyTable();
        renderDistrictDetail();
      }
    });

    elements.districtRankings.addEventListener("click", event => {
      const item = event.target.closest("[data-district-row]");
      if (!item) return;
      state.districtKey = item.dataset.districtRow;
      renderAll();
    });

    renderAll();
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
        "Open index.html in a browser. This standalone dashboard explores DPR seat-adjustment scenarios using existing repo data and factor-based seat scaling.\n",
        encoding="utf-8",
    )
    print("Wrote pileg scenario dashboard to", output_path)


if __name__ == "__main__":
    main()
