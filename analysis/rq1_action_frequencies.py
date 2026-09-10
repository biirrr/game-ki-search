"""RQ1: How common are the individual actions?

Descriptive counts/proportions of the controlled action vocabulary,
sliced by game, participant, and annotator, plus per-session normalized
rates (since session length varies a lot between the two games).

`Experiment ended` is a session/task terminator rather than a real search
action (see docs/planning_and_background.md, sec 4.1/4.2); it's included
in the raw counts for completeness but excluded from the "search action"
rate tables so it doesn't dilute the comparison of actual search behavior.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from data import NON_SEARCH_ACTIONS, load_events

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "rq1_action_frequencies"


def action_counts(events: pd.DataFrame, by: list[str] | None = None) -> pd.DataFrame:
    """Count and proportion of each action, optionally grouped by `by`."""
    group_cols = (by or []) + ["action"]
    counts = events.groupby(group_cols, observed=True).size().rename("count")
    counts = counts.reset_index()
    if by:
        totals = counts.groupby(by)["count"].transform("sum")
    else:
        totals = counts["count"].sum()
    counts["proportion"] = counts["count"] / totals
    sort_cols = (by or []) + ["count"]
    return counts.sort_values(sort_cols, ascending=[True] * len(by or []) + [False])


def session_lengths(events: pd.DataFrame) -> pd.DataFrame:
    """Session length (all events, and search-only events) per participant/game."""
    all_len = events.groupby(["participant_id", "game"]).size().rename("n_events_all")
    search_only = events[~events["action"].isin(NON_SEARCH_ACTIONS)]
    search_len = search_only.groupby(["participant_id", "game"]).size().rename("n_events_search")
    return pd.concat([all_len, search_len], axis=1).reset_index()


def per_participant_rates(events: pd.DataFrame) -> pd.DataFrame:
    """Per-participant-per-game action rate, normalized by search-only session length."""
    search_only = events[~events["action"].isin(NON_SEARCH_ACTIONS)]
    counts = (
        search_only.groupby(["participant_id", "game", "action"], observed=True)
        .size()
        .rename("count")
        .reset_index()
    )
    session_len = counts.groupby(["participant_id", "game"])["count"].transform("sum")
    counts["rate"] = counts["count"] / session_len
    return counts


def plot_overall_frequencies(overall: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    plotted = overall.sort_values("count", ascending=True)
    ax.barh(plotted["action"], plotted["count"], color="#4C72B0")
    ax.set_xlabel("Number of annotated events")
    ax.set_title("Overall action frequency (all 21 participants, both games)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_by_game(by_game: pd.DataFrame, path: Path) -> None:
    pivot = by_game.pivot(index="action", columns="game", values="proportion").fillna(0)
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=True).index]
    fig, ax = plt.subplots(figsize=(7, 4))
    pivot.plot(kind="barh", ax=ax, color=["#DD8452", "#4C72B0"])
    ax.set_xlabel("Proportion of that game's events")
    ax.set_title("Action mix by game")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    events = load_events()

    overall = action_counts(events)
    overall.to_csv(RESULTS_DIR / "action_frequencies_overall.csv", index=False)

    by_game = action_counts(events, by=["game"])
    by_game.to_csv(RESULTS_DIR / "action_frequencies_by_game.csv", index=False)

    by_annotator = action_counts(events, by=["annotator"])
    by_annotator.to_csv(RESULTS_DIR / "action_frequencies_by_annotator.csv", index=False)

    lengths = session_lengths(events)
    lengths.to_csv(RESULTS_DIR / "session_lengths.csv", index=False)

    rates = per_participant_rates(events)
    rates.to_csv(RESULTS_DIR / "action_rates_by_participant_game.csv", index=False)

    plot_overall_frequencies(overall, RESULTS_DIR / "overall_frequencies.png")
    plot_by_game(by_game, RESULTS_DIR / "frequencies_by_game.png")

    print("=== Overall action frequencies (search + non-search) ===")
    print(overall.to_string(index=False))
    print("\n=== Session length summary (search-only events) ===")
    print(lengths.groupby("game")["n_events_search"].describe().to_string())
    print(f"\nOutputs written to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
