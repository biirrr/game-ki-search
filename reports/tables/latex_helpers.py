"""Shared LaTeX table writer used by every reports/tables/rqN.py module.

Produces one standalone booktabs table.tex per call (\\begin{table}...
\\caption{}...\\label{}...\\end{table}, ready for \\input{}), so paper source
can pull in a table by label without hand-copying numbers out of
reports/report.md.
"""

from pathlib import Path

import pandas as pd

TABLE_TEMPLATE = """\\begin{{table}}[t]
\\centering
\\caption{{{caption}}}
\\label{{{label}}}
{tabular}\\end{{table}}
"""


def default_column_format(df: pd.DataFrame) -> str:
    """First column left-aligned, the rest right-aligned -- matches this
    project's markdown table convention (`|---|---:|---:|...`)."""
    return "l" + "r" * (len(df.columns) - 1)


def write_table(
    df: pd.DataFrame,
    out_path: Path,
    caption: str,
    label: str,
    column_format: str | None = None,
) -> None:
    """Render `df` as a standalone booktabs table.tex at `out_path`.

    All cell values should already be formatted as display strings (e.g.
    "27.6%", "0.003") by the caller -- this function only lays the table
    out, it doesn't round or format numbers. Special LaTeX characters
    (e.g. the literal "%" in "27.6%") are escaped automatically -- callers
    should pass plain, unescaped display strings.
    """
    tabular = df.to_latex(
        index=False,
        escape=True,
        column_format=column_format or default_column_format(df),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(TABLE_TEMPLATE.format(caption=caption, label=label, tabular=tabular))
