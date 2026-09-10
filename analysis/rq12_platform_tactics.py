"""RQ12: search tactics with `Platform switch` split by finer category.

RQ11 found Best Buds' recurring tactics are dominated by generic
`Platform switch` steps threaded through the `Query <-> View result
list` core loop (see RQ11 building-blocks table). But `Platform switch`
collapses very different moves into one symbol -- switching to reverse
image search is not the same tactic as switching to ChatGPT. This reruns
RQ11's exact machinery (supermaximal repeats + RE-PAIR grammar,
participant-count-based reporting -- see rq11_maximal_repeats.py for the
full method writeup) with `Platform switch` expanded into its finer
destination category from `data/platform_map.json` (researcher-curated:
Web / Image / Conversational / Game search, plus Other for everything
rare), to see whether RQ11's "tactics" survive once we can tell which
platform was actually involved, or whether some were really several
participants' unrelated platform choices that just looked like one
shared tactic under the coarse label.

Only the `Platform switch` action itself is split (matching RQ9's
`build_state`) -- unlike RQ10, this does *not* recolor every other
action by which platform it's currently happening on (`context`); doing
that would fragment `Query`/`View result list`/etc. into up to 5 symbols
each and change what's being asked. `View single result`'s destination
is a specific landing site, not one of `platform_map.json`'s search
platforms, so (as in RQ10) it's left alone here too.
"""

from pathlib import Path

import pandas as pd

from data import NON_SEARCH_ACTIONS, load_events
from rq3_game_differences import BESTBUDS, TOWNSCAPER
from rq10_finer_platform_categories import categorize, load_platform_map
from rq11_maximal_repeats import (
    MIN_PARTICIPANTS,
    MIN_REPEAT_LEN,
    MPL_ACTION_COLOR,
    build_corpus,
    build_grammar,
    find_supermaximal_repeats,
    plot_grammar_trees,
    plot_tactics_catalog,
    tactic_building_blocks,
)

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "rq12_platform_tactics"

# Shades of RQ2's "Platform switch" green, lightest-to-darkest by roughly
# how specific/common the category is -- reads as "still Platform switch,
# just this flavor" rather than 5 unrelated hues competing with the base
# action palette. Order matches platform_map.json's category set exactly;
# add a new shade here if the map ever gains another category.
_PLATFORM_STATE_RGB = {
    "Platform switch: Web search": (17, 119, 51),
    "Platform switch: Image search": (69, 149, 96),
    "Platform switch: Conversational search": (122, 179, 141),
    "Platform switch: Game search": (165, 203, 177),
    "Platform switch: Other": (207, 228, 214),
}
MPL_ACTION_COLOR.update({state: tuple(c / 255 for c in rgb) for state, rgb in _PLATFORM_STATE_RGB.items()})


# --- sequences ---------------------------------------------------------

def build_state(action: str, action_details: object, platform_map: dict[str, str]) -> str:
    if action == "Platform switch" and pd.notna(action_details):
        return f"Platform switch: {categorize(action_details, platform_map)}"
    return action


def build_sequences(events: pd.DataFrame, game: str, platform_map: dict[str, str]) -> dict[str, list[str]]:
    events = events[events["game"] == game]
    events = events[~events["action"].isin(NON_SEARCH_ACTIONS)]
    events = events.sort_values(["participant_id", "step"]).copy()
    events["state"] = [
        build_state(a, d, platform_map)
        for a, d in zip(events["action"], events["action_details_clean"])
    ]
    return {pid: grp["state"].tolist() for pid, grp in events.groupby("participant_id")}


# --- main ----------------------------------------------------------------

def run_for(events: pd.DataFrame, platform_map: dict[str, str], game: str, label: str, slug: str) -> None:
    out = RESULTS_DIR
    sequences = build_sequences(events, game, platform_map)
    corpus, spans = build_corpus(sequences)
    n_sessions = len(sequences)

    repeats = find_supermaximal_repeats(corpus, spans)
    repeats.to_csv(out / f"supermaximal_repeats_{slug}.csv", index=False)
    tactics = repeats[
        (repeats["length"] >= MIN_REPEAT_LEN) & (repeats["n_participants"] >= MIN_PARTICIPANTS)
    ]
    tactics.to_csv(out / f"tactics_{slug}.csv", index=False)

    blocks = tactic_building_blocks(tactics)
    blocks.to_csv(out / f"tactics_building_blocks_{slug}.csv", index=False)

    grammar = build_grammar(corpus)
    grammar.rule_table(spans).to_csv(out / f"repair_rules_{slug}.csv", index=False)
    (out / f"repair_top_level_{slug}.txt").write_text(grammar.top_level_sequence())

    plot_tactics_catalog(tactics, label, out / f"tactics_catalog_{slug}.png")
    plot_grammar_trees(grammar, spans, label, out / f"grammar_trees_{slug}.png")

    print(f"\n=== {label} ({n_sessions} sessions, {len(corpus) - n_sessions} actions) ===")
    print(f"Supermaximal repeats: {len(repeats)} total, {len(tactics)} at length>={MIN_REPEAT_LEN} "
          f"& n_participants>={MIN_PARTICIPANTS} (of {n_sessions} sessions)")
    if len(tactics):
        print(tactics.head(10).to_string(index=False))
        print("Building blocks (bigrams shared across >=2 tactics):")
        print(blocks[blocks["n_tactics"] >= 2].to_string(index=False))
    print(f"RE-PAIR grammar: {len(grammar.rules)} rules")


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    events = load_events()
    platform_map = load_platform_map()

    run_for(events, platform_map, BESTBUDS, "Best Buds vs Bad Guys", "bestbuds")
    run_for(events, platform_map, TOWNSCAPER, "Townscaper", "townscaper")

    print(f"\nOutputs written to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
