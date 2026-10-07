"""LaTeX tables for RQ7 (reports/report.md sec 7.1-7.3)."""

from pathlib import Path

import pandas as pd
from scipy.stats import mannwhitneyu

from latex_helpers import write_table

CLUSTER_LABELS = {
    "Best Buds vs Bad Guys": {0: "list-browsers", 1: "AI-assisted"},
    "Townscaper": {0: "typical", 1: "AI-quick"},
}
GAME_SLUG = {"Best Buds vs Bad Guys": "bestbuds", "Townscaper": "townscaper"}


def ai_assistant_share_by_cluster(results_root: Path, out_dir: Path) -> Path:
    rows = []
    for game, slug in GAME_SLUG.items():
        df = pd.read_csv(results_root / "rq7_platform_details" / f"platform_category_by_cluster_{slug}.csv")
        for _, r in df.sort_values("feature_cluster").iterrows():
            cluster_id = int(r["feature_cluster"])
            label = CLUSTER_LABELS[game][cluster_id]
            rows.append((game, f"{cluster_id} -- {label}", f"{r['AI assistant'] * 100:.0f}%"))
    table = pd.DataFrame(rows, columns=["Game", "Cluster", "AI-assistant share of platform switches"])
    path = out_dir / "rq7_ai_assistant_share_by_cluster.tex"
    write_table(table, path, "AI-assistant share of platform switches, by RQ4 cluster", "tab:rq7-ai-assistant-share")
    return path


def query_length_by_cluster(results_root: Path, out_dir: Path) -> Path:
    query_lengths = pd.read_csv(results_root / "rq7_platform_details" / "query_lengths.csv")
    per_participant_median = query_lengths.groupby(["participant_id", "game"])["action_details_num_tokens"].median()
    per_participant_median = per_participant_median.reset_index()

    rows = []
    for game, slug in GAME_SLUG.items():
        clusters = pd.read_csv(results_root / "rq4_clustering" / f"cluster_assignments_{slug}.csv")[["participant_id", "feature_cluster"]]
        merged = per_participant_median[per_participant_median["game"] == game].merge(clusters, on="participant_id")
        groups = {cid: g["action_details_num_tokens"] for cid, g in merged.groupby("feature_cluster")}
        _, p = mannwhitneyu(groups[0], groups[1], alternative="two-sided")
        for cluster_id in sorted(groups):
            label = CLUSTER_LABELS[game][cluster_id]
            rows.append({
                "Game": game,
                "Cluster": label,
                "Median query length (tokens)": f"{groups[cluster_id].median():.1f}",
                "Mann-Whitney p": f"{p:.2f}" if cluster_id == 1 else "",
            })
    table = pd.DataFrame(rows)
    path = out_dir / "rq7_query_length_by_cluster.tex"
    write_table(table, path, "Per-participant median query length, by RQ4 cluster", "tab:rq7-query-length-by-cluster")
    return path


def self_loop_same_source(results_root: Path, out_dir: Path) -> Path:
    bb = pd.read_csv(results_root / "rq7_platform_details" / "view_single_result_self_loops.csv")
    bb = bb[bb["game"] == "Best Buds vs Bad Guys"]
    ts = pd.read_csv(results_root / "rq7_platform_details" / "self_loop_same_source_by_order_townscaper.csv")

    rows = [
        ("Best Buds", len(bb), f"{bb['same_source'].mean() * 100:.0f}%"),
        ("Townscaper", int(ts["n_self_loops"].sum()), f"{ts['n_same_source'].sum() / ts['n_self_loops'].sum() * 100:.0f}%"),
    ]
    table = pd.DataFrame(rows, columns=["Game", "Self-loops", "Same source repeated"])
    path = out_dir / "rq7_self_loop_same_source.tex"
    write_table(table, path, "`View single result' self-loops that revisit the same source", "tab:rq7-self-loop-same-source")
    return path


def build(results_root: Path, out_dir: Path) -> list[Path]:
    return [
        ai_assistant_share_by_cluster(results_root, out_dir),
        query_length_by_cluster(results_root, out_dir),
        self_loop_same_source(results_root, out_dir),
    ]
