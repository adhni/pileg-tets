#!/usr/bin/env python3
"""Generate lightweight matplotlib plots from Python analysis outputs."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[2] / "analysis" / "python_outputs" / ".mplconfig"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from common import PREPARED_DATA_DIR, PYTHON_OUTPUT_DIR, parse_float, parse_int, read_csv


OUTPUT_DIR = PYTHON_OUTPUT_DIR / "plots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def apply_style() -> None:
    plt.style.use("default")
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#d0d7de",
            "axes.labelcolor": "#243447",
            "axes.titleweight": "bold",
            "axes.titlesize": 13,
            "font.size": 10,
            "xtick.color": "#425466",
            "ytick.color": "#425466",
            "grid.color": "#e5e7eb",
        }
    )


def save_figure(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()


def plot_top_share_histogram() -> None:
    rows = read_csv(PREPARED_DATA_DIR / "dpr_party_slates.csv")
    values = [parse_float(row["top_candidate_vote_share"]) for row in rows]
    values = [value for value in values if value is not None]

    plt.figure(figsize=(8, 4.8))
    plt.hist(values, bins=20, color="#1f7a8c", edgecolor="white")
    plt.xlabel("Top candidate share of candidate votes")
    plt.ylabel("Party slates")
    plt.title("DPR candidate vote concentration")
    plt.grid(axis="y", alpha=0.3)
    save_figure(OUTPUT_DIR / "dpr_top_candidate_share_hist.png")


def plot_estimated_seats_by_party() -> None:
    rows = read_csv(PYTHON_OUTPUT_DIR / "dpr_estimated_winners" / "estimated_seats_by_party.csv")
    labels = [row["party_code"] for row in rows]
    values = [parse_int(row["estimated_seats"]) for row in rows]

    plt.figure(figsize=(9, 5.2))
    plt.bar(labels, values, color="#2a9d8f")
    plt.ylabel("Estimated seats")
    plt.title("Threshold-adjusted DPR seats by party")
    plt.grid(axis="y", alpha=0.3)
    save_figure(OUTPUT_DIR / "estimated_seats_by_party.png")


def plot_representation_coverage_histogram() -> None:
    rows = read_csv(PYTHON_OUTPUT_DIR / "representation_gap" / "coverage_by_district.csv")
    values = [parse_float(row["coverage"]) for row in rows]
    values = [value for value in values if value is not None]
    mean_value = sum(values) / len(values)

    plt.figure(figsize=(8, 4.8))
    plt.hist(values, bins=20, color="#e76f51", edgecolor="white")
    plt.axvline(mean_value, color="#264653", linestyle="--", linewidth=1.5)
    plt.xlabel("Winning-candidate coverage of district votes")
    plt.ylabel("Districts")
    plt.title("Threshold-adjusted representation coverage across DPR districts")
    plt.grid(axis="y", alpha=0.3)
    save_figure(OUTPUT_DIR / "representation_coverage_hist.png")


def plot_seat_minus_vote() -> None:
    rows = read_csv(PYTHON_OUTPUT_DIR / "representation_gap" / "party_distortion.csv")
    labels = [row["party_code"] for row in rows]
    values = [parse_float(row["seat_minus_vote"]) or 0.0 for row in rows]
    colors = ["#2166ac" if value >= 0 else "#b2182b" for value in values]

    plt.figure(figsize=(9, 5.2))
    plt.bar(labels, values, color=colors)
    plt.axhline(0, color="#4b5563", linewidth=1)
    plt.ylabel("Seat share minus vote share")
    plt.title("Threshold-adjusted seat-vote distortion by party")
    plt.grid(axis="y", alpha=0.3)
    save_figure(OUTPUT_DIR / "seat_minus_vote_by_party.png")


def plot_threshold_vote_share() -> None:
    rows = read_csv(PYTHON_OUTPUT_DIR / "dpr_estimated_winners" / "party_threshold_status.csv")
    labels = [row["party_code"] for row in rows]
    values = [(parse_float(row["national_vote_share"]) or 0.0) * 100 for row in rows]
    threshold = (parse_float(rows[0]["threshold_percent"]) or 0.0) * 100 if rows else 4.0
    colors = ["#0f766e" if row["passes_dpr_threshold"] == "true" else "#b91c1c" for row in rows]

    plt.figure(figsize=(9.4, 5.4))
    plt.bar(labels, values, color=colors)
    plt.axhline(threshold, color="#111827", linestyle="--", linewidth=1.2)
    plt.ylabel("National DPR vote share (%)")
    plt.title("National DPR vote share vs 4% parliamentary threshold")
    plt.grid(axis="y", alpha=0.3)
    save_figure(OUTPUT_DIR / "dpr_threshold_vote_share.png")


def plot_party_ratio_by_party() -> None:
    rows = read_csv(PYTHON_OUTPUT_DIR / "party_ratio_analysis" / "party_ratio_table.csv")
    labels = [row["party_code"] for row in rows]
    values = [parse_float(row["party_to_candidate_ratio"]) or 0.0 for row in rows]

    plt.figure(figsize=(9, 5.2))
    plt.bar(labels, values, color="#577590")
    plt.ylabel("Party vote / candidate vote")
    plt.title("National party-vote reliance by party")
    plt.grid(axis="y", alpha=0.3)
    save_figure(OUTPUT_DIR / "party_vote_ratio_by_party.png")


def plot_psi_scatter() -> None:
    rows = read_csv(PYTHON_OUTPUT_DIR / "party_ratio_analysis" / "psi_province_summary.csv")
    x_values = [parse_int(row["candidate_vote_total"]) for row in rows]
    y_values = [parse_int(row["party_vote_total"]) for row in rows]
    labels = [row["province"] for row in rows]

    plt.figure(figsize=(7.4, 5.2))
    plt.scatter(x_values, y_values, color="#bc4749", alpha=0.8)
    max_value = max(x_values + y_values) if x_values and y_values else 0
    plt.plot([0, max_value], [0, max_value], linestyle="--", color="#6b7280", linewidth=1)
    for idx, label in enumerate(labels[:8]):
        plt.annotate(label, (x_values[idx], y_values[idx]), fontsize=8, xytext=(4, 4), textcoords="offset points")
    plt.xlabel("Candidate votes")
    plt.ylabel("Party votes")
    plt.title("PSI party vs candidate votes by province")
    plt.grid(alpha=0.3)
    save_figure(OUTPUT_DIR / "psi_party_vs_candidate_votes.png")


def main() -> None:
    apply_style()
    plot_top_share_histogram()
    plot_threshold_vote_share()
    plot_estimated_seats_by_party()
    plot_representation_coverage_histogram()
    plot_seat_minus_vote()
    plot_party_ratio_by_party()
    plot_psi_scatter()
    print("Wrote plot outputs to", OUTPUT_DIR)


if __name__ == "__main__":
    main()
