#!/usr/bin/env python3
"""Python port of the core representation-gap analysis."""
from __future__ import annotations

import json
from collections import Counter, defaultdict

from common import (
    PREPARED_DATA_DIR,
    PYTHON_OUTPUT_DIR,
    ensure_dir,
    format_float,
    median_or_none,
    parse_int,
    read_csv,
    write_csv,
)


OUTPUT_DIR = ensure_dir(PYTHON_OUTPUT_DIR / "representation_gap")


def main() -> None:
    candidate_rows = read_csv(PREPARED_DATA_DIR / "dpr_candidates_standardized.csv")
    seat_rows = read_csv(PYTHON_OUTPUT_DIR / "dpr_estimated_winners" / "estimated_seats_by_district_party.csv")

    seat_lookup = {}
    district_total_votes = Counter()
    party_vote_rows = {}
    candidates_by_slate = defaultdict(list)

    for row in seat_rows:
        key = (row["province"], row["district"], row["party_code"])
        seats_won = parse_int(row["seats_won"])
        total_votes = parse_int(row["total_votes"])
        seat_lookup[key] = seats_won
        district_total_votes[(row["province"], row["district"])] += total_votes
        party_vote_rows[key] = {
            "province": row["province"],
            "district": row["district"],
            "party_code": row["party_code"],
            "party_name": row["party_name"],
            "total_votes": total_votes,
            "seats_won": seats_won,
        }

    for row in candidate_rows:
        key = (row["province"], row["district"], row["party_code"])
        candidates_by_slate[key].append(
            {
                "province": row["province"],
                "district": row["district"],
                "party_code": row["party_code"],
                "party_name": row["party_name"],
                "candidate_name": row["candidate_name"],
                "candidate_number": parse_int(row["candidate_number"]),
                "candidate_vote": parse_int(row["candidate_vote"]),
            }
        )

    winning_candidate_rows = []
    coverage_acc = defaultdict(lambda: {"winning_votes": 0, "seats": 0, "parties": set()})
    party_winning_votes = Counter()
    seat_count_by_party = Counter()
    total_votes_by_party = Counter()

    for key, slate_meta in party_vote_rows.items():
        province, district, party_code = key
        party_name = slate_meta["party_name"]
        seats_won = int(slate_meta["seats_won"])
        total_votes = int(slate_meta["total_votes"])
        total_votes_by_party[(party_code, party_name)] += total_votes
        seat_count_by_party[(party_code, party_name)] += seats_won

        if seats_won <= 0:
            continue

        district_total = district_total_votes[(province, district)]
        ranked_candidates = sorted(
            candidates_by_slate[key],
            key=lambda item: (-item["candidate_vote"], item["candidate_name"], item["candidate_number"]),
        )

        for list_position, candidate in enumerate(ranked_candidates, start=1):
            if list_position > seats_won:
                break
            vote_share_district = candidate["candidate_vote"] / district_total if district_total else None
            vote_share_party = candidate["candidate_vote"] / total_votes if total_votes else None
            winning_candidate_rows.append(
                {
                    "province": province,
                    "district": district,
                    "party_code": party_code,
                    "party_name": party_name,
                    "candidate_name": candidate["candidate_name"],
                    "candidate_vote": candidate["candidate_vote"],
                    "district_total_votes": district_total,
                    "party_total_votes": total_votes,
                    "list_position": list_position,
                    "vote_share_district": format_float(vote_share_district),
                    "vote_share_party": format_float(vote_share_party),
                }
            )
            coverage_acc[(province, district)]["winning_votes"] += candidate["candidate_vote"]
            coverage_acc[(province, district)]["seats"] += 1
            coverage_acc[(province, district)]["parties"].add(party_code)
            party_winning_votes[(party_code, party_name)] += candidate["candidate_vote"]

    coverage_rows = []
    coverages = []
    for (province, district), acc in sorted(coverage_acc.items()):
        district_total = district_total_votes[(province, district)]
        coverage = acc["winning_votes"] / district_total if district_total else None
        residual = (1 - coverage) if coverage is not None else None
        if coverage is not None:
            coverages.append(coverage)
        coverage_rows.append(
            {
                "province": province,
                "district": district,
                "district_total_votes": district_total,
                "winning_candidate_votes": acc["winning_votes"],
                "coverage": format_float(coverage),
                "residual": format_float(residual),
                "seats": acc["seats"],
                "parties": len(acc["parties"]),
            }
        )

    province_rows = []
    province_acc = defaultdict(lambda: {"coverage_sum": 0.0, "districts": 0})
    for row in coverage_rows:
        coverage = float(row["coverage"]) if row["coverage"] else 0.0
        province_acc[row["province"]]["coverage_sum"] += coverage
        province_acc[row["province"]]["districts"] += 1
    for province, acc in sorted(province_acc.items()):
        province_rows.append(
            {
                "province": province,
                "districts": acc["districts"],
                "avg_coverage": format_float(acc["coverage_sum"] / acc["districts"]),
            }
        )

    total_seats = sum(seat_count_by_party.values())
    total_votes_all = sum(total_votes_by_party.values())
    party_distortion_rows = []
    for (party_code, party_name), total_votes in sorted(total_votes_by_party.items()):
        seats_won = seat_count_by_party[(party_code, party_name)]
        aggregate_winning_votes = party_winning_votes[(party_code, party_name)]
        seat_share = seats_won / total_seats if total_seats else None
        vote_share = total_votes / total_votes_all if total_votes_all else None
        seat_minus_vote = (seat_share - vote_share) if seat_share is not None and vote_share is not None else None
        avg_winning_mandate = aggregate_winning_votes / seats_won if seats_won else None
        party_distortion_rows.append(
            {
                "party_code": party_code,
                "party_name": party_name,
                "total_votes": total_votes,
                "seats_won": seats_won,
                "aggregate_winning_votes": aggregate_winning_votes,
                "seat_share": format_float(seat_share),
                "vote_share": format_float(vote_share),
                "seat_minus_vote": format_float(seat_minus_vote),
                "avg_winning_mandate": format_float(avg_winning_mandate),
            }
        )
    party_distortion_rows.sort(key=lambda item: float(item["seat_minus_vote"]), reverse=True)

    coverage_rows_sorted = sorted(coverage_rows, key=lambda item: float(item["coverage"]))
    with (OUTPUT_DIR / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "districts": len(coverage_rows),
                "winning_candidates": len(winning_candidate_rows),
                "avg_coverage": format_float(sum(coverages) / len(coverages) if coverages else None),
                "median_coverage": format_float(median_or_none(coverages)),
                "min_coverage": format_float(min(coverages) if coverages else None),
                "max_coverage": format_float(max(coverages) if coverages else None),
            },
            handle,
            indent=2,
        )

    write_csv(
        OUTPUT_DIR / "winning_candidates_with_shares.csv",
        [
            "province",
            "district",
            "party_code",
            "party_name",
            "candidate_name",
            "candidate_vote",
            "district_total_votes",
            "party_total_votes",
            "list_position",
            "vote_share_district",
            "vote_share_party",
        ],
        winning_candidate_rows,
    )
    write_csv(
        OUTPUT_DIR / "coverage_by_district.csv",
        [
            "province",
            "district",
            "district_total_votes",
            "winning_candidate_votes",
            "coverage",
            "residual",
            "seats",
            "parties",
        ],
        coverage_rows,
    )
    write_csv(
        OUTPUT_DIR / "lowest_coverage_districts.csv",
        [
            "province",
            "district",
            "district_total_votes",
            "winning_candidate_votes",
            "coverage",
            "residual",
            "seats",
            "parties",
        ],
        coverage_rows_sorted[:20],
    )
    write_csv(
        OUTPUT_DIR / "coverage_by_province.csv",
        ["province", "districts", "avg_coverage"],
        province_rows,
    )
    write_csv(
        OUTPUT_DIR / "party_distortion.csv",
        [
            "party_code",
            "party_name",
            "total_votes",
            "seats_won",
            "aggregate_winning_votes",
            "seat_share",
            "vote_share",
            "seat_minus_vote",
            "avg_winning_mandate",
        ],
        party_distortion_rows,
    )

    print("Wrote representation gap outputs to", OUTPUT_DIR)
    print(
        "Coverage summary:",
        {
            "districts": len(coverage_rows),
            "avg_coverage": format_float(sum(coverages) / len(coverages) if coverages else None),
            "median_coverage": format_float(median_or_none(coverages)),
        },
    )


if __name__ == "__main__":
    main()
