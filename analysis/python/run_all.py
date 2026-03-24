#!/usr/bin/env python3
"""Run the Python data prep and analysis pipeline end to end."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

STEPS = [
    ["analysis/prepare_python_data.py"],
    ["analysis/python/validate_prepared_data.py"],
    ["analysis/python/dpr_vote_dynamics.py"],
    ["analysis/python/dpr_estimated_winners.py"],
    ["analysis/python/data_coverage_report.py"],
    ["analysis/python/party_ratio_analysis.py"],
    ["analysis/python/representation_gap.py"],
    ["analysis/python/plot_quicklooks.py"],
    ["analysis/python/report_builder.py"],
    ["analysis/python/build_interactive_dashboard.py"],
    ["analysis/python/build_pileg_seat_dashboard.py"],
    ["analysis/python/build_pilpres_vs_pileg_dashboard.py"],
]


def main() -> None:
    for step in STEPS:
        cmd = [sys.executable, *step]
        print(f"==> Running {' '.join(step)}")
        subprocess.run(cmd, cwd=ROOT, check=True)
    print("Pipeline complete")


if __name__ == "__main__":
    main()
