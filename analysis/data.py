"""Shared loader for the search-process annotation TSVs.

Kept separate from any single RQ script since RQ2-RQ5 all start from the
same tidy event table.
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "search_process"

NON_SEARCH_ACTIONS = {"Experiment ended"}


def _repair_rank_column(df: pd.DataFrame, source: Path) -> pd.DataFrame:
    """Replace `rank` with 1-indexed row position if it contains spreadsheet
    error values (e.g. `#REF!`, seen in ID12 after a row was deleted upstream).

    Verified equivalence: in every file checked, `rank` already equals the
    row's position among that file's data rows, so falling back to row
    position for a broken file is a like-for-like repair, not a guess.
    """
    numeric = pd.to_numeric(df["rank"], errors="coerce")
    if numeric.isna().any():
        n_bad = int(numeric.isna().sum())
        print(f"[data] {source.name}: repaired {n_bad} non-numeric `rank` value(s) using row position")
        return df.assign(rank=range(1, len(df) + 1))
    return df.assign(rank=numeric.astype(int))


def load_raw_events(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Concatenate all per-participant TSVs into one long event table."""
    files = sorted(data_dir.glob("search_process_annotations-participant_*.tsv"))
    if not files:
        raise FileNotFoundError(f"No annotation files found in {data_dir}")

    frames = [_repair_rank_column(pd.read_csv(f, sep="\t", dtype=str), f) for f in files]
    events = pd.concat(frames, ignore_index=True)
    events["rank"] = events["rank"].astype(int)
    if "action_details_num_tokens" in events.columns:
        events["action_details_num_tokens"] = pd.to_numeric(
            events["action_details_num_tokens"], errors="coerce"
        )
    return events


def dedupe_experiment_ended(events: pd.DataFrame) -> pd.DataFrame:
    """Keep only the last `Experiment ended` row per (participant, game).

    Some sessions have more than one `Experiment ended` row for the same
    game due to an annotation slip; per the researcher's rule, all but the
    last such row should be dropped.
    """
    is_end = events["action"] == "Experiment ended"
    end_events = events[is_end]
    last_end_idx = (
        end_events.groupby(["participant_id", "game"])["rank"].idxmax()
    )
    drop_idx = end_events.index.difference(last_end_idx)
    return events.drop(index=drop_idx).reset_index(drop=True)


def truncate_after_experiment_ended(events: pd.DataFrame) -> pd.DataFrame:
    """Drop any rows recorded after `Experiment ended` within a (participant,
    game) session.

    `Experiment ended` is meant to be a terminal marker (see
    dedupe_experiment_ended), but at least one session
    (ID10, Townscaper) has an action annotated after it — likely a stray
    post-task event (e.g. closing the app). Since this breaks the
    absorbing-end-state assumption used for the RQ2 transition analysis,
    anything after the marker is dropped.
    """
    end_rank = (
        events[events["action"] == "Experiment ended"]
        .groupby(["participant_id", "game"])["rank"]
        .min()
        .rename("end_rank")
    )
    events = events.merge(end_rank, on=["participant_id", "game"], how="left")
    keep = events["end_rank"].isna() | (events["rank"] <= events["end_rank"])
    return events[keep].drop(columns="end_rank").reset_index(drop=True)


def add_session_step(events: pd.DataFrame) -> pd.DataFrame:
    """Add a contiguous `step` (1..N) per (participant, game) after cleanup,
    since dropping duplicate `Experiment ended` rows can leave gaps in `rank`.
    """
    events = events.sort_values(["participant_id", "game", "rank"]).copy()
    events["step"] = (
        events.groupby(["participant_id", "game"]).cumcount() + 1
    )
    return events


def add_platform_context(events: pd.DataFrame) -> pd.DataFrame:
    """Add a `context` column: which platform/website an action happens on.

    Not directly annotated -- reconstructed under one assumption (the
    researcher confirmed this is safe from looking at the raw annotation
    files): most actions happen in the context of the most recent
    `Platform switch` destination. `View single result` is the exception --
    it's the action where the participant lands on a *different* site than
    the platform they switched to, so its context is its own
    `action_details_clean` value rather than the inherited platform.

    Concretely: `Platform switch` rows seed the context with their own
    destination; every row up to (but not including) the next
    `Platform switch` in the same (participant, game) session inherits that
    value by forward-fill; `View single result` rows override the inherited
    value with their own `action_details_clean`. Rows before the first
    `Platform switch` in a session (rare -- almost every session opens with
    one) get a missing context rather than a guess.
    """
    events = events.sort_values(["participant_id", "game", "step"]).copy()
    is_switch = events["action"] == "Platform switch"
    is_view_single = events["action"] == "View single result"

    events["_platform_seed"] = events["action_details_clean"].where(is_switch)
    events["context"] = events.groupby(["participant_id", "game"])["_platform_seed"].ffill()
    events.loc[is_view_single, "context"] = events.loc[is_view_single, "action_details_clean"]
    return events.drop(columns="_platform_seed")


def load_events(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Full pipeline: load, fix duplicate end-markers, add contiguous step,
    add the reconstructed `context` (platform/website) column."""
    events = load_raw_events(data_dir)
    events = dedupe_experiment_ended(events)
    events = truncate_after_experiment_ended(events)
    events = add_session_step(events)
    events = add_platform_context(events)
    return events


if __name__ == "__main__":
    df = load_events()
    print(df.shape)
    print(df.head(10))
