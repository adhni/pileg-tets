# DPRD Seat Exploration

Exploratory DPRD seat tables live here until they are promoted into a supported
pipeline or dashboard.

## Files

- `dprd_provincial_seats.csv`
  DPRD provinsi seats by province and party.

- `dprd_kabkot_seats.csv`
  DPRD kabupaten/kota seats by province and party.

- `dprd_seat_ratios.csv`
  Province-party comparison between kabupaten/kota and provincial DPRD seats.

- `dprd_seat_totals.csv`
  National party totals and ratio checks.

## Status

These files are intentionally outside `data/prepared/` and
`analysis/reference/dashboard_inputs/`. They are not required by
`validate_prepared_data.py`, `data_coverage_report.py`, or the Render publish
pipeline.
