"""LaTeX tables for RQ5 (reports/report.md sec 5.1, 5.3)."""

from pathlib import Path

import pandas as pd

from latex_helpers import write_table

GAME_ORDER = ["Best Buds vs Bad Guys", "Townscaper"]
ANNOTATOR_ORDER = ["annotator1", "annotator2", "annotator3", "annotator5", "annotator6"]
ACTION_ORDER = [
    "View result list",
    "View single result",
    "Platform switch",
    "Browsing",
    "View AI response",
    "View info box",
]


def krippendorff_alpha(results_root: Path, out_dir: Path) -> Path:
    df = pd.read_csv(results_root / "rq5_annotator_agreement" / "krippendorff_alpha.csv")
    df = df.set_index("game").loc[GAME_ORDER].reset_index()
    table = pd.DataFrame({
        "Game": df["game"],
        "Krippendorff's alpha (aligned)": df["krippendorff_alpha"].map("{:.2f}".format),
    })
    path = out_dir / "rq5_krippendorff_alpha.tex"
    write_table(table, path, "Krippendorff's alpha by game, agreement sample", "tab:rq5-krippendorff-alpha")
    return path


def coverage_and_agreement(results_root: Path, out_dir: Path) -> Path:
    df = pd.read_csv(results_root / "rq5_annotator_agreement" / "coverage_and_agreement.csv")
    wide = df.pivot(index="annotator", columns="game", values=["coverage", "agreement_on_covered"]).loc[ANNOTATOR_ORDER]
    table = pd.DataFrame({"Annotator": wide.index})
    for game, short in [("Best Buds vs Bad Guys", "Best Buds"), ("Townscaper", "Townscaper")]:
        for stat, header in [("coverage", "coverage"), ("agreement_on_covered", "agreement-when-covered")]:
            table[f"{short} {header}"] = (wide[(stat, game)] * 100).map("{:.0f}%".format).values
    path = out_dir / "rq5_coverage_and_agreement.tex"
    write_table(table, path, "Per-annotator coverage and agreement-when-covered, agreement sample", "tab:rq5-coverage-agreement")
    return path


def corroboration(results_root: Path, out_dir: Path) -> Path:
    df = pd.read_csv(results_root / "rq5b_annotator_confound" / "annotator_action_profiles.csv").set_index("annotator")
    others = df.drop(index="annotator2").mean(axis=0)
    a2 = df.loc["annotator2"]
    diff_pp = (a2 - others) * 100

    table = pd.DataFrame({
        "Action": ACTION_ORDER,
        "annotator2": [f"{a2[a] * 100:.1f}%" for a in ACTION_ORDER],
        "other annotators": [f"{others[a] * 100:.1f}%" for a in ACTION_ORDER],
        "difference": [f"{diff_pp[a]:+.1f}pp" for a in ACTION_ORDER],
    })
    path = out_dir / "rq5_corroboration.tex"
    write_table(table, path, "annotator2's action-rate profile vs. the other three annotators, main dataset", "tab:rq5-corroboration")
    return path


def icc_by_feature(results_root: Path, out_dir: Path) -> Path:
    df = pd.read_csv(results_root / "rq5b_annotator_confound" / "icc_by_feature.csv")
    df = df[df["converged"]].sort_values("icc_annotator", ascending=False)
    table = pd.DataFrame({
        "Feature": df["feature"],
        "ICC (annotator block)": df["icc_annotator"].map("{:.2f}".format),
    })
    path = out_dir / "rq5_icc_by_feature.tex"
    write_table(table, path, "Intraclass correlation by feature, annotator as grouping factor", "tab:rq5-icc-by-feature")
    return path


def build(results_root: Path, out_dir: Path) -> list[Path]:
    return [
        krippendorff_alpha(results_root, out_dir),
        coverage_and_agreement(results_root, out_dir),
        corroboration(results_root, out_dir),
        icc_by_feature(results_root, out_dir),
    ]
