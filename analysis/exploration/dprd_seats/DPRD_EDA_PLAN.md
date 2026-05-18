# DPRD EDA V1 Plan

## Summary

- Build a small exploratory analysis for DPRD provincial seats.
- Keep it outside the public dashboard pipeline.
- Compare DPRD provincial seats against DPR estimated seats and Pilpres coalition patterns.
- Produce CSV summaries, a short Markdown readout, and a few static charts.

## Key Changes

- Add one EDA script under `analysis/exploration/dprd_seats/`.
- Read these inputs:
  - `analysis/exploration/dprd_seats/dprd_provincial_seats.csv`
  - `analysis/python_outputs/dpr_estimated_winners/estimated_seats_by_party.csv`
  - `analysis/python_outputs/dpr_estimated_winners/estimated_seats_by_district_party.csv`
  - `data/prepared/dpr_party_slates.csv`
  - `analysis/reference/pilpres_vs_pileg/election_results.csv`
- Write outputs under `analysis/exploration/dprd_seats/eda_outputs/`:
  - `party_summary.csv`
  - `province_party_summary.csv`
  - `province_leaders.csv`
  - `coalition_summary.csv`
  - `dprd_vs_pilpres.csv`
  - `summary.md`
  - `summary.json`

## Charts

- Save static PNG charts under `analysis/exploration/dprd_seats/eda_outputs/charts/`.
- Include:
  - National DPRD provincial seats by party.
  - DPRD seat share vs DPR seat share by party.
  - Coalition DPRD share vs Pilpres vote share by province.
  - Largest province-party DPRD strength gaps versus DPR province strength.

## Analysis Rules

- Use `dprd_provincial_seats.csv` as the canonical DPRD provincial source.
- Treat missing DPRD party rows as zero seats.
- Use threshold-adjusted DPR estimated seats as the DPR seat comparison.
- Use existing Pilpres coalition groupings:
  - Anies: `PKB`, `PKS`, `NasDem`, `Ummat`
  - Prabowo: `Gerindra`, `Golkar`, `PAN`, `Demokrat`, `PSI`, `Gelora`, `Garuda`
  - Ganjar: `PDIP`, `PPP`, `Hanura`, `Perindo`
- Keep DPRD kabupaten/kota out of v1.

## Test Plan

- Run the EDA script from the repo root.
- Confirm DPRD provincial seats total `2,372`.
- Confirm all 38 provinces appear in DPRD and Pilpres joins.
- Confirm output CSVs are non-empty and have expected columns.
- Confirm chart PNGs are created.
- Confirm existing public pipeline remains unaffected:
  - `python3 analysis/python/validate_prepared_data.py`
  - `python3 analysis/python/publish_render_site.py`

## Assumptions

- This remains exploratory and does not touch `data/prepared/`.
- No public dashboard or Render routing changes in v1.
- Pilpres coalition alignment is the first "other things" comparison.
