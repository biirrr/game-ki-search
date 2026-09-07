"""RQ6.4: does order change *how* people search within each game, not
just whether they do?

Sharpens RQ6's null result on session-level features (§4.6 bullet 1) by
applying RQ3's full toolkit -- action mix, transition matrices, closing
moves, first/second-half dynamics -- split by play order instead of by
game. Two comparisons:
  A. Best Buds: played first (n=10) vs. played second, after a
     Townscaper win (n=11).
  B. Townscaper: played first (n=11) vs. played second, after Best Buds
     frustration (n=10).

See docs/planning_and_background.md sec 4.6 "RQ6.4" for the full plan and
caveats (small per-cell N; confounded with the opening-carryover effect
found in RQ6, checked directly in part 5 below).
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial.distance import jensenshannon
from scipy.stats import chi2_contingency, wilcoxon

from data import NON_SEARCH_ACTIONS, load_events
from rq2_patterns import ACTIONS, build_sequences, probability_matrix, to_matrix, transition_counts
from rq3_game_differences import BESTBUDS, TOWNSCAPER, compare_transition_matrices, half_split_analysis, shannon_entropy
from rq6_order_effects import position_table

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "rq6_4"
FIRST, SECOND = "first", "second"


def sequences_for_order(seqs_by_key: dict, pos: pd.DataFrame, game: str, position: str) -> list[list[str]]:
    pids = set(pos.loc[(pos["game"] == game) & (pos["position"] == position), "participant_id"])
    return [seq for (pid, g), seq in seqs_by_key.items() if g == game and pid in pids]


# --- 1. action-mix comparison -------------------------------------------------

def action_mix_comparison(seqs_a: list[list[str]], seqs_b: list[list[str]], label_a: str, label_b: str) -> tuple[pd.DataFrame, dict]:
    real_actions = [a for a in ACTIONS if a != "Experiment ended"]
    counts_a = pd.Series([a for s in seqs_a for a in s if a != "Experiment ended"]).value_counts().reindex(real_actions, fill_value=0)
    counts_b = pd.Series([a for s in seqs_b for a in s if a != "Experiment ended"]).value_counts().reindex(real_actions, fill_value=0)
    table = pd.DataFrame({label_a: counts_a, label_b: counts_b})
    chi2, p, dof, _ = chi2_contingency(table.values.T)
    js = jensenshannon(counts_a / counts_a.sum(), counts_b / counts_b.sum(), base=2)
    return table, {"chi2": chi2, "dof": dof, "p_value": p, "js_divergence": float(js)}


# --- 3. Townscaper closing-move by order -------------------------------------

def exit_probabilities(seqs: list[list[str]]) -> pd.Series:
    mat = to_matrix(transition_counts(seqs))
    probs = probability_matrix(mat)
    return probs["Experiment ended"]


# --- 5. confound check: strip the opening ------------------------------------

def strip_opening(seqs: list[list[str]], n: int = 3) -> list[list[str]]:
    return [seq[n:] for seq in seqs if len(seq) > n]


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    events = load_events()
    seqs_by_key = build_sequences(events)
    pos = position_table(events)

    summary_lines = []

    for game, slug in [(BESTBUDS, "bestbuds"), (TOWNSCAPER, "townscaper")]:
        print(f"\n{'='*70}\n{game}\n{'='*70}")
        seqs_first = sequences_for_order(seqs_by_key, pos, game, FIRST)
        seqs_second = sequences_for_order(seqs_by_key, pos, game, SECOND)
        print(f"n first={len(seqs_first)}, n second={len(seqs_second)}")

        # 1. action mix
        mix_table, mix_stats = action_mix_comparison(seqs_first, seqs_second, "played_first", "played_second")
        mix_table.to_csv(RESULTS_DIR / f"action_mix_by_order_{slug}.csv")
        pd.DataFrame([mix_stats]).to_csv(RESULTS_DIR / f"action_mix_test_{slug}.csv", index=False)
        print("\n--- 1. Action mix (counts) ---")
        print(mix_table.to_string())
        print(f"chi2={mix_stats['chi2']:.3f} p={mix_stats['p_value']:.4f} JS={mix_stats['js_divergence']:.3f}")

        # 2. transition matrix comparison
        mat_first = to_matrix(transition_counts(seqs_first))
        mat_second = to_matrix(transition_counts(seqs_second))
        comparison = compare_transition_matrices(mat_first, mat_second)
        comparison.round(4).to_csv(RESULTS_DIR / f"transition_comparison_{slug}.csv", index=False)
        print("\n--- 2. Transition matrix comparison (per from-state) ---")
        print(comparison.round(3).to_string(index=False))

        # 5. confound check: same comparison with the first 3 actions stripped
        trimmed_first = strip_opening(seqs_first)
        trimmed_second = strip_opening(seqs_second)
        mat_first_trim = to_matrix(transition_counts(trimmed_first))
        mat_second_trim = to_matrix(transition_counts(trimmed_second))
        comparison_trim = compare_transition_matrices(mat_first_trim, mat_second_trim)
        comparison_trim.round(4).to_csv(RESULTS_DIR / f"transition_comparison_trimmed_{slug}.csv", index=False)
        print("\n--- 5. Same comparison with first 3 actions stripped (confound check) ---")
        print(comparison_trim.round(3).to_string(index=False))

        summary_lines.append(
            f"{game}: untrimmed min p={comparison['p_value'].min():.4f}, "
            f"trimmed min p={comparison_trim['p_value'].min():.4f}"
        )

        if game == TOWNSCAPER:
            # 3. closing-move check
            exit_first = exit_probabilities(seqs_first).rename("played_first")
            exit_second = exit_probabilities(seqs_second).rename("played_second")
            exit_table = pd.concat([exit_first, exit_second], axis=1).drop(index="Experiment ended")
            exit_table.round(4).to_csv(RESULTS_DIR / "closing_move_by_order_townscaper.csv")
            print("\n--- 3. P(action -> Experiment ended), by order ---")
            print(exit_table.round(3).to_string())

        if game == BESTBUDS:
            # 4. half-split per order group
            print("\n--- 4. Best Buds first/second-half entropy, by order group ---")
            for label, subset in [("played_first", seqs_first), ("played_second", seqs_second)]:
                half = half_split_analysis(subset)
                half.to_csv(RESULTS_DIR / f"bestbuds_half_split_{label}.csv", index=False)
                stat, p = wilcoxon(half["first_half_entropy"], half["second_half_entropy"])
                print(
                    f"{label} (n={len(half)}): first-half entropy={half['first_half_entropy'].mean():.3f}, "
                    f"second-half entropy={half['second_half_entropy'].mean():.3f}, "
                    f"mean novel-bigram rate={half['second_half_novel_bigram_rate'].mean():.1%}, "
                    f"Wilcoxon p={p:.4f}"
                )

    # 5b. likely Townscaper non-solver (inferred, not ground truth)
    lengths = (
        events[~events["action"].isin(NON_SEARCH_ACTIONS)]
        .groupby(["participant_id", "game"])
        .size()
        .unstack()
    )
    ts_outlier = lengths[TOWNSCAPER].idxmax()
    outlier_order = pos.loc[(pos["participant_id"] == ts_outlier) & (pos["game"] == TOWNSCAPER), "position"].iloc[0]
    print(f"\n--- Likely Townscaper non-solver (longest session, NOT a ground-truth label) ---")
    print(
        f"{ts_outlier}: Townscaper length={lengths.loc[ts_outlier, TOWNSCAPER]} "
        f"(next longest={lengths[TOWNSCAPER].sort_values(ascending=False).iloc[1]}), "
        f"played Townscaper {outlier_order}"
    )

    print("\n=== Summary: does the order effect on transitions survive stripping the opening? ===")
    for line in summary_lines:
        print(line)

    print(f"\nOutputs written to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
