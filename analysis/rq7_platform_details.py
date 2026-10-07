"""RQ7: enriching the action-level analyses with *where* people went and
*how much* they typed.

Two new columns (added 2026-08-19): `action_details_clean` (destination
platform for `Platform switch`, source site for `View single result`) and
`action_details_num_tokens` (length of the withheld free-text
`action_details` field -- most meaningful for `Query`, per the
researcher).

Three parts:
  1. Platform-switch destinations, categorized (search engine / AI
     assistant / storefront / community / game database), overall and by
     the RQ4 "AI-assisted" vs. "list-browser" clusters -- does the cluster
     that leans on `View AI response` actually switch to AI platforms?
  2. Query length (tokens): overall, by game, first-half vs. second-half
     of Best Buds sessions (ties to RQ3 sec 4.3), and by RQ4 cluster.
  3. View-single-result self-loops (the strongest RQ6.4 finding, Townscaper
     played-second): when someone re-views a single result right after
     viewing one, is it the *same* source (double-checking) or a
     *different* one (browsing multiple sources)?

`action_details_clean` is free text; a a handful of values (see
`UNMAPPED_PLATFORM_VALUES` if any print at runtime) don't fit the
platform-switch taxonomy cleanly and are bucketed as "other" rather than
guessed at. View-single-result sources are long-tailed (60+ distinct
values, many singletons -- underlying gaming blogs/forums/wikis) so
part 3 uses only same/different comparisons, and part 1's summary table
reports the top sources rather than forcing a full taxonomy onto data
that can't support one.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, wilcoxon

from config import BB_COLOUR, TS_COLOUR
from data import NON_SEARCH_ACTIONS, load_events
from rq3_game_differences import BESTBUDS, TOWNSCAPER, shannon_entropy
from rq6_order_effects import position_table

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "rq7_platform_details"
RQ4_DIR = Path(__file__).resolve().parent.parent / "results" / "rq4_clustering"

PLATFORM_CATEGORY = {
    "Google": "Search engine",
    "Google DE": "Search engine",
    "Google Image Search": "Search engine",
    "Google product search": "Search engine",
    "Google video search": "Search engine",
    "DuckDuckGo": "Search engine",
    "DuckDuckGo Bilder": "Search engine",
    "ChatGPT": "AI assistant",
    "ChatGPT image search": "AI assistant",
    "Google AI Mode": "AI assistant",
    "Meta.AI": "AI assistant",
    "Steam": "Storefront",
    'Steam "More like this"': "Storefront",
    "PC Games": "Storefront",
    "Reddit": "Community",
    "Reddit CozyGames": "Community",
    "Reddit tipofmyjoystick": "Community",
    "Tik Tok": "Community",
    "MobyGames": "Game database",
    "Dosgames": "Game database",
    'Dosgames "More like this"': "Game database",
    "Ranker.com": "Game database",
    "Stern.de": "Other",
    "RetroGameTalk": "Other",
}


def categorize_platform(value: str) -> str:
    value = value.strip()
    category = PLATFORM_CATEGORY.get(value)
    if category is None:
        print(f"[rq7] Unmapped platform-switch destination, bucketed as 'Other': {value!r}")
        category = "Other"
    return category


# --- 1. platform-switch destinations -----------------------------------------

def platform_switch_table(events: pd.DataFrame) -> pd.DataFrame:
    switches = events[events["action"] == "Platform switch"].copy()
    switches["destination"] = switches["action_details_clean"].fillna("(missing)").str.strip()
    switches["category"] = switches["destination"].apply(
        lambda v: categorize_platform(v) if v != "(missing)" else "(missing)"
    )
    return switches


def platform_category_by_cluster(switches: pd.DataFrame, cluster_csv: Path) -> pd.DataFrame | None:
    if not cluster_csv.exists():
        return None
    clusters = pd.read_csv(cluster_csv)[["participant_id", "feature_cluster"]]
    merged = switches.merge(clusters, on="participant_id", how="inner")
    table = pd.crosstab(merged["feature_cluster"], merged["category"], normalize="index")
    return table.round(3)


def plot_platform_categories(switches: pd.DataFrame, path: Path) -> None:
    counts = switches[switches["category"] != "(missing)"].groupby(["game", "category"]).size().unstack(fill_value=0)
    counts = counts.div(counts.sum(axis=1), axis=0)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    counts.T.plot(kind="barh", ax=ax, color=[BB_COLOUR, TS_COLOUR])
    ax.set_xlabel("Share of that game's platform switches")
    ax.set_title("Platform-switch destination category, by game")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# --- 2. query length -----------------------------------------------------

def query_length_table(events: pd.DataFrame) -> pd.DataFrame:
    queries = events[events["action"] == "Query"].dropna(subset=["action_details_num_tokens"])
    return queries[["participant_id", "game", "step", "action_details_num_tokens"]]


def query_length_by_game(queries: pd.DataFrame) -> pd.DataFrame:
    return queries.groupby("game")["action_details_num_tokens"].describe()


def query_length_half_split(events: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Query length, first half vs second half of Best Buds sessions."""
    rows = []
    search = events[~events["action"].isin(NON_SEARCH_ACTIONS)]
    for pid, grp in search[search["game"] == BESTBUDS].groupby("participant_id"):
        grp = grp.sort_values("step")
        mid = len(grp) // 2
        first_q = grp.iloc[:mid].query("action == 'Query'")["action_details_num_tokens"].dropna()
        second_q = grp.iloc[mid:].query("action == 'Query'")["action_details_num_tokens"].dropna()
        if len(first_q) and len(second_q):
            rows.append({"participant_id": pid, "first_half_mean_tokens": first_q.mean(), "second_half_mean_tokens": second_q.mean()})
    df = pd.DataFrame(rows)
    stat, p = wilcoxon(df["first_half_mean_tokens"], df["second_half_mean_tokens"])
    return df, {"wilcoxon_stat": stat, "p_value": p, "n": len(df)}


def query_length_by_cluster(queries: pd.DataFrame, cluster_csv: Path, game: str) -> tuple[pd.DataFrame, dict] | None:
    """Per-participant MEDIAN query length (robust to a single very long
    query skewing a participant's own mean), aggregated by RQ4 cluster.
    Reports mean/median/min/max of those per-participant medians so an
    outlier participant's influence stays visible rather than hidden."""
    if not cluster_csv.exists():
        return None
    clusters = pd.read_csv(cluster_csv)[["participant_id", "feature_cluster"]]
    per_participant = (
        queries[queries["game"] == game]
        .groupby("participant_id")["action_details_num_tokens"]
        .median()
        .reset_index()
        .merge(clusters, on="participant_id")
    )
    groups = per_participant.groupby("feature_cluster")["action_details_num_tokens"]
    summary = groups.agg(["count", "mean", "median", "min", "max"])
    labels = sorted(per_participant["feature_cluster"].unique())
    stat_result = {}
    if len(labels) == 2:
        a = per_participant.loc[per_participant["feature_cluster"] == labels[0], "action_details_num_tokens"]
        b = per_participant.loc[per_participant["feature_cluster"] == labels[1], "action_details_num_tokens"]
        stat, p = mannwhitneyu(a, b, alternative="two-sided")
        stat_result = {"cluster_a": labels[0], "cluster_b": labels[1], "mannwhitney_u": stat, "p_value": p}
    return summary, stat_result


# --- 3. View-single-result self-loop: same source or different? -------------

def self_loop_source_check(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    search = events[~events["action"].isin(NON_SEARCH_ACTIONS)].sort_values(["participant_id", "game", "step"])
    for (pid, game), grp in search.groupby(["participant_id", "game"]):
        actions = grp["action"].tolist()
        details = grp["action_details_clean"].tolist()
        for i in range(len(actions) - 1):
            if actions[i] == "View single result" and actions[i + 1] == "View single result":
                same = (details[i] == details[i + 1]) and pd.notna(details[i])
                rows.append({"participant_id": pid, "game": game, "source_a": details[i], "source_b": details[i + 1], "same_source": same})
    return pd.DataFrame(rows)


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    events = load_events()

    # 1. platform-switch destinations
    switches = platform_switch_table(events)
    switches[["participant_id", "game", "destination", "category"]].to_csv(RESULTS_DIR / "platform_switches.csv", index=False)
    cat_counts = switches.groupby(["game", "category"]).size().unstack(fill_value=0)
    cat_counts.to_csv(RESULTS_DIR / "platform_category_by_game.csv")
    plot_platform_categories(switches, RESULTS_DIR / "platform_categories_by_game.png")

    print("=== 1. Platform-switch destination category, by game ===")
    print(cat_counts.to_string())

    for game, slug in [(BESTBUDS, "bestbuds"), (TOWNSCAPER, "townscaper")]:
        table = platform_category_by_cluster(switches[switches["game"] == game], RQ4_DIR / f"cluster_assignments_{slug}.csv")
        if table is not None:
            table.to_csv(RESULTS_DIR / f"platform_category_by_cluster_{slug}.csv")
            print(f"\n--- {game}: platform-switch category share, by RQ4 cluster ---")
            print(table.to_string())

    # 2. query length
    queries = query_length_table(events)
    queries.to_csv(RESULTS_DIR / "query_lengths.csv", index=False)
    by_game = query_length_by_game(queries)
    by_game.round(2).to_csv(RESULTS_DIR / "query_length_by_game.csv")
    print("\n=== 2. Query length (tokens), by game ===")
    print(by_game.round(2).to_string())

    half_split, half_stats = query_length_half_split(events)
    half_split.to_csv(RESULTS_DIR / "query_length_half_split_bestbuds.csv", index=False)
    print(f"\n--- Best Buds query length, first half vs second half (n={half_stats['n']}) ---")
    print(f"mean first-half tokens={half_split['first_half_mean_tokens'].mean():.2f}, "
          f"mean second-half tokens={half_split['second_half_mean_tokens'].mean():.2f}, "
          f"Wilcoxon p={half_stats['p_value']:.4f}")

    for game, slug in [(BESTBUDS, "bestbuds"), (TOWNSCAPER, "townscaper")]:
        result = query_length_by_cluster(queries, RQ4_DIR / f"cluster_assignments_{slug}.csv", game)
        if result is not None:
            summary, stat_result = result
            summary.round(2).to_csv(RESULTS_DIR / f"query_length_by_cluster_{slug}.csv")
            print(f"\n--- {game}: mean query length (tokens), by RQ4 cluster ---")
            print(summary.round(2).to_string())
            if stat_result:
                print(f"Mann-Whitney p={stat_result['p_value']:.4f}")

    # 3. self-loop source check
    self_loops = self_loop_source_check(events)
    pos = position_table(events)
    self_loops = self_loops.merge(pos, on=["participant_id", "game"], how="left")
    self_loops.to_csv(RESULTS_DIR / "view_single_result_self_loops.csv", index=False)
    print("\n=== 3. View single result -> View single result: same source or different? ===")
    print(self_loops.groupby("game")["same_source"].agg(["sum", "count", "mean"]).rename(
        columns={"sum": "n_same_source", "count": "n_self_loops", "mean": "share_same_source"}
    ).round(3).to_string())

    ts_loops = self_loops[self_loops["game"] == TOWNSCAPER]
    by_order = ts_loops.groupby("position")["same_source"].agg(["sum", "count", "mean"]).rename(
        columns={"sum": "n_same_source", "count": "n_self_loops", "mean": "share_same_source"}
    )
    by_order.round(3).to_csv(RESULTS_DIR / "self_loop_same_source_by_order_townscaper.csv")
    print("\n--- Townscaper View-single-result self-loops: same source or different, by play order ---")
    print(by_order.round(3).to_string())

    print(f"\nOutputs written to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
