"""RQ8: which platforms show up in Townscaper sessions, and in what order?

Follow-up to RQ7, requested by the researcher: RQ7 categorized *where*
platform switches go, pooled across a whole session. This asks the more
specific question -- for Townscaper (the game almost everyone solves),
which platforms are actually involved in finding it, which one is
typically showing when the game gets identified, and is there a
consistent *order* in which platforms get visited?

Four parts:
  1. Platform involvement: Platform-switch destinations (categorized,
     reusing RQ7's taxonomy) and View-single-result sources (top raw
     sites -- that column is long-tailed, so no forced taxonomy, same
     discipline as RQ7 sec 8).
  2. The "winning platform": the View-single-result source right before
     the session's Experiment ended, for sessions that actually reach one.
  3. First vs. last platform switched to per session -- does a session
     typically open on one kind of platform and close on another?
  4. Platform-category transitions (Platform-switch events only, in
     order) -- a smaller-alphabet version of RQ2's action-transition
     analysis, applied to *where* rather than *what*.

Best Buds is included as a secondary comparison column throughout, since
it's cheap and clarifies whether a Townscaper pattern is
Townscaper-specific or just how everyone navigates.
"""

from collections import Counter
from itertools import combinations, product
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from data import NON_SEARCH_ACTIONS, load_events
from rq3_game_differences import BESTBUDS, TOWNSCAPER
from rq7_platform_details import PLATFORM_CATEGORY, categorize_platform

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "rq8_platform_sequence"
CATEGORIES = ["Search engine", "AI assistant", "Storefront", "Community", "Game database", "Other"]


# --- 1. platform involvement --------------------------------------------

def platform_switch_categories(events: pd.DataFrame, game: str) -> pd.Series:
    switches = events[(events["action"] == "Platform switch") & (events["game"] == game)]
    dest = switches["action_details_clean"].dropna().str.strip()
    return dest.apply(categorize_platform).value_counts()


def view_single_result_top_sources(events: pd.DataFrame, game: str, top_n: int = 12) -> pd.Series:
    views = events[(events["action"] == "View single result") & (events["game"] == game)]
    sources = views["action_details_clean"].dropna().str.strip()
    return sources.value_counts().head(top_n)


# --- 2. the winning platform ----------------------------------------------

def winning_platforms(events: pd.DataFrame, game: str) -> pd.DataFrame:
    rows = []
    search = events[events["game"] == game].sort_values(["participant_id", "step"])
    for pid, grp in search.groupby("participant_id"):
        actions = grp["action"].tolist()
        details = grp["action_details_clean"].tolist()
        if actions and actions[-1] == "Experiment ended" and len(actions) >= 2:
            prev_action, prev_detail = actions[-2], details[-2]
            rows.append({"participant_id": pid, "closing_action": prev_action, "source": prev_detail})
    return pd.DataFrame(rows)


# --- 3. first vs last platform switched to ------------------------------

def first_last_platform(events: pd.DataFrame, game: str) -> pd.DataFrame:
    rows = []
    switches = events[(events["action"] == "Platform switch") & (events["game"] == game)].sort_values(
        ["participant_id", "step"]
    )
    for pid, grp in switches.groupby("participant_id"):
        dest = grp["action_details_clean"].dropna().str.strip().tolist()
        if not dest:
            continue
        rows.append(
            {
                "participant_id": pid,
                "first_category": categorize_platform(dest[0]),
                "last_category": categorize_platform(dest[-1]),
                "n_switches": len(dest),
            }
        )
    return pd.DataFrame(rows)


# --- 4. platform-category transitions ----------------------------------

def platform_category_transitions(events: pd.DataFrame, game: str) -> pd.DataFrame:
    switches = events[(events["action"] == "Platform switch") & (events["game"] == game)].sort_values(
        ["participant_id", "step"]
    )
    counts = Counter()
    for pid, grp in switches.groupby("participant_id"):
        cats = [categorize_platform(d) for d in grp["action_details_clean"].dropna().str.strip().tolist()]
        for a, b in zip(cats, cats[1:]):
            counts[(a, b)] += 1
    idx = pd.MultiIndex.from_tuples(product(CATEGORIES, CATEGORIES), names=["from", "to"])
    s = pd.Series({k: counts.get(k, 0) for k in idx}, index=idx, name="count")
    mat = s.reset_index().pivot(index="from", columns="to", values="count")
    mat = mat.reindex(index=CATEGORIES, columns=CATEGORIES, fill_value=0)
    keep = [c for c in CATEGORIES if mat.loc[c].sum() > 0 or mat[c].sum() > 0]
    return mat.loc[keep, keep]


def plot_platform_transitions(mat: pd.DataFrame, title: str, path: Path) -> None:
    present = list(mat.index) if not mat.empty else []
    fig, ax = plt.subplots(figsize=(6, 5))
    if mat.empty or not present:
        ax.text(0.5, 0.5, "No platform-to-platform transitions", ha="center", va="center")
        ax.axis("off")
    else:
        sub = mat.reindex(index=present, columns=present).fillna(0)
        im = ax.imshow(sub.values, cmap="YlOrBr")
        ax.set_xticks(range(len(present)))
        ax.set_xticklabels(present, rotation=45, ha="right", fontsize=8)
        ax.set_yticks(range(len(present)))
        ax.set_yticklabels(present, fontsize=8)
        for i in range(len(present)):
            for j in range(len(present)):
                v = int(sub.values[i, j])
                if v:
                    ax.text(j, i, str(v), ha="center", va="center", fontsize=8,
                             color="white" if v > sub.values.max() * 0.6 else "black")
        fig.colorbar(im, ax=ax, shrink=0.8, label="Count")
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    events = load_events()

    for game, slug in [(TOWNSCAPER, "townscaper"), (BESTBUDS, "bestbuds")]:
        print(f"\n{'='*70}\n{game}\n{'='*70}")

        # 1. platform involvement
        cats = platform_switch_categories(events, game)
        cats.to_csv(RESULTS_DIR / f"platform_switch_categories_{slug}.csv")
        print("--- 1a. Platform-switch destination categories ---")
        print(cats.to_string())

        top_sources = view_single_result_top_sources(events, game)
        top_sources.to_csv(RESULTS_DIR / f"view_single_result_top_sources_{slug}.csv")
        print("\n--- 1b. Top View-single-result sources ---")
        print(top_sources.to_string())

        # 2. winning platform
        winners = winning_platforms(events, game)
        winners.to_csv(RESULTS_DIR / f"winning_platform_{slug}.csv", index=False)
        print(f"\n--- 2. Action immediately before Experiment ended (n={len(winners)} resolved sessions) ---")
        print(winners["closing_action"].value_counts().to_string())
        print("\nSource, when closing action is View single result:")
        vsr_sources = winners.loc[winners["closing_action"] == "View single result", "source"].value_counts()
        print(vsr_sources.to_string())

        # 3. first vs last platform
        fl = first_last_platform(events, game)
        fl.to_csv(RESULTS_DIR / f"first_last_platform_{slug}.csv", index=False)
        print(f"\n--- 3. First platform-switch category per session (n={len(fl)}) ---")
        print(fl["first_category"].value_counts().to_string())
        print("\nLast platform-switch category per session:")
        print(fl["last_category"].value_counts().to_string())
        same = (fl["first_category"] == fl["last_category"]).mean() if len(fl) else float("nan")
        print(f"\nShare of sessions where first == last platform category: {same:.1%}")

        # 4. platform-category transitions
        trans = platform_category_transitions(events, game)
        trans.to_csv(RESULTS_DIR / f"platform_category_transitions_{slug}.csv")
        plot_platform_transitions(trans, f"Platform-category transitions — {game}", RESULTS_DIR / f"platform_transitions_{slug}.png")
        print("\n--- 4. Platform-category transition counts ---")
        print(trans.fillna(0).astype(int).to_string())

    print(f"\nOutputs written to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
