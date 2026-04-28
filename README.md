# Pileg Reports

Interactive Indonesian election analysis reports for DPR candidate dynamics,
seat-scenario proportionality, and Pilpres-vs-Pileg coalition alignment.

## Public Site

The published reports are available at:

- Main site: <https://pileg-tets.onrender.com/>
- DPR Dashboard: <https://pileg-tets.onrender.com/dpr/>
- Pileg Seats: <https://pileg-tets.onrender.com/pileg-seats/>
- Pilpres vs Pileg: <https://pileg-tets.onrender.com/pilpres-vs-pileg/>

## Main Reports

- **DPR Dashboard**
  Candidate and party vote dashboard with dapil map filtering,
  threshold-aware winners, and candidate-vs-party dynamics.

- **Pileg Seats**
  Seat-scenario and proportionality dashboard focused on DPR seat adjustments,
  seat premium, and dapil-level distortions.

- **Pilpres vs Pileg**
  Province coalition alignment dashboard comparing presidential vote share with
  coalition legislative strength.

## Python Workflow

Run the full local pipeline:

```bash
python3 analysis/python/run_all.py
```

That command rebuilds the prepared data and Python analysis outputs, including:

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
- `analysis/python_outputs/pilpres_vs_pileg_dashboard/`

To rebuild the public Render site locally:

```bash
python3 analysis/python/publish_render_site.py
```

That script rebuilds the three published dashboards, stages shared assets, and
writes the static site to `analysis/python_outputs/published_site/`.

Dependency installation is intentionally not pinned in this repo yet. If a
`requirements.txt` file is added later, install it before running the pipeline:

```bash
python3 -m pip install -r requirements.txt
```

## Main Files

### Data and Validation

- `analysis/prepare_python_data.py`
  Builds the normalized Python-first data layer.

- `analysis/python/validate_prepared_data.py`
  Validates prepared outputs and treats expected source gaps as notes.

### Analysis Outputs

- `analysis/python/run_all.py`
  Runs the full Python pipeline end to end.

- `analysis/python/dpr_vote_dynamics.py`
  Builds party-vs-candidate vote concentration summaries.

- `analysis/python/dpr_estimated_winners.py`
  Estimates DPR winners with threshold-adjusted and comparison outputs.

- `analysis/python/party_ratio_analysis.py`
  Builds ratio-focused party analysis outputs.

- `analysis/python/representation_gap.py`
  Builds representation-gap analysis outputs.

### Dashboards and Reports

- `analysis/python/report_builder.py`
  Builds the consolidated HTML and Markdown report.

- `analysis/python/build_interactive_dashboard.py`
  Builds the DPR dashboard.

- `analysis/python/build_pileg_seat_dashboard.py`
  Builds the Pileg seat-scenario dashboard.

- `analysis/python/build_pilpres_vs_pileg_dashboard.py`
  Builds the Pilpres-vs-Pileg coalition alignment dashboard.

### Publishing

- `analysis/python/publish_render_site.py`
  Packages the three public dashboards into one static site.

- `render.yaml`
  Render Blueprint for publishing the combined public site.
