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
        "label": "DPR Dashboard",
        "title": "Candidate and party vote dashboard",
        "summary": "The main interactive DPR view with dapil map filtering, threshold-aware winners, and candidate-vs-party dynamics.",
        "output_dir": build_interactive_dashboard.OUTPUT_DIR,
        "builder": build_interactive_dashboard.main,
        "accent": "#0f766e",
    },
    {
        "slug": "pileg-seats",
        "label": "Pileg Seats",
        "title": "Seat-scenario and proportionality dashboard",
        "summary": "Scenario-based DPR seat adjustments, focused on proportionality, seat premium, and dapil-level distortions.",
        "output_dir": build_pileg_seat_dashboard.OUTPUT_DIR,
        "builder": build_pileg_seat_dashboard.main,
        "accent": "#b45309",
    },
    {
        "slug": "pilpres-vs-pileg",
        "label": "Pilpres vs Pileg",
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
          <p>{escape(str(card['subtitle']) or str(card['summary']))}</p>
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
      --paper: #f5efe2;
      --ink: #15202b;
      --muted: #5f6b76;
      --line: rgba(21, 32, 43, 0.12);
      --shadow: 0 24px 50px rgba(21, 32, 43, 0.12);
      --radius: 28px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      font-family: "Avenir Next", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(15,118,110,0.14), transparent 28%),
        radial-gradient(circle at top right, rgba(180,83,9,0.12), transparent 24%),
        linear-gradient(180deg, #f8f3e9 0%, #f7f1e6 42%, #efe6d5 100%);
    }}
    .page {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 28px 20px 64px;
    }}
    .hero {{
      padding: 34px;
      border-radius: 36px;
      background:
        linear-gradient(135deg, rgba(255,255,255,0.90), rgba(255,255,255,0.76)),
        linear-gradient(135deg, rgba(15,118,110,0.10), rgba(29,78,216,0.08));
      border: 1px solid rgba(255,255,255,0.62);
      box-shadow: var(--shadow);
    }}
    .eyebrow {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(15,118,110,0.10);
      color: #0f766e;
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    h1, h2 {{
      margin: 0;
      font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
      letter-spacing: -0.02em;
    }}
    h1 {{
      margin-top: 16px;
      max-width: 12ch;
      font-size: clamp(2.3rem, 5vw, 4.8rem);
      line-height: 0.94;
    }}
    .hero p {{
      margin: 16px 0 0;
      max-width: 64ch;
      color: var(--muted);
      line-height: 1.62;
      font-size: 1rem;
    }}
    .meta-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 20px;
    }}
    .meta-chip {{
      padding: 9px 12px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.82);
      color: var(--muted);
      font-size: 0.84rem;
    }}
    .reports {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 18px;
      margin-top: 26px;
    }}
    .report-card {{
      display: grid;
      gap: 14px;
      padding: 24px;
      border-radius: var(--radius);
      background:
        linear-gradient(145deg, rgba(255,255,255,0.92), rgba(255,255,255,0.78)),
        linear-gradient(145deg, color-mix(in srgb, var(--accent) 12%, white), rgba(255,255,255,0.0));
      border: 1px solid rgba(255,255,255,0.68);
      box-shadow: var(--shadow);
      text-decoration: none;
      color: inherit;
      transition: transform 180ms ease, box-shadow 180ms ease;
    }}
    .report-card:hover {{
      transform: translateY(-4px);
      box-shadow: 0 28px 56px rgba(21, 32, 43, 0.16);
    }}
    .card-label {{
      justify-self: start;
      padding: 8px 11px;
      border-radius: 999px;
      background: color-mix(in srgb, var(--accent) 12%, white);
      color: var(--accent);
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}
    .report-card h2 {{
      font-size: 1.5rem;
      line-height: 1.08;
    }}
    .report-card p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.58;
    }}
    .card-link {{
      font-weight: 700;
      color: var(--accent);
    }}
    .footer {{
      margin-top: 22px;
      color: var(--muted);
      font-size: 0.86rem;
    }}
    @media (max-width: 980px) {{
      .reports {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <span class="eyebrow">Public dashboard bundle</span>
      <h1>Three election dashboards, one public entry point.</h1>
      <p>
        This static site packages the DPR dashboard, the seat-scenario dashboard, and the Pilpres-vs-Pileg alignment dashboard
        under a single Render deployment. Each report stays standalone, but the landing page keeps the whole analysis legible.
      </p>
      <div class="meta-row">
        <span class="meta-chip">Generated {escape(generated_at)}</span>
        <span class="meta-chip">Static build for Render</span>
        <span class="meta-chip">No generated HTML committed</span>
      </div>
    </section>
    <section class="reports">
      {card_html}
    </section>
    <p class="footer">
      The site is rebuilt from Python source, tracked reference inputs, and the existing map geometry in this repo.
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
