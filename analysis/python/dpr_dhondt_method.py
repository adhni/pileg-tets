#!/usr/bin/env python3
"""Compare the current DPR Sainte-Lague rule with a D'Hondt alternative."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from common import PREPARED_DATA_DIR, PYTHON_OUTPUT_DIR, ROOT, ensure_dir, format_float, parse_int, read_csv, write_csv


OUTPUT_DIR = ensure_dir(PYTHON_OUTPUT_DIR / "dpr_dhondt_method")
REFERENCE_INPUT_DIR = ROOT / "analysis" / "reference" / "dashboard_inputs"
PARLIAMENTARY_THRESHOLD = 0.04


def resolve_input_path(filename: str) -> Path:
    prepared_path = PREPARED_DATA_DIR / filename
    if prepared_path.exists():
        return prepared_path
    reference_path = REFERENCE_INPUT_DIR / filename
    if reference_path.exists():
        return reference_path
    raise FileNotFoundError(f"Missing required input file: {filename}")


def allocate_sainte_lague(party_rows: list[dict[str, object]], seat_count: int) -> dict[str, int]:
    quotients: list[tuple[float, int, str]] = []
    for row in party_rows:
        total_votes = int(row["total_votes"])
        if total_votes <= 0:
            continue
        for divisor in range(1, 2 * seat_count, 2):
            quotients.append((total_votes / divisor, int(row["party_number"]), str(row["party_code"])))
    quotients.sort(key=lambda item: (-item[0], item[1], item[2]))
    winners = quotients[:seat_count]
    return dict(Counter(item[2] for item in winners))


def allocate_dhondt(party_rows: list[dict[str, object]], seat_count: int) -> dict[str, int]:
    quotients: list[tuple[float, int, str]] = []
    for row in party_rows:
        total_votes = int(row["total_votes"])
        if total_votes <= 0:
            continue
        for divisor in range(1, seat_count + 1):
            quotients.append((total_votes / divisor, int(row["party_number"]), str(row["party_code"])))
    quotients.sort(key=lambda item: (-item[0], item[1], item[2]))
    winners = quotients[:seat_count]
    return dict(Counter(item[2] for item in winners))


def slate_key(province: str, district: str, party_code: str) -> tuple[str, str, str]:
    return (province, district, party_code)


def build_model_outputs(
    district_party_rows: dict[tuple[str, str], list[dict[str, object]]],
    candidates_by_slate: dict[tuple[str, str, str], list[dict[str, object]]],
    seat_map: dict[tuple[str, str], int],
    eligible_party_codes: set[str],
) -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    Counter[tuple[str, str]],
    Counter[tuple[str, str]],
]:
    district_rows: list[dict[str, object]] = []
    sainte_winners: list[dict[str, object]] = []
    dhondt_winners: list[dict[str, object]] = []
    sainte_by_party: Counter[tuple[str, str]] = Counter()
    dhondt_by_party: Counter[tuple[str, str]] = Counter()

    for district_key, party_rows in sorted(district_party_rows.items()):
        province, district = district_key
        seat_count = seat_map[district_key]
        eligible_rows = [row for row in party_rows if str(row["party_code"]) in eligible_party_codes]
        if not eligible_rows:
            raise ValueError(f"No eligible parties for seat allocation in {district_key}")

        district_total_votes = sum(int(row["total_votes"]) for row in eligible_rows)
        sainte_seats = allocate_sainte_lague(eligible_rows, seat_count)
        dhondt_seats = allocate_dhondt(eligible_rows, seat_count)

        if sum(sainte_seats.values()) != seat_count:
            raise AssertionError(f"Sainte-Lague model failed to fill all seats in {district_key}")
        if sum(dhondt_seats.values()) != seat_count:
            raise AssertionError(f"D'Hondt model failed to fill all seats in {district_key}")

        for row in sorted(eligible_rows, key=lambda item: (int(item["party_number"]), str(item["party_code"]))):
            party_code = str(row["party_code"])
            party_name = str(row["party_name"])
            sainte_count = sainte_seats.get(party_code, 0)
            dhondt_count = dhondt_seats.get(party_code, 0)
            district_rows.append(
                {
                    "province": province,
                    "district": district,
                    "seat_count": seat_count,
                    "district_total_votes": district_total_votes,
                    "party_number": row["party_number"],
                    "party_code": party_code,
                    "party_name": party_name,
                    "total_votes": row["total_votes"],
                    "vote_share": format_float(int(row["total_votes"]) / district_total_votes if district_total_votes else None),
                    "seats_sainte_lague": sainte_count,
                    "seats_dhondt": dhondt_count,
                    "seat_delta": dhondt_count - sainte_count,
                }
            )
            sainte_by_party[(party_code, party_name)] += sainte_count
            dhondt_by_party[(party_code, party_name)] += dhondt_count

            ranked_candidates = sorted(
                candidates_by_slate[(province, district, party_code)],
                key=lambda item: (-int(item["candidate_vote"]), str(item["candidate_name"]), int(item["candidate_number"])),
            )
            for list_position, candidate in enumerate(ranked_candidates, start=1):
                if list_position <= sainte_count:
                    sainte_winners.append(
                        {
                            "province": province,
                            "district": district,
                            "party_code": party_code,
                            "party_name": party_name,
                            "candidate_number": candidate["candidate_number"],
                            "candidate_name": candidate["candidate_name"],
                            "candidate_vote": candidate["candidate_vote"],
                            "list_position": list_position,
                            "winner_model": "sainte_lague",
                        }
                    )
                if list_position <= dhondt_count:
                    dhondt_winners.append(
                        {
                            "province": province,
                            "district": district,
                            "party_code": party_code,
                            "party_name": party_name,
                            "candidate_number": candidate["candidate_number"],
                            "candidate_name": candidate["candidate_name"],
                            "candidate_vote": candidate["candidate_vote"],
                            "list_position": list_position,
                            "winner_model": "dhondt",
                        }
                    )

    return district_rows, sainte_winners, dhondt_winners, sainte_by_party, dhondt_by_party


def main() -> None:
    candidate_rows = read_csv(resolve_input_path("dpr_candidates_standardized.csv"))
    seat_rows = read_csv(resolve_input_path("dapil_seats.csv"))

    seat_map = {(row["province"], row["district"]): parse_int(row["seat_count"]) for row in seat_rows}
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
    qualified_party_codes: set[str] = set()
    national_rows: list[dict[str, object]] = []
    for (party_code, party_name), votes in sorted(
        national_votes_by_party.items(), key=lambda item: (-item[1], party_number_by_code[item[0][0]], item[0][0])
    ):
        share = votes / total_national_valid_votes if total_national_valid_votes else None
        passes_threshold = share is not None and share >= PARLIAMENTARY_THRESHOLD
        if passes_threshold:
            qualified_party_codes.add(party_code)
        national_rows.append(
            {
                "party_code": party_code,
                "party_name": party_name,
                "party_number": party_number_by_code[party_code],
                "national_valid_votes": votes,
                "national_vote_share": format_float(share),
                "passes_dpr_threshold": "true" if passes_threshold else "false",
            }
        )

    district_rows, sainte_winners, dhondt_winners, sainte_by_party, dhondt_by_party = build_model_outputs(
        district_party_rows,
        candidates_by_slate,
        seat_map,
        qualified_party_codes,
    )

    national_summary_rows: list[dict[str, object]] = []
    for row in sorted(national_rows, key=lambda item: (int(item["party_number"]), str(item["party_code"]))):
        party_key = (str(row["party_code"]), str(row["party_name"]))
        sainte_count = int(sainte_by_party.get(party_key, 0))
        dhondt_count = int(dhondt_by_party.get(party_key, 0))
        national_summary_rows.append(
            {
                **row,
                "seats_sainte_lague": sainte_count,
                "seats_dhondt": dhondt_count,
                "seat_delta": dhondt_count - sainte_count,
            }
        )

    changed_districts = sorted(
        {
            (row["province"], row["district"])
            for row in district_rows
            if int(row["seat_delta"]) != 0
        }
    )
    top_gainers = sorted(
        [row for row in national_summary_rows if int(row["seat_delta"]) > 0],
        key=lambda item: (-int(item["seat_delta"]), -int(item["seats_dhondt"]), int(item["party_number"]), str(item["party_code"])),
    )
    top_losers = sorted(
        [row for row in national_summary_rows if int(row["seat_delta"]) < 0],
        key=lambda item: (int(item["seat_delta"]), -int(item["seats_dhondt"]), int(item["party_number"]), str(item["party_code"])),
    )

    write_csv(
        OUTPUT_DIR / "national_party_summary.csv",
        list(national_summary_rows[0].keys()),
        national_summary_rows,
    )
    write_csv(
        OUTPUT_DIR / "district_party_comparison.csv",
        list(district_rows[0].keys()),
        district_rows,
    )
    write_csv(
        OUTPUT_DIR / "dhondt_winners.csv",
        list(dhondt_winners[0].keys()),
        dhondt_winners,
    )
    write_csv(
        OUTPUT_DIR / "sainte_lague_winners.csv",
        list(sainte_winners[0].keys()),
        sainte_winners,
    )

    summary = {
        "method": "dhondt",
        "assumption": "Keeps the 4% national DPR threshold, then allocates seats in each dapil by D'Hondt divisors 1,2,3,4...",
        "input_paths": {
            "candidates": str(resolve_input_path("dpr_candidates_standardized.csv").relative_to(ROOT)),
            "dapil_seats": str(resolve_input_path("dapil_seats.csv").relative_to(ROOT)),
        },
        "total_dpr_seats": sum(int(row["seats_dhondt"]) for row in national_summary_rows),
        "changed_district_count": len(changed_districts),
        "changed_district_share": len(changed_districts) / len(seat_map) if seat_map else None,
        "top_gainers": [
            {
                "party_code": row["party_code"],
                "party_name": row["party_name"],
                "seat_delta": row["seat_delta"],
                "seats_dhondt": row["seats_dhondt"],
            }
            for row in top_gainers[:5]
        ],
        "top_losers": [
            {
                "party_code": row["party_code"],
                "party_name": row["party_name"],
                "seat_delta": row["seat_delta"],
                "seats_dhondt": row["seats_dhondt"],
            }
            for row in top_losers[:5]
        ],
    }
    (OUTPUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("Built D'Hondt comparison outputs in", OUTPUT_DIR.relative_to(ROOT))
    print("Changed districts:", len(changed_districts), "of", len(seat_map))
    for row in top_gainers[:5]:
        print("GAIN", row["party_code"], row["seat_delta"], "=>", row["seats_dhondt"])
    for row in top_losers[:5]:
        print("LOSS", row["party_code"], row["seat_delta"], "=>", row["seats_dhondt"])


if __name__ == "__main__":
    main()
