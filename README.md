# Pileg Test

This repo is now set up to run the analysis workflow from Python.

## Python Workflow

Install the current dependency set:

```bash
python3 -m pip install -r requirements.txt
```

Run the full pipeline:

```bash
python3 analysis/python/run_all.py
```

That command rebuilds:

- `data/prepared/`
- `analysis/python_outputs/dpr_vote_dynamics/`
- `analysis/python_outputs/dpr_estimated_winners/`
- `analysis/python_outputs/data_coverage/`
- `analysis/python_outputs/party_ratio_analysis/`
- `analysis/python_outputs/representation_gap/`
- `analysis/python_outputs/plots/`
- `analysis/python_outputs/report/`
- `analysis/python_outputs/dashboard/`
- `analysis/python_outputs/pileg_dashboard/`
- `analysis/python_outputs/pilpres_vs_pileg_dashboard/` when the optional local Pilpres CSV is present

## Main Files

- `analysis/prepare_python_data.py`
  Builds the normalized Python-first data layer.

- `analysis/python/validate_prepared_data.py`
  Validates prepared outputs and treats expected source gaps as notes.

- `analysis/python/run_all.py`
  Runs the full Python pipeline end to end.

- `analysis/python/report_builder.py`
  Builds the consolidated HTML and Markdown report.

- `analysis/python/build_interactive_dashboard.py`
  Builds the standalone interactive dashboard.

- `analysis/python/build_pileg_seat_dashboard.py`
  Builds the separate seat-adjustment scenario dashboard.

- `analysis/python/build_pilpres_vs_pileg_dashboard.py`
  Builds the separate Pilpres-vs-Pileg coalition alignment dashboard.

## Notes

- The current Python scripts use only the standard library plus `matplotlib`.
- For DPR analysis, vote views include all parties, while seat and winner outputs default to the legal 4% national parliamentary-threshold model.
- Raw all-party seat simulations are still exported for comparison so threshold-driven replacement winners can be inspected directly.
- The seat-adjustment scenario dashboard uses existing repo data only; it takes inspiration from the archived Quarto scenario framing but does not reuse the notebook's hardcoded vote table.
- The Pilpres-vs-Pileg dashboard uses an optional local CSV at `Pilpres V Pileg/election_results.csv` because the repo does not yet have a prepared province-level Pilpres layer.
- `analysis/python/run_all.py` skips the Pilpres-vs-Pileg dashboard automatically when that optional local CSV is absent.
- `Papua Barat Daya` is expected to be absent from the DPD source.
- `DKI Jakarta` is expected to be absent from the DPRD kabupaten/kota source.
- Legacy R notebooks are archived under `archive/r_reference/` and are no longer part of the active pipeline.
