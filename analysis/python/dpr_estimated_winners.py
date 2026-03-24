#!/usr/bin/env python3
"""Estimate DPR winners in Python using explicit dapil seat counts."""
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
    seats_won = Counter(item[1] for item in winners)
    return dict(seats_won)


def main() -> None:
    candidate_rows = read_csv(PREPARED_DATA_DIR / "dpr_candidates_standardized.csv")
    dapil_seat_rows = read_csv(PREPARED_DATA_DIR / "dapil_seats.csv")

    seat_map = {(row["province"], row["district"]): parse_int(row["seat_count"]) for row in dapil_seat_rows}
    candidates_by_slate = defaultdict(list)
    slate_stats = {}

    for row in candidate_rows:
        province = row["province"]
        district = row["district"]
        key = (province, district, row["party_code"])
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

    district_party_rows = defaultdict(list)
    for key, slate in slate_stats.items():
        district_party_rows[(slate["province"], slate["district"])].append(slate)

    seat_allocations = []
    winners = []
    seats_by_party = Counter()

    for district_key, party_rows in sorted(district_party_rows.items()):
        province, district = district_key
        if district_key not in seat_map:
            raise KeyError(f"Missing seat count for {district_key}")
        seat_count = seat_map[district_key]
        seats_won = allocate_sainte_lague(party_rows, seat_count)

        for row in sorted(party_rows, key=lambda item: (int(item["party_number"]), item["party_code"])):
            party_seats = seats_won.get(row["party_code"], 0)
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
                }
            )
            seats_by_party[(row["party_code"], row["party_name"])] += party_seats

            slate_candidates = sorted(
                candidates_by_slate[(province, district, row["party_code"])],
                key=lambda item: (-item["candidate_vote"], item["candidate_name"], item["candidate_number"]),
            )
            for list_position, candidate in enumerate(slate_candidates, start=1):
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
                            candidate["candidate_vote"] / int(row["total_votes"]) if int(row["total_votes"]) else None
                        ),
                    }
                )

    party_summary_rows = [
        {
            "party_code": party_code,
            "party_name": party_name,
            "estimated_seats": seat_total,
        }
        for (party_code, party_name), seat_total in sorted(
            seats_by_party.items(), key=lambda item: (-item[1], item[0][0])
        )
    ]

    with (OUTPUT_DIR / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "districts": len(district_party_rows),
                "total_seats": sum(parse_int(row["seat_count"]) for row in dapil_seat_rows),
                "winning_candidates": len(winners),
                "parties_winning_seats": sum(1 for row in party_summary_rows if row["estimated_seats"] > 0),
            },
            handle,
            indent=2,
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
        ],
        seat_allocations,
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
        ],
        winners,
    )
    write_csv(
        OUTPUT_DIR / "estimated_seats_by_party.csv",
        ["party_code", "party_name", "estimated_seats"],
        party_summary_rows,
    )

    print("Wrote estimated DPR winner outputs to", OUTPUT_DIR)
    print("Total seats:", sum(row["estimated_seats"] for row in party_summary_rows))


if __name__ == "__main__":
    main()
