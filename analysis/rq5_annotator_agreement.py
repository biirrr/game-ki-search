"""RQ5: does the annotator influence how a search process gets coded?

Uses the dedicated four-annotator agreement sample: participant ID13, both
games, independently segmented and labeled by annotator1-4
(data/agreement/). annotator4 is the annotator who coded ID13 in the main
dataset (data/search_process/), so it doubles as the reference sequence.

Because annotators independently *segmented* the recording rather than
labeling a shared fixed set of events -- the four files have different row
counts (e.g. 53/32/54/62 for Townscaper+Best Buds combined) -- a plain
per-row Cohen's kappa isn't possible; there's no shared "item" to rate
without first deciding which events correspond to which. So:

  1. Sequence alignment (minimum-edit-distance, via Levenshtein.opcodes)
     of each of annotator1-3 against the annotator4 reference, producing a
     shared set of reference positions (unmatched positions -> missing).
  2. Krippendorff's alpha (nominal) across all 4 annotators on that
     aligned matrix.
  3. Pairwise normalized edit-distance similarity (all 6 pairs,
     alignment-free) -- also reflects segmentation disagreement, which
     alpha on the reference-aligned matrix doesn't fully capture.
  4. A pooled confusion table (aligned ref-label vs other-label) to see
     *where* annotators disagree, and per-action count agreement.
"""

from itertools import combinations
from pathlib import Path

import krippendorff
import Levenshtein
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from rq2_patterns import ACTIONS

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "agreement"
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "rq5"

ANNOTATORS = ["annotator1", "annotator2", "annotator3", "annotator4"]
REFERENCE_ANNOTATOR = "annotator4"
GAMES = ["Best Buds vs Bad Guys", "Townscaper"]
SYMBOL = {a: chr(65 + i) for i, a in enumerate(ACTIONS)}


def load_agreement_events() -> pd.DataFrame:
    files = sorted(DATA_DIR.glob("agreement_search_process_annotations-*.tsv"))
    if not files:
        raise FileNotFoundError(f"No agreement files found in {DATA_DIR}")
    frames = [pd.read_csv(f, sep="\t", dtype=str) for f in files]
    events = pd.concat(frames, ignore_index=True)
    events["rank"] = events["rank"].astype(int)
    return events


def build_sequences(events: pd.DataFrame) -> dict[tuple[str, str], list[str]]:
    events = events.sort_values(["annotator", "game", "rank"])
    return {key: grp["action"].tolist() for key, grp in events.groupby(["annotator", "game"])}


def encode(seq: list[str]) -> str:
    return "".join(SYMBOL[a] for a in seq)


# --- 3. pairwise, alignment-free similarity ----------------------------------

def pairwise_similarity(seqs: dict, game: str) -> pd.DataFrame:
    rows = []
    for a1, a2 in combinations(ANNOTATORS, 2):
        s1, s2 = seqs[(a1, game)], seqs[(a2, game)]
        e1, e2 = encode(s1), encode(s2)
        d = Levenshtein.distance(e1, e2)
        norm = d / max(len(e1), len(e2))
        rows.append(
            {
                "game": game,
                "annotator_a": a1,
                "annotator_b": a2,
                "n_a": len(s1),
                "n_b": len(s2),
                "edit_distance": d,
                "similarity": 1 - norm,
            }
        )
    return pd.DataFrame(rows)


def plot_similarity_heatmaps(sim_bb: pd.DataFrame, sim_ts: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    for ax, sim, title in zip(axes, [sim_bb, sim_ts], GAMES):
        mat = pd.DataFrame(1.0, index=ANNOTATORS, columns=ANNOTATORS)
        for _, r in sim.iterrows():
            mat.loc[r["annotator_a"], r["annotator_b"]] = r["similarity"]
            mat.loc[r["annotator_b"], r["annotator_a"]] = r["similarity"]
        im = ax.imshow(mat.values, vmin=0, vmax=1, cmap="YlOrBr_r")
        ax.set_xticks(range(4))
        ax.set_xticklabels(ANNOTATORS, rotation=45, ha="right", fontsize=8)
        ax.set_yticks(range(4))
        ax.set_yticklabels(ANNOTATORS, fontsize=8)
        for i in range(4):
            for j in range(4):
                ax.text(j, i, f"{mat.values[i,j]:.2f}", ha="center", va="center", fontsize=8,
                         color="white" if mat.values[i, j] < 0.6 else "black")
        ax.set_title(title, fontsize=10)
    fig.colorbar(im, ax=axes, shrink=0.8, label="Sequence similarity (1 - normalized edit distance)")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# --- 1 & 2. reference alignment + Krippendorff's alpha -----------------------

def align_to_reference(ref_seq: list[str], other_seq: list[str]) -> list[str | None]:
    """Return len(ref_seq) labels: other_seq's label at each aligned
    reference position, or None where the reference has no match (a
    'delete' relative to the reference -- this annotator missed it)."""
    ref_enc, other_enc = encode(ref_seq), encode(other_seq)
    aligned: list[str | None] = [None] * len(ref_seq)
    for tag, i1, i2, j1, j2 in Levenshtein.opcodes(ref_enc, other_enc):
        if tag in ("equal", "replace"):
            n = min(i2 - i1, j2 - j1)
            for offset in range(n):
                aligned[i1 + offset] = other_seq[j1 + offset]
    return aligned


def reference_alignment_matrix(seqs: dict, game: str) -> tuple[list[list], list[str]]:
    ref = seqs[(REFERENCE_ANNOTATOR, game)]
    columns = {REFERENCE_ANNOTATOR: list(ref)}
    for a in ANNOTATORS:
        if a == REFERENCE_ANNOTATOR:
            continue
        columns[a] = align_to_reference(ref, seqs[(a, game)])
    data = [columns[a] for a in ANNOTATORS]
    return data, ref


def krippendorff_alpha_nominal(data: list[list]) -> float:
    clean = [[np.nan if v is None else v for v in row] for row in data]
    return float(krippendorff.alpha(reliability_data=clean, level_of_measurement="nominal"))


def coverage_and_agreement(data: list[list], ref: list[str]) -> pd.DataFrame:
    rows = []
    ref_row = data[ANNOTATORS.index(REFERENCE_ANNOTATOR)]
    for i, a in enumerate(ANNOTATORS):
        if a == REFERENCE_ANNOTATOR:
            continue
        col = data[i]
        matched = sum(1 for v in col if v is not None)
        agree = sum(1 for v, r in zip(col, ref_row) if v is not None and v == r)
        rows.append(
            {
                "annotator": a,
                "n_reference_positions": len(ref),
                "coverage": matched / len(ref),
                "agreement_on_covered": agree / matched if matched else float("nan"),
                "agreement_overall": agree / len(ref),
            }
        )
    return pd.DataFrame(rows)


def pooled_confusion(all_game_data: dict) -> pd.DataFrame:
    pairs = []
    for game, (data, ref) in all_game_data.items():
        ref_row = data[ANNOTATORS.index(REFERENCE_ANNOTATOR)]
        for i, a in enumerate(ANNOTATORS):
            if a == REFERENCE_ANNOTATOR:
                continue
            for v, r in zip(data[i], ref_row):
                if v is not None:
                    pairs.append({"game": game, "annotator": a, "reference_label": r, "other_label": v, "match": v == r})
    df = pd.DataFrame(pairs)
    confusion = df[~df["match"]].groupby(["reference_label", "other_label"]).size().reset_index(name="count")
    return confusion.sort_values("count", ascending=False)


# --- 4. per-action count agreement --------------------------------------------

def action_counts_by_annotator(seqs: dict) -> pd.DataFrame:
    rows = []
    for (a, g), seq in seqs.items():
        counts = pd.Series(seq).value_counts()
        for action in ACTIONS:
            rows.append({"annotator": a, "game": g, "action": action, "count": int(counts.get(action, 0))})
    return pd.DataFrame(rows)


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    events = load_agreement_events()
    seqs = build_sequences(events)

    # 3. pairwise similarity
    sim_bb = pairwise_similarity(seqs, GAMES[0])
    sim_ts = pairwise_similarity(seqs, GAMES[1])
    pd.concat([sim_bb, sim_ts]).round(3).to_csv(RESULTS_DIR / "pairwise_similarity.csv", index=False)
    plot_similarity_heatmaps(sim_bb, sim_ts, RESULTS_DIR / "similarity_heatmaps.png")

    print("=== Pairwise sequence similarity (1 - normalized edit distance) ===")
    print(pd.concat([sim_bb, sim_ts])[["game", "annotator_a", "annotator_b", "n_a", "n_b", "similarity"]].round(3).to_string(index=False))

    # 1 & 2. reference alignment + alpha
    alpha_rows = []
    all_game_data = {}
    coverage_frames = []
    for game in GAMES:
        data, ref = reference_alignment_matrix(seqs, game)
        all_game_data[game] = (data, ref)
        alpha = krippendorff_alpha_nominal(data)
        alpha_rows.append({"game": game, "n_reference_positions": len(ref), "krippendorff_alpha": alpha})
        cov = coverage_and_agreement(data, ref)
        cov.insert(0, "game", game)
        coverage_frames.append(cov)

    alpha_df = pd.DataFrame(alpha_rows)
    alpha_df.round(3).to_csv(RESULTS_DIR / "krippendorff_alpha.csv", index=False)
    coverage_df = pd.concat(coverage_frames, ignore_index=True)
    coverage_df.round(3).to_csv(RESULTS_DIR / "coverage_and_agreement.csv", index=False)

    print("\n=== Krippendorff's alpha (nominal), annotator4-referenced alignment ===")
    print(alpha_df.round(3).to_string(index=False))
    print("\n=== Coverage & agreement vs. reference (annotator4) ===")
    print(coverage_df.round(3).to_string(index=False))

    # confusion + action counts
    confusion = pooled_confusion(all_game_data)
    confusion.to_csv(RESULTS_DIR / "confusion_pairs.csv", index=False)
    print("\n=== Top disagreement pairs (reference label -> other label) ===")
    print(confusion.head(10).to_string(index=False))

    counts = action_counts_by_annotator(seqs)
    counts.to_csv(RESULTS_DIR / "action_counts_by_annotator.csv", index=False)

    print(f"\nOutputs written to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
