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

## Notes

- The current Python scripts use only the standard library plus `matplotlib`.
- `Papua Barat Daya` is expected to be absent from the DPD source.
- `DKI Jakarta` is expected to be absent from the DPRD kabupaten/kota source.
- Legacy R notebooks are archived under `archive/r_reference/` and are no longer part of the active pipeline.
