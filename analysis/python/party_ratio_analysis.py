#!/usr/bin/env python3
"""Python port of the party ratio analysis."""
from __future__ import annotations

import json
from collections import defaultdict

from common import (
    PREPARED_DATA_DIR,
    PYTHON_OUTPUT_DIR,
    ensure_dir,
    format_float,
    parse_float,
    parse_int,
    read_csv,
    write_csv,
)


OUTPUT_DIR = ensure_dir(PYTHON_OUTPUT_DIR / "party_ratio_analysis")


def main() -> None:
    slate_rows = read_csv(PREPARED_DATA_DIR / "dpr_party_slates.csv")

    party_totals = defaultdict(lambda: {"party_name": "", "party_vote_total": 0, "candidate_vote_total": 0})
    province_totals = defaultdict(lambda: {"party_vote_total": 0, "candidate_vote_total": 0})
    party_province_totals = defaultdict(lambda: {"party_name": "", "party_vote_total": 0, "candidate_vote_total": 0})

    for row in slate_rows:
        province = row["province"]
        party_code = row["party_code"]
        party_name = row["party_name"]
        party_vote = parse_int(row["party_vote"])
        candidate_vote_total = parse_int(row["candidate_vote_total"])

        party_totals[party_code]["party_name"] = party_name
        party_totals[party_code]["party_vote_total"] += party_vote
        party_totals[party_code]["candidate_vote_total"] += candidate_vote_total

        province_totals[province]["party_vote_total"] += party_vote
        province_totals[province]["candidate_vote_total"] += candidate_vote_total

        party_province_totals[(province, party_code)]["party_name"] = party_name
        party_province_totals[(province, party_code)]["party_vote_total"] += party_vote
        party_province_totals[(province, party_code)]["candidate_vote_total"] += candidate_vote_total

    party_ratio_rows = []
    for party_code, totals in party_totals.items():
        party_vote_total = totals["party_vote_total"]
        candidate_vote_total = totals["candidate_vote_total"]
        ratio = party_vote_total / candidate_vote_total if candidate_vote_total else None
        share = party_vote_total / (party_vote_total + candidate_vote_total) if (party_vote_total + candidate_vote_total) else None
        party_ratio_rows.append(
            {
                "party_code": party_code,
                "party_name": totals["party_name"],
                "party_vote_total": party_vote_total,
                "candidate_vote_total": candidate_vote_total,
                "party_to_candidate_ratio": format_float(ratio),
                "party_vote_share_of_total": format_float(share),
            }
        )
    party_ratio_rows.sort(key=lambda item: float(item["party_to_candidate_ratio"]), reverse=True)

    province_ratio_rows = []
    for province, totals in province_totals.items():
        party_vote_total = totals["party_vote_total"]
        candidate_vote_total = totals["candidate_vote_total"]
        ratio = party_vote_total / candidate_vote_total if candidate_vote_total else None
        share = party_vote_total / (party_vote_total + candidate_vote_total) if (party_vote_total + candidate_vote_total) else None
        province_ratio_rows.append(
            {
                "province": province,
                "party_vote_total": party_vote_total,
                "candidate_vote_total": candidate_vote_total,
                "party_to_candidate_ratio": format_float(ratio),
                "party_vote_share_of_total": format_float(share),
            }
        )
    province_ratio_rows.sort(key=lambda item: float(item["party_to_candidate_ratio"]), reverse=True)

    party_province_ratio_rows = []
    for (province, party_code), totals in party_province_totals.items():
        party_vote_total = totals["party_vote_total"]
        candidate_vote_total = totals["candidate_vote_total"]
        ratio = party_vote_total / candidate_vote_total if candidate_vote_total else None
        share = party_vote_total / (party_vote_total + candidate_vote_total) if (party_vote_total + candidate_vote_total) else None
        party_province_ratio_rows.append(
            {
                "province": province,
                "party_code": party_code,
                "party_name": totals["party_name"],
                "party_vote_total": party_vote_total,
                "candidate_vote_total": candidate_vote_total,
                "party_to_candidate_ratio": format_float(ratio),
                "party_vote_share_of_total": format_float(share),
            }
        )
    party_province_ratio_rows.sort(
        key=lambda item: (item["province"], -float(item["party_to_candidate_ratio"]), item["party_code"])
    )

    psi_rows = [row for row in party_province_ratio_rows if row["party_code"] == "PSI"]
    psi_rows.sort(key=lambda item: float(item["party_vote_share_of_total"]), reverse=True)

    comparison_rows = [
        row for row in party_province_ratio_rows if row["party_code"] in {"PSI", "Buruh", "Perindo"}
    ]
    comparison_rows.sort(key=lambda item: (item["party_code"], item["province"]))

    with (OUTPUT_DIR / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "parties": len(party_ratio_rows),
                "provinces": len(province_ratio_rows),
                "highest_party_ratio_party": party_ratio_rows[0]["party_code"] if party_ratio_rows else None,
                "highest_party_ratio_value": party_ratio_rows[0]["party_to_candidate_ratio"] if party_ratio_rows else None,
                "highest_province_ratio": province_ratio_rows[0]["province"] if province_ratio_rows else None,
                "highest_province_ratio_value": province_ratio_rows[0]["party_to_candidate_ratio"] if province_ratio_rows else None,
                "psi_top_province_by_share": psi_rows[0]["province"] if psi_rows else None,
                "psi_top_share": psi_rows[0]["party_vote_share_of_total"] if psi_rows else None,
                "notes": [
                    "This Python port focuses on the ratio sections of the original notebook.",
                    "Winner estimation and representation coverage now live in dedicated Python scripts.",
                ],
            },
            handle,
            indent=2,
        )

    write_csv(
        OUTPUT_DIR / "party_ratio_table.csv",
        [
            "party_code",
            "party_name",
            "party_vote_total",
            "candidate_vote_total",
            "party_to_candidate_ratio",
            "party_vote_share_of_total",
        ],
        party_ratio_rows,
    )
    write_csv(
        OUTPUT_DIR / "province_ratio_table.csv",
        [
            "province",
            "party_vote_total",
            "candidate_vote_total",
            "party_to_candidate_ratio",
            "party_vote_share_of_total",
        ],
        province_ratio_rows,
    )
    write_csv(
        OUTPUT_DIR / "party_province_ratios.csv",
        [
            "province",
            "party_code",
            "party_name",
            "party_vote_total",
            "candidate_vote_total",
            "party_to_candidate_ratio",
            "party_vote_share_of_total",
        ],
        party_province_ratio_rows,
    )
    write_csv(
        OUTPUT_DIR / "psi_province_summary.csv",
        [
            "province",
            "party_code",
            "party_name",
            "party_vote_total",
            "candidate_vote_total",
            "party_to_candidate_ratio",
            "party_vote_share_of_total",
        ],
        psi_rows,
    )
    write_csv(
        OUTPUT_DIR / "small_party_comparison.csv",
        [
            "province",
            "party_code",
            "party_name",
            "party_vote_total",
            "candidate_vote_total",
            "party_to_candidate_ratio",
            "party_vote_share_of_total",
        ],
        comparison_rows,
    )

    print("Wrote party ratio outputs to", OUTPUT_DIR)
    if party_ratio_rows:
        print(
            "Top party ratio:",
            party_ratio_rows[0]["party_code"],
            party_ratio_rows[0]["party_to_candidate_ratio"],
        )


if __name__ == "__main__":
    main()
