"""RQ10: finer-grained platform categories (data/platform_map.json),
applied via the new `context` column, to surface image-search reliance.

Two things distinguish this from RQ7/RQ8/RQ9:
  1. The category scheme is the researcher's own (`data/platform_map.json`),
     not the 4-6 coarse buckets used in RQ7/RQ8/RQ9 -- it separates plain
     web search from image / game / conversational / video / news / list /
     product / forum search, motivated by the observation that many
     participants leaned heavily on image search specifically.
  2. It's applied to the `context` column (analysis/data.py
     `add_platform_context`), not just to raw `Platform switch`
     destinations -- so a `Query` or `View result list` typed/seen *while*
     on Google Image Search also gets tagged "Image search", not just the
     `Platform switch` event that got them there.

`View single result`'s context is a specific landing site (from its own
`action_details_clean`), not one of `platform_map.json`'s search-platform
keys, so it's intentionally left out of this categorization -- that's
RQ8's question (which *site* people land on), not this one (which *kind
of search platform* they're using).

Three parts:
  1. Category frequency, overall and by game -- how common is image
     search, concretely.
  2. RQ3-style test: does image-search reliance differ between the two
     games?
  3. An expanded Markov model (RQ9-style, but `Platform switch` split by
     this finer scheme) plus n-grams over the categorized action stream.
"""

import json
import re
from collections import Counter
from itertools import product
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
from scipy.spatial.distance import jensenshannon
from scipy.stats import chi2_contingency

from data import NON_SEARCH_ACTIONS, load_events
from rq3_game_differences import BESTBUDS, TOWNSCAPER

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "rq10_finer_platform_categories"
MAP_PATH = Path(__file__).resolve().parent.parent / "data" / "platform_map.json"

# Known issue in the source file: "Meta.AI" -> "Conservational search" is a
# typo for "Conversational search" (all three other AI-assistant entries --
# ChatGPT, ChatGPT image search, Google AI Mode -- use the correct
# spelling). Normalized here; flagged, not silently left to fragment the
# category into two near-duplicates.
_TYPO_FIXES = {"Conservational search": "Conversational search"}


def load_platform_map() -> dict[str, str]:
    raw = json.loads(MAP_PATH.read_text())
    # Two of the source file's own keys carry trailing whitespace
    # ('RetroGameTalk  ', 'PC Games ') that the (already-stripped) context
    # values in the data would never match -- strip keys too, so lookups
    # aren't sabotaged by whitespace that isn't visible in the JSON.
    stripped = {k.strip(): v for k, v in raw.items()}
    fixed = {k: _TYPO_FIXES.get(v, v) for k, v in stripped.items()}
    n_fixed = sum(1 for v in raw.values() if v in _TYPO_FIXES)
    if n_fixed:
        print(f"[rq10] Normalized {n_fixed} '{list(_TYPO_FIXES)[0]}' typo -> "
              f"'{_TYPO_FIXES['Conservational search']}' ({[k for k,v in raw.items() if v in _TYPO_FIXES]})")
    return fixed


def categorize(context: str, platform_map: dict[str, str]) -> str:
    context = context.strip()
    if context in platform_map:
        return platform_map[context]
    print(f"[rq10] Unmapped platform context, bucketed as 'Uncategorized': {context!r}")
    return "Uncategorized"


def add_category_column(events: pd.DataFrame, platform_map: dict[str, str]) -> pd.DataFrame:
    events = events.copy()
    is_view_single = events["action"] == "View single result"
    categorizable = events["context"].notna() & ~is_view_single
    events["platform_category"] = pd.NA
    events.loc[categorizable, "platform_category"] = events.loc[categorizable, "context"].apply(
        lambda v: categorize(v, platform_map)
    )
    return events


# --- 1. category frequency ----------------------------------------------

def category_counts(events: pd.DataFrame, by_game: bool) -> pd.DataFrame:
    search = events[~events["action"].isin(NON_SEARCH_ACTIONS) & events["platform_category"].notna()]
    group = ["game", "platform_category"] if by_game else ["platform_category"]
    return search.groupby(group).size().rename("count").reset_index()


# --- 2. image-search reliance: RQ3-style game comparison --------------------

def image_search_share_per_session(events: pd.DataFrame) -> pd.DataFrame:
    """Share of each session's *categorizable* events spent in Image search."""
    search = events[~events["action"].isin(NON_SEARCH_ACTIONS) & events["platform_category"].notna()]
    rows = []
    for (pid, game), grp in search.groupby(["participant_id", "game"]):
        n = len(grp)
        n_image = (grp["platform_category"] == "Image search").sum()
        rows.append({"participant_id": pid, "game": game, "n_categorizable": n,
                      "n_image_search": int(n_image), "image_search_share": n_image / n if n else 0.0})
    return pd.DataFrame(rows)


def category_distribution_test(events: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    counts = category_counts(events, by_game=True)
    table = counts.pivot(index="game", columns="platform_category", values="count").fillna(0)
    chi2, p, dof, _ = chi2_contingency(table.values)
    a, b = table.loc[BESTBUDS].values, table.loc[TOWNSCAPER].values
    js = jensenshannon(a / a.sum(), b / b.sum(), base=2)
    return table, {"chi2": float(chi2), "dof": int(dof), "p_value": float(p), "js_divergence": float(js)}


def plot_category_by_game(table: pd.DataFrame, path: Path) -> None:
    props = table.div(table.sum(axis=1), axis=0).T.sort_values(BESTBUDS)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    props.plot(kind="barh", ax=ax, color=["#b3690f", "#009485"])
    ax.set_xlabel("Share of that game's categorizable events")
    ax.set_title("Finer platform category (platform_map.json), by game")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# --- 3. expanded Markov model + n-grams --------------------------------------

def build_state(action: str, category) -> str:
    if action == "Platform switch" and pd.notna(category):
        return f"Platform switch: {category}"
    return action


def build_sequences(events: pd.DataFrame) -> dict[tuple[str, str], list[str]]:
    events = events.sort_values(["participant_id", "game", "step"])
    states = [build_state(a, c) for a, c in zip(events["action"], events["platform_category"])]
    events = events.assign(state=states)
    return {key: grp["state"].tolist() for key, grp in events.groupby(["participant_id", "game"])}


def all_states(seqs_by_key: dict) -> list[str]:
    seen: dict[str, None] = {}
    order_hint = [
        "Query", "View result list", "View single result", "View AI response",
        "View info box", "Browsing", "Experiment ended",
    ]
    switch_states = sorted({s for seq in seqs_by_key.values() for s in seq if s.startswith("Platform switch")})
    for s in order_hint + switch_states:
        seen[s] = None
    return list(seen)


def transition_counts(seqs: list[list[str]], states: list[str]) -> pd.DataFrame:
    counts = Counter()
    for seq in seqs:
        for a, b in zip(seq, seq[1:]):
            counts[(a, b)] += 1
    idx = pd.MultiIndex.from_tuples(product(states, states), names=["from", "to"])
    s = pd.Series({k: counts.get(k, 0) for k in idx}, index=idx, name="count")
    return s.reset_index()


def to_matrix(counts_df: pd.DataFrame, states: list[str]) -> pd.DataFrame:
    return counts_df.pivot(index="from", columns="to", values="count").reindex(index=states, columns=states).fillna(0).astype(int)


def probability_matrix(mat: pd.DataFrame) -> pd.DataFrame:
    row_sums = mat.sum(axis=1)
    return mat.div(row_sums.replace(0, pd.NA), axis=0).fillna(0.0).astype(float)


def plot_graph(counts: pd.DataFrame, probs: pd.DataFrame, states: list[str], title: str, path: Path, min_prob: float = 0.15) -> None:
    g = nx.DiGraph()
    g.add_nodes_from(states)
    for a in states:
        for b in states:
            p, c = probs.loc[a, b], counts.loc[a, b]
            if c > 0 and p >= min_prob:
                g.add_edge(a, b, weight=p)
    # Isolated nodes (no edge clears min_prob) are kept, not dropped: dropping
    # them would shrink the node count differently per game/threshold, which
    # shifts circular_layout's angular spacing and makes the same action land
    # in a different position across plots -- exactly what breaks comparability.
    pos = nx.circular_layout(g)
    fig, ax = plt.subplots(figsize=(11, 11))
    nx.draw_networkx_nodes(g, pos, node_color="#eef1ef", edgecolors="#435350", node_size=2600, ax=ax)
    nx.draw_networkx_labels(g, pos, font_size=7, ax=ax)
    for u, v, d in g.edges(data=True):
        style = "arc3,rad=0.15" if u != v else "arc3,rad=0.7"
        nx.draw_networkx_edges(g, pos, edgelist=[(u, v)], width=max(d["weight"] * 6, 0.6),
                                edge_color="#b3690f", alpha=0.65, connectionstyle=style,
                                arrowsize=12, min_source_margin=26, min_target_margin=26, ax=ax)
    edge_labels = {(u, v): f"{d['weight']:.0%}" for u, v, d in g.edges(data=True) if u != v}
    nx.draw_networkx_edge_labels(g, pos, edge_labels=edge_labels, font_size=6, ax=ax, rotate=False)
    ax.set_title(title, fontsize=12)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def top_ngrams(seqs: list[list[str]], n: int, k: int = 15) -> pd.DataFrame:
    counts = Counter()
    for seq in seqs:
        for i in range(len(seq) - n + 1):
            counts[tuple(seq[i:i + n])] += 1
    return pd.DataFrame([{"pattern": " -> ".join(p), "count": c} for p, c in counts.most_common(k)])


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    platform_map = load_platform_map()
    events = load_events()
    events = add_category_column(events, platform_map)

    # 1. category frequency
    overall = category_counts(events, by_game=False).sort_values("count", ascending=False)
    overall.to_csv(RESULTS_DIR / "category_counts_overall.csv", index=False)
    print("=== 1. Platform category frequency (overall, via context column) ===")
    print(overall.to_string(index=False))

    # image-search share per session
    img_share = image_search_share_per_session(events)
    img_share.to_csv(RESULTS_DIR / "image_search_share_by_session.csv", index=False)
    print("\n--- Image-search share per session, by game ---")
    print(img_share.groupby("game")["image_search_share"].describe().to_string())
    print("\n--- Participants who used image search at all, by game ---")
    print(img_share.assign(used=img_share["n_image_search"] > 0).groupby("game")["used"].agg(["sum", "count"]))

    # 2. game comparison
    table, stats = category_distribution_test(events)
    table.to_csv(RESULTS_DIR / "category_counts_by_game.csv")
    plot_category_by_game(table, RESULTS_DIR / "category_by_game.png")
    print("\n=== 2. Category distribution: Best Buds vs Townscaper ===")
    print(table.to_string())
    print(f"chi2={stats['chi2']:.3f} dof={stats['dof']} p={stats['p_value']:.4f} JS={stats['js_divergence']:.3f}")

    # 3. expanded Markov model + n-grams
    seqs_by_key = build_sequences(events)
    states = all_states(seqs_by_key)
    for game, slug in [(None, "overall"), (BESTBUDS, "bestbuds"), (TOWNSCAPER, "townscaper")]:
        seqs = list(seqs_by_key.values()) if game is None else [s for (_, g), s in seqs_by_key.items() if g == game]
        counts_df = transition_counts(seqs, states)
        counts_df.to_csv(RESULTS_DIR / f"transitions_counts_{slug}.csv", index=False)
        mat = to_matrix(counts_df, states)
        probs = probability_matrix(mat)
        probs.round(3).to_csv(RESULTS_DIR / f"transitions_probs_{slug}.csv")
        plot_graph(mat, probs, states, f"Finer-platform transitions — {slug}", RESULTS_DIR / f"transition_graph_{slug}.png")

        top_ngrams(seqs, 2).to_csv(RESULTS_DIR / f"top_2grams_{slug}.csv", index=False)
        top_ngrams(seqs, 3).to_csv(RESULTS_DIR / f"top_3grams_{slug}.csv", index=False)

        print(f"\n=== 3. {slug}: states involving Image search ===")
        img_states = [s for s in states if "Image search" in s]
        for s in img_states:
            n = int(mat.loc[s].sum())
            if n == 0:
                continue
            row = probs.loc[s]
            top = row[row > 0].sort_values(ascending=False)
            print(f"  {s} (n={n}): " + ", ".join(f"{k2} {v:.0%}" for k2, v in top.items()))
            incoming = mat[s]
            top_in = incoming[incoming > 0].sort_values(ascending=False)
            print(f"    into {s}: " + ", ".join(f"{k2} ({v})" for k2, v in top_in.items()))

    print(f"\nOutputs written to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
