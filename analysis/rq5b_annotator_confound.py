"""RQ5b: secondary, confounded check of annotator effects on the main
21-participant dataset.

RQ5's primary analysis (rq5_annotator_agreement.py) uses the dedicated
agreement sample -- the one place multiple annotators coded the *same*
recording, so annotator effects are actually identifiable. This script
instead looks at the 21 individually-annotated participants, where each
annotator coded a disjoint block: annotator1 -> ID1-5, annotator2 ->
ID6-10, annotator4 -> ID11-15, annotator3 -> ID16-21. "Annotator" and
"which five/six participants" are therefore the same partition of the
data -- any pattern found here could be genuine annotator coding style,
or it could just be that those particular five people behave
differently, and this dataset alone cannot tell the two apart. Every
result below is descriptive and should be read alongside (not instead
of) RQ5's unconfounded finding, per the plan
(docs/planning_and_background.md sec 4.5).

Because session lengths vary hugely (13-71 events for Best Buds, 4-55
for Townscaper) and each annotator's block is small (5-6 participants),
raw pooled action/bigram *counts* would mostly reflect which annotator
happened to get the participant with the longest session, not coding
style. So every feature here is computed per (participant, game) first,
normalized within that session, *then* averaged across the participants
in an annotator's block -- each session gets equal weight regardless of
length.

Four parts:
  1. Per-annotator mean action-rate profile (7 actions + entropy),
     pairwise Jensen-Shannon divergence.
  2. A random-intercept model per action rate (annotator as the
     grouping factor, game as a fixed effect) -- reports the ICC: how
     much of the between-session variance sits "within annotator
     block" vs residual. This quantifies clustering by block; it
     cannot by itself attribute that clustering to annotator style
     specifically, for the reason above.
  3. The same per-participant-first averaging applied to the 8 most
     common action bigrams overall.
  4. A direct corroboration check: does the pattern found here for
     annotator2 -- the one annotator RQ5's agreement sample
     independently showed to be a coarser segmenter -- match that
     finding (e.g. relatively low View result list / Platform switch /
     Browsing rates, shorter sessions)? Agreement is suggestive, not
     proof, but it's the closest thing to a cross-check this confounded
     view can offer.
"""

from collections import Counter
from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.spatial.distance import jensenshannon

from data import NON_SEARCH_ACTIONS, load_events
from rq2_patterns import ACTIONS
from rq3_game_differences import shannon_entropy

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "rq5b"
REAL_ACTIONS = [a for a in ACTIONS if a != "Experiment ended"]
FEATURES = REAL_ACTIONS + ["entropy"]


# --- setup -----------------------------------------------------------------

def participant_annotator_map(events: pd.DataFrame) -> pd.Series:
    return events.groupby("participant_id")["annotator"].first()


def session_action_rates(events: pd.DataFrame) -> pd.DataFrame:
    search = events[~events["action"].isin(NON_SEARCH_ACTIONS)]
    ann_map = participant_annotator_map(events)
    rows = []
    for (pid, game), grp in search.groupby(["participant_id", "game"]):
        acts = grp.sort_values("step")["action"].tolist()
        counts = pd.Series(acts).value_counts()
        props = (counts / counts.sum()).reindex(REAL_ACTIONS, fill_value=0.0)
        row = {
            "participant_id": pid,
            "game": game,
            "annotator": ann_map[pid],
            "length": len(acts),
            "entropy": shannon_entropy(acts),
        }
        row.update(props.to_dict())
        rows.append(row)
    return pd.DataFrame(rows)


# --- 1. annotator profiles + JS divergence -----------------------------------

def annotator_profiles(rates: pd.DataFrame) -> pd.DataFrame:
    return rates.groupby("annotator")[REAL_ACTIONS].mean()


def pairwise_js(profiles: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for a, b in combinations(profiles.index, 2):
        js = jensenshannon(profiles.loc[a].values, profiles.loc[b].values, base=2)
        rows.append({"annotator_a": a, "annotator_b": b, "js_divergence": float(js)})
    return pd.DataFrame(rows).sort_values("js_divergence", ascending=False)


def plot_profiles(profiles: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = np.arange(len(REAL_ACTIONS))
    width = 0.8 / len(profiles)
    palette = ["#b3690f", "#009485", "#5b4b8a", "#a33b56", "#4b7a3c", "#3c5b7a"]
    for i, (annotator, row) in enumerate(profiles.iterrows()):
        ax.bar(x + i * width, row.values, width=width, label=annotator, color=palette[i % len(palette)])
    ax.set_xticks(x + width * (len(profiles) - 1) / 2)
    ax.set_xticklabels(REAL_ACTIONS, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("Mean share of session (participant-averaged within annotator block)")
    ax.set_title("Action-rate profile by annotator -- main dataset (confounded with participant block)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# --- 2. ICC via random-intercept model ----------------------------------

def icc_per_feature(rates: pd.DataFrame) -> pd.DataFrame:
    results = []
    for feat in FEATURES:
        df = rates[["annotator", "game", feat]].rename(columns={feat: "y"})
        try:
            fit = smf.mixedlm("y ~ C(game)", df, groups=df["annotator"]).fit(reml=True)
            var_group = float(fit.cov_re.iloc[0, 0])
            var_resid = float(fit.scale)
            denom = var_group + var_resid
            icc = var_group / denom if denom > 0 else float("nan")
            results.append(
                {
                    "feature": feat,
                    "icc_annotator": icc,
                    "var_annotator": var_group,
                    "var_residual": var_resid,
                    "converged": bool(fit.converged),
                }
            )
        except Exception as exc:  # noqa: BLE001 -- report, don't crash the run
            results.append({"feature": feat, "icc_annotator": float("nan"), "error": str(exc)})
    return pd.DataFrame(results)


# --- 3. bigram rates -------------------------------------------------------

def top_overall_bigrams(events: pd.DataFrame, k: int = 8) -> list[tuple[str, str]]:
    search = events[~events["action"].isin(NON_SEARCH_ACTIONS)].sort_values(["participant_id", "game", "step"])
    counts = Counter()
    for _, grp in search.groupby(["participant_id", "game"]):
        acts = grp["action"].tolist()
        counts.update(zip(acts, acts[1:]))
    return [bg for bg, _ in counts.most_common(k)]


def bigram_rates(events: pd.DataFrame, bigrams: list[tuple[str, str]]) -> pd.DataFrame:
    search = events[~events["action"].isin(NON_SEARCH_ACTIONS)].sort_values(["participant_id", "game", "step"])
    ann_map = participant_annotator_map(events)
    rows = []
    for (pid, game), grp in search.groupby(["participant_id", "game"]):
        acts = grp["action"].tolist()
        pair_counts = Counter(zip(acts, acts[1:]))
        total = sum(pair_counts.values())
        row = {"participant_id": pid, "game": game, "annotator": ann_map[pid]}
        for bg in bigrams:
            row[" -> ".join(bg)] = pair_counts.get(bg, 0) / total if total else 0.0
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    events = load_events()
    rates = session_action_rates(events)
    rates.to_csv(RESULTS_DIR / "session_action_rates.csv", index=False)

    # 1. profiles + JS divergence
    profiles = annotator_profiles(rates)
    profiles.round(3).to_csv(RESULTS_DIR / "annotator_action_profiles.csv")
    plot_profiles(profiles, RESULTS_DIR / "annotator_action_profiles.png")
    js = pairwise_js(profiles)
    js.round(3).to_csv(RESULTS_DIR / "annotator_profile_js_divergence.csv", index=False)

    print("=== 1. Mean action-rate profile by annotator (confounded with participant block) ===")
    print(profiles.round(3).to_string())
    print("\nPairwise JS divergence between annotator profiles:")
    print(js.round(3).to_string(index=False))

    # session length by annotator (simple, robust corroboration signal)
    length_by_annotator = rates.groupby(["annotator", "game"])["length"].agg(["count", "mean", "median"])
    length_by_annotator.round(1).to_csv(RESULTS_DIR / "session_length_by_annotator.csv")
    print("\n=== Session length by annotator (search-only events) ===")
    print(length_by_annotator.round(1).to_string())

    # 2. ICC
    icc = icc_per_feature(rates)
    icc.round(3).to_csv(RESULTS_DIR / "icc_by_feature.csv", index=False)
    print("\n=== 2. ICC (share of variance 'within annotator block'), random-intercept model, game as fixed effect ===")
    print(icc.round(3).to_string(index=False))

    # 3. bigram rates
    top_bg = top_overall_bigrams(events)
    bg_rates = bigram_rates(events, top_bg)
    bg_rates.to_csv(RESULTS_DIR / "bigram_rates.csv", index=False)
    bg_cols = [" -> ".join(bg) for bg in top_bg]
    bg_profile = bg_rates.groupby("annotator")[bg_cols].mean()
    bg_profile.round(3).to_csv(RESULTS_DIR / "annotator_bigram_profiles.csv")
    print("\n=== 3. Mean bigram rate by annotator (top 8 overall bigrams) ===")
    print(bg_profile.round(3).to_string())

    # 4. corroboration check
    print("\n=== 4. Corroboration check: annotator2 (independently known coarser segmenter, RQ5 sec 6.1) ===")
    print("Action-rate profile, annotator2 vs. the other 3:")
    others_mean = profiles.drop(index="annotator2").mean()
    compare = pd.DataFrame({"annotator2": profiles.loc["annotator2"], "other_annotators_mean": others_mean})
    compare["annotator2_minus_others"] = compare["annotator2"] - compare["other_annotators_mean"]
    print(compare.round(3).to_string())

    print(f"\nOutputs written to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
