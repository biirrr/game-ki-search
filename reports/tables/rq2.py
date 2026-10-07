"""LaTeX tables for RQ2 (reports/report.md sec 2.1-2.2).

Both tables here are curated views of the full transition-probability
matrices (results/rq2_patterns/transitions_probs_*.csv), not verbatim
CSV dumps -- report.md only calls out the "core loop" states and the
states with a non-trivial chance of ending a session. The selection
rules below reproduce report.md's own selections exactly (verified
against the live report text), so re-running this after a data refresh
keeps the same curation logic rather than hardcoding report.md's numbers.
"""

from pathlib import Path

import pandas as pd

from latex_helpers import write_table

CORE_LOOP_STATES = ["Query", "View result list", "Platform switch", "View AI response", "Experiment ended"]
CORE_LOOP_THRESHOLD = 0.2


def core_search_loop(results_root: Path, out_dir: Path) -> Path:
    probs = pd.read_csv(results_root / "rq2_patterns" / "transitions_probs_overall.csv").set_index("from")

    rows = []
    for state in CORE_LOOP_STATES:
        top = probs.loc[state].loc[lambda s: s >= CORE_LOOP_THRESHOLD].sort_values(ascending=False)
        if top.empty:
            next_actions = "(none -- confirmed absorbing)"
        else:
            next_actions = " . ".join(f"{action} ({prob * 100:.0f}%)" for action, prob in top.items())
        rows.append((f"{state} ->", next_actions))

    table = pd.DataFrame(rows, columns=["From", "Most likely next action(s)"])
    path = out_dir / "rq2_core_search_loop.tex"
    write_table(table, path, "First-order transition probabilities: the core search loop", "tab:rq2-core-loop", column_format="ll")
    return path


def exit_probabilities(results_root: Path, out_dir: Path, n_top: int = 3) -> Path:
    bb = pd.read_csv(results_root / "rq2_patterns" / "transitions_probs_bestbuds.csv").set_index("from")["Experiment ended"]
    ts = pd.read_csv(results_root / "rq2_patterns" / "transitions_probs_townscaper.csv").set_index("from")["Experiment ended"]
    exits = pd.DataFrame({"bestbuds": bb, "townscaper": ts}).drop(index="Experiment ended")

    ranked = exits.assign(rank_key=exits.max(axis=1)).sort_values("rank_key", ascending=False)
    top = ranked.iloc[:n_top]
    rest = ranked.iloc[n_top:]

    rows = [(f"{state} ->", f"{r.bestbuds * 100:.1f}%", f"{r.townscaper * 100:.1f}%") for state, r in top.iterrows()]
    rows.append((
        "(all other actions)",
        f"<= {rest['bestbuds'].max() * 100:.1f}%",
        f"<= {rest['townscaper'].max() * 100:.1f}%",
    ))

    table = pd.DataFrame(rows, columns=["From -> Experiment ended", "Best Buds vs Bad Guys", "Townscaper"])
    path = out_dir / "rq2_exit_probabilities.tex"
    write_table(table, path, "Probability of ending the session, by prior action", "tab:rq2-exit-probabilities")
    return path


def build(results_root: Path, out_dir: Path) -> list[Path]:
    return [
        core_search_loop(results_root, out_dir),
        exit_probabilities(results_root, out_dir),
    ]
