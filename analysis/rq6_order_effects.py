"""RQ6: does game order affect search strategy, and do participants carry
a strategy over from one game to the next?

Motivating idea (researcher, 2026-08-19): participants who played
Townscaper first started on a successful, positive note; participants who
played Best Buds first may have built up frustration before Townscaper.
Related: do participants open each game the same way regardless of order,
or does their second game's opening resemble their first game's (a
carried-over strategy) more than chance would predict?

Game order is derived from the data itself: within a participant's file,
`rank` is a single counter spanning both games, so whichever game has the
lower starting rank was played first -- no separate order field needed.

Three parts:
  1. Order effect on session-level features (length, entropy, query rate,
     platform-switch rate) -- unpaired comparison (played-this-game-first
     vs played-this-game-second are different participants), per game.
  2. Opening-strategy carryover -- is a participant's second-game opening
     (first 3 actions) more similar to their own first-game opening than
     to a randomly paired participant's opening (permutation test)? Does
     carryover strength depend on which game came first?
  3. Cross-reference with the RQ4 clusters -- does play order predict
     which behavioral cluster a participant falls into?
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact, mannwhitneyu

from data import load_events
from rq2_patterns import build_sequences, sequences_for
from rq3_game_differences import BESTBUDS, TOWNSCAPER, session_features

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "rq6"
RQ4_DIR = Path(__file__).resolve().parent.parent / "results" / "rq4"
OPENING_LEN = 3
N_PERMUTATIONS = 10_000
RNG_SEED = 0


# --- order derivation ----------------------------------------------------

def first_game_per_participant(events: pd.DataFrame) -> pd.Series:
    start_rank = events.groupby(["participant_id", "game"])["rank"].min().unstack()
    return start_rank.idxmin(axis=1).rename("first_game")


def position_table(events: pd.DataFrame) -> pd.DataFrame:
    """One row per (participant, game) with 'position' = 'first' or 'second'."""
    first_game = first_game_per_participant(events)
    games = events[["participant_id", "game"]].drop_duplicates()
    games = games.merge(first_game.rename("first_game"), on="participant_id")
    games["position"] = np.where(games["game"] == games["first_game"], "first", "second")
    return games.drop(columns="first_game")


# --- 1. order effect on session features -------------------------------------

def order_effect_tests(events: pd.DataFrame, pos: pd.DataFrame) -> pd.DataFrame:
    feats = session_features(events).merge(pos, on=["participant_id", "game"])
    rows = []
    for game in [BESTBUDS, TOWNSCAPER]:
        sub = feats[feats["game"] == game]
        for feature in ["length", "entropy", "query_rate", "platform_switch_rate"]:
            a = sub.loc[sub["position"] == "first", feature]
            b = sub.loc[sub["position"] == "second", feature]
            stat, p = mannwhitneyu(a, b, alternative="two-sided")
            rows.append(
                {
                    "game": game,
                    "feature": feature,
                    "n_first": len(a),
                    "n_second": len(b),
                    "median_first": a.median(),
                    "median_second": b.median(),
                    "mannwhitney_u": stat,
                    "p_value": p,
                }
            )
    return pd.DataFrame(rows)


# --- 2. opening-strategy carryover -------------------------------------------

def opening(seq: list[str], n: int = OPENING_LEN) -> tuple[str, ...]:
    return tuple(seq[:n])


def normalized_hamming(a: tuple[str, ...], b: tuple[str, ...]) -> float:
    n = max(len(a), len(b))
    if n == 0:
        return 0.0
    mismatches = sum(1 for x, y in zip(a, b) if x != y) + abs(len(a) - len(b))
    return mismatches / n


def carryover_analysis(seqs_by_key: dict, pos: pd.DataFrame) -> pd.DataFrame:
    participants = sorted({pid for pid, _ in seqs_by_key})
    rows = []
    for pid in participants:
        p_pos = pos[pos["participant_id"] == pid].set_index("game")["position"]
        first_game = p_pos[p_pos == "first"].index[0]
        second_game = p_pos[p_pos == "second"].index[0]
        opening_first = opening(seqs_by_key[(pid, first_game)])
        opening_second = opening(seqs_by_key[(pid, second_game)])
        rows.append(
            {
                "participant_id": pid,
                "first_game": first_game,
                "opening_first": " > ".join(opening_first),
                "opening_second": " > ".join(opening_second),
                "own_pair_distance": normalized_hamming(opening_first, opening_second),
            }
        )
    return pd.DataFrame(rows)


def permutation_test(carryover: pd.DataFrame, seqs_by_key: dict, pos: pd.DataFrame) -> dict:
    """Is the observed mean own-pair opening distance lower than expected
    under random (participant, participant) pairing of first/second
    openings? One-tailed permutation test."""
    participants = carryover["participant_id"].tolist()
    firsts = []
    seconds = []
    for pid in participants:
        p_pos = pos[pos["participant_id"] == pid].set_index("game")["position"]
        first_game = p_pos[p_pos == "first"].index[0]
        second_game = p_pos[p_pos == "second"].index[0]
        firsts.append(opening(seqs_by_key[(pid, first_game)]))
        seconds.append(opening(seqs_by_key[(pid, second_game)]))

    observed = np.mean([normalized_hamming(f, s) for f, s in zip(firsts, seconds)])

    rng = np.random.default_rng(RNG_SEED)
    n = len(participants)
    perm_means = np.empty(N_PERMUTATIONS)
    idx = np.arange(n)
    for i in range(N_PERMUTATIONS):
        shuffled = rng.permutation(idx)
        perm_means[i] = np.mean([normalized_hamming(firsts[j], seconds[k]) for j, k in zip(idx, shuffled)])

    p_value = float((perm_means <= observed).mean())
    return {
        "observed_mean_own_pair_distance": float(observed),
        "permuted_mean": float(perm_means.mean()),
        "permuted_sd": float(perm_means.std()),
        "p_value_one_tailed": p_value,
        "n_permutations": N_PERMUTATIONS,
    }


def carryover_by_order(carryover: pd.DataFrame) -> pd.DataFrame:
    a = carryover.loc[carryover["first_game"] == TOWNSCAPER, "own_pair_distance"]
    b = carryover.loc[carryover["first_game"] == BESTBUDS, "own_pair_distance"]
    stat, p = mannwhitneyu(a, b, alternative="two-sided")
    return pd.DataFrame(
        [
            {
                "group": "Townscaper first",
                "n": len(a),
                "median_own_pair_distance": a.median(),
            },
            {
                "group": "Best Buds first",
                "n": len(b),
                "median_own_pair_distance": b.median(),
            },
        ]
    ), {"mannwhitney_u": stat, "p_value": p}


# --- 3. order vs RQ4 cluster ------------------------------------------------

def order_vs_cluster(pos: pd.DataFrame) -> dict[str, pd.DataFrame]:
    out = {}
    for game, slug in [(BESTBUDS, "bestbuds"), (TOWNSCAPER, "townscaper")]:
        path = RQ4_DIR / f"cluster_assignments_{slug}.csv"
        if not path.exists():
            continue
        clusters = pd.read_csv(path)[["participant_id", "feature_cluster"]]
        merged = clusters.merge(pos[pos["game"] == game], on="participant_id")
        table = pd.crosstab(merged["position"], merged["feature_cluster"])
        out[game] = table
    return out


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    events = load_events()
    seqs_by_key = build_sequences(events)
    pos = position_table(events)
    pos.to_csv(RESULTS_DIR / "game_order.csv", index=False)

    print("=== Game order ===")
    print(first_game_per_participant(events).value_counts().to_string())

    # 1. order effect on session features
    order_tests = order_effect_tests(events, pos)
    order_tests.round(4).to_csv(RESULTS_DIR / "order_effect_tests.csv", index=False)
    print("\n=== Order effect on session-level features (Mann-Whitney U, unpaired) ===")
    print(order_tests.round(4).to_string(index=False))

    # 2. carryover
    carryover = carryover_analysis(seqs_by_key, pos)
    carryover.to_csv(RESULTS_DIR / "opening_carryover.csv", index=False)
    perm_result = permutation_test(carryover, seqs_by_key, pos)
    pd.DataFrame([perm_result]).to_csv(RESULTS_DIR / "carryover_permutation_test.csv", index=False)

    print(f"\n=== Opening-strategy carryover (first {OPENING_LEN} actions) ===")
    print(f"Observed mean own-pair distance: {perm_result['observed_mean_own_pair_distance']:.3f}")
    print(f"Permuted (random pairing) mean:  {perm_result['permuted_mean']:.3f} (sd={perm_result['permuted_sd']:.3f})")
    print(f"One-tailed permutation p-value:  {perm_result['p_value_one_tailed']:.4f}")

    by_order, by_order_test = carryover_by_order(carryover)
    by_order.round(3).to_csv(RESULTS_DIR / "carryover_by_order_group.csv", index=False)
    print("\n=== Carryover distance by which game came first ===")
    print(by_order.round(3).to_string(index=False))
    print(f"Mann-Whitney p={by_order_test['p_value']:.4f}")

    # 3. order vs cluster
    print("\n=== Order (first/second) vs. RQ4 feature-cluster ===")
    cross = order_vs_cluster(pos)
    for game, table in cross.items():
        table.to_csv(RESULTS_DIR / f"order_vs_cluster_{'bestbuds' if game == BESTBUDS else 'townscaper'}.csv")
        print(f"\n{game}:")
        print(table.to_string())
        if table.shape == (2, 2):
            odds, p = fisher_exact(table.values)
            print(f"Fisher exact p={p:.4f}")

    print(f"\nOutputs written to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
