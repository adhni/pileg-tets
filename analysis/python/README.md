# Python Analysis Scripts

Small Python ports that run against `data/prepared`.

## Scripts

- `prepare_python_data.py`
  Builds the normalized data layer in `data/prepared`.

- `python/dpr_vote_dynamics.py`
  Recreates the core party-vs-candidate vote concentration summaries and exports CSV/JSON outputs.

- `python/dpr_estimated_winners.py`
  Estimates DPR winners using explicit dapil seat counts from `data/prepared/dapil_seats.csv`.

- `python/data_coverage_report.py`
  Summarizes province coverage across DPR, DPD, DPRD, and dapil seat datasets.

- `python/validate_prepared_data.py`
  Validates the prepared data layer and records expected source coverage gaps as notes instead of failures.

- `python/party_ratio_analysis.py`
  Ports the ratio-focused sections of the original `party_ratio_analysis.Rmd` notebook.

- `python/representation_gap.py`
  Ports the core representation-gap calculations using explicit dapil seat counts and the Python winner estimates.

- `python/plot_quicklooks.py`
  Generates a few lightweight PNG charts from the prepared data and Python analysis outputs.

- `python/report_builder.py`
  Builds one consolidated HTML/Markdown report from the Python outputs.

- `python/build_interactive_dashboard.py`
  Builds a standalone interactive HTML dashboard with party-ratio logic, candidate drilldowns, and slate-level exploration.

- `python/run_all.py`
  Runs the Python prep and analysis pipeline end to end.

## Run

```bash
python3 analysis/prepare_python_data.py
python3 analysis/python/validate_prepared_data.py
python3 analysis/python/dpr_vote_dynamics.py
python3 analysis/python/dpr_estimated_winners.py
python3 analysis/python/data_coverage_report.py
python3 analysis/python/party_ratio_analysis.py
python3 analysis/python/representation_gap.py
python3 analysis/python/plot_quicklooks.py
python3 analysis/python/report_builder.py
python3 analysis/python/build_interactive_dashboard.py
python3 analysis/python/run_all.py
```

## Outputs

All script outputs land in `analysis/python_outputs/`.
