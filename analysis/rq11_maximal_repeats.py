"""RQ11: search tactics as recurring action sub-sequences.

Inspired by Wildemuth, Oh & Marchionini (2010), who derived search tactics
from Maximal Repeating Patterns (MRP) in coded action sequences, found with
Siochi & Ehrich's (1991) suffix-based tool, then manually deduplicated any
MRP occurrence that's subsumed by (contained within) a longer MRP at the
same position.

Two complementary, automated takes on that same idea, run per game:

  1. Supermaximal repeats via a (generalized) suffix array + LCP array.
    "Maximal" = right-maximal (can't extend right without losing an
    occurrence) and left-maximal (can't extend left without losing one);
    "supermaximal" = a maximal repeat with no occurrence contained inside
    an occurrence of another, longer maximal repeat. That containment
    check is the automated equivalent of Wildemuth's manual subsumption
    step, applied occurrence-by-occurrence rather than pattern-by-pattern
    (closer to what she actually did by hand).
  2. A grammar-based compression, in the spirit of Sequitur
    (Nevill-Manning & Witten 1997): repeatedly find the most frequent
    adjacent pair ("digram") in the sequence and replace every
    non-overlapping occurrence with a new grammar rule, then repeat on
    the now-shorter sequence (which may contain rule symbols as well as
    original actions) until no digram repeats. This is RE-PAIR (Larsson
    & Moffat 1999) -- a close relative of Sequitur that builds the same
    kind of *hierarchical* repeat structure (a rule can itself be built
    out of other rules) but as a simple offline "replace, then repeat"
    loop rather than Sequitur's online, cascading digram-uniqueness
    bookkeeping, which makes it much easier to implement and verify
    correctly at this scale. Where (1) gives a flat list of repeats,
    this gives a small hierarchy, which can reveal tactics-within-tactics
    (a repeated pattern normally used as one step inside a larger
    repeated pattern).

Sessions within a game are concatenated into one corpus per game, each
separated by a unique sentinel so no repeat is ever allowed to bridge two
participants' sessions. `Experiment ended` is dropped first (see
NON_SEARCH_ACTIONS in data.py) -- it's a fixed absorbing bookkeeping
marker, not a search move, and including it would just produce a
"whatever preceded the end" pseudo-tactic for every session.
"""

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import plotly.colors as pc

from data import NON_SEARCH_ACTIONS, load_events
from rq2_patterns import ACTION_COLOR
from rq3_game_differences import BESTBUDS, TOWNSCAPER

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "rq11_maximal_repeats"

# ACTION_COLOR values are plotly "rgb(r,g,b)" strings; matplotlib needs 0-1 tuples.
MPL_ACTION_COLOR = {action: tuple(c / 255 for c in pc.unlabel_rgb(rgb)) for action, rgb in ACTION_COLOR.items()}

MIN_REPEAT_LEN = 3  # drop length-2 repeats from the reported tactics (already covered by RQ2 bigrams), per Wildemuth
MIN_PARTICIPANTS = 3  # drop repeats used by fewer distinct participants than this


# --- sequences ---------------------------------------------------------

def build_sequences(events: pd.DataFrame, game: str) -> dict[str, list[str]]:
    events = events[events["game"] == game]
    events = events[~events["action"].isin(NON_SEARCH_ACTIONS)]
    events = events.sort_values(["participant_id", "step"])
    return {pid: grp["action"].tolist() for pid, grp in events.groupby("participant_id")}


def build_corpus(sequences: dict[str, list[str]]) -> tuple[list[str], list[tuple[int, int, str]]]:
    """Concatenate sessions with unique sentinels; return the corpus plus a
    list of (start, end, participant_id) spans (end exclusive, sentinel not
    included) for mapping corpus positions back to sessions."""
    corpus: list[str] = []
    spans: list[tuple[int, int, str]] = []
    for i, (pid, seq) in enumerate(sequences.items()):
        start = len(corpus)
        corpus.extend(seq)
        spans.append((start, len(corpus), pid))
        corpus.append(f"<END_{i}>")  # unique sentinel: repeats can never cross it
    return corpus, spans


def session_of(pos: int, spans: list[tuple[int, int, str]]) -> str:
    for start, end, pid in spans:
        if start <= pos < end:
            return pid
    return "?"  # a sentinel position; never used as a repeat's start


# --- 1. suffix array + LCP array ----------------------------------------

def build_suffix_array(corpus: list[str]) -> list[int]:
    """Naive O(n^2 log n) construction: fine at this scale (a few hundred
    to ~1000 tokens per game) and easy to verify against a suffix tree by
    hand; a doubling algorithm would be needed for much larger corpora."""
    n = len(corpus)
    return sorted(range(n), key=lambda i: corpus[i:])


def build_lcp_array(corpus: list[str], sa: list[int]) -> list[int]:
    """lcp[i] = length of the common prefix of the suffixes at sa[i-1] and
    sa[i] (lcp[0] is unused, kept 0). A sentinel is unique to its session,
    so a common-prefix scan always stops there -- no repeat can cross a
    session boundary."""
    n = len(corpus)
    lcp = [0] * n
    for i in range(1, n):
        a, b = sa[i - 1], sa[i]
        L = 0
        while a + L < n and b + L < n and corpus[a + L] == corpus[b + L]:
            L += 1
        lcp[i] = L
    return lcp


@dataclass
class RepeatOccurrence:
    pattern: tuple[str, ...]
    start: int  # corpus position
    length: int


def enumerate_right_maximal_repeats(corpus: list[str], sa: list[int], lcp: list[int]) -> list[list[int]]:
    """Enumerate every LCP-array interval (= every internal node of the
    implicit suffix tree) via a monotonic stack. Each interval is a
    right-maximal repeat: a run of >=2 suffixes sharing a common prefix of
    exactly that interval's length (any longer shared prefix would have
    merged them into a higher-LCP run instead). Returns, for each such
    repeat, the list of corpus start positions of its occurrences."""
    n = len(sa)
    intervals: list[tuple[int, int, int]] = []  # (length, sa_lo, sa_hi) inclusive
    stack: list[tuple[int, int]] = []  # (lcp_value, sa_start_index)
    for i in range(1, n):
        start = i
        while stack and stack[-1][0] > lcp[i]:
            v, s = stack.pop()
            if v >= 2:
                intervals.append((v, s - 1, i - 1))
            start = s
        if not stack or stack[-1][0] < lcp[i]:
            stack.append((lcp[i], start))
    while stack:
        v, s = stack.pop()
        if v >= 2:
            intervals.append((v, s - 1, n - 1))

    occurrences_by_pattern: dict[tuple[int, int], list[int]] = {}
    for length, lo, hi in intervals:
        occurrences_by_pattern[(length, lo)] = [sa[j] for j in range(lo, hi + 1)]
    return [(length, positions) for (length, _lo), positions in occurrences_by_pattern.items()]


def left_maximal_filter(corpus: list[str], repeats: list[tuple[int, list[int]]]) -> list[tuple[int, list[int]]]:
    """Keep only repeats where the occurrences are NOT all preceded by the
    same character (or where at least one occurrence starts a session) --
    otherwise every occurrence could be extended one step to the left and
    this is really a sub-repeat of a longer one that will be found in its
    own right."""
    kept = []
    for length, positions in repeats:
        left_chars = set()
        extendable = True
        for p in positions:
            if p == 0 or corpus[p - 1].startswith("<END_"):
                extendable = False
                break
            left_chars.add(corpus[p - 1])
        if not extendable or len(left_chars) > 1:
            kept.append((length, positions))
    return kept


def subsume_occurrences(
    corpus: list[str], maximal_repeats: list[tuple[int, list[int]]]
) -> list[tuple[tuple[str, ...], list[int]]]:
    """Occurrence-level dedup, mirroring Wildemuth's manual step: drop any
    occurrence of a repeat that falls entirely inside an occurrence of a
    strictly longer maximal repeat. What survives are the supermaximal
    occurrences; patterns with zero surviving occurrences are dropped."""
    # index all occurrence spans by length, longest first, for containment checks
    all_spans = [(length, p, p + length) for length, positions in maximal_repeats for p in positions]
    all_spans.sort(key=lambda s: -s[0])

    def is_subsumed(length: int, start: int) -> bool:
        end = start + length
        for L, s, e in all_spans:
            if L <= length:
                break  # sorted longest-first; nothing shorter can subsume
            if s <= start and end <= e and not (s == start and e == end and L == length):
                return True
        return False

    result = []
    for length, positions in maximal_repeats:
        survivors = [p for p in positions if not is_subsumed(length, p)]
        if len(survivors) >= 2:
            pattern = tuple(corpus[positions[0]: positions[0] + length])
            result.append((pattern, survivors))
    return result


def find_supermaximal_repeats(corpus: list[str], spans: list[tuple[int, int, str]]) -> pd.DataFrame:
    """One row per supermaximal repeat. `n_occurrences` counts every
    surviving occurrence in the corpus; `n_participants` counts only the
    *distinct* participants that contributed at least one of those
    occurrences -- a participant whose own session happens to repeat the
    same tactic twice would otherwise inflate `n_occurrences` without
    the tactic actually being any more widespread. The two are equal
    unless some participant repeats a tactic within their own session."""
    sa = build_suffix_array(corpus)
    lcp = build_lcp_array(corpus, sa)
    right_maximal = enumerate_right_maximal_repeats(corpus, sa, lcp)
    maximal = left_maximal_filter(corpus, right_maximal)
    supermaximal = subsume_occurrences(corpus, maximal)

    rows = [
        {
            "pattern": " -> ".join(pattern),
            "length": len(pattern),
            "n_occurrences": len(positions),
            "n_participants": len({session_of(p, spans) for p in positions}),
        }
        for pattern, positions in supermaximal
    ]
    df = pd.DataFrame(rows).drop_duplicates(subset="pattern")
    return df.sort_values(
        ["n_participants", "n_occurrences", "length"], ascending=[False, False, False]
    ).reset_index(drop=True)


def tactic_building_blocks(tactics: pd.DataFrame, k: int = 2) -> pd.DataFrame:
    """For the reported tactics, which short (length-k) sub-patterns
    recur across *multiple different* tactics? Answers "what are these
    tactics actually made of" directly: a bigram used by many tactics is
    a shared building block, not a coincidence of one specific pattern.
    Counts each bigram at most once per tactic (tactic-level coverage,
    not raw occurrence count within a pattern)."""
    if tactics.empty:
        return pd.DataFrame(columns=["building_block", "n_tactics"])
    coverage = Counter()
    for pattern in tactics["pattern"]:
        steps = pattern.split(" -> ")
        blocks = {tuple(steps[i:i + k]) for i in range(len(steps) - k + 1)}
        for b in blocks:
            coverage[b] += 1
    rows = [
        {"building_block": " -> ".join(b), "n_tactics": n}
        for b, n in coverage.most_common()
    ]
    return pd.DataFrame(rows)


# --- 2. RE-PAIR grammar (Sequitur-family, hierarchical repeat structure) --

class RepairGrammar:
    """RE-PAIR (Larsson & Moffat, 1999): repeatedly replace the most
    frequent adjacent symbol pair in the sequence with a new rule, until
    no pair repeats. Every rule has exactly two symbols on its
    right-hand side (a terminal action or another rule), so nesting a
    rule inside another rule is exactly how a "tactic built out of
    smaller tactics" shows up.
    """

    def __init__(self) -> None:
        self.rules: dict[str, tuple[str, str]] = {}
        self.top_level: list[str] = []
        self._counter = 0

    def build(self, sequence: list[str]) -> None:
        symbols = list(sequence)
        while True:
            counts = Counter(zip(symbols, symbols[1:]))
            if not counts:
                break
            # try candidates most-frequent-first; a digram's *non-overlapping*
            # replacement count can be lower than its raw adjacent count
            # (e.g. "a a a" has raw count 2 for (a,a) but only 1 non-overlapping
            # replacement), so skip down the ranking until one actually pays off
            candidates = [dg for dg, c in counts.most_common() if c >= 2]
            replaced = False
            for digram in candidates:
                new_symbols, occ = self._replace_non_overlapping(symbols, digram)
                if occ >= 2:
                    symbols = new_symbols
                    replaced = True
                    break
            if not replaced:
                break
        self.top_level = symbols

    def _replace_non_overlapping(self, symbols: list[str], digram: tuple[str, str]) -> tuple[list[str], int]:
        rule_name = f"R{self._counter + 1}"
        out: list[str] = []
        i, n, occ = 0, len(symbols), 0
        while i < n:
            if i + 1 < n and (symbols[i], symbols[i + 1]) == digram:
                out.append(rule_name)
                i += 2
                occ += 1
            else:
                out.append(symbols[i])
                i += 1
        if occ >= 2:
            self._counter += 1
            self.rules[rule_name] = digram
        return out, occ

    def expand(self, symbol: str) -> list[str]:
        if symbol not in self.rules:
            return [symbol]
        a, b = self.rules[symbol]
        return self.expand(a) + self.expand(b)

    def occurrence_count(self, symbol: str, _memo: dict[str, int] | None = None) -> int:
        """How many times this rule's fully-expanded pattern actually
        occurs in the original corpus. Not the same as counting direct
        references to `symbol`: a rule nested only inside another rule
        that's itself used 3 times occurs 3 times in the data, even
        though it's directly referenced just once (from within that
        parent rule's own single definition). Computed recursively:
        direct top-level occurrences, plus (for every rule that embeds
        this symbol in its body) that rule's own occurrence count, times
        how many times the symbol appears in that rule's body."""
        if _memo is None:
            _memo = {}
        if symbol in _memo:
            return _memo[symbol]
        _memo[symbol] = 0  # guard against pathological self-reference
        count = self.top_level.count(symbol)
        for name, (a, b) in self.rules.items():
            n_in_body = (a == symbol) + (b == symbol)
            if n_in_body:
                count += self.occurrence_count(name, _memo) * n_in_body
        _memo[symbol] = count
        return count

    def occurrence_starts(self, symbol: str) -> list[int]:
        """Corpus start position of every occurrence of `symbol`'s pattern,
        at any nesting depth. Walks the whole grammar once, tracking a
        running corpus offset; a terminal always advances the offset by
        1, a rule recurses into its two children (whose combined advance
        equals the rule's own expanded length) -- so the offset is
        correct at every point regardless of whether `symbol` matches."""
        starts: list[int] = []
        offset = [0]

        def visit(sym: str) -> None:
            if sym == symbol:
                starts.append(offset[0])
            if sym in self.rules:
                a, b = self.rules[sym]
                visit(a)
                visit(b)
            else:
                offset[0] += 1

        for s in self.top_level:
            visit(s)
        return starts

    def rule_table(self, spans: list[tuple[int, int, str]] | None = None) -> pd.DataFrame:
        memo: dict[str, int] = {}
        rows = []
        for name, digram in self.rules.items():
            row = {
                "rule": name,
                "expansion": " -> ".join(digram),
                "fully_expanded": " -> ".join(self.expand(name)),
                "n_occurrences": self.occurrence_count(name, memo),
                "expanded_length": len(self.expand(name)),
            }
            if spans is not None:
                starts = self.occurrence_starts(name)
                row["n_participants"] = len({session_of(p, spans) for p in starts})
            rows.append(row)
        df = pd.DataFrame(rows)
        sort_cols = ["expanded_length", "n_participants" if spans is not None else "n_occurrences"]
        return df.sort_values(sort_cols, ascending=[False, False]).reset_index(drop=True)

    def top_level_sequence(self) -> str:
        return " -> ".join(self.top_level)


def build_grammar(corpus: list[str]) -> RepairGrammar:
    """One grammar built across a game's whole sentinel-separated corpus
    (same corpus as the suffix-array method), so rules can capture
    structure repeated *across* sessions, not just within one."""
    grammar = RepairGrammar()
    grammar.build(corpus)
    return grammar


# --- plots -----------------------------------------------------------------

def _legend_handles(actions: list[str]) -> tuple[list, list[str]]:
    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=MPL_ACTION_COLOR.get(a, "#cccccc")) for a in actions]
    return handles, actions


def plot_tactics_catalog(tactics: pd.DataFrame, label: str, path: Path) -> None:
    """Flat perspective: one horizontal strip per supermaximal-repeat
    tactic, each step colored by action (same palette as RQ2's transition
    graphs). Rows are sorted by how many *distinct participants* used the
    tactic (ties broken by raw occurrence count, then by length) -- the
    table this reads from (`tactics_{slug}.csv`) is already sorted this
    way, so the plot just mirrors row order top to bottom."""
    if tactics.empty:
        return
    rows = [row.pattern.split(" -> ") for row in tactics.itertuples()]
    n_participants = tactics["n_participants"].tolist()
    n_occurrences = tactics["n_occurrences"].tolist()
    n = len(rows)
    max_len = max(len(r) for r in rows)

    fig, ax = plt.subplots(figsize=(max(7.5, 0.85 * max_len + 3.2), 0.55 * n + 2.3))
    used_actions: list[str] = []
    for i, (steps, n_p, n_o) in enumerate(zip(rows, n_participants, n_occurrences)):
        y = n - i - 1
        for j, action in enumerate(steps):
            ax.add_patch(plt.Rectangle((j, y + 0.1), 0.94, 0.8, facecolor=MPL_ACTION_COLOR.get(action, "#cccccc"),
                                        edgecolor="white", linewidth=1.2))
            if action not in used_actions:
                used_actions.append(action)
        label_text = f"{n_p} ppts" if n_p == n_o else f"{n_p} ppts ({n_o}×)"
        ax.text(len(steps) + 0.25, y + 0.5, label_text, va="center", fontsize=9, color="#435350")

    ax.set_xlim(0, max_len + 2.6)
    ax.set_ylim(0, n)
    ax.set_yticks([])
    ax.set_xticks(range(max_len + 1))
    ax.set_xlabel("step within tactic", labelpad=10)
    ax.set_title(f"Recurring tactics (supermaximal repeats) — {label}", fontsize=12)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)

    handles, ordered_actions = _legend_handles(used_actions)
    ax.legend(handles, ordered_actions, loc="upper center", bbox_to_anchor=(0.5, -0.28),
              ncol=min(4, len(ordered_actions)), frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _tree_layout(grammar: RepairGrammar, root: str):
    """Simple recursive layout: leaves get sequential x in left-to-right
    order, an internal node's x is the midpoint of its children's, y is
    -depth along that path. Returns (positions, edges, node_kind) keyed
    by a synthetic per-instance node id (a rule symbol can legitimately
    appear more than once in one tree)."""
    positions: dict[int, tuple[float, int]] = {}
    edges: list[tuple[int, int]] = []
    kind: dict[int, tuple[str, str]] = {}  # id -> (symbol, "rule"|"terminal")
    counter = [0]
    next_leaf_x = [0]

    def visit(symbol: str, depth: int) -> int:
        node_id = counter[0]
        counter[0] += 1
        if symbol in grammar.rules:
            a, b = grammar.rules[symbol]
            left_id = visit(a, depth + 1)
            right_id = visit(b, depth + 1)
            x = (positions[left_id][0] + positions[right_id][0]) / 2
            positions[node_id] = (x, -depth)
            kind[node_id] = (symbol, "rule")
            edges.append((node_id, left_id))
            edges.append((node_id, right_id))
        else:
            positions[node_id] = (float(next_leaf_x[0]), -depth)
            next_leaf_x[0] += 1
            kind[node_id] = (symbol, "terminal")
        return node_id

    root_id = visit(root, 0)
    return root_id, positions, edges, kind


def plot_grammar_trees(
    grammar: RepairGrammar, spans: list[tuple[int, int, str]], label: str, path: Path, top_k: int = 5
) -> None:
    """Hierarchical perspective: the expansion tree of the top-k most
    composite RE-PAIR rules (by fully-expanded length), each rule node
    breaking down into its two children down to terminal actions --
    shows a repeated pattern built out of smaller repeated patterns.
    Every internal node (not just the root) is labeled with its own
    participant count, so a "sub-tactic" nested inside a longer one can
    be read on its own terms, not just as part of the parent."""
    table = grammar.rule_table(spans).head(top_k)
    if table.empty:
        return

    participants_memo: dict[str, int] = {}

    def n_participants(symbol: str) -> int:
        if symbol not in participants_memo:
            starts = grammar.occurrence_starts(symbol)
            participants_memo[symbol] = len({session_of(p, spans) for p in starts})
        return participants_memo[symbol]

    fig, axes = plt.subplots(1, len(table), figsize=(4.3 * len(table), 4.6))
    if len(table) == 1:
        axes = [axes]

    used_actions: list[str] = []
    for ax, row in zip(axes, table.itertuples()):
        root_id, positions, edges, kind = _tree_layout(grammar, row.rule)
        for pid, cid in edges:
            x0, y0 = positions[pid]
            x1, y1 = positions[cid]
            ax.plot([x0, x1], [y0, y1], color="#b7c2be", linewidth=1.2, zorder=1)
        for node_id, (x, y) in positions.items():
            symbol, node_kind = kind[node_id]
            if node_kind == "terminal":
                ax.scatter([x], [y], s=420, color=MPL_ACTION_COLOR.get(symbol, "#cccccc"),
                           edgecolor="white", linewidth=1, zorder=2)
                ax.text(x, y - 0.34, symbol, ha="center", va="top", fontsize=6, rotation=25)
                if symbol not in used_actions:
                    used_actions.append(symbol)
            else:
                ax.scatter([x], [y], s=190, color="#eef1ef", edgecolor="#435350", linewidth=1, zorder=2)
                # Root's count is already in the panel title; only annotate
                # internal (non-root) rule nodes here to avoid double-labeling.
                if node_id != root_id:
                    ax.text(x, y + 0.22, f"n={n_participants(symbol)}", ha="center", va="bottom",
                            fontsize=6, color="#435350")
        ax.set_title(f"{row.rule}  ({row.n_participants} ppts, {row.expanded_length} steps)", fontsize=9)
        ax.axis("off")
        ax.margins(y=0.18)

    handles, ordered_actions = _legend_handles(used_actions)
    fig.legend(handles, ordered_actions, loc="lower center", bbox_to_anchor=(0.5, -0.05),
               ncol=min(4, len(ordered_actions)), frameon=False, fontsize=8)
    fig.suptitle(f"RE-PAIR grammar — most composite tactics — {label}", fontsize=12)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# --- main ----------------------------------------------------------------

def run_for(events: pd.DataFrame, game: str, label: str, slug: str, 
            min_repeat_len: int, min_participants: int) -> None:
    print(f"running with min_participants: {min_participants}\tmin_repeat_len: {min_repeat_len}")
    out = RESULTS_DIR
    sequences = build_sequences(events, game)
    corpus, spans = build_corpus(sequences)
    n_sessions = len(sequences)

    repeats = find_supermaximal_repeats(corpus, spans)
    repeats.to_csv(out / f"supermaximal_repeats_{slug}.csv", index=False)
    tactics = repeats[
        (repeats["length"] >= min_repeat_len) & (repeats["n_participants"] >= min_participants)
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
    print(f"Supermaximal repeats: {len(repeats)} total, {len(tactics)} at length>={min_repeat_len} "
          f"& n_participants>={min_participants} (of {n_sessions} sessions)")
    if len(tactics):
        print(tactics.head(10).to_string(index=False))
        print("Building blocks (bigrams shared across >=2 tactics):")
        print(blocks[blocks["n_tactics"] >= 2].to_string(index=False))
    print(f"RE-PAIR grammar: {len(grammar.rules)} rules")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-participants", type=int, default=3)
    parser.add_argument("--min-repeat-length", type=int, default=3)
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    events = load_events()

    run_for(events, BESTBUDS, "Best Buds vs Bad Guys", "bestbuds", 
            min_participants=args.min_participants, min_repeat_len=args.min_repeat_length)
    run_for(events, TOWNSCAPER, "Townscaper", "townscaper",
            min_participants=args.min_participants, min_repeat_len=args.min_repeat_length)

    print(f"\nOutputs written to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
