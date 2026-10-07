"""LaTeX tables for RQ6.4 (reports/report.md sec 6.4).

Both tables here need more than the saved results/*.csv files: report.md's
§6.4 "closing-move by order" table is the full per-target-action
transition row out of `View single result`, split by play order, which
rq6_4_order_within_game.py computes in memory but only ever saves the
`-> Experiment ended` column (results/rq6_4_order_within_game/
closing_move_by_order_townscaper.csv) and per-from-state chi2/JS summary
stats, not the full row. So this module re-derives it the same way the
analysis script does, importing that script's own helpers rather than
recomputing the pipeline a second, possibly-divergent way. The half-split
entropy table (§6.4's second table) *is* fully backed by saved CSVs.
"""

from pathlib import Path

import pandas as pd
from scipy.stats import wilcoxon

from data import load_events
from rq2_patterns import build_sequences, probability_matrix, to_matrix, transition_counts
from rq3_game_differences import TOWNSCAPER
from rq6_4_order_within_game import FIRST, SECOND, sequences_for_order
from rq6_order_effects import position_table

from latex_helpers import write_table

CLOSING_MOVE_ROWS = ["Experiment ended", "Platform switch", "Browsing", "View single result"]
ORDER_LABEL = {FIRST: "Played first", SECOND: "Played second (after Best Buds)"}


def closing_move_by_order(results_root: Path, out_dir: Path) -> Path:
    events = load_events()
    seqs_by_key = build_sequences(events)
    pos = position_table(events)

    rows = {}
    for order in (FIRST, SECOND):
        seqs = sequences_for_order(seqs_by_key, pos, TOWNSCAPER, order)
        probs = probability_matrix(to_matrix(transition_counts(seqs)))
        rows[order] = probs.loc["View single result"]

    table = pd.DataFrame({
        "From `View single result` ->": [
            f"{r}" + (" (self-loop)" if r == "View single result" else "") for r in CLOSING_MOVE_ROWS
        ],
        "Played first": [f"{rows[FIRST][r] * 100:.0f}%" for r in CLOSING_MOVE_ROWS],
        "Played second (after Best Buds)": [f"{rows[SECOND][r] * 100:.0f}%" for r in CLOSING_MOVE_ROWS],
    })
    path = out_dir / "rq6_closing_move_by_order.tex"
    write_table(
        table, path,
        "Townscaper: next action after `View single result', by play order",
        "tab:rq6-closing-move-by-order",
    )
    return path


def bestbuds_order_entropy(results_root: Path, out_dir: Path) -> Path:
    rows = []
    for label, fname in [("Played first (n=10)", "bestbuds_half_split_played_first.csv"),
                          ("Played second, after Townscaper win (n=11)", "bestbuds_half_split_played_second.csv")]:
        half = pd.read_csv(results_root / "rq6_4_order_within_game" / fname)
        _, p = wilcoxon(half["first_half_entropy"], half["second_half_entropy"])
        rows.append({
            "Best Buds order": label,
            "First-half entropy": f"{half['first_half_entropy'].mean():.2f}",
            "Second-half entropy": f"{half['second_half_entropy'].mean():.2f}",
            "Wilcoxon p": f"{p:.3f}",
            "Novel-bigram rate (2nd half)": f"{half['second_half_novel_bigram_rate'].mean() * 100:.0f}%",
        })
    table = pd.DataFrame(rows)
    path = out_dir / "rq6_bestbuds_order_entropy.tex"
    write_table(
        table, path,
        "Best Buds first/second-half entropy and novel-bigram rate, by play order",
        "tab:rq6-bestbuds-order-entropy",
        column_format="lrrrr",
    )
    return path


def build(results_root: Path, out_dir: Path) -> list[Path]:
    return [
        closing_move_by_order(results_root, out_dir),
        bestbuds_order_entropy(results_root, out_dir),
    ]
