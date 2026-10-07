"""LaTeX tables for RQ13 (reports/report.md sec 13)."""

from pathlib import Path

import pandas as pd

from latex_helpers import write_table

GAME_ORDER = ["Best Buds vs Bad Guys", "Townscaper"]


def chatbot_experience_vs_cluster(results_root: Path, out_dir: Path) -> Path:
    df = pd.read_csv(results_root / "rq13_experience" / "chatbot_experience_vs_rq4_cluster.csv")
    df = df.set_index("game").loc[GAME_ORDER].reset_index()
    table = pd.DataFrame({
        "Game": df["game"],
        "Majority-cluster median": df["median_cluster0"].map("{:.1f}".format),
        "AI-cluster median": df["median_cluster1"].map("{:.1f}".format),
        "Mann-Whitney p": df["p_value"].map("{:.3f}".format),
    })
    path = out_dir / "rq13_chatbot_experience_vs_cluster.tex"
    write_table(table, path, "Prior chatbot-tool familiarity by RQ4 cluster", "tab:rq13-chatbot-experience")
    return path


def build(results_root: Path, out_dir: Path) -> list[Path]:
    return [chatbot_experience_vs_cluster(results_root, out_dir)]
