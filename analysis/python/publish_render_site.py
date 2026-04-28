#!/usr/bin/env python3
"""Build and package the public static site for Render."""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from html import escape
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_interactive_dashboard
import build_pileg_seat_dashboard
import build_pilpres_vs_pileg_dashboard
import data_coverage_report
import dpr_estimated_winners
import dpr_vote_dynamics
import party_ratio_analysis
import representation_gap
import validate_prepared_data
from common import PREPARED_DATA_DIR, PYTHON_OUTPUT_DIR, ROOT, ensure_dir


REFERENCE_INPUT_DIR = ROOT / "analysis" / "reference" / "dashboard_inputs"
PUBLIC_SITE_DIR = PYTHON_OUTPUT_DIR / "published_site"
PUBLIC_LOGO_DIR = PUBLIC_SITE_DIR / "assets" / "logos"

DASHBOARD_CONFIG = [
    {
        "slug": "dpr",
        "label": "Legislative Results",
        "title": "Candidate and party vote dashboard",
        "summary": "The main interactive DPR view with dapil map filtering, threshold-aware winners, and candidate-vs-party dynamics.",
        "output_dir": build_interactive_dashboard.OUTPUT_DIR,
        "builder": build_interactive_dashboard.main,
        "accent": "#0f766e",
    },
    {
        "slug": "pileg-seats",
        "label": "Seat Allocation Scenarios",
        "title": "Seat-scenario and proportionality dashboard",
        "summary": "Scenario-based DPR seat adjustments, focused on proportionality, seat premium, and dapil-level distortions.",
        "output_dir": build_pileg_seat_dashboard.OUTPUT_DIR,
        "builder": build_pileg_seat_dashboard.main,
        "accent": "#b45309",
    },
    {
        "slug": "pilpres-vs-pileg",
        "label": "Presidential vs Legislative Alignment",
        "title": "Province coalition alignment dashboard",
        "summary": "Province-by-province comparison between presidential vote share and coalition legislative strength.",
        "output_dir": build_pilpres_vs_pileg_dashboard.OUTPUT_DIR,
        "builder": build_pilpres_vs_pileg_dashboard.main,
        "accent": "#1d4ed8",
    },
]


def hydrate_reference_inputs() -> None:
    """Materialize tracked dashboard inputs into data/prepared when the local data tree is absent."""
    ensure_dir(PREPARED_DATA_DIR)
    for source_path in sorted(REFERENCE_INPUT_DIR.glob("*.csv")):
        target_path = PREPARED_DATA_DIR / source_path.name
        if not target_path.exists():
            shutil.copy2(source_path, target_path)


def run_build_chain() -> None:
    hydrate_reference_inputs()
    validate_prepared_data.main()
    dpr_vote_dynamics.main()
    dpr_estimated_winners.main()
    data_coverage_report.main()
    party_ratio_analysis.main()
    representation_gap.main()
    for config in DASHBOARD_CONFIG:
        config["builder"]()


def copy_logos() -> None:
    if PUBLIC_LOGO_DIR.exists():
        shutil.rmtree(PUBLIC_LOGO_DIR)
    shutil.copytree(ROOT / "assets" / "logos", PUBLIC_LOGO_DIR, dirs_exist_ok=True)


def rewrite_dashboard_html(slug: str, html: str) -> str:
    if slug == "dpr":
        return html.replace("../../../assets/logos/", "/assets/logos/")
    return html


def stage_dashboard(config: dict[str, object]) -> dict[str, object]:
    slug = str(config["slug"])
    output_dir = Path(config["output_dir"])
    target_dir = ensure_dir(PUBLIC_SITE_DIR / slug)

    html = (output_dir / "index.html").read_text(encoding="utf-8")
    (target_dir / "index.html").write_text(rewrite_dashboard_html(slug, html), encoding="utf-8")

    metadata_path = output_dir / "dashboard_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    if metadata_path.exists():
        shutil.copy2(metadata_path, target_dir / "dashboard_metadata.json")

    readme_path = output_dir / "README.txt"
    if readme_path.exists():
        shutil.copy2(readme_path, target_dir / "README.txt")

    return {
        "slug": slug,
        "label": str(config["label"]),
        "title": str(config["title"]),
        "summary": str(config["summary"]),
        "accent": str(config["accent"]),
        "subtitle": str(metadata.get("subtitle", "")).strip(),
        "generatedAt": str(metadata.get("generatedAt", "")),
    }


def build_homepage(cards: list[dict[str, object]]) -> str:
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    card_html = "\n".join(
        f"""
        <a class="report-card" href="/{escape(str(card['slug']))}/" style="--accent: {escape(str(card['accent']))};">
          <span class="card-label">{escape(str(card['label']))}</span>
          <h2>{escape(str(card['title']))}</h2>
          <p>{escape(str(card['summary']))}</p>
          <span class="card-link">Open report</span>
        </a>
        """.strip()
        for card in cards
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Pileg Reports</title>
  <style>
    :root {{
      --paper: #f7f8fa;
      --surface: #ffffff;
      --ink: #17202a;
      --muted: #5d6673;
      --line: #dce2ea;
      --line-strong: #b9c2cf;
      --shadow: 0 12px 28px rgba(23, 32, 42, 0.08);
      --radius: 8px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      font-family: Inter, "Avenir Next", "Segoe UI", sans-serif;
      background: var(--paper);
    }}
    .page {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 24px 20px 56px;
    }}
    .masthead {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      padding: 0 0 18px;
      border-bottom: 1px solid var(--line);
      color: var(--muted);
      font-size: 0.9rem;
    }}
    .brand {{
      color: var(--ink);
      font-weight: 800;
      font-size: 1.15rem;
      text-decoration: none;
    }}
    .site-links {{
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 10px 14px;
    }}
    .site-links a {{
      color: var(--muted);
      font-weight: 700;
      text-decoration: none;
    }}
    .site-links a:hover {{
      color: var(--ink);
    }}
    .hero {{
      display: grid;
      grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.6fr);
      gap: 34px;
      padding: 42px 0 30px;
      border-bottom: 1px solid var(--line);
    }}
    .eyebrow {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: #0f766e;
      font-size: 0.82rem;
      font-weight: 800;
      letter-spacing: 0;
      text-transform: uppercase;
    }}
    h1, h2, h3 {{
      margin: 0;
      letter-spacing: 0;
    }}
    h1 {{
      margin-top: 14px;
      max-width: 13ch;
      font-size: clamp(2.6rem, 7vw, 5.8rem);
      line-height: 0.95;
    }}
    .hero p {{
      margin: 22px 0 0;
      max-width: 68ch;
      color: var(--muted);
      line-height: 1.65;
      font-size: 1.05rem;
    }}
    .context-panel {{
      align-self: end;
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--surface);
      box-shadow: var(--shadow);
    }}
    .context-panel h2 {{
      font-size: 0.92rem;
      text-transform: uppercase;
    }}
    .context-panel ul {{
      display: grid;
      gap: 10px;
      margin: 14px 0 0;
      padding: 0;
      list-style: none;
    }}
    .context-panel li {{
      display: flex;
      justify-content: space-between;
      gap: 18px;
      padding-top: 10px;
      border-top: 1px solid var(--line);
      color: var(--muted);
      font-size: 0.92rem;
    }}
    .context-panel strong {{
      color: var(--ink);
    }}
    .section-head {{
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 18px;
      margin-top: 28px;
    }}
    .section-head h2 {{
      font-size: 1.15rem;
    }}
    .section-head p {{
      margin: 0;
      color: var(--muted);
      font-size: 0.92rem;
    }}
    .basics {{
      display: grid;
      grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
      gap: 16px;
      margin-top: 24px;
      padding: 20px;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--surface);
      box-shadow: var(--shadow);
    }}
    .basics h2 {{
      font-size: 1.15rem;
    }}
    .basics p {{
      margin: 10px 0 0;
      color: var(--muted);
      line-height: 1.6;
    }}
    .glossary {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}
    .glossary div {{
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: #fbfcfd;
    }}
    .glossary strong {{
      display: block;
      color: var(--ink);
    }}
    .glossary span {{
      display: block;
      margin-top: 4px;
      color: var(--muted);
      line-height: 1.45;
      font-size: 0.9rem;
    }}
    .reports {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
      margin-top: 16px;
    }}
    .report-card {{
      display: grid;
      grid-template-rows: auto auto 1fr auto;
      gap: 12px;
      min-height: 260px;
      padding: 20px;
      border-radius: var(--radius);
      background: var(--surface);
      border: 1px solid var(--line);
      border-top: 4px solid var(--accent);
      box-shadow: var(--shadow);
      text-decoration: none;
      color: inherit;
      transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
    }}
    .report-card:hover {{
      transform: translateY(-3px);
      border-color: var(--line-strong);
      box-shadow: 0 16px 32px rgba(23, 32, 42, 0.12);
    }}
    .card-label {{
      color: var(--accent);
      font-size: 0.78rem;
      font-weight: 800;
      letter-spacing: 0;
      text-transform: uppercase;
    }}
    .report-card h2 {{
      font-size: 1.4rem;
      line-height: 1.14;
    }}
    .report-card p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.58;
    }}
    .card-link {{
      font-weight: 800;
      color: var(--accent);
    }}
    .footer {{
      margin-top: 22px;
      color: var(--muted);
      font-size: 0.86rem;
    }}
    @media (max-width: 980px) {{
      .hero {{
        grid-template-columns: 1fr;
      }}
      .context-panel {{
        align-self: start;
      }}
      .reports {{
        grid-template-columns: 1fr;
      }}
      .basics {{
        grid-template-columns: 1fr;
      }}
    }}
    @media (max-width: 620px) {{
      .masthead, .section-head {{
        align-items: start;
        flex-direction: column;
      }}
      h1 {{
        font-size: clamp(2.35rem, 14vw, 4rem);
      }}
      .glossary {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <header class="masthead">
      <a class="brand" href="/">Home</a>
      <nav class="site-links" aria-label="Report navigation">
        <a href="/dpr/">Legislative Results</a>
        <a href="/pileg-seats/">Seat Scenarios</a>
        <a href="/pilpres-vs-pileg/">Presidential Alignment</a>
        <a href="#glossary">Glossary</a>
      </nav>
    </header>
    <section class="hero">
      <div>
        <span class="eyebrow">Public report hub</span>
        <h1>2024 Indonesian Election Reports</h1>
        <p>
          Interactive reports for reading Indonesia's 2024 House of Representatives election alongside seat-allocation
          scenarios and province-level Pilpres-vs-Pileg coalition alignment.
        </p>
      </div>
      <aside class="context-panel" aria-label="Report coverage">
        <h2>Coverage</h2>
        <ul>
          <li><strong>Election year</strong><span>2024</span></li>
          <li><strong>Primary focus</strong><span>DPR Pileg</span></li>
          <li><strong>Comparison view</strong><span>Pilpres vs Pileg</span></li>
        </ul>
      </aside>
    </section>
    <section class="basics" id="glossary" aria-labelledby="basics-heading">
      <div>
        <h2 id="basics-heading">Election Basics</h2>
        <p>
          Indonesia's House of Representatives election uses multi-member districts, open party lists,
          and a 4% national parliamentary threshold.
        </p>
      </div>
      <div class="glossary" aria-label="Short glossary">
        <div><strong>Pileg</strong><span>Legislative election.</span></div>
        <div><strong>Pilpres</strong><span>Presidential election.</span></div>
        <div><strong>DPR</strong><span>National House of Representatives.</span></div>
        <div><strong>Dapil</strong><span>Electoral district.</span></div>
        <div><strong>Parliamentary threshold</strong><span>Parties below 4% national DPR vote do not receive DPR seats.</span></div>
      </div>
    </section>
    <section class="section-head" aria-labelledby="reports-heading">
      <h2 id="reports-heading">Choose a report</h2>
      <p>Three standalone dashboards published from the same analysis pipeline.</p>
    </section>
    <section class="reports">
      {card_html}
    </section>
    <p class="footer">
      Built from Python source, tracked reference inputs, and map geometry in this repository. Last rebuilt {escape(generated_at)}.
    </p>
  </main>
</body>
</html>
"""


def main() -> None:
    run_build_chain()

    if PUBLIC_SITE_DIR.exists():
        shutil.rmtree(PUBLIC_SITE_DIR)
    ensure_dir(PUBLIC_SITE_DIR)
    copy_logos()

    cards = [stage_dashboard(config) for config in DASHBOARD_CONFIG]
    homepage = build_homepage(cards)
    (PUBLIC_SITE_DIR / "index.html").write_text(homepage, encoding="utf-8")
    (PUBLIC_SITE_DIR / "404.html").write_text(homepage, encoding="utf-8")
    (PUBLIC_SITE_DIR / "README.txt").write_text(
        "Render publish directory for the combined public dashboard site.\n",
        encoding="utf-8",
    )
    print("Wrote combined public site to", PUBLIC_SITE_DIR)


if __name__ == "__main__":
    main()
