"""
Shared saving helpers for the experiment scripts in experiments.py.

Every experiment writes three things under the same base name:

    data/generated/<name>.csv     the logged time series, SIMULATED DATA
    results/figures/<name>.png    a plot of the same run
    results/reports/<name>.json   a summary: what was configured, and the
                                   metrics computed from the run

Keeping the three in lockstep under one name is what makes it possible to
go from a plot back to the exact numbers behind it.
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "generated"
FIGURES_DIR = PROJECT_ROOT / "results" / "figures"
REPORTS_DIR = PROJECT_ROOT / "results" / "reports"


def save_outputs(name: str, df=None, fig=None, summary: dict = None):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    paths = {}

    if df is not None:
        csv_path = DATA_DIR / f"{name}.csv"
        df.to_csv(csv_path, index=False)
        paths["csv"] = str(csv_path)

    if fig is not None:
        png_path = FIGURES_DIR / f"{name}.png"
        fig.savefig(png_path, dpi=140)
        paths["png"] = str(png_path)

    if summary is not None:
        summary = dict(summary)
        summary["data_label"] = "SIMULATED DATA, not a physical measurement"
        json_path = REPORTS_DIR / f"{name}.json"

        def _default(o):
            try:
                return float(o)
            except (TypeError, ValueError):
                return str(o)

        with open(json_path, "w") as f:
            json.dump(summary, f, indent=2, default=_default)
        paths["json"] = str(json_path)

    return paths
