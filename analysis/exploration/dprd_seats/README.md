# DPRD Seat Exploration

Exploratory DPRD seat tables live here until they are promoted into a supported
pipeline or dashboard.

## Files

- `source/dprd_province_seats_2024_complete.csv`
  Original province-level DPRD seat source.

- `dprd_provincial_seats.csv`
  Cleaned version to use for DPRD province work.

- `dprd_kabkot_seats.csv`
  DPRD kabupaten/kota seats by province and party.

## Normalization

The cleaned province file normalizes these labels:

- `DK Jakarta` -> `DKI Jakarta`
- `DI Yogyakarta` -> `Daerah Istimewa Yogyakarta`
- `PDI-P` -> `PDIP`
- `Partai Aceh` -> `PA`

Current province file:

- 394 elected-party rows
- 38 provinces
- 20 parties with seats
- 2,372 total provincial DPRD seats
- source URL and note columns kept

## Status

These files are intentionally outside `data/prepared/` and
`analysis/reference/dashboard_inputs/`. They are not required by
`validate_prepared_data.py`, `data_coverage_report.py`, or the Render publish
pipeline.
