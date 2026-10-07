"""LaTeX tables for RQ8 (reports/report.md sec 8.1)."""

from pathlib import Path

import pandas as pd

from latex_helpers import write_table

ROWS = ["Search engine", "Storefront", "Community"]
COLS = ["Search engine", "AI assistant", "Storefront", "Community"]


def platform_transition_matrix(results_root: Path, out_dir: Path) -> Path:
    df = pd.read_csv(results_root / "rq8_platform_sequence" / "platform_category_transitions_townscaper.csv")
    df = df.set_index("from").loc[ROWS, COLS]

    table = pd.DataFrame({"From / To": ROWS})
    for col in COLS:
        table[col] = df[col].values
    path = out_dir / "rq8_platform_transition_matrix.tex"
    write_table(table, path, "Townscaper platform-category transition counts", "tab:rq8-platform-transitions")
    return path


def build(results_root: Path, out_dir: Path) -> list[Path]:
    return [platform_transition_matrix(results_root, out_dir)]
