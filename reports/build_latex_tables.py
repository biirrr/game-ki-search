#!/usr/bin/env python3
"""Generate reports/tables/*.tex from the results/rqN_*/*.csv analysis outputs.

Usage:
    python3 reports/build_latex_tables.py

The LaTeX counterpart of reports/build_html.py: reads the same per-RQ
results/ CSVs the markdown report's tables are built from (recomputing a
handful of derived statistics -- e.g. Mann-Whitney p-values, cluster
aggregates -- the same way the analysis/rqN_*.py scripts do, rather than
transcribing numbers out of reports/report.md), and writes one standalone
booktabs `\\begin{table}...\\end{table}` per table to reports/tables/,
ready for `\\input{}` in the paper. Re-run this (after `make rq-all`) any
time the underlying data changes.

Only tables that already appear in reports/report.md are covered here;
see each reports/tables/rqN.py module for the report.md section it
mirrors. Arrows are written as plain "->" and comparisons as "<=" rather
than unicode glyphs, so the output doesn't depend on a unicode-capable
LaTeX engine.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_ROOT = ROOT / "results"
OUT_DIR = ROOT / "reports" / "tables"

sys.path.insert(0, str(ROOT / "analysis"))
sys.path.insert(0, str(OUT_DIR))

import rq1  # noqa: E402
import rq2  # noqa: E402
import rq3  # noqa: E402
import rq4  # noqa: E402
import rq5  # noqa: E402
import rq6  # noqa: E402
import rq7  # noqa: E402
import rq8  # noqa: E402
import rq10  # noqa: E402
import rq11  # noqa: E402
import rq13  # noqa: E402

MODULES = [rq1, rq2, rq3, rq4, rq5, rq6, rq7, rq8, rq10, rq11, rq13]


def build() -> None:
    written = []
    for module in MODULES:
        written.extend(module.build(RESULTS_ROOT, OUT_DIR))

    for path in written:
        print(f"Wrote {path.relative_to(ROOT)}")
    print(f"\n{len(written)} tables written to {OUT_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    build()
