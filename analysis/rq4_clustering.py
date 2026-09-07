"""RQ4: are there clusters of participants with similar search processes?

Two complementary views, run separately per game (21 sessions each --
pooling both games would likely just rediscover the RQ3 game split rather
than within-game strategy variation):

  1. Sequence-distance clustering -- normalized Levenshtein edit distance
     between raw action sequences, agglomerative (average-linkage)
     clustering, k chosen by silhouette score.
  2. Feature-based clustering -- per-session action-mix vector (proportions
     of the 7 real actions + entropy), standardized, KMeans, k chosen by
     silhouette score.

Cluster stability is checked via leave-one-out: recluster with each
session removed in turn and compare (Adjusted Rand Index) against the
full clustering restricted to the remaining sessions -- a low mean ARI
means the clustering is not robust to which 21 people happened to be in
the sample, which matters a lot at this N.

Finally: does a participant's cluster in Best Buds relate to their
cluster in Townscaper (are people consistent across tasks, or does
behavior mostly depend on the task)?
"""

from itertools import combinations
from pathlib import Path

import Levenshtein
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.manifold import MDS
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from data import load_events
from rq2_patterns import ACTIONS, build_sequences, sequences_for

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "rq4"
BESTBUDS = "Best Buds vs Bad Guys"
TOWNSCAPER = "Townscaper"
REAL_ACTIONS = [a for a in ACTIONS if a != "Experiment ended"]
SYMBOL = {a: chr(65 + i) for i, a in enumerate(ACTIONS)}


# --- 1. sequence-distance clustering -----------------------------------------

def edit_distance_matrix(seqs: list[list[str]]) -> np.ndarray:
    strs = ["".join(SYMBOL[a] for a in s) for s in seqs]
    n = len(strs)
    dist = np.zeros((n, n))
    for i, j in combinations(range(n), 2):
        d = Levenshtein.distance(strs[i], strs[j])
        norm = d / max(len(strs[i]), len(strs[j]))
        dist[i, j] = dist[j, i] = norm
    return dist


def best_k_precomputed(dist: np.ndarray, k_range=range(2, 6)) -> tuple[int, float, np.ndarray]:
    best = (None, -1, None)
    for k in k_range:
        labels = AgglomerativeClustering(n_clusters=k, metric="precomputed", linkage="average").fit_predict(dist)
        score = silhouette_score(dist, labels, metric="precomputed")
        if score > best[1]:
            best = (k, score, labels)
    return best


def loo_stability_precomputed(dist: np.ndarray, k: int, full_labels: np.ndarray) -> tuple[float, float]:
    n = dist.shape[0]
    aris = []
    for i in range(n):
        idx = [j for j in range(n) if j != i]
        sub_dist = dist[np.ix_(idx, idx)]
        sub_labels = AgglomerativeClustering(n_clusters=k, metric="precomputed", linkage="average").fit_predict(sub_dist)
        aris.append(adjusted_rand_score(full_labels[idx], sub_labels))
    return float(np.mean(aris)), float(np.std(aris))


def plot_dendrogram(dist: np.ndarray, labels: list[str], title: str, path: Path) -> None:
    condensed = squareform(dist, checks=False)
    z = linkage(condensed, method="average")
    fig, ax = plt.subplots(figsize=(9, 5))
    dendrogram(z, labels=labels, ax=ax, color_threshold=0.7 * max(z[:, 2]), leaf_font_size=9)
    ax.set_title(title)
    ax.set_ylabel("Normalized edit distance")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_mds(dist: np.ndarray, labels: np.ndarray, participant_ids: list[str], title: str, path: Path) -> None:
    coords = MDS(n_components=2, dissimilarity="precomputed", random_state=0, normalized_stress="auto").fit_transform(dist)
    fig, ax = plt.subplots(figsize=(6, 6))
    palette = ["#b3690f", "#009485", "#5b4b8a", "#a33b56"]
    for cluster in sorted(set(labels)):
        mask = labels == cluster
        ax.scatter(coords[mask, 0], coords[mask, 1], color=palette[cluster % len(palette)], s=60, label=f"cluster {cluster}")
    for (x, y), pid in zip(coords, participant_ids):
        ax.annotate(pid, (x, y), fontsize=7, xytext=(4, 4), textcoords="offset points")
    ax.set_title(title)
    ax.legend()
    ax.set_xticks([])
    ax.set_yticks([])
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# --- 2. feature-based clustering ----------------------------------------------

def session_feature_matrix(seqs_by_key: dict, game: str) -> pd.DataFrame:
    rows = []
    for (pid, g), seq in seqs_by_key.items():
        if g != game:
            continue
        real = [a for a in seq if a != "Experiment ended"]
        counts = pd.Series(real).value_counts()
        props = (counts / counts.sum()).reindex(REAL_ACTIONS, fill_value=0.0)
        p = counts / counts.sum()
        entropy = float(-(p * np.log2(p)).sum())
        row = {"participant_id": pid, "entropy": entropy, "length": len(real)}
        row.update(props.to_dict())
        rows.append(row)
    return pd.DataFrame(rows).set_index("participant_id").sort_index()


def best_k_features(features: np.ndarray, k_range=range(2, 6)) -> tuple[int, float, np.ndarray]:
    best = (None, -1, None)
    for k in k_range:
        labels = KMeans(n_clusters=k, n_init=10, random_state=0).fit_predict(features)
        score = silhouette_score(features, labels)
        if score > best[1]:
            best = (k, score, labels)
    return best


def loo_stability_features(features: np.ndarray, k: int, full_labels: np.ndarray) -> tuple[float, float]:
    n = features.shape[0]
    aris = []
    for i in range(n):
        idx = [j for j in range(n) if j != i]
        sub = features[idx]
        sub_labels = KMeans(n_clusters=k, n_init=10, random_state=0).fit_predict(sub)
        aris.append(adjusted_rand_score(full_labels[idx], sub_labels))
    return float(np.mean(aris)), float(np.std(aris))


def plot_cluster_profiles(feat_df: pd.DataFrame, labels: np.ndarray, title: str, path: Path) -> None:
    feat_df = feat_df.copy()
    feat_df["cluster"] = labels
    profile = feat_df.groupby("cluster")[REAL_ACTIONS].mean()
    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = np.arange(len(REAL_ACTIONS))
    width = 0.8 / len(profile)
    palette = ["#b3690f", "#009485", "#5b4b8a", "#a33b56"]
    for i, (cluster, row) in enumerate(profile.iterrows()):
        ax.bar(x + i * width, row.values, width=width, label=f"cluster {cluster} (n={int((labels==cluster).sum())})", color=palette[i % len(palette)])
    ax.set_xticks(x + width * (len(profile) - 1) / 2)
    ax.set_xticklabels(REAL_ACTIONS, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("Mean share of session")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# --- main ----------------------------------------------------------------

def run_for_game(seqs_by_key: dict, game: str, slug: str) -> pd.Series:
    out = RESULTS_DIR
    keys = sorted(k for k in seqs_by_key if k[1] == game)
    pids = [k[0] for k in keys]
    seqs = [seqs_by_key[k] for k in keys]

    # 1. sequence-distance
    dist = edit_distance_matrix(seqs)
    k_seq, sil_seq, labels_seq = best_k_precomputed(dist)
    loo_mean_seq, loo_std_seq = loo_stability_precomputed(dist, k_seq, labels_seq)
    plot_dendrogram(dist, pids, f"Sequence-distance dendrogram — {game}", out / f"dendrogram_{slug}.png")
    plot_mds(dist, labels_seq, pids, f"Sequence-distance clusters (MDS) — {game}", out / f"mds_{slug}.png")

    # 2. feature-based
    feat_df = session_feature_matrix(seqs_by_key, game)
    feat_df = feat_df.loc[pids]  # align order with sequence view
    scaled = StandardScaler().fit_transform(feat_df[REAL_ACTIONS + ["entropy"]].values)
    k_feat, sil_feat, labels_feat = best_k_features(scaled)
    loo_mean_feat, loo_std_feat = loo_stability_features(scaled, k_feat, labels_feat)
    plot_cluster_profiles(feat_df, labels_feat, f"Feature-based cluster profiles — {game}", out / f"cluster_profiles_{slug}.png")

    agreement = adjusted_rand_score(labels_seq, labels_feat)

    assignments = pd.DataFrame(
        {
            "participant_id": pids,
            "game": game,
            "sequence_cluster": labels_seq,
            "feature_cluster": labels_feat,
            **{c: feat_df[c].values for c in REAL_ACTIONS},
            "entropy": feat_df["entropy"].values,
            "length": feat_df["length"].values,
        }
    )
    assignments.to_csv(out / f"cluster_assignments_{slug}.csv", index=False)

    print(f"\n=== {game} ===")
    print(f"Sequence-distance: k={k_seq}, silhouette={sil_seq:.3f}, LOO mean ARI={loo_mean_seq:.3f} (sd={loo_std_seq:.3f})")
    print(f"  sizes: {pd.Series(labels_seq).value_counts().to_dict()}")
    print(f"Feature-based:     k={k_feat}, silhouette={sil_feat:.3f}, LOO mean ARI={loo_mean_feat:.3f} (sd={loo_std_feat:.3f})")
    print(f"  sizes: {pd.Series(labels_feat).value_counts().to_dict()}")
    print(f"Agreement between the two views (ARI): {agreement:.3f}")

    return pd.Series(labels_feat, index=pids, name=f"{slug}_feature_cluster")


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    events = load_events()
    seqs_by_key = build_sequences(events)

    bb_labels = run_for_game(seqs_by_key, BESTBUDS, "bestbuds")
    ts_labels = run_for_game(seqs_by_key, TOWNSCAPER, "townscaper")

    cross = pd.concat([bb_labels, ts_labels], axis=1)
    cross.to_csv(RESULTS_DIR / "cross_game_cluster_labels.csv")
    cross_ari = adjusted_rand_score(cross.iloc[:, 0], cross.iloc[:, 1])
    contingency = pd.crosstab(cross.iloc[:, 0], cross.iloc[:, 1])
    contingency.to_csv(RESULTS_DIR / "cross_game_contingency.csv")

    print("\n=== Cross-game consistency (feature-based clusters) ===")
    print(f"ARI between a participant's Best Buds cluster and their Townscaper cluster: {cross_ari:.3f}")
    print(contingency.to_string())

    print(f"\nOutputs written to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
