"""RQ2: typical action patterns / sequences.

Three complementary views, overall and per game:
  1. First-order Markov transition matrix (counts + probabilities) and a
     directed-graph rendering of it.
  2. A positional Sankey diagram of the first N steps of each session —
     shows how sequences typically *open*, which a stationary transition
     matrix can't (it collapses step position away).
  3. Frequent action patterns: contiguous n-grams (literal repeated
     sub-sequences) and PrefixSpan closed sequential patterns (order-
     preserving, not necessarily contiguous).

`Experiment ended` is kept as an explicit absorbing end-state (see
docs/planning_and_background.md sec 4.2): it has no outgoing transitions,
so it always ends up a sink in the transition graph.
"""

from collections import Counter
from itertools import product
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import plotly.colors as pc
import plotly.graph_objects as go
from prefixspan import PrefixSpan

from data import load_events

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "rq2_patterns"

ACTIONS = [
    "Query",
    "View result list",
    "View single result",
    "Platform switch",
    "View AI response",
    "View info box",
    "Browsing",
    "Experiment ended",
]
ACTION_COLOR = dict(zip(ACTIONS, pc.qualitative.Safe))

SANKEY_STEPS = 6


# --- sequences -------------------------------------------------------------

def build_sequences(events: pd.DataFrame) -> dict[tuple[str, str], list[str]]:
    events = events.sort_values(["participant_id", "game", "step"])
    return {
        key: grp["action"].tolist()
        for key, grp in events.groupby(["participant_id", "game"])
    }


def sequences_for(sequences: dict, game: str | None = None) -> list[list[str]]:
    if game is None:
        return list(sequences.values())
    return [seq for (_, g), seq in sequences.items() if g == game]


# --- 1. transition matrix ----------------------------------------------------

def transition_counts(seqs: list[list[str]]) -> pd.DataFrame:
    counts = Counter()
    for seq in seqs:
        for a, b in zip(seq, seq[1:]):
            counts[(a, b)] += 1
    idx = pd.MultiIndex.from_tuples(product(ACTIONS, ACTIONS), names=["from", "to"])
    s = pd.Series({k: counts.get(k, 0) for k in idx}, index=idx, name="count")
    return s.reset_index()


def to_matrix(counts_df: pd.DataFrame) -> pd.DataFrame:
    return (
        counts_df.pivot(index="from", columns="to", values="count")
        .reindex(index=ACTIONS, columns=ACTIONS)
        .fillna(0)
        .astype(int)
    )


def probability_matrix(mat: pd.DataFrame) -> pd.DataFrame:
    row_sums = mat.sum(axis=1)
    return mat.div(row_sums.replace(0, pd.NA), axis=0).fillna(0.0).astype(float)


def plot_transition_graph(counts: pd.DataFrame, probs: pd.DataFrame, title: str, path: Path, min_prob: float = 0.20) -> None:
    g = nx.DiGraph()
    g.add_nodes_from(ACTIONS)
    for a in ACTIONS:
        for b in ACTIONS:
            p, c = probs.loc[a, b], counts.loc[a, b]
            if c > 0 and p >= min_prob:
                g.add_edge(a, b, weight=p, count=int(c))

    pos = nx.circular_layout(g)
    fig, ax = plt.subplots(figsize=(8.5, 8.5))
    nx.draw_networkx_nodes(g, pos, node_color="#eef1ef", edgecolors="#435350", node_size=2800, ax=ax)
    nx.draw_networkx_labels(g, pos, font_size=8, ax=ax)

    for u, v, d in g.edges(data=True):
        rad = 0.15 if u != v else 0.0
        style = "arc3,rad=0.15" if u != v else "arc3,rad=0.7"
        nx.draw_networkx_edges(
            g, pos, edgelist=[(u, v)], width=max(d["weight"] * 7, 0.6),
            edge_color="#b3690f", alpha=0.65, connectionstyle=style,
            arrowsize=13, min_source_margin=30, min_target_margin=30, ax=ax,
        )
    edge_labels = {(u, v): f"{d['weight']:.0%}" for u, v, d in g.edges(data=True) if u != v}
    nx.draw_networkx_edge_labels(g, pos, edge_labels=edge_labels, font_size=6.5, ax=ax, rotate=False)

    ax.set_title(title, fontsize=12)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# --- 2. positional sankey ----------------------------------------------------

def plot_positional_sankey(seqs: list[list[str]], title: str, path: Path, n_steps: int = SANKEY_STEPS) -> None:
    node_index: dict[tuple[int, str], int] = {}
    node_labels: list[str] = []
    node_colors: list[str] = []

    node_x: list[float] = []
    node_y: list[float] = []

    def node_id(step: int, action: str) -> int:
        key = (step, action)
        if key not in node_index:
            node_index[key] = len(node_labels)
            node_labels.append(action)
            node_colors.append(ACTION_COLOR[action])
            # Fixed grid position: column = step, row = action's rank in
            # ACTIONS, so the same action lines up horizontally across
            # steps and the diagram reads like a sequence-index plot
            # rather than a value-sorted hairball.
            node_x.append(0.02 + 0.88 * (step - 1) / (n_steps - 1))
            node_y.append(0.03 + 0.94 * ACTIONS.index(action) / (len(ACTIONS) - 1))
        return node_index[key]

    link_counts: Counter = Counter()
    for seq in seqs:
        trimmed = seq[:n_steps]
        for step, (a, b) in enumerate(zip(trimmed, trimmed[1:]), start=1):
            src, dst = node_id(step, a), node_id(step + 1, b)
            link_counts[(src, dst)] += 1

    sources = [s for s, _ in link_counts]
    targets = [t for _, t in link_counts]
    values = list(link_counts.values())

    def to_rgba(rgb_color: str, alpha: float = 0.45) -> str:
        r, g, b = pc.unlabel_rgb(rgb_color)
        return f"rgba({r},{g},{b},{alpha})"

    link_colors = [to_rgba(node_colors[s]) for s in sources]

    fig = go.Figure(
        go.Sankey(
            arrangement="fixed",
            node=dict(
                label=node_labels, color=node_colors, x=node_x, y=node_y,
                pad=12, thickness=12,
                line=dict(color="rgba(0,0,0,0.25)", width=0.5),
            ),
            link=dict(source=sources, target=targets, value=values, color=link_colors),
        )
    )
    fig.update_layout(title=title, font_size=11, margin=dict(l=10, r=120, t=50, b=10))
    fig.write_html(path, include_plotlyjs="cdn")


# --- 3. frequent patterns ----------------------------------------------------

def top_ngrams(seqs: list[list[str]], n: int, k: int = 15) -> pd.DataFrame:
    counts = Counter()
    for seq in seqs:
        for i in range(len(seq) - n + 1):
            counts[tuple(seq[i : i + n])] += 1
    top = counts.most_common(k)
    return pd.DataFrame(
        [{"pattern": " -> ".join(p), "count": c} for p, c in top]
    )


def top_prefixspan_patterns(seqs: list[list[str]], k: int = 15, min_len: int = 2) -> pd.DataFrame:
    ps = PrefixSpan(seqs)
    results = ps.topk(k + 20, closed=True)
    rows = [
        {"pattern": " -> ".join(pat), "support": support}
        for support, pat in sorted(results, key=lambda x: -x[0])
        if len(pat) >= min_len
    ]
    return pd.DataFrame(rows[:k])


# --- main ----------------------------------------------------------------

def run_for(seqs: list[list[str]], label: str, slug: str) -> None:
    out = RESULTS_DIR
    counts_df = transition_counts(seqs)
    counts_df.to_csv(out / f"transitions_counts_{slug}.csv", index=False)
    mat = to_matrix(counts_df)
    probs = probability_matrix(mat)
    probs.round(3).to_csv(out / f"transitions_probs_{slug}.csv")

    for min_prob in [0.05, 0.1, 0.2]:
        plot_transition_graph(mat, probs, f"Action transitions — {label}",
            out / f"transition_graph_{slug}-min_prob_{min_prob}.png", min_prob=min_prob)
    # Canonical copy at the report's chosen threshold (0.2, the most legible),
    # under the plain filename the report links to -- keeps that link valid
    # and current without re-running min_prob=0.2 under two different names
    # silently drifting apart.
    plot_transition_graph(mat, probs, f"Action transitions — {label}",
        out / f"transition_graph_{slug}.png", min_prob=0.2)
    plot_positional_sankey(seqs, f"First {SANKEY_STEPS} steps — {label}", out / f"sankey_{slug}.html")

    top_ngrams(seqs, 2, k=50).to_csv(out / f"top_2-grams_{slug}.csv", index=False)
    top_ngrams(seqs, 3, k=50).to_csv(out / f"top_3-grams_{slug}.csv", index=False)
    top_ngrams(seqs, 4, k=50).to_csv(out / f"top_4-grams_{slug}.csv", index=False)
    top_ngrams(seqs, 5, k=50).to_csv(out / f"top_5-grams_{slug}.csv", index=False)
    top_ngrams(seqs, 6, k=50).to_csv(out / f"top_6-grams_{slug}.csv", index=False)
    top_prefixspan_patterns(seqs).to_csv(out / f"top_prefixspan_patterns_{slug}.csv", index=False)

    print(f"\n=== {label} ({len(seqs)} sessions) ===")
    print("Top bigrams:")
    print(top_ngrams(seqs, 2, 8).to_string(index=False))


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    events = load_events()
    seqs_by_key = build_sequences(events)

    run_for(sequences_for(seqs_by_key), "All sessions", "overall")
    run_for(sequences_for(seqs_by_key, "Best Buds vs Bad Guys"), "Best Buds vs Bad Guys", "bestbuds")
    run_for(sequences_for(seqs_by_key, "Townscaper"), "Townscaper", "townscaper")

    print(f"\nOutputs written to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
