#!/usr/bin/env python3
"""Estimate DPR winners with and without the national parliamentary threshold."""
from __future__ import annotations

import json
from collections import Counter, defaultdict

from common import (
    PREPARED_DATA_DIR,
    PYTHON_OUTPUT_DIR,
    ensure_dir,
    format_float,
    parse_int,
    read_csv,
    write_csv,
)


OUTPUT_DIR = ensure_dir(PYTHON_OUTPUT_DIR / "dpr_estimated_winners")
PARLIAMENTARY_THRESHOLD = 0.04


def allocate_sainte_lague(party_rows: list[dict[str, object]], seat_count: int) -> dict[str, int]:
    quotients = []
    for row in party_rows:
        total_votes = int(row["total_votes"])
        for divisor in range(1, 2 * seat_count, 2):
            quotients.append(
                (
                    total_votes / divisor,
                    row["party_code"],
                    row["party_name"],
                    int(row["party_number"]),
                )
            )
    quotients.sort(key=lambda item: (-item[0], item[3], item[1]))
    winners = quotients[:seat_count]
    return dict(Counter(item[1] for item in winners))


def slate_key(province: str, district: str, party_code: str) -> tuple[str, str, str]:
    return (province, district, party_code)


def winner_key(row: dict[str, object]) -> tuple[str, str, str, int]:
    return (str(row["province"]), str(row["district"]), str(row["party_code"]), int(row["candidate_number"]))


def select_fields(row: dict[str, object], fieldnames: list[str]) -> dict[str, object]:
    return {field: row.get(field, "") for field in fieldnames}


def build_model_outputs(
    district_party_rows: dict[tuple[str, str], list[dict[str, object]]],
    candidates_by_slate: dict[tuple[str, str, str], list[dict[str, object]]],
    seat_map: dict[tuple[str, str], int],
    eligible_party_codes: set[str] | None,
    model_name: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]], Counter[tuple[str, str]]]:
    seat_allocations: list[dict[str, object]] = []
    winners: list[dict[str, object]] = []
    seats_by_party: Counter[tuple[str, str]] = Counter()

    for district_key, party_rows in sorted(district_party_rows.items()):
        province, district = district_key
        if district_key not in seat_map:
            raise KeyError(f"Missing seat count for {district_key}")

        seat_count = seat_map[district_key]
        eligible_rows = [
            row for row in party_rows if eligible_party_codes is None or str(row["party_code"]) in eligible_party_codes
        ]
        if not eligible_rows:
            raise ValueError(f"No eligible parties available for seat allocation in {district_key}")

        seats_won = allocate_sainte_lague(eligible_rows, seat_count)
        if sum(seats_won.values()) != seat_count:
            raise AssertionError(f"{model_name} seat allocation failed to fill all seats in {district_key}")

        for row in sorted(party_rows, key=lambda item: (int(item["party_number"]), str(item["party_code"]))):
            party_seats = seats_won.get(str(row["party_code"]), 0)
            seat_allocations.append(
                {
                    "province": province,
                    "district": district,
                    "seat_count": seat_count,
                    "party_number": row["party_number"],
                    "party_code": row["party_code"],
                    "party_name": row["party_name"],
                    "party_vote": row["party_vote"],
                    "candidate_vote_total": row["candidate_vote_total"],
                    "total_votes": row["total_votes"],
                    "candidate_count": row["candidate_count"],
                    "seats_won": party_seats,
                    "seat_allocation_model": model_name,
                }
            )
            seats_by_party[(str(row["party_code"]), str(row["party_name"]))] += party_seats

            if party_seats <= 0:
                continue

            ranked_candidates = sorted(
                candidates_by_slate[(province, district, str(row["party_code"]))],
                key=lambda item: (-int(item["candidate_vote"]), str(item["candidate_name"]), int(item["candidate_number"])),
            )
            for list_position, candidate in enumerate(ranked_candidates, start=1):
                if list_position > party_seats:
                    break
                winners.append(
                    {
                        "province": province,
                        "district": district,
                        "seat_count": seat_count,
                        "party_number": row["party_number"],
                        "party_code": row["party_code"],
                        "party_name": row["party_name"],
                        "party_vote": row["party_vote"],
                        "total_votes": row["total_votes"],
                        "candidate_number": candidate["candidate_number"],
                        "candidate_name": candidate["candidate_name"],
                        "candidate_vote": candidate["candidate_vote"],
                        "list_position": list_position,
                        "candidate_vote_share_of_party_total": format_float(
                            int(candidate["candidate_vote"]) / int(row["total_votes"]) if int(row["total_votes"]) else None
                        ),
                        "winner_model": model_name,
                    }
                )

    if sum(int(row["seats_won"]) for row in seat_allocations) != sum(seat_map.values()):
        raise AssertionError(f"{model_name} seat allocation did not total to the expected chamber size")

    return seat_allocations, winners, seats_by_party


def main() -> None:
    candidate_rows = read_csv(PREPARED_DATA_DIR / "dpr_candidates_standardized.csv")
    dapil_seat_rows = read_csv(PREPARED_DATA_DIR / "dapil_seats.csv")

    seat_map = {(row["province"], row["district"]): parse_int(row["seat_count"]) for row in dapil_seat_rows}
    candidates_by_slate: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    slate_stats: dict[tuple[str, str, str], dict[str, object]] = {}

    for row in candidate_rows:
        province = row["province"]
        district = row["district"]
        key = slate_key(province, district, row["party_code"])
        candidate_vote = parse_int(row["candidate_vote"])
        party_vote = parse_int(row["party_vote"])
        candidate_number = parse_int(row["candidate_number"])
        party_number = parse_int(row["party_number"])

        candidates_by_slate[key].append(
            {
                "province": province,
                "district": district,
                "party_code": row["party_code"],
                "party_name": row["party_name"],
                "party_number": party_number,
                "candidate_number": candidate_number,
                "candidate_name": row["candidate_name"],
                "candidate_vote": candidate_vote,
            }
        )

        slate = slate_stats.setdefault(
            key,
            {
                "province": province,
                "district": district,
                "party_code": row["party_code"],
                "party_name": row["party_name"],
                "party_number": party_number,
                "party_vote": party_vote,
                "candidate_vote_total": 0,
                "total_votes": 0,
                "candidate_count": 0,
            },
        )
        if int(slate["party_vote"]) != party_vote:
            raise ValueError(f"Inconsistent party vote for slate {key}")
        slate["candidate_vote_total"] = int(slate["candidate_vote_total"]) + candidate_vote
        slate["total_votes"] = int(slate["party_vote"]) + int(slate["candidate_vote_total"])
        slate["candidate_count"] = int(slate["candidate_count"]) + 1

    district_party_rows: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    national_votes_by_party: Counter[tuple[str, str]] = Counter()
    party_number_by_code: dict[str, int] = {}
    for slate in slate_stats.values():
        district_party_rows[(str(slate["province"]), str(slate["district"]))].append(slate)
        party_key = (str(slate["party_code"]), str(slate["party_name"]))
        national_votes_by_party[party_key] += int(slate["total_votes"])
        party_number_by_code[str(slate["party_code"])] = int(slate["party_number"])

    total_national_valid_votes = sum(national_votes_by_party.values())
    threshold_status_rows = []
    threshold_status_lookup: dict[str, dict[str, object]] = {}
    qualified_party_codes: set[str] = set()

    for (party_code, party_name), votes in sorted(
        national_votes_by_party.items(), key=lambda item: (-item[1], party_number_by_code[item[0][0]], item[0][0])
    ):
        share = votes / total_national_valid_votes if total_national_valid_votes else None
        passes_threshold = share is not None and share >= PARLIAMENTARY_THRESHOLD
        if passes_threshold:
            qualified_party_codes.add(party_code)
        row = {
            "party_code": party_code,
            "party_name": party_name,
            "party_number": party_number_by_code[party_code],
            "national_valid_votes": votes,
            "national_vote_share": format_float(share),
            "passes_dpr_threshold": "true" if passes_threshold else "false",
            "threshold_percent": format_float(PARLIAMENTARY_THRESHOLD),
            "excluded_from_dpr_seat_allocation": "false" if passes_threshold else "true",
            "threshold_scope": "DPR only; DPRD seats are not filtered by the national parliamentary threshold.",
        }
        threshold_status_rows.append(row)
        threshold_status_lookup[party_code] = row

    raw_seat_allocations, raw_winners, raw_seats_by_party = build_model_outputs(
        district_party_rows,
        candidates_by_slate,
        seat_map,
        eligible_party_codes=None,
        model_name="raw_all_parties",
    )
    threshold_seat_allocations, threshold_winners, threshold_seats_by_party = build_model_outputs(
        district_party_rows,
        candidates_by_slate,
        seat_map,
        eligible_party_codes=qualified_party_codes,
        model_name="threshold_adjusted",
    )

    raw_seat_lookup = {
        slate_key(row["province"], row["district"], row["party_code"]): parse_int(row["seats_won"]) for row in raw_seat_allocations
    }
    threshold_seat_lookup = {
        slate_key(row["province"], row["district"], row["party_code"]): parse_int(row["seats_won"])
        for row in threshold_seat_allocations
    }
    raw_winner_lookup = {winner_key(row): row for row in raw_winners}
    threshold_winner_lookup = {winner_key(row): row for row in threshold_winners}

    default_seat_rows = []
    raw_seat_rows = []
    for row in threshold_seat_allocations:
        key = slate_key(row["province"], row["district"], row["party_code"])
        raw_seats = raw_seat_lookup[key]
        status_row = threshold_status_lookup[row["party_code"]]
        default_seat_rows.append(
            {
                **row,
                "passes_dpr_threshold": status_row["passes_dpr_threshold"],
                "national_valid_votes": status_row["national_valid_votes"],
                "national_vote_share": status_row["national_vote_share"],
                "seats_won_raw": raw_seats,
                "seat_delta": parse_int(row["seats_won"]) - raw_seats,
            }
        )
    for row in raw_seat_allocations:
        key = slate_key(row["province"], row["district"], row["party_code"])
        threshold_seats = threshold_seat_lookup[key]
        status_row = threshold_status_lookup[row["party_code"]]
        raw_seat_rows.append(
            {
                **row,
                "passes_dpr_threshold": status_row["passes_dpr_threshold"],
                "national_valid_votes": status_row["national_valid_votes"],
                "national_vote_share": status_row["national_vote_share"],
                "seats_won_threshold": threshold_seats,
                "seat_delta_threshold_vs_raw": threshold_seats - parse_int(row["seats_won"]),
            }
        )

    default_winner_rows = []
    raw_winner_rows = []
    for row in threshold_winners:
        key = winner_key(row)
        raw_row = raw_winner_lookup.get(key)
        status_row = threshold_status_lookup[row["party_code"]]
        default_winner_rows.append(
            {
                **row,
                "passes_dpr_threshold": status_row["passes_dpr_threshold"],
                "national_vote_share": status_row["national_vote_share"],
                "raw_winner": "true" if raw_row else "false",
            }
        )
    for row in raw_winners:
        key = winner_key(row)
        threshold_row = threshold_winner_lookup.get(key)
        status_row = threshold_status_lookup[row["party_code"]]
        raw_winner_rows.append(
            {
                **row,
                "passes_dpr_threshold": status_row["passes_dpr_threshold"],
                "national_vote_share": status_row["national_vote_share"],
                "threshold_winner": "true" if threshold_row else "false",
            }
        )

    winner_change_rows = []
    replacement_rows = []
    displaced_rows = []
    for key, row in threshold_winner_lookup.items():
        if key in raw_winner_lookup:
            continue
        party_key = (row["party_code"], row["party_name"])
        status_row = threshold_status_lookup[row["party_code"]]
        change_row = {
            "province": row["province"],
            "district": row["district"],
            "seat_count": row["seat_count"],
            "party_number": row["party_number"],
            "party_code": row["party_code"],
            "party_name": row["party_name"],
            "candidate_number": row["candidate_number"],
            "candidate_name": row["candidate_name"],
            "candidate_vote": row["candidate_vote"],
            "party_vote": row["party_vote"],
            "total_votes": row["total_votes"],
            "raw_list_position": "",
            "threshold_list_position": row["list_position"],
            "raw_winner": "false",
            "threshold_winner": "true",
            "change_type": "replacement_winner",
            "change_reason": "Entered the DPR winning set after parties below the 4% national threshold were removed and seats were reallocated among threshold-passing parties.",
            "passes_dpr_threshold": status_row["passes_dpr_threshold"],
            "national_vote_share": status_row["national_vote_share"],
            "party_seats_raw": raw_seats_by_party.get(party_key, 0),
            "party_seats_threshold": threshold_seats_by_party.get(party_key, 0),
            "party_seat_delta": threshold_seats_by_party.get(party_key, 0) - raw_seats_by_party.get(party_key, 0),
        }
        winner_change_rows.append(change_row)
        replacement_rows.append(change_row)

    for key, row in raw_winner_lookup.items():
        if key in threshold_winner_lookup:
            continue
        party_key = (row["party_code"], row["party_name"])
        status_row = threshold_status_lookup[row["party_code"]]
        disqualified_party = status_row["passes_dpr_threshold"] == "false"
        reason = (
            "Would be a winner in the raw all-party simulation, but the party fell below the 4% national DPR threshold."
            if disqualified_party
            else "Lost the seat after threshold-driven reallocation among eligible parties."
        )
        change_row = {
            "province": row["province"],
            "district": row["district"],
            "seat_count": row["seat_count"],
            "party_number": row["party_number"],
            "party_code": row["party_code"],
            "party_name": row["party_name"],
            "candidate_number": row["candidate_number"],
            "candidate_name": row["candidate_name"],
            "candidate_vote": row["candidate_vote"],
            "party_vote": row["party_vote"],
            "total_votes": row["total_votes"],
            "raw_list_position": row["list_position"],
            "threshold_list_position": "",
            "raw_winner": "true",
            "threshold_winner": "false",
            "change_type": "displaced_winner",
            "change_reason": reason,
            "passes_dpr_threshold": status_row["passes_dpr_threshold"],
            "national_vote_share": status_row["national_vote_share"],
            "party_seats_raw": raw_seats_by_party.get(party_key, 0),
            "party_seats_threshold": threshold_seats_by_party.get(party_key, 0),
            "party_seat_delta": threshold_seats_by_party.get(party_key, 0) - raw_seats_by_party.get(party_key, 0),
        }
        winner_change_rows.append(change_row)
        displaced_rows.append(change_row)

    winner_change_rows.sort(
        key=lambda row: (
            row["province"],
            row["district"],
            row["change_type"],
            -parse_int(str(row["candidate_vote"])),
            row["candidate_name"],
        )
    )

    district_change_lookup: dict[tuple[str, str], dict[str, list[dict[str, object]]]] = defaultdict(
        lambda: {"replacement": [], "displaced": []}
    )
    for row in replacement_rows:
        district_change_lookup[(str(row["province"]), str(row["district"]))]["replacement"].append(row)
    for row in displaced_rows:
        district_change_lookup[(str(row["province"]), str(row["district"]))]["displaced"].append(row)

    district_impact_rows = []
    affected_districts = 0
    for district_key, party_rows in sorted(district_party_rows.items()):
        province, district = district_key
        district_total_votes = sum(int(row["total_votes"]) for row in party_rows)
        disqualified_rows = [
            row for row in party_rows if threshold_status_lookup[str(row["party_code"])]["passes_dpr_threshold"] == "false"
        ]
        disqualified_votes = sum(int(row["total_votes"]) for row in disqualified_rows)
        raw_seats_lost = sum(raw_seat_lookup[slate_key(province, district, str(row["party_code"]))] for row in disqualified_rows)
        replacement_count = len(district_change_lookup[district_key]["replacement"])
        displaced_count = len(district_change_lookup[district_key]["displaced"])
        seat_delta_rows = [
            row for row in default_seat_rows if row["province"] == province and row["district"] == district and int(row["seat_delta"]) != 0
        ]
        parties_gaining = sorted({str(row["party_code"]) for row in seat_delta_rows if int(row["seat_delta"]) > 0})
        parties_losing = sorted({str(row["party_code"]) for row in seat_delta_rows if int(row["seat_delta"]) < 0})
        top_disqualified = max(disqualified_rows, key=lambda row: int(row["total_votes"]), default=None)
        threshold_changed = raw_seats_lost > 0 or replacement_count > 0 or displaced_count > 0
        if threshold_changed:
            affected_districts += 1
        district_impact_rows.append(
            {
                "province": province,
                "district": district,
                "seat_count": seat_map[district_key],
                "district_total_votes": district_total_votes,
                "disqualified_party_votes": disqualified_votes,
                "disqualified_vote_share": format_float(disqualified_votes / district_total_votes if district_total_votes else None),
                "disqualified_parties": ",".join(sorted(str(row["party_code"]) for row in disqualified_rows)),
                "raw_seats_lost_to_threshold": raw_seats_lost,
                "replacement_winners": replacement_count,
                "displaced_winners": displaced_count,
                "parties_gaining_seats": ",".join(parties_gaining),
                "parties_losing_seats": ",".join(parties_losing),
                "top_disqualified_party": str(top_disqualified["party_code"]) if top_disqualified else "",
                "top_disqualified_party_votes": int(top_disqualified["total_votes"]) if top_disqualified else 0,
                "threshold_changed": "true" if threshold_changed else "false",
            }
        )

    total_seats = sum(parse_int(row["seat_count"]) for row in dapil_seat_rows)
    excluded_votes = sum(
        parse_int(str(row["national_valid_votes"]))
        for row in threshold_status_rows
        if row["passes_dpr_threshold"] == "false"
    )

    if sum(parse_int(str(row["estimated_seats"])) for row in []) != 0:
        raise AssertionError("Unexpected internal party summary accumulator state")

    party_summary_rows = []
    raw_party_summary_rows = []
    for status_row in threshold_status_rows:
        party_key = (str(status_row["party_code"]), str(status_row["party_name"]))
        threshold_seats = threshold_seats_by_party.get(party_key, 0)
        raw_seats = raw_seats_by_party.get(party_key, 0)
        party_summary_rows.append(
            {
                "party_code": status_row["party_code"],
                "party_name": status_row["party_name"],
                "party_number": status_row["party_number"],
                "national_valid_votes": status_row["national_valid_votes"],
                "national_vote_share": status_row["national_vote_share"],
                "passes_dpr_threshold": status_row["passes_dpr_threshold"],
                "estimated_seats": threshold_seats,
                "estimated_seats_raw": raw_seats,
                "seat_delta": threshold_seats - raw_seats,
            }
        )
        raw_party_summary_rows.append(
            {
                "party_code": status_row["party_code"],
                "party_name": status_row["party_name"],
                "party_number": status_row["party_number"],
                "national_valid_votes": status_row["national_valid_votes"],
                "national_vote_share": status_row["national_vote_share"],
                "passes_dpr_threshold": status_row["passes_dpr_threshold"],
                "estimated_seats": raw_seats,
                "estimated_seats_threshold": threshold_seats,
                "seat_delta_threshold_vs_raw": threshold_seats - raw_seats,
            }
        )

    party_summary_rows.sort(
        key=lambda row: (-parse_int(str(row["estimated_seats"])), -parse_int(str(row["estimated_seats_raw"])), -parse_int(str(row["national_valid_votes"])), str(row["party_code"]))
    )
    raw_party_summary_rows.sort(
        key=lambda row: (-parse_int(str(row["estimated_seats"])), -parse_int(str(row["estimated_seats_threshold"])), -parse_int(str(row["national_valid_votes"])), str(row["party_code"]))
    )

    if sum(int(row["estimated_seats"]) for row in party_summary_rows) != total_seats:
        raise AssertionError("Threshold-adjusted party seats do not sum to 580")
    if sum(int(row["estimated_seats"]) for row in raw_party_summary_rows) != total_seats:
        raise AssertionError("Raw party seats do not sum to 580")
    if any(row["passes_dpr_threshold"] == "false" and int(row["estimated_seats"]) > 0 for row in party_summary_rows):
        raise AssertionError("A sub-threshold party still received seats in the legal DPR model")

    summary = {
        "threshold_percent": format_float(PARLIAMENTARY_THRESHOLD),
        "default_model": "threshold_adjusted",
        "districts": len(district_party_rows),
        "total_seats": total_seats,
        "qualified_parties": sum(1 for row in threshold_status_rows if row["passes_dpr_threshold"] == "true"),
        "disqualified_parties": sum(1 for row in threshold_status_rows if row["passes_dpr_threshold"] == "false"),
        "excluded_votes": excluded_votes,
        "excluded_vote_share": format_float(excluded_votes / total_national_valid_votes if total_national_valid_votes else None),
        "replacement_winners": len(replacement_rows),
        "displaced_winners": len(displaced_rows),
        "affected_districts": affected_districts,
        "raw": {
            "winning_candidates": len(raw_winners),
            "parties_winning_seats": sum(1 for row in raw_party_summary_rows if int(row["estimated_seats"]) > 0),
        },
        "threshold_adjusted": {
            "winning_candidates": len(threshold_winners),
            "parties_winning_seats": sum(1 for row in party_summary_rows if int(row["estimated_seats"]) > 0),
        },
        "notes": [
            "The 4% national parliamentary threshold applies to DPR seat allocation only.",
            "The threshold-adjusted outputs are the default legal DPR model for this repo.",
            "Raw all-party seat outputs are kept alongside the legal model for transparency and comparison.",
        ],
    }

    with (OUTPUT_DIR / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    write_csv(
        OUTPUT_DIR / "party_threshold_status.csv",
        [
            "party_code",
            "party_name",
            "party_number",
            "national_valid_votes",
            "national_vote_share",
            "passes_dpr_threshold",
            "threshold_percent",
            "excluded_from_dpr_seat_allocation",
            "threshold_scope",
        ],
        threshold_status_rows,
    )
    write_csv(
        OUTPUT_DIR / "estimated_seats_by_district_party.csv",
        [
            "province",
            "district",
            "seat_count",
            "party_number",
            "party_code",
            "party_name",
            "party_vote",
            "candidate_vote_total",
            "total_votes",
            "candidate_count",
            "seats_won",
            "seat_allocation_model",
            "passes_dpr_threshold",
            "national_valid_votes",
            "national_vote_share",
            "seats_won_raw",
            "seat_delta",
        ],
        default_seat_rows,
    )
    write_csv(
        OUTPUT_DIR / "estimated_seats_by_district_party_raw.csv",
        [
            "province",
            "district",
            "seat_count",
            "party_number",
            "party_code",
            "party_name",
            "party_vote",
            "candidate_vote_total",
            "total_votes",
            "candidate_count",
            "seats_won",
            "seat_allocation_model",
            "passes_dpr_threshold",
            "national_valid_votes",
            "national_vote_share",
            "seats_won_threshold",
            "seat_delta_threshold_vs_raw",
        ],
        raw_seat_rows,
    )
    write_csv(
        OUTPUT_DIR / "estimated_winners.csv",
        [
            "province",
            "district",
            "seat_count",
            "party_number",
            "party_code",
            "party_name",
            "party_vote",
            "total_votes",
            "candidate_number",
            "candidate_name",
            "candidate_vote",
            "list_position",
            "candidate_vote_share_of_party_total",
            "winner_model",
            "passes_dpr_threshold",
            "national_vote_share",
            "raw_winner",
        ],
        default_winner_rows,
    )
    write_csv(
        OUTPUT_DIR / "estimated_winners_raw.csv",
        [
            "province",
            "district",
            "seat_count",
            "party_number",
            "party_code",
            "party_name",
            "party_vote",
            "total_votes",
            "candidate_number",
            "candidate_name",
            "candidate_vote",
            "list_position",
            "candidate_vote_share_of_party_total",
            "winner_model",
            "passes_dpr_threshold",
            "national_vote_share",
            "threshold_winner",
        ],
        raw_winner_rows,
    )
    write_csv(
        OUTPUT_DIR / "estimated_seats_by_party.csv",
        [
            "party_code",
            "party_name",
            "party_number",
            "national_valid_votes",
            "national_vote_share",
            "passes_dpr_threshold",
            "estimated_seats",
            "estimated_seats_raw",
            "seat_delta",
        ],
        party_summary_rows,
    )
    write_csv(
        OUTPUT_DIR / "estimated_seats_by_party_raw.csv",
        [
            "party_code",
            "party_name",
            "party_number",
            "national_valid_votes",
            "national_vote_share",
            "passes_dpr_threshold",
            "estimated_seats",
            "estimated_seats_threshold",
            "seat_delta_threshold_vs_raw",
        ],
        raw_party_summary_rows,
    )
    write_csv(
        OUTPUT_DIR / "winner_changes.csv",
        [
            "province",
            "district",
            "seat_count",
            "party_number",
            "party_code",
            "party_name",
            "candidate_number",
            "candidate_name",
            "candidate_vote",
            "party_vote",
            "total_votes",
            "raw_list_position",
            "threshold_list_position",
            "raw_winner",
            "threshold_winner",
            "change_type",
            "change_reason",
            "passes_dpr_threshold",
            "national_vote_share",
            "party_seats_raw",
            "party_seats_threshold",
            "party_seat_delta",
        ],
        winner_change_rows,
    )
    write_csv(
        OUTPUT_DIR / "replacement_winners.csv",
        replacement_fieldnames := [
            "province",
            "district",
            "seat_count",
            "party_number",
            "party_code",
            "party_name",
            "candidate_number",
            "candidate_name",
            "candidate_vote",
            "party_vote",
            "total_votes",
            "threshold_list_position",
            "change_reason",
            "passes_dpr_threshold",
            "national_vote_share",
            "party_seats_raw",
            "party_seats_threshold",
            "party_seat_delta",
        ],
        [select_fields(row, replacement_fieldnames) for row in replacement_rows],
    )
    write_csv(
        OUTPUT_DIR / "displaced_winners.csv",
        displaced_fieldnames := [
            "province",
            "district",
            "seat_count",
            "party_number",
            "party_code",
            "party_name",
            "candidate_number",
            "candidate_name",
            "candidate_vote",
            "party_vote",
            "total_votes",
            "raw_list_position",
            "change_reason",
            "passes_dpr_threshold",
            "national_vote_share",
            "party_seats_raw",
            "party_seats_threshold",
            "party_seat_delta",
        ],
        [select_fields(row, displaced_fieldnames) for row in displaced_rows],
    )
    write_csv(
        OUTPUT_DIR / "district_threshold_impact.csv",
        [
            "province",
            "district",
            "seat_count",
            "district_total_votes",
            "disqualified_party_votes",
            "disqualified_vote_share",
            "disqualified_parties",
            "raw_seats_lost_to_threshold",
            "replacement_winners",
            "displaced_winners",
            "parties_gaining_seats",
            "parties_losing_seats",
            "top_disqualified_party",
            "top_disqualified_party_votes",
            "threshold_changed",
        ],
        district_impact_rows,
    )

    print("Wrote estimated DPR winner outputs to", OUTPUT_DIR)
    print("Total seats:", sum(int(row["estimated_seats"]) for row in party_summary_rows))
    print(
        "Threshold summary:",
        {
            "qualified_parties": summary["qualified_parties"],
            "excluded_vote_share": summary["excluded_vote_share"],
            "replacement_winners": summary["replacement_winners"],
        },
    )


if __name__ == "__main__":
    main()
