"""LaTeX tables for RQ1 (reports/report.md sec 1.1-1.3)."""

from pathlib import Path

import pandas as pd

from latex_helpers import write_table

ACTION_ORDER = [
    "View result list",
    "Query",
    "Platform switch",
    "View single result",
    "View AI response",
    "View info box",
    "Browsing",
    "Experiment ended",
]


def overall_frequency(results_root: Path, out_dir: Path) -> Path:
    df = pd.read_csv(results_root / "rq1_action_frequencies" / "action_frequencies_overall.csv")
    df = df.set_index("action").loc[ACTION_ORDER].reset_index()
    table = pd.DataFrame({
        "Action": df["action"],
        "Count": df["count"],
        "Share": (df["proportion"] * 100).map("{:.1f}%".format),
    })
    path = out_dir / "rq1_overall_frequency.tex"
    write_table(table, path, "Overall action frequency", "tab:rq1-overall-frequency")
    return path


def by_game(results_root: Path, out_dir: Path) -> Path:
    df = pd.read_csv(results_root / "rq1_action_frequencies" / "action_frequencies_by_game.csv")
    wide = df.pivot(index="action", columns="game", values="proportion").loc[ACTION_ORDER]
    table = pd.DataFrame({
        "Action": wide.index,
        "Best Buds vs Bad Guys": (wide["Best Buds vs Bad Guys"] * 100).map("{:.1f}%".format),
        "Townscaper": (wide["Townscaper"] * 100).map("{:.1f}%".format),
    })
    path = out_dir / "rq1_by_game.tex"
    write_table(table, path, "Action mix by game", "tab:rq1-by-game")
    return path


def session_length_by_game(results_root: Path, out_dir: Path) -> Path:
    df = pd.read_csv(results_root / "rq1_action_frequencies" / "session_lengths.csv")
    summary = df.groupby("game")["n_events_search"].agg(["mean", "median", "min", "max"])
    summary = summary.loc[["Best Buds vs Bad Guys", "Townscaper"]]
    table = pd.DataFrame({
        "Game": summary.index,
        "Mean": summary["mean"].map("{:.1f}".format),
        "Median": summary["median"].astype(int),
        "Min": summary["min"].astype(int),
        "Max": summary["max"].astype(int),
    })
    path = out_dir / "rq1_session_length_by_game.tex"
    write_table(table, path, "Session length by game (search-only events)", "tab:rq1-session-length")
    return path


def build(results_root: Path, out_dir: Path) -> list[Path]:
    return [
        overall_frequency(results_root, out_dir),
        by_game(results_root, out_dir),
        session_length_by_game(results_root, out_dir),
    ]
