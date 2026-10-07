"""LaTeX tables for RQ10 (reports/report.md sec 10.1)."""

from pathlib import Path

import pandas as pd

from latex_helpers import write_table

CATEGORY_ORDER = ["Web search", "Image search", "Conversational search", "Game search", "Other"]


def finer_platform_category_overall(results_root: Path, out_dir: Path) -> Path:
    df = pd.read_csv(results_root / "rq10_finer_platform_categories" / "category_counts_overall.csv")
    df = df.set_index("platform_category").loc[CATEGORY_ORDER].reset_index()
    total = df["count"].sum()
    table = pd.DataFrame({
        "Category": df["platform_category"],
        "Count": df["count"],
        "Share": (df["count"] / total * 100).map("{:.0f}%".format),
    })
    path = out_dir / "rq10_finer_platform_category.tex"
    write_table(table, path, "Finer platform category, overall", "tab:rq10-finer-platform-category")
    return path


def build(results_root: Path, out_dir: Path) -> list[Path]:
    return [finer_platform_category_overall(results_root, out_dir)]
