#!/usr/bin/env python3
"""Quick Python port of the DPR vote-dynamics summaries."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from common import (
    PREPARED_DATA_DIR,
    PYTHON_OUTPUT_DIR,
    ensure_dir,
    format_float,
    median_or_none,
    parse_float,
    parse_int,
    pearson_correlation,
    read_csv,
    write_csv,
)


OUTPUT_DIR = ensure_dir(PYTHON_OUTPUT_DIR / "dpr_vote_dynamics")


def main() -> None:
    rows = read_csv(PREPARED_DATA_DIR / "dpr_party_slates.csv")
    parsed_rows = []
    provinces = set()
    districts = set()
    top_shares = []
    party_vote_shares = []
    paired_top_shares = []
    paired_party_vote_shares = []

    province_acc = defaultdict(lambda: {"slates": 0, "top_share_sum": 0.0, "party_share_sum": 0.0})
    party_acc = defaultdict(
        lambda: {
            "slates": 0,
            "top_share_sum": 0.0,
            "party_share_sum": 0.0,
            "party_vote_total": 0,
            "candidate_vote_total": 0,
            "total_votes": 0,
        }
    )

    for row in rows:
        province = row["province"]
        district = row["district"]
        party_code = row["party_code"]
        party_name = row["party_name"]
        party_vote = parse_int(row["party_vote"])
        candidate_vote_total = parse_int(row["candidate_vote_total"])
        total_votes = parse_int(row["total_votes"])
        top_share = parse_float(row["top_candidate_vote_share"])
        party_vote_share = parse_float(row["party_vote_share"])

        parsed_rows.append(
            {
                "province": province,
                "district": district,
                "party_code": party_code,
                "party_name": party_name,
                "party_number": row["party_number"],
                "party_vote": party_vote,
                "candidate_count": parse_int(row["candidate_count"]),
                "candidate_vote_total": candidate_vote_total,
                "total_votes": total_votes,
                "top_candidate_name": row["top_candidate_name"],
                "top_candidate_vote": parse_int(row["top_candidate_vote"]),
                "top_candidate_vote_share": top_share,
                "party_vote_share": party_vote_share,
            }
        )

        provinces.add(province)
        districts.add((province, district))
        if top_share is not None:
            top_shares.append(top_share)
        if party_vote_share is not None:
            party_vote_shares.append(party_vote_share)
        if top_share is not None and party_vote_share is not None:
            paired_top_shares.append(top_share)
            paired_party_vote_shares.append(party_vote_share)

        province_acc[province]["slates"] += 1
        province_acc[province]["top_share_sum"] += top_share or 0.0
        province_acc[province]["party_share_sum"] += party_vote_share or 0.0

        party_acc[(party_code, party_name)]["slates"] += 1
        party_acc[(party_code, party_name)]["top_share_sum"] += top_share or 0.0
        party_acc[(party_code, party_name)]["party_share_sum"] += party_vote_share or 0.0
        party_acc[(party_code, party_name)]["party_vote_total"] += party_vote
        party_acc[(party_code, party_name)]["candidate_vote_total"] += candidate_vote_total
        party_acc[(party_code, party_name)]["total_votes"] += total_votes

    summary = {
        "provinces_covered": len(provinces),
        "districts_covered": len(districts),
        "party_slates": len(parsed_rows),
        "median_top_candidate_vote_share": median_or_none(top_shares),
        "median_party_vote_share": median_or_none(party_vote_shares),
        "top_vs_party_vote_share_correlation": pearson_correlation(paired_top_shares, paired_party_vote_shares),
    }

    province_rows = []
    for province, acc in sorted(province_acc.items()):
        province_rows.append(
            {
                "province": province,
                "slates": acc["slates"],
                "avg_top_candidate_vote_share": format_float(acc["top_share_sum"] / acc["slates"]),
                "avg_party_vote_share": format_float(acc["party_share_sum"] / acc["slates"]),
            }
        )

    party_rows = []
    for (party_code, party_name), acc in sorted(party_acc.items()):
        party_rows.append(
            {
                "party_code": party_code,
                "party_name": party_name,
                "slates": acc["slates"],
                "party_vote_total": acc["party_vote_total"],
                "candidate_vote_total": acc["candidate_vote_total"],
                "total_votes": acc["total_votes"],
                "avg_top_candidate_vote_share": format_float(acc["top_share_sum"] / acc["slates"]),
                "avg_party_vote_share": format_float(acc["party_share_sum"] / acc["slates"]),
            }
        )
    party_rows.sort(key=lambda item: int(item["total_votes"]), reverse=True)

    top_dominance_rows = sorted(
        parsed_rows,
        key=lambda item: (
            item["top_candidate_vote_share"] if item["top_candidate_vote_share"] is not None else -1.0,
            item["top_candidate_vote"],
        ),
        reverse=True,
    )[:25]
    top_brand_rows = sorted(
        parsed_rows,
        key=lambda item: (
            item["party_vote_share"] if item["party_vote_share"] is not None else -1.0,
            item["party_vote"],
        ),
        reverse=True,
    )[:25]

    with (OUTPUT_DIR / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                key: format_float(value) if isinstance(value, float) else value
                for key, value in summary.items()
            },
            handle,
            indent=2,
        )

    write_csv(
        OUTPUT_DIR / "province_summary.csv",
        ["province", "slates", "avg_top_candidate_vote_share", "avg_party_vote_share"],
        province_rows,
    )
    write_csv(
        OUTPUT_DIR / "party_summary.csv",
        [
            "party_code",
            "party_name",
            "slates",
            "party_vote_total",
            "candidate_vote_total",
            "total_votes",
            "avg_top_candidate_vote_share",
            "avg_party_vote_share",
        ],
        party_rows,
    )
    write_csv(
        OUTPUT_DIR / "top_candidate_dominance.csv",
        [
            "province",
            "district",
            "party_code",
            "party_name",
            "party_number",
            "top_candidate_name",
            "top_candidate_vote",
            "candidate_vote_total",
            "top_candidate_vote_share",
            "party_vote",
            "party_vote_share",
        ],
        (
            {
                "province": row["province"],
                "district": row["district"],
                "party_code": row["party_code"],
                "party_name": row["party_name"],
                "party_number": row["party_number"],
                "top_candidate_name": row["top_candidate_name"],
                "top_candidate_vote": row["top_candidate_vote"],
                "candidate_vote_total": row["candidate_vote_total"],
                "top_candidate_vote_share": format_float(row["top_candidate_vote_share"]),
                "party_vote": row["party_vote"],
                "party_vote_share": format_float(row["party_vote_share"]),
            }
            for row in top_dominance_rows
        ),
    )
    write_csv(
        OUTPUT_DIR / "top_party_vote_share.csv",
        [
            "province",
            "district",
            "party_code",
            "party_name",
            "party_number",
            "party_vote",
            "candidate_vote_total",
            "total_votes",
            "party_vote_share",
            "top_candidate_name",
            "top_candidate_vote_share",
        ],
        (
            {
                "province": row["province"],
                "district": row["district"],
                "party_code": row["party_code"],
                "party_name": row["party_name"],
                "party_number": row["party_number"],
                "party_vote": row["party_vote"],
                "candidate_vote_total": row["candidate_vote_total"],
                "total_votes": row["total_votes"],
                "party_vote_share": format_float(row["party_vote_share"]),
                "top_candidate_name": row["top_candidate_name"],
                "top_candidate_vote_share": format_float(row["top_candidate_vote_share"]),
            }
            for row in top_brand_rows
        ),
    )

    print("Wrote DPR vote dynamics outputs to", OUTPUT_DIR)
    print("Summary:", {key: (format_float(value) if isinstance(value, float) else value) for key, value in summary.items()})


if __name__ == "__main__":
    main()
