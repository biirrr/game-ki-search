"""RQ9: alternative Markov models with platform switches split by type.

RQ2-RQ4's transition analysis treats `Platform switch` as one node, which
hides what's actually a meaningfully different move depending on
destination -- switching to another search engine is not the same
action as switching to a GenAI assistant or to Steam. This rebuilds the
Markov chain with that distinction folded into the state space, using
the destination/source data added for RQ7.

Definitions (researcher, 2026-08-19): a "platform switch" is a switch
between *platforms* -- search engines (including GenAI models) and
storefronts like Steam -- not a jump between regular websites. So:

  - `Platform switch` expands to 4 states by destination category:
    Search engine / AI assistant / Storefront / Other (Other collapses
    RQ7's Community, Game database, and Other buckets -- none of those
    are "platforms" in the sense above, they're specific websites/apps).
  - `View single result` expands to 3 states by source, using simple
    keyword matching rather than RQ7's exact-value platform dict (that
    column is long-tailed -- 60+ distinct sites, mostly one-off gaming
    blogs/forums -- so no exact taxonomy could cover it): Storefront
    (Steam) / Community (Reddit) / Other site (everything else,
    collapsed into a single node per the researcher's suggestion).
  - Every other action (`Query`, `View result list`, `View AI response`,
    `View info box`, `Browsing`, `Experiment ended`) is unchanged.

That's a 13-state chain (vs. RQ2's 8), built overall and per game. This
is exploratory: several of the new states are thin (Platform switch:
Other has 14 events total across both games), so read the resulting
probabilities descriptively, not as hypothesis tests.
"""

from collections import Counter
from itertools import product
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

from data import load_events
from rq3_game_differences import BESTBUDS, TOWNSCAPER
from rq7_platform_details import categorize_platform

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "rq9"

EXPANDED_ACTIONS = [
    "Query",
    "View result list",
    "View single result: Storefront",
    "View single result: Community",
    "View single result: Other site",
    "Platform switch: Search engine",
    "Platform switch: AI assistant",
    "Platform switch: Storefront",
    "Platform switch: Other",
    "View AI response",
    "View info box",
    "Browsing",
    "Experiment ended",
]

# Alternative state space, investigated 2026-08-19 at the researcher's
# suggestion: merge `Platform switch: Other` (14-15 events total -- the
# thinnest state in the split model) into `View single result: Other
# site` as one shared "Other site" node, on the theory that *which*
# action got you to a non-platform site matters less than the fact that
# it's a non-platform site at all. Tested empirically in main() below
# before deciding whether the merge is actually justified.
MERGED_ACTIONS = [
    "Query",
    "View result list",
    "View single result: Storefront",
    "View single result: Community",
    "Other site",
    "Platform switch: Search engine",
    "Platform switch: AI assistant",
    "Platform switch: Storefront",
    "View AI response",
    "View info box",
    "Browsing",
    "Experiment ended",
]

# Collapse RQ7's 6-way platform-switch taxonomy to the 4-way split the
# researcher asked for: only search engine / AI assistant / storefront
# count as "platforms"; everything else is one "Other" node.
_PLATFORM_MERGE = {
    "Search engine": "Search engine",
    "AI assistant": "AI assistant",
    "Storefront": "Storefront",
    "Community": "Other",
    "Game database": "Other",
    "Other": "Other",
}


def categorize_platform_switch(value: str) -> str:
    return _PLATFORM_MERGE[categorize_platform(value)]


def categorize_view_single_result(value: str) -> str:
    v = value.lower()
    if "steam" in v:
        return "Storefront"
    if "reddit" in v:
        return "Community"
    return "Other site"


def expand_label(action: str, detail) -> str:
    if action == "Platform switch":
        if pd.isna(detail):
            return "Platform switch: Other"
        return f"Platform switch: {categorize_platform_switch(str(detail).strip())}"
    if action == "View single result":
        if pd.isna(detail):
            return "View single result: Other site"
        return f"View single result: {categorize_view_single_result(str(detail).strip())}"
    return action


def expand_label_merged(action: str, detail) -> str:
    """Same as expand_label, but Platform switch: Other and View single
    result: Other site both collapse to one shared 'Other site' node."""
    label = expand_label(action, detail)
    if label in ("Platform switch: Other", "View single result: Other site"):
        return "Other site"
    return label


def build_sequences_with(events: pd.DataFrame, label_fn) -> dict[tuple[str, str], list[str]]:
    events = events.sort_values(["participant_id", "game", "step"]).copy()
    events["expanded"] = [
        label_fn(a, d) for a, d in zip(events["action"], events["action_details_clean"])
    ]
    return {key: grp["expanded"].tolist() for key, grp in events.groupby(["participant_id", "game"])}


def sequences_for(seqs_by_key: dict, game: str | None) -> list[list[str]]:
    if game is None:
        return list(seqs_by_key.values())
    return [seq for (_, g), seq in seqs_by_key.items() if g == game]


def transition_counts(seqs: list[list[str]], actions: list[str]) -> pd.DataFrame:
    counts = Counter()
    for seq in seqs:
        for a, b in zip(seq, seq[1:]):
            counts[(a, b)] += 1
    idx = pd.MultiIndex.from_tuples(product(actions, actions), names=["from", "to"])
    s = pd.Series({k: counts.get(k, 0) for k in idx}, index=idx, name="count")
    return s.reset_index()


def to_matrix(counts_df: pd.DataFrame, actions: list[str]) -> pd.DataFrame:
    return (
        counts_df.pivot(index="from", columns="to", values="count")
        .reindex(index=actions, columns=actions)
        .fillna(0)
        .astype(int)
    )


def probability_matrix(mat: pd.DataFrame) -> pd.DataFrame:
    row_sums = mat.sum(axis=1)
    return mat.div(row_sums.replace(0, pd.NA), axis=0).fillna(0.0).astype(float)


def plot_transition_graph(counts: pd.DataFrame, probs: pd.DataFrame, actions: list[str], title: str, path: Path, min_prob: float = 0.22) -> None:
    g = nx.DiGraph()
    g.add_nodes_from(actions)
    for a in actions:
        for b in actions:
            p, c = probs.loc[a, b], counts.loc[a, b]
            if c > 0 and p >= min_prob:
                g.add_edge(a, b, weight=p, count=int(c))
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
        nx.draw_networkx_edges(
            g, pos, edgelist=[(u, v)], width=max(d["weight"] * 6, 0.6),
            edge_color="#b3690f", alpha=0.65, connectionstyle=style,
            arrowsize=12, min_source_margin=26, min_target_margin=26, ax=ax,
        )
    edge_labels = {(u, v): f"{d['weight']:.0%}" for u, v, d in g.edges(data=True) if u != v}
    nx.draw_networkx_edge_labels(g, pos, edge_labels=edge_labels, font_size=6, ax=ax, rotate=False)

    ax.set_title(title, fontsize=12)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def run_for(seqs: list[list[str]], label: str, slug: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    out = RESULTS_DIR
    counts_df = transition_counts(seqs, EXPANDED_ACTIONS)
    counts_df.to_csv(out / f"expanded_transitions_counts_{slug}.csv", index=False)
    mat = to_matrix(counts_df, EXPANDED_ACTIONS)
    probs = probability_matrix(mat)
    probs.round(3).to_csv(out / f"expanded_transitions_probs_{slug}.csv")

    plot_transition_graph(mat, probs, EXPANDED_ACTIONS, f"Expanded (platform-split) transitions — {label}", out / f"expanded_transition_graph_{slug}.png")

    print(f"\n=== {label} ({len(seqs)} sessions) — split model ===")
    print("State frequency (as 'from' state, i.e. how often each state occurs with an outgoing transition):")
    print(mat.sum(axis=1).sort_values(ascending=False).to_string())
    print("\nOutgoing transitions for the 4 platform-switch states:")
    for state in ["Platform switch: Search engine", "Platform switch: AI assistant", "Platform switch: Storefront", "Platform switch: Other"]:
        row = probs.loc[state]
        top = row[row > 0].sort_values(ascending=False)
        n = int(mat.loc[state].sum())
        print(f"  {state} (n={n}): " + ", ".join(f"{k} {v:.0%}" for k, v in top.items()))
    print("\nOutgoing transitions for the 3 View-single-result states:")
    for state in ["View single result: Storefront", "View single result: Community", "View single result: Other site"]:
        row = probs.loc[state]
        top = row[row > 0].sort_values(ascending=False)
        n = int(mat.loc[state].sum())
        print(f"  {state} (n={n}): " + ", ".join(f"{k} {v:.0%}" for k, v in top.items()))
    return mat, probs


def run_merged_for(seqs: list[list[str]], label: str, slug: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    out = RESULTS_DIR
    counts_df = transition_counts(seqs, MERGED_ACTIONS)
    counts_df.to_csv(out / f"merged_transitions_counts_{slug}.csv", index=False)
    mat = to_matrix(counts_df, MERGED_ACTIONS)
    probs = probability_matrix(mat)
    probs.round(3).to_csv(out / f"merged_transitions_probs_{slug}.csv")

    plot_transition_graph(mat, probs, MERGED_ACTIONS, f"Merged-'Other' transitions — {label}", out / f"merged_transition_graph_{slug}.png")

    print(f"\n=== {label} ({len(seqs)} sessions) — merged 'Other site' model ===")
    row = probs.loc["Other site"]
    top = row[row > 0].sort_values(ascending=False)
    n = int(mat.loc["Other site"].sum())
    print(f"  Other site (n={n}): " + ", ".join(f"{k} {v:.0%}" for k, v in top.items()))
    return mat, probs


def compare_other_states(split_probs: pd.DataFrame, label: str) -> None:
    """Is merging actually justified? Compare the two states' outgoing
    transition profiles directly (JS divergence) rather than assuming."""
    from scipy.spatial.distance import jensenshannon

    a = split_probs.loc["Platform switch: Other"]
    b = split_probs.loc["View single result: Other site"]
    common_targets = sorted(set(a.index) | set(b.index))
    a_vec = a.reindex(common_targets, fill_value=0.0).values
    b_vec = b.reindex(common_targets, fill_value=0.0).values
    if a_vec.sum() == 0 or b_vec.sum() == 0:
        print(f"  {label}: one state has zero outgoing transitions -- can't compare")
        return
    js = jensenshannon(a_vec, b_vec, base=2)
    print(f"  {label}: JS divergence between the two 'Other' states' outgoing profiles = {js:.3f}")
    print(f"    Platform switch: Other -> Experiment ended: {a.get('Experiment ended', 0):.0%}")
    print(f"    View single result: Other site -> Experiment ended: {b.get('Experiment ended', 0):.0%}")


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    events = load_events()
    split_seqs = build_sequences_with(events, expand_label)
    merged_seqs = build_sequences_with(events, expand_label_merged)

    print("#" * 70)
    print("# Is merging 'Platform switch: Other' into 'View single result:")
    print("# Other site' justified? Compare their outgoing-transition")
    print("# profiles directly before deciding.")
    print("#" * 70)
    for game, label in [(None, "All sessions"), (BESTBUDS, "Best Buds vs Bad Guys"), (TOWNSCAPER, "Townscaper")]:
        _, split_probs = run_for(sequences_for(split_seqs, game), label, "overall" if game is None else ("bestbuds" if game == BESTBUDS else "townscaper"))
        compare_other_states(split_probs, label)

    print("\n" + "#" * 70)
    print("# Merged model")
    print("#" * 70)
    for game, label, slug in [(None, "All sessions", "overall"), (BESTBUDS, "Best Buds vs Bad Guys", "bestbuds"), (TOWNSCAPER, "Townscaper", "townscaper")]:
        run_merged_for(sequences_for(merged_seqs, game), label, slug)

    print(f"\nOutputs written to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
