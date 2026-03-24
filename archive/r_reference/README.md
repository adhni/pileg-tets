# Archived R References

These files are no longer part of the active repo workflow.

The current maintained path is Python-first:

- Prep: `analysis/prepare_python_data.py`
- Validation: `analysis/python/validate_prepared_data.py`
- Analysis pipeline: `analysis/python/run_all.py`
- Public-facing dashboard: `analysis/python/build_interactive_dashboard.py`

The archived R notebooks are kept only for reference, comparison, and historical provenance.

## Mapping

- `candidate_vote_concentration.qmd`
  Replaced by `analysis/python/dpr_vote_dynamics.py`.

- `dpr_dashboard.qmd`
  Replaced by `analysis/python/report_builder.py` and `analysis/python/build_interactive_dashboard.py`.

- `party_ratio_analysis.Rmd`
  Core ratio logic replaced by `analysis/python/party_ratio_analysis.py`.
  The old notebook still shows the original R map-based exploration.

- `representation_gap_analysis.Rmd`
  Core calculations replaced by `analysis/python/representation_gap.py`.
  The archived notebook uses the old longest-slate seat heuristic and should not be treated as the active method.

- `winner_summary.qmd`
  Standard winner estimation is replaced by `analysis/python/dpr_estimated_winners.py`.
  Coalition and presidential-bloc scenario sections remain R-only historical experiments.

- `pileg_seat copy.qmd`
  Kept as historical exploratory work. The explicit dapil seat counts have been externalized into `analysis/reference/dapil_seat_counts.csv`.
