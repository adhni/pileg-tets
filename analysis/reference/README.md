# Reference Inputs

Small tracked source tables that feed the Python pipeline live here.

## Files

- `dapil_seat_counts.csv`
  Explicit DPR dapil seat counts used by `analysis/prepare_python_data.py`.
  This replaces the old notebook-scraping dependency on the archived R seat notebook.

- `dapil_map/gadm41_IDN_2.json`
  Base Indonesia level-2 geometry used by the interactive DAPIL map in the Python dashboard.

- `dapil_map/gadm_sf_dapil.csv`
  Lookup table mapping level-2 geometry rows to DPR dapil labels for the dashboard map.
