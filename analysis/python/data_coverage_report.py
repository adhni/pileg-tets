#!/usr/bin/env python3
"""Summarize cross-dataset coverage in the prepared data layer."""
from __future__ import annotations

import json

from common import PREPARED_DATA_DIR, PYTHON_OUTPUT_DIR, ensure_dir, read_csv, write_csv


OUTPUT_DIR = ensure_dir(PYTHON_OUTPUT_DIR / "data_coverage")


def main() -> None:
    dpr_candidate_rows = read_csv(PREPARED_DATA_DIR / "dpr_candidates_standardized.csv")
    dpd_candidate_rows = read_csv(PREPARED_DATA_DIR / "dpd_candidates_standardized.csv")
    dprd_provincial_rows = read_csv(PREPARED_DATA_DIR / "dprd_provincial_seats.csv")
    dprd_kabkot_rows = read_csv(PREPARED_DATA_DIR / "dprd_kabkot_seats.csv")
    dapil_rows = read_csv(PREPARED_DATA_DIR / "dapil_seats.csv")

    dpr_provinces = {row["province"] for row in dpr_candidate_rows}
    dpd_provinces = {row["province"] for row in dpd_candidate_rows}
    dprd_provincial_provinces = {row["province"] for row in dprd_provincial_rows}
    dprd_kabkot_provinces = {row["province"] for row in dprd_kabkot_rows}
    dapil_provinces = {row["province"] for row in dapil_rows}

    all_provinces = sorted(
        dpr_provinces | dpd_provinces | dprd_provincial_provinces | dprd_kabkot_provinces | dapil_provinces
    )

    coverage_rows = []
    for province in all_provinces:
        coverage_rows.append(
            {
                "province": province,
                "has_dpr_candidates": "true" if province in dpr_provinces else "false",
                "has_dpd_candidates": "true" if province in dpd_provinces else "false",
                "has_dprd_provincial_seats": "true" if province in dprd_provincial_provinces else "false",
                "has_dprd_kabkot_seats": "true" if province in dprd_kabkot_provinces else "false",
                "has_dapil_seats": "true" if province in dapil_provinces else "false",
            }
        )

    summary = {
        "dpr_provinces": len(dpr_provinces),
        "dpd_provinces": len(dpd_provinces),
        "dprd_provincial_provinces": len(dprd_provincial_provinces),
        "dprd_kabkot_provinces": len(dprd_kabkot_provinces),
        "dapil_seat_provinces": len(dapil_provinces),
        "dpd_missing_from_dpr": sorted(dpr_provinces - dpd_provinces),
        "dprd_kabkot_missing_from_dpr": sorted(dpr_provinces - dprd_kabkot_provinces),
        "notes": [
            "DPD source coverage currently excludes Papua Barat Daya. Treat this as expected source coverage, not a normalization or join failure.",
            "DPRD kabupaten/kota coverage currently excludes DKI Jakarta in this dataset. Treat this as expected source coverage.",
        ],
    }

    write_csv(
        OUTPUT_DIR / "province_dataset_coverage.csv",
        [
            "province",
            "has_dpr_candidates",
            "has_dpd_candidates",
            "has_dprd_provincial_seats",
            "has_dprd_kabkot_seats",
            "has_dapil_seats",
        ],
        coverage_rows,
    )
    with (OUTPUT_DIR / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    (OUTPUT_DIR / "NOTES.md").write_text(
        "\n".join(
            [
                "# Coverage Notes",
                "",
                "- DPD source coverage currently excludes `Papua Barat Daya`. This is expected source coverage.",
                "- DPRD kabupaten/kota coverage currently excludes `DKI Jakarta` in this dataset. This is expected source coverage.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print("Wrote coverage report to", OUTPUT_DIR)
    print("DPD missing from DPR:", summary["dpd_missing_from_dpr"])
    print("DPRD kabkot missing from DPR:", summary["dprd_kabkot_missing_from_dpr"])


if __name__ == "__main__":
    main()
