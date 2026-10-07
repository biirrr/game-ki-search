"""LaTeX tables for RQ3 (reports/report.md sec 3.1-3.2)."""

from pathlib import Path

import pandas as pd

from latex_helpers import write_table

TRANSITION_ROW_ORDER = [
    "View info box",
    "View single result",
    "View AI response",
    "Browsing",
    "View result list",
    "Platform switch",
    "Query",
]

FEATURE_LABELS = {
    "length": "Session length",
    "entropy": "Action entropy",
    "query_rate": "Query rate",
    "platform_switch_rate": "Platform-switch rate",
}
FEATURE_ORDER = ["length", "entropy", "query_rate", "platform_switch_rate"]


def transition_matrix_comparison(results_root: Path, out_dir: Path) -> Path:
    df = pd.read_csv(results_root / "rq3_game_differences" / "transition_matrix_comparison.csv")
    df = df.set_index("from").loc[TRANSITION_ROW_ORDER].reset_index()
    table = pd.DataFrame({
        "From": df["from"],
        "chi2": df["chi2"].map("{:.2f}".format),
        "p": df["p_value"].map("{:.3f}".format),
        "JS divergence": df["js_divergence"].map("{:.3f}".format),
    })
    path = out_dir / "rq3_transition_comparison.tex"
    write_table(table, path, "Per-state transition distribution comparison between games", "tab:rq3-transition-comparison")
    return path


def session_level_features(results_root: Path, out_dir: Path) -> Path:
    df = pd.read_csv(results_root / "rq3_game_differences" / "paired_feature_tests.csv")
    df = df.set_index("feature").loc[FEATURE_ORDER].reset_index()

    def fmt(feature: str, value: float) -> str:
        return f"{value:.2f} bits" if feature == "entropy" else f"{value:.2f}" if not float(value).is_integer() else f"{int(value)}"

    table = pd.DataFrame({
        "Feature": df["feature"].map(FEATURE_LABELS),
        "Median (Best Buds)": [fmt(f, v) for f, v in zip(df["feature"], df["median_bestbuds"])],
        "Median (Townscaper)": [fmt(f, v) for f, v in zip(df["feature"], df["median_townscaper"])],
        "Wilcoxon p": df["p_value"].map("{:.4f}".format),
    })
    path = out_dir / "rq3_session_level_features.tex"
    write_table(table, path, "Paired session-level features by participant (n=21)", "tab:rq3-session-features")
    return path


def build(results_root: Path, out_dir: Path) -> list[Path]:
    return [
        transition_matrix_comparison(results_root, out_dir),
        session_level_features(results_root, out_dir),
    ]
