#!/usr/bin/env python3
"""Validate the prepared data layer and record expected source gaps."""
from __future__ import annotations

import json
from pathlib import Path

from common import PREPARED_DATA_DIR, PYTHON_OUTPUT_DIR, parse_int, read_csv


OUTPUT_DIR = PYTHON_OUTPUT_DIR / "validation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    required_files = [
        "party_lookup.csv",
        "province_lookup.csv",
        "dpr_candidates_standardized.csv",
        "dpr_party_slates.csv",
        "dpd_candidates_standardized.csv",
        "dprd_provincial_seats.csv",
        "dprd_kabkot_seats.csv",
        "dprd_seat_ratios.csv",
        "dprd_seat_totals.csv",
        "dapil_seats.csv",
    ]
    for filename in required_files:
        expect((PREPARED_DATA_DIR / filename).exists(), f"Missing prepared file: {filename}")

    dpr_candidates = read_csv(PREPARED_DATA_DIR / "dpr_candidates_standardized.csv")
    dpr_slates = read_csv(PREPARED_DATA_DIR / "dpr_party_slates.csv")
    dpd_candidates = read_csv(PREPARED_DATA_DIR / "dpd_candidates_standardized.csv")
    dprd_provincial = read_csv(PREPARED_DATA_DIR / "dprd_provincial_seats.csv")
    dprd_kabkot = read_csv(PREPARED_DATA_DIR / "dprd_kabkot_seats.csv")
    dprd_ratios = read_csv(PREPARED_DATA_DIR / "dprd_seat_ratios.csv")
    dprd_totals = read_csv(PREPARED_DATA_DIR / "dprd_seat_totals.csv")
    dapil_seats = read_csv(PREPARED_DATA_DIR / "dapil_seats.csv")
    province_lookup = read_csv(PREPARED_DATA_DIR / "province_lookup.csv")
    party_lookup = read_csv(PREPARED_DATA_DIR / "party_lookup.csv")

    dpr_provinces = {row["province"] for row in dpr_candidates}
    dpd_provinces = {row["province"] for row in dpd_candidates}
    dprd_provincial_provinces = {row["province"] for row in dprd_provincial}
    dprd_kabkot_provinces = {row["province"] for row in dprd_kabkot}

    expected_dpd_gap = {"Papua Barat Daya"}
    expected_kabkot_gap = {"DKI Jakarta"}
    observed_dpd_gap = dpr_provinces - dpd_provinces
    observed_kabkot_gap = dpr_provinces - dprd_kabkot_provinces

    expect(len(party_lookup) == 24, "Expected 24 party lookup rows")
    expect(len(dpr_candidates) == 9908, "Unexpected DPR candidate row count")
    expect(len(dpr_slates) == 1509, "Unexpected DPR slate row count")
    expect(len(dprd_provincial) == 912, "Unexpected DPRD provincial row count")
    expect(len(dprd_kabkot) == 888, "Unexpected DPRD kabupaten/kota row count")
    expect(len(dprd_ratios) == 912, "Unexpected DPRD ratio row count")
    expect(len(dprd_totals) == 24, "Unexpected DPRD total row count")
    expect(len(dapil_seats) == 84, "Unexpected dapil seat row count")
    expect(len(dpr_provinces) == 38, "Unexpected DPR province count")
    expect(len(dpd_provinces) == 37, "Unexpected DPD province count")
    expect(len(dprd_provincial_provinces) == 38, "Unexpected DPRD provincial province count")
    expect(len(dprd_kabkot_provinces) == 37, "Unexpected DPRD kabupaten/kota province count")
    expect(observed_dpd_gap == expected_dpd_gap, f"Unexpected DPD coverage gap: {sorted(observed_dpd_gap)}")
    expect(
        observed_kabkot_gap == expected_kabkot_gap,
        f"Unexpected DPRD kabupaten/kota coverage gap: {sorted(observed_kabkot_gap)}",
    )
    expect(sum(parse_int(row["seat_count"]) for row in dapil_seats) == 580, "Unexpected total dapil seats")
    expect(all(row["province"] != "Total seats" for row in dprd_provincial), "Found Total seats in dprd_provincial_seats")
    expect(all(row["province"] != "Total seats" for row in dprd_kabkot), "Found Total seats in dprd_kabkot_seats")
    expect(all("inf" not in (row["kabkot_to_provincial_ratio"] or "").lower() for row in dprd_ratios), "Found inf ratio")
    expect(
        all((row["kabkot_to_provincial_ratio"] == "") == (row["ratio_defined"] == "false") for row in dprd_ratios),
        "Ratio blankness does not match ratio_defined flag",
    )
    expect(len({(row["province_raw"], row["province"], row["source_dataset"]) for row in province_lookup}) == len(province_lookup), "Duplicate province lookup rows")

    report = {
        "status": "ok",
        "checks": {
            "party_lookup_rows": len(party_lookup),
            "dpr_candidate_rows": len(dpr_candidates),
            "dpr_slate_rows": len(dpr_slates),
            "dpd_candidate_rows": len(dpd_candidates),
            "dprd_provincial_rows": len(dprd_provincial),
            "dprd_kabkot_rows": len(dprd_kabkot),
            "dprd_ratio_rows": len(dprd_ratios),
            "dprd_total_rows": len(dprd_totals),
            "dapil_rows": len(dapil_seats),
            "total_dapil_seats": sum(parse_int(row["seat_count"]) for row in dapil_seats),
        },
        "expected_source_gaps": {
            "dpd_missing_from_dpr": sorted(observed_dpd_gap),
            "dprd_kabkot_missing_from_dpr": sorted(observed_kabkot_gap),
        },
        "notes": [
            "Papua Barat Daya is expected to be absent from the DPD source.",
            "DKI Jakarta is expected to be absent from the DPRD kabupaten/kota source.",
            "The validator treats those two coverage gaps as expected source constraints, not data errors.",
        ],
    }

    with (OUTPUT_DIR / "prepared_data_validation.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    (OUTPUT_DIR / "NOTES.md").write_text(
        "\n".join(
            [
                "# Validation Notes",
                "",
                "- `Papua Barat Daya` is expected to be absent from the DPD source.",
                "- `DKI Jakarta` is expected to be absent from the DPRD kabupaten/kota source.",
                "- Those two source gaps are treated as expected coverage, not failures.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print("Prepared data validation passed")
    print("Validation report:", OUTPUT_DIR / "prepared_data_validation.json")


if __name__ == "__main__":
    main()
