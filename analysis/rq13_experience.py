"""RQ13: does prior experience (gaming, search) relate to search behavior?

Researcher-provided pre-experiment questionnaire data (`data/survey_data/`):
  - `game_experience.tsv`: `game_exp` (1-4 self-rated gaming experience) and
    `game_hours` (weekly hours, bucketed: 0/1/4/8/14). Weakly correlated
    with each other (Spearman rho~0.33, p~0.14 -- checked, not assumed) so
    kept as two separate predictors rather than combined.
  - `search_systems_experience.tsv`: familiarity (0-4) with each of 6
    system types, rated independently, not a single dimension (inter-item
    correlations are weak/mixed). Only `Chatbot-style AI tools` is used
    here -- the one item with real variance and direct theoretical
    relevance (RQ4/RQ10's AI-cluster/image-search findings).
  - `complex_search_experience.tsv`: 8-item self-efficacy scale, -2..+2,
    one reverse-keyed item ("If I can't find what I'm looking for, I
    usually give up."). Cronbach's alpha = 0.57 after reverse-coding --
    modest, reported as a caveat rather than treated as a clean unitary
    scale. Used two ways: the full 8-item composite, and the single
    "alternatives" item on its own (researcher's hypothesis: unlike the
    "keep grinding" items, this one specifically predicts *not* looping,
    so it may behave differently from the composite).

Three questions, matching the researcher's own framing:
  1. Chatbot-AI experience vs. RQ4 cluster membership (hypothesis:
     AI-cluster members are more experienced with chatbot tools).
  2. Gaming experience vs. reliance on game-specific platforms (Steam,
     MobyGames, Dosgames, ... -- `platform_map.json`'s "Game search"
     category), via the `context` column: both *switching to* (share of
     `Platform switch` events) and *dwelling in* (share of all
     categorizable actions, RQ10-style) a game platform.
  3. Search self-efficacy (composite and the "alternatives" item alone)
     vs. RQ11 tactic engagement: how many of RQ11's reported tactics
     (results/rq11_maximal_repeats/tactics_{slug}.csv) does each participant's own
     session contain as a literal contiguous subsequence, whether or not
     that specific occurrence is the one RQ11's subsumption step
     credited (a participant clearly *performed* a tactic even if a
     longer repeat swallowed the formal count).

Every test here is Spearman (continuous predictor) or Mann-Whitney U
(binary/group predictor) -- the project's existing nonparametric idiom,
chosen again for the same reason: n=21, no distributional assumptions
wanted. Treat all of this as exploratory/descriptive, not confirmatory --
four predictors and several outcomes at n=21 is not a regime for firm
conclusions, and multiple-comparison correction was *not* applied since
these are three researcher-specified hypotheses, not a fishing expedition.
"""

from pathlib import Path

import pandas as pd
from scipy.stats import mannwhitneyu, spearmanr

from data import NON_SEARCH_ACTIONS, load_events
from rq3_game_differences import BESTBUDS, TOWNSCAPER
from rq10_finer_platform_categories import add_category_column, load_platform_map
from rq11_maximal_repeats import build_sequences as rq11_build_sequences

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "rq13_experience"
SURVEY_DIR = Path(__file__).resolve().parent.parent / "data" / "survey_data"
RQ4_DIR = Path(__file__).resolve().parent.parent / "results" / "rq4_clustering"
RQ11_DIR = Path(__file__).resolve().parent.parent / "results" / "rq11_maximal_repeats"

GAME_SLUG = {BESTBUDS: "bestbuds", TOWNSCAPER: "townscaper"}


# --- survey loading & scoring ----------------------------------------------

def load_game_experience() -> pd.DataFrame:
    df = pd.read_csv(SURVEY_DIR / "game_experience.tsv", sep="\t")
    return df.rename(columns={"Response ID": "participant_id"}).set_index("participant_id")


def load_chatbot_experience() -> pd.Series:
    df = pd.read_csv(SURVEY_DIR / "search_systems_experience.tsv", sep="\t")
    df = df.rename(columns={"Response ID": "participant_id"}).set_index("participant_id")
    return df["Chatbot-style AI tools"].rename("chatbot_experience")


def load_search_self_efficacy() -> pd.DataFrame:
    """Returns a frame with `composite` (mean of all 8 items, reverse-coding
    the one negatively-keyed item) and `alternatives` (that one item alone,
    not reverse-coded -- it's already keyed the way we want: higher =
    more likely to generate alternative strategies)."""
    df = pd.read_csv(SURVEY_DIR / "complex_search_experience.tsv", sep="\t")
    df = df.rename(columns={"Response ID": "participant_id"}).set_index("participant_id")
    items = list(df.columns)
    give_up_col = items[1]  # "If I can't find what I'm looking for, I usually give up."
    alternatives_col = items[5]  # "I can usually come up with alternative searching strategies..."
    scored = df[items].copy()
    scored[give_up_col] = -scored[give_up_col]
    return pd.DataFrame({
        "composite": scored.mean(axis=1),
        "alternatives": df[alternatives_col],
    })


# --- 1. chatbot experience vs RQ4 cluster -----------------------------------

def chatbot_vs_cluster(chatbot: pd.Series) -> pd.DataFrame:
    rows = []
    for game, slug in GAME_SLUG.items():
        clusters = pd.read_csv(RQ4_DIR / f"cluster_assignments_{slug}.csv")
        clusters = clusters.set_index("participant_id")["feature_cluster"]
        merged = pd.concat([clusters, chatbot], axis=1, join="inner")
        g0 = merged.loc[merged["feature_cluster"] == 0, "chatbot_experience"]
        g1 = merged.loc[merged["feature_cluster"] == 1, "chatbot_experience"]
        stat, p = mannwhitneyu(g1, g0, alternative="two-sided")
        rows.append({
            "game": game, "n_cluster0": len(g0), "n_cluster1": len(g1),
            "median_cluster0": g0.median(), "median_cluster1": g1.median(),
            "mannwhitney_u": stat, "p_value": p,
        })
    return pd.DataFrame(rows)


# --- 2. gaming experience vs game-platform reliance -------------------------

def game_platform_reliance(events: pd.DataFrame) -> pd.DataFrame:
    """Per (participant, game): share of Platform-switch events landing on
    a "Game search" platform (switching to), and share of all categorizable
    actions spent with that platform as context (dwelling in) -- same
    per-session-first normalization as RQ10's image_search_share_per_session."""
    search = events[~events["action"].isin(NON_SEARCH_ACTIONS) & events["platform_category"].notna()]
    switches = search[search["action"] == "Platform switch"]
    rows = []
    for (pid, game), grp in search.groupby(["participant_id", "game"]):
        n = len(grp)
        n_dwell = (grp["platform_category"] == "Game search").sum()
        sw = switches[(switches["participant_id"] == pid) & (switches["game"] == game)]
        n_sw = len(sw)
        n_sw_game = (sw["platform_category"] == "Game search").sum()
        rows.append({
            "participant_id": pid, "game": game,
            "n_categorizable": n, "n_dwell_game": int(n_dwell),
            "dwell_game_share": n_dwell / n if n else 0.0,
            "n_switches": n_sw, "n_switches_to_game": int(n_sw_game),
            "switch_to_game_share": n_sw_game / n_sw if n_sw else 0.0,
        })
    return pd.DataFrame(rows)


def gaming_experience_vs_reliance(reliance: pd.DataFrame, game_exp: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for game in GAME_SLUG:
        sub = reliance[reliance["game"] == game].set_index("participant_id")
        merged = sub.join(game_exp, how="inner")
        for predictor in ["game_exp", "game_hours"]:
            for outcome in ["dwell_game_share", "switch_to_game_share"]:
                rho, p = spearmanr(merged[predictor], merged[outcome])
                rows.append({"game": game, "predictor": predictor, "outcome": outcome,
                              "n": len(merged), "spearman_rho": rho, "p_value": p})
    return pd.DataFrame(rows)


# --- 3. self-efficacy vs RQ11 tactic engagement -----------------------------

def participant_tactic_usage(tactics: pd.DataFrame, sequences: dict[str, list[str]]) -> pd.DataFrame:
    """For each participant, how many of the reported tactics appear
    literally, contiguously, anywhere in their own session -- regardless
    of whether RQ11's subsumption step credited that specific occurrence
    to this pattern or to a longer one containing it. A participant who
    performed the moves still performed them."""
    patterns = [tuple(p.split(" -> ")) for p in tactics["pattern"]]
    rows = []
    for pid, seq in sequences.items():
        used = []
        for pat in patterns:
            L = len(pat)
            if any(tuple(seq[i:i + L]) == pat for i in range(len(seq) - L + 1)):
                used.append(" -> ".join(pat))
        rows.append({"participant_id": pid, "n_tactics_used": len(used), "used_any_tactic": len(used) > 0})
    return pd.DataFrame(rows)


def self_efficacy_vs_tactics(events: pd.DataFrame, self_efficacy: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for game, slug in GAME_SLUG.items():
        tactics_path = RQ11_DIR / f"tactics_{slug}.csv"
        tactics = pd.read_csv(tactics_path)
        if tactics.empty:
            print(f"[rq13] {game}: RQ11 reports 0 tactics, nothing to correlate against -- skipped.")
            continue
        sequences = rq11_build_sequences(events, game)
        usage = participant_tactic_usage(tactics, sequences).set_index("participant_id")
        merged = usage.join(self_efficacy, how="inner")
        for predictor in ["composite", "alternatives"]:
            rho, p = spearmanr(merged[predictor], merged["n_tactics_used"])
            rows.append({
                "game": game, "predictor": predictor, "outcome": "n_tactics_used",
                "n": len(merged), "spearman_rho": rho, "p_value": p,
                "n_tactics_available": len(tactics),
            })
            used = merged.loc[merged["used_any_tactic"], predictor]
            not_used = merged.loc[~merged["used_any_tactic"], predictor]
            if len(used) >= 2 and len(not_used) >= 2:
                stat, p2 = mannwhitneyu(used, not_used, alternative="two-sided")
                rows.append({
                    "game": game, "predictor": predictor, "outcome": "used_any_tactic",
                    "n": len(merged), "n_used": len(used), "n_not_used": len(not_used),
                    "median_used": used.median(), "median_not_used": not_used.median(),
                    "mannwhitney_u": stat, "p_value": p2,
                })
    return pd.DataFrame(rows)


# --- main --------------------------------------------------------------

def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    events = load_events()
    platform_map = load_platform_map()
    events = add_category_column(events, platform_map)

    game_exp = load_game_experience()
    chatbot = load_chatbot_experience()
    self_efficacy = load_search_self_efficacy()

    print("=== 1. Chatbot-AI experience vs RQ4 cluster ===")
    t1 = chatbot_vs_cluster(chatbot)
    t1.to_csv(RESULTS_DIR / "chatbot_experience_vs_rq4_cluster.csv", index=False)
    print(t1.to_string(index=False))

    print("\n=== 2. Gaming experience vs game-platform reliance ===")
    reliance = game_platform_reliance(events)
    reliance.to_csv(RESULTS_DIR / "game_platform_reliance.csv", index=False)
    t2 = gaming_experience_vs_reliance(reliance, game_exp)
    t2.to_csv(RESULTS_DIR / "game_experience_vs_reliance.csv", index=False)
    print(t2.to_string(index=False))

    print("\n=== 3. Search self-efficacy vs RQ11 tactic engagement ===")
    t3 = self_efficacy_vs_tactics(events, self_efficacy)
    t3.to_csv(RESULTS_DIR / "self_efficacy_vs_tactics.csv", index=False)
    print(t3.to_string(index=False))

    print(f"\nOutputs written to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
