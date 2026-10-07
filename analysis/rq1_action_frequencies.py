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

from config import GAME_COLOURS
from data import NON_SEARCH_ACTIONS, load_events
from rq3_game_differences import BESTBUDS, TOWNSCAPER

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
    pivot.plot(kind="barh", ax=ax, color=[GAME_COLOURS['Best Buds'], GAME_COLOURS['Townscaper']])
    ax.set_xlabel("Proportion of that game's events")
    ax.set_title("Action mix by game")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_session_length_distribution(lengths: pd.DataFrame, path: Path, games: list[str]) -> None:
    """Horizontal min/Q1/median/Q3/max range per game, search-only event
    counts. Quartiles use pandas' default linear interpolation -- same
    convention as every other quantile reported in this project."""
    fig, ax = plt.subplots(figsize=(7, 0.9 * len(games) + 0.2))
    for i, game in enumerate(games):
        y = len(games) - i - 1
        s = lengths.loc[lengths["game"] == game, "n_events_search"]
        lo, q1, med, q3, hi = s.min(), s.quantile(0.25), s.median(), s.quantile(0.75), s.max()
        color = GAME_COLOURS.get(game, "#666666")

        y_amp = 0.12
        rect_amp = 0.22
        rect_offset = rect_amp / 2
        ax.plot([lo, hi], [y, y], color=color, linewidth=1, alpha=0.6, zorder=1)
        ax.plot([lo, lo], [y - y_amp, y + y_amp], color=color, linewidth=1.5, zorder=2)
        ax.plot([hi, hi], [y - y_amp, y + y_amp], color=color, linewidth=1.5, zorder=2)
        ax.add_patch(plt.Rectangle((q1, y - rect_offset), q3 - q1, rect_amp, facecolor=color, alpha=0.3,
                                    edgecolor="none", zorder=1))
        ax.plot([med, med], [y - 0.16, y + 0.16], color=color, linewidth=3, zorder=3)

        ax.text(hi + 1.5, y, f"median {med:.0f} · mean {s.mean():.1f}", va="center",
                fontsize=11, color="#435350")

    ax.set_yticks(range(len(games) - 1, -1, -1), games)
    ax.tick_params(axis="y", which="major", labelsize=11)
    ax.set_xlim(0, max(lengths["n_events_search"]) * 1.55)
    ax.set_xlabel("Search actions per session", fontsize=12)
    ax.set_title("Session length distribution by game")
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_session_duration_distribution(lengths: pd.DataFrame, path: Path, games: list[str]) -> None:
    """Horizontal min/Q1/median/Q3/max range per game, search-only event
    counts. Quartiles use pandas' default linear interpolation -- same
    convention as every other quantile reported in this project."""
    fig, ax = plt.subplots(figsize=(7, 0.9 * len(games) + 0.2))
    for i, game in enumerate(games):
        y = len(games) - i - 1
        s = lengths.loc[lengths["game"] == game, "search_duration"]
        lo, q1, med, q3, hi = s.min(), s.quantile(0.25), s.median(), s.quantile(0.75), s.max()
        color = GAME_COLOURS.get(game, "#666666")

        y_amp = 0.12
        rect_amp = 0.22
        rect_offset = rect_amp / 2
        ax.plot([lo, hi], [y, y], color=color, linewidth=1, alpha=0.6, zorder=1)
        ax.plot([lo, lo], [y - y_amp, y + y_amp], color=color, linewidth=1.5, zorder=2)
        ax.plot([hi, hi], [y - y_amp, y + y_amp], color=color, linewidth=1.5, zorder=2)
        ax.add_patch(plt.Rectangle((q1, y - rect_offset), q3 - q1, rect_amp, facecolor=color, alpha=0.3,
                                    edgecolor="none", zorder=1))
        ax.plot([med, med], [y - 0.16, y + 0.16], color=color, linewidth=3, zorder=3)

        ax.text(hi + 15, y, f"median {med:.0f} · mean {s.mean():.1f}", va="center",
                fontsize=11, color="#435350")

    ax.set_yticks(range(len(games) - 1, -1, -1), games)
    ax.tick_params(axis="y", which="major", labelsize=11)
    ax.set_xlim(0, max(lengths["search_duration"]) * 1.75)
    ax.set_xlabel("Search duration in seconds", fontsize=12)
    ax.set_title("Session duration distribution by game")
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
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
    plot_session_length_distribution(
        lengths, RESULTS_DIR / "session_length_distribution.png", [BESTBUDS, TOWNSCAPER]
    )

    print("=== Overall action frequencies (search + non-search) ===")
    print(overall.to_string(index=False))
    print("\n=== Session length summary (search-only events) ===")
    print(lengths.groupby("game")["n_events_search"].describe().to_string())
    print(f"\nOutputs written to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
