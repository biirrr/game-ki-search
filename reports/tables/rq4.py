"""LaTeX tables for RQ4 (reports/report.md sec 4.1-4.2).

Cluster labels ("list-browsers", "AI-assisted", "typical", "AI-quick")
are report.md's editorial names for each game's feature_cluster id, kept
here since they're the names the paper prose would refer back to -- the
underlying profile numbers are all recomputed live from
results/rq4_clustering/cluster_assignments_*.csv.
"""

from pathlib import Path

import pandas as pd

from latex_helpers import write_table

BESTBUDS_CLUSTER_LABELS = {0: "list-browsers", 1: "AI-assisted"}
TOWNSCAPER_CLUSTER_LABELS = {0: "typical", 1: "AI-quick"}


def _cluster_profile(results_root: Path, slug: str, labels: dict[int, str], feature_cols: list[str]) -> pd.DataFrame:
    df = pd.read_csv(results_root / "rq4_clustering" / f"cluster_assignments_{slug}.csv")
    agg = df.groupby("feature_cluster").agg(n=("participant_id", "count"), **{c: (c, "mean") for c in feature_cols})
    agg = agg.sort_index()

    table = pd.DataFrame({"Cluster": [f"{i} -- {labels[i]}" for i in agg.index], "n": agg["n"].astype(int)})
    for col in feature_cols:
        if col in ("entropy", "length"):
            table[col] = agg[col].map("{:.2f}".format if col == "entropy" else "{:.0f}".format)
        else:
            table[col] = (agg[col] * 100).map("{:.0f}%".format)
    return table


def bestbuds_clusters(results_root: Path, out_dir: Path) -> Path:
    cols = ["Query", "View result list", "View AI response", "View info box", "entropy", "length"]
    table = _cluster_profile(results_root, "bestbuds", BESTBUDS_CLUSTER_LABELS, cols)
    table = table.rename(columns={"entropy": "Entropy", "length": "Length"})
    path = out_dir / "rq4_bestbuds_clusters.tex"
    write_table(table, path, "Best Buds vs Bad Guys: feature-based cluster profiles", "tab:rq4-bestbuds-clusters")
    return path


def townscaper_clusters(results_root: Path, out_dir: Path) -> Path:
    cols = ["Query", "View AI response", "Browsing", "length"]
    table = _cluster_profile(results_root, "townscaper", TOWNSCAPER_CLUSTER_LABELS, cols)
    table = table.rename(columns={"length": "Length"})
    path = out_dir / "rq4_townscaper_clusters.tex"
    write_table(table, path, "Townscaper: feature-based cluster profiles", "tab:rq4-townscaper-clusters")
    return path


def build(results_root: Path, out_dir: Path) -> list[Path]:
    return [
        bestbuds_clusters(results_root, out_dir),
        townscaper_clusters(results_root, out_dir),
    ]
