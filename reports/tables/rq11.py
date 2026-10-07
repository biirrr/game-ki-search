"""LaTeX tables for RQ11 (reports/report.md sec 11.1)."""

from pathlib import Path

import pandas as pd

from latex_helpers import write_table


def building_blocks(results_root: Path, out_dir: Path, min_n_tactics: int = 3) -> Path:
    tactics = pd.read_csv(results_root / "rq11_maximal_repeats" / "tactics_bestbuds.csv")
    n_tactics = len(tactics)

    blocks = pd.read_csv(results_root / "rq11_maximal_repeats" / "tactics_building_blocks_bestbuds.csv")
    blocks = blocks[blocks["n_tactics"] >= min_n_tactics].sort_values("n_tactics", ascending=False)

    table = pd.DataFrame({
        "Building block": blocks["building_block"],
        f"In how many of the {n_tactics} tactics": blocks["n_tactics"],
    })
    path = out_dir / "rq11_building_blocks.tex"
    write_table(
        table, path,
        f"Best Buds vs Bad Guys: 2-step building blocks shared across recurring tactics (n>={min_n_tactics})",
        "tab:rq11-building-blocks",
    )
    return path


def build(results_root: Path, out_dir: Path) -> list[Path]:
    return [building_blocks(results_root, out_dir)]
