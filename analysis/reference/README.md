# Reference Inputs

Small tracked source tables that feed the Python pipeline live here.

## Files

- `dashboard_inputs/`
  Tracked fallback inputs for the supported public dashboards and validation
  pipeline.

- `dashboard_inputs/dapil_seats.csv`
  Explicit DPR dapil seat counts used by `analysis/prepare_python_data.py`.
  This replaces the old notebook-scraping dependency on the archived R seat notebook.

Exploratory DPRD seat tables are kept outside this reference input directory in
`analysis/exploration/dprd_seats/`.
