"""RQ3: how do search strategies differ between the two games?

Formalizes the resolved-vs-unresolved contrast previewed in RQ2 (the
per-game exit-probability table): see
docs/planning_and_background.md sec 4.3.

Three parts:
  1. Statistical comparison of the two games' transition matrices --
     a chi-square test per "from" state, plus Jensen-Shannon divergence
     (robust to the sparse cells chi-square struggles with).
  2. Paired, within-subject comparison of session-level features (same 21
     participants played both games): length, action entropy, query rate,
     platform-switch rate -- Wilcoxon signed-rank per feature.
  3. Within Best Buds specifically (the game nobody solved): does the
     second half of the session look different from the first --
     plateauing (repeating already-seen bigrams) or continued exploration
     (novel bigrams)?
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial.distance import jensenshannon
from scipy.stats import chi2_contingency, wilcoxon

from data import NON_SEARCH_ACTIONS, load_events
from rq2_patterns import (
    ACTIONS,
    build_sequences,
    probability_matrix,
    sequences_for,
    to_matrix,
    transition_counts,
)

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "rq3"
BESTBUDS = "Best Buds vs Bad Guys"
TOWNSCAPER = "Townscaper"


# --- 1. transition matrix comparison ----------------------------------------

def compare_transition_matrices(mat_a: pd.DataFrame, mat_b: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for state in ACTIONS:
        if state == "Experiment ended":
            continue  # absorbing: no outgoing transitions to compare
        a_counts = mat_a.loc[state].values.astype(float)
        b_counts = mat_b.loc[state].values.astype(float)

        table = np.vstack([a_counts, b_counts])
        nonzero_cols = table.sum(axis=0) > 0
        table = table[:, nonzero_cols]
        if table.shape[1] >= 2 and table.sum() > 0:
            chi2, p, dof, _ = chi2_contingency(table)
        else:
            chi2, p, dof = np.nan, np.nan, np.nan

        a_prob = a_counts / a_counts.sum() if a_counts.sum() else a_counts
        b_prob = b_counts / b_counts.sum() if b_counts.sum() else b_counts
        js = jensenshannon(a_prob, b_prob, base=2)

        rows.append(
            {
                "from": state,
                "n_bestbuds": int(a_counts.sum()),
                "n_townscaper": int(b_counts.sum()),
                "chi2": chi2,
                "dof": dof,
                "p_value": p,
                "js_divergence": js,
            }
        )
    return pd.DataFrame(rows).sort_values("js_divergence", ascending=False)


def global_js_divergence(mat_a: pd.DataFrame, mat_b: pd.DataFrame) -> float:
    """JS divergence between the two games' pooled (from,to) joint distributions."""
    a = mat_a.drop(index="Experiment ended").values.flatten().astype(float)
    b = mat_b.drop(index="Experiment ended").values.flatten().astype(float)
    return float(jensenshannon(a / a.sum(), b / b.sum(), base=2))


# --- 2. session-level paired features ----------------------------------------

def shannon_entropy(actions: list[str]) -> float:
    counts = pd.Series(actions).value_counts()
    p = counts / counts.sum()
    return float(-(p * np.log2(p)).sum())


def session_features(events: pd.DataFrame) -> pd.DataFrame:
    search = events[~events["action"].isin(NON_SEARCH_ACTIONS)]
    rows = []
    for (pid, game), grp in search.groupby(["participant_id", "game"]):
        acts = grp.sort_values("step")["action"].tolist()
        rows.append(
            {
                "participant_id": pid,
                "game": game,
                "length": len(acts),
                "entropy": shannon_entropy(acts),
                "query_rate": acts.count("Query") / len(acts),
                "platform_switch_rate": acts.count("Platform switch") / len(acts),
            }
        )
    return pd.DataFrame(rows)


def paired_tests(feats: pd.DataFrame) -> pd.DataFrame:
    wide = feats.pivot(index="participant_id", columns="game")
    results = []
    for feature in ["length", "entropy", "query_rate", "platform_switch_rate"]:
        a = wide[(feature, BESTBUDS)]
        b = wide[(feature, TOWNSCAPER)]
        stat, p = wilcoxon(a, b)
        results.append(
            {
                "feature": feature,
                "median_bestbuds": a.median(),
                "median_townscaper": b.median(),
                "wilcoxon_stat": stat,
                "p_value": p,
            }
        )
    return pd.DataFrame(results)


def plot_paired_features(feats: pd.DataFrame, path: Path) -> None:
    features = ["length", "entropy", "query_rate", "platform_switch_rate"]
    titles = ["Session length (events)", "Action entropy (bits)", "Query rate", "Platform-switch rate"]
    wide = feats.pivot(index="participant_id", columns="game")

    fig, axes = plt.subplots(1, 4, figsize=(15, 4.5))
    for ax, feature, ttl in zip(axes, features, titles):
        a = wide[(feature, BESTBUDS)]
        b = wide[(feature, TOWNSCAPER)]
        for pid in a.index:
            ax.plot([0, 1], [a[pid], b[pid]], color="#c3c2b7", linewidth=0.8, zorder=1)
        ax.scatter([0] * len(a), a, color="#b3690f", zorder=2, s=28)
        ax.scatter([1] * len(b), b, color="#009485", zorder=2, s=28)
        ax.set_xlim(-0.3, 1.3)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Best Buds", "Townscaper"])
        ax.set_title(ttl, fontsize=10)
    fig.suptitle("Session-level features, paired by participant (n=21)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# --- 3. Best Buds: first half vs second half ---------------------------------

def half_split_analysis(seqs_bestbuds: list[list[str]]) -> pd.DataFrame:
    def bigrams(s: list[str]) -> list[tuple[str, str]]:
        return list(zip(s, s[1:]))

    rows = []
    for seq in seqs_bestbuds:
        mid = len(seq) // 2
        first, second = seq[:mid], seq[mid:]
        first_bigrams = set(bigrams(first))
        second_bigram_list = bigrams(second)
        novel_rate = (
            sum(1 for bg in second_bigram_list if bg not in first_bigrams) / len(second_bigram_list)
            if second_bigram_list
            else np.nan
        )
        rows.append(
            {
                "session_length": len(seq),
                "first_half_entropy": shannon_entropy(first),
                "second_half_entropy": shannon_entropy(second),
                "second_half_novel_bigram_rate": novel_rate,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    events = load_events()
    seqs_by_key = build_sequences(events)

    # 1. transition matrices
    mat_bb = to_matrix(transition_counts(sequences_for(seqs_by_key, BESTBUDS)))
    mat_ts = to_matrix(transition_counts(sequences_for(seqs_by_key, TOWNSCAPER)))
    comparison = compare_transition_matrices(mat_bb, mat_ts)
    comparison.round(4).to_csv(RESULTS_DIR / "transition_matrix_comparison.csv", index=False)
    global_js = global_js_divergence(mat_bb, mat_ts)

    print("=== Transition matrix comparison (per from-state) ===")
    print(comparison.round(3).to_string(index=False))
    print(f"\nGlobal JS divergence (pooled matrices): {global_js:.3f}")

    # 2. session-level paired features
    feats = session_features(events)
    feats.to_csv(RESULTS_DIR / "session_features.csv", index=False)
    tests = paired_tests(feats)
    tests.round(4).to_csv(RESULTS_DIR / "paired_feature_tests.csv", index=False)
    plot_paired_features(feats, RESULTS_DIR / "paired_features.png")

    print("\n=== Paired session-level feature tests (Wilcoxon, n=21) ===")
    print(tests.round(4).to_string(index=False))

    # 3. Best Buds half-split
    half_split = half_split_analysis(sequences_for(seqs_by_key, BESTBUDS))
    half_split.to_csv(RESULTS_DIR / "bestbuds_half_split.csv", index=False)
    stat, p = wilcoxon(half_split["first_half_entropy"], half_split["second_half_entropy"])

    print("\n=== Best Buds: first half vs second half of session ===")
    print(f"Mean entropy: first half {half_split['first_half_entropy'].mean():.3f} bits, "
          f"second half {half_split['second_half_entropy'].mean():.3f} bits "
          f"(Wilcoxon p={p:.4f})")
    print(f"Mean share of second-half bigrams that are NEW (not seen in first half): "
          f"{half_split['second_half_novel_bigram_rate'].mean():.1%}")

    print(f"\nOutputs written to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
