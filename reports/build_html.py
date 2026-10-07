#!/usr/bin/env python3
"""Generate reports/report.html from reports/report.md.

Usage:
    python3 reports/build_html.py

Renders report.md through Python-Markdown (tables + raw-HTML passthrough,
so the `<a id="...">` anchors already in the source just work), then
applies a handful of report-specific post-processing passes to recover
the visual components plain Markdown has no syntax for:

  - a paragraph opening with a **bold lead-in:** (this project's existing
    convention for a caveat/aside, e.g. "**Data cleaning applied:** ...")
    becomes an `aside.note` callout box
  - every `<table>` gets wrapped in a scrollable `.table-wrap` div
  - every image is embedded as base64 (resolved relative to reports/) and
    wrapped in a `<figure>` -- so the page stays a single self-contained
    file, publishable as a Claude Artifact with no external assets
  - the "Jump to:" list becomes the boxed section-navigation `<nav>`
  - "^ Back to top" links get the back-to-top paragraph styling
  - everything after the final `<hr>` becomes the page `<footer>`

Wrapped in the same CSS/typography shell (colors, fonts, light/dark
tokens) as the report has used throughout, so the visual language stays
consistent even though the page is now fully generated rather than
hand-maintained in parallel with report.md. Known, deliberate
simplification: the ornamental header eyebrow/dek/stat-row chrome and
report.md's `## N.`-numbered headings are not reproduced/stripped
specially -- headings render with their number inline, exactly as
written in the source.
"""

import base64
import re
from pathlib import Path

import markdown

REPORTS_DIR = Path(__file__).resolve().parent
ROOT = REPORTS_DIR.parent
SOURCE_MD = REPORTS_DIR / "report.md"
OUTPUT_HTML = REPORTS_DIR / "report.html"

CSS = """
  :root {
    --bg: #f4f6f5;
    --surface: #ffffff;
    --surface-2: #eef1ef;
    --ink: #16201e;
    --secondary: #435350;
    --muted: #7c8b87;
    --border: #dbe1de;
    --amber: #b3690f;
    --amber-fill: #b3690f;
    --teal: #009485;
    --teal-fill: #009485;
    --track: #e3e8e5;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg: #14191a;
      --surface: #1b2223;
      --surface-2: #212a2b;
      --ink: #e9ece9;
      --secondary: #b7c2be;
      --muted: #8b9995;
      --border: #2c3637;
      --amber: #d9a63c;
      --amber-fill: #ad7e28;
      --teal: #5cc2b0;
      --teal-fill: #3fa895;
      --track: #29322f;
    }
  }
  :root[data-theme="dark"] {
    --bg: #14191a;
    --surface: #1b2223;
    --surface-2: #212a2b;
    --ink: #e9ece9;
    --secondary: #b7c2be;
    --muted: #8b9995;
    --border: #2c3637;
    --amber: #d9a63c;
    --amber-fill: #ad7e28;
    --teal: #5cc2b0;
    --teal-fill: #3fa895;
    --track: #29322f;
  }

  * { box-sizing: border-box; }
  body {
    background: var(--bg);
    color: var(--ink);
    font-family: "Public Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
    line-height: 1.55;
    max-width: 780px;
    margin: 0 auto;
    padding: 3.5rem 1.5rem 6rem;
  }
  ::selection { background: color-mix(in srgb, var(--amber) 30%, transparent); }

  h1, h2, h3 { font-family: "Fraunces", Georgia, serif; text-wrap: balance; color: var(--ink); }
  h1 { font-size: clamp(2.1rem, 5vw, 2.9rem); font-weight: 600; margin: 0.3em 0 0.15em; letter-spacing: -0.01em; }
  h2 { font-size: 1.5rem; font-weight: 600; margin: 2.6em 0 0.9em; padding-top: 0.6em; border-top: 1px solid var(--border); }
  h3 { font-size: 1.12rem; font-weight: 600; margin: 1.8em 0 0.7em; color: var(--secondary); }
  p { max-width: 66ch; }
  a { color: var(--amber); text-decoration-color: color-mix(in srgb, var(--amber) 45%, transparent); text-underline-offset: 0.15em; }
  a:hover { text-decoration-thickness: 2px; }
  code { font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 0.88em; background: var(--surface-2); padding: 0.1em 0.4em; border-radius: 4px; }

  aside.note {
    background: var(--surface-2);
    border-left: 3px solid var(--amber);
    border-radius: 0 8px 8px 0;
    padding: 0.9rem 1.1rem;
    margin: 1.4rem 0;
    font-size: 0.92rem;
    color: var(--secondary);
  }
  aside.note strong { color: var(--ink); }
  aside.note p:first-child { margin-top: 0; }
  aside.note p:last-child { margin-bottom: 0; }

  figure { margin: 1.6rem 0 2.2rem; }
  figcaption { font-size: 0.85rem; color: var(--muted); margin-top: 0.6rem; max-width: 60ch; }
  .chart { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 0.6rem; overflow-x: auto; }
  .chart img { display: block; width: 100%; height: auto; border-radius: 6px; }

  table { width: 100%; border-collapse: collapse; font-size: 0.92rem; }
  .table-wrap { overflow-x: auto; margin: 1rem 0 1.8rem; }
  th, td { text-align: right; padding: 0.5em 0.7em; border-bottom: 1px solid var(--border); font-variant-numeric: tabular-nums; }
  th:first-child, td:first-child { text-align: left; font-variant-numeric: normal; }
  th { font-weight: 600; color: var(--secondary); font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.03em; }
  tbody tr:last-child td { border-bottom: none; }

  footer { margin-top: 3.5rem; padding-top: 1.2rem; border-top: 1px solid var(--border); font-size: 0.82rem; color: var(--muted); }
  footer a { color: var(--secondary); }
  .back-to-top { margin: 2.4em 0 0; font-size: 0.82rem; }
  .back-to-top a { color: var(--muted); }
  .jump-list { list-style: none; margin: 0.6em 0 0; padding: 0; }
  .jump-list li { margin: 0.3em 0; }
  .jump-list code { font-size: 0.85em; }
""".strip("\n")

PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Public+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
{css}
</style>
</head>
<body>
{body}
</body>
</html>
"""

# Bold lead-in ending in a colon or period, immediately followed by more
# text in the same paragraph -- e.g. "**Data cleaning applied:** the
# duplicate ..." or "**How to read the figure below.** Each strip ...".
# A bold line with *nothing* else in its paragraph (e.g. "**Jump to:**",
# which is its own paragraph followed by a list) is deliberately excluded.
_ASIDE_RE = re.compile(r"^\*\*[^*]+[:.]\*\*\s+\S", re.MULTILINE)


def wrap_asides(md_text: str) -> str:
    blocks = md_text.split("\n\n")
    out = []
    for block in blocks:
        if _ASIDE_RE.match(block):
            out.append(f'<aside class="note" markdown="1">\n\n{block}\n\n</aside>')
        else:
            out.append(block)
    return "\n\n".join(out)


def embed_images(html: str) -> str:
    def repl(match: "re.Match[str]") -> str:
        full_img_tag, alt, src = match.group(0), match.group("alt"), match.group("src")
        if src.startswith("http://") or src.startswith("https://") or src.startswith("data:"):
            return f'<figure><div class="chart">{full_img_tag}</div></figure>'
        img_path = (REPORTS_DIR / src).resolve()
        data = img_path.read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        new_img = f'<img src="data:image/png;base64,{b64}" alt="{alt}">'
        return f'<figure><div class="chart">{new_img}</div></figure>'

    # Python-Markdown emits a standalone image line as <p><img .../></p>;
    # swallow the wrapping <p> along with it.
    pattern = re.compile(
        r'<p><img alt="(?P<alt>[^"]*)" src="(?P<src>[^"]+)"\s*/?></p>'
    )
    return pattern.sub(repl, html)


def wrap_tables(html: str) -> str:
    return re.sub(r"(<table>.*?</table>)", r'<div class="table-wrap">\1</div>', html, flags=re.DOTALL)


def wrap_jump_nav(html: str) -> str:
    pattern = re.compile(r"<p><strong>Jump to:</strong></p>\s*<ul>(.*?)</ul>", re.DOTALL)

    def repl(match: "re.Match[str]") -> str:
        items = match.group(1)
        return (
            '<nav aria-label="Section navigation" style="font-size:0.85rem;color:var(--secondary);'
            'margin:0 0 1.5rem;padding:0.8rem 1rem;background:var(--surface);border:1px solid '
            'var(--border);border-radius:8px;">\n'
            '  <strong style="color:var(--ink);">Jump to:</strong>\n'
            f'  <ul class="jump-list">{items}</ul>\n'
            "</nav>"
        )

    return pattern.sub(repl, html)


def style_back_to_top(html: str) -> str:
    return html.replace(
        '<p><a href="#top">',
        '<p class="back-to-top"><a href="#top">',
    )


def merge_anchor_ids(html: str) -> str:
    """report.md marks each section with a standalone `<a id="...">` right
    before its heading (or, for #top, right before the H1). Markdown wraps
    that lone anchor in its own empty <p>; move the id onto the heading
    itself instead (or drop it if nothing follows, e.g. a trailing one)."""
    pattern = re.compile(r'<p><a id="([^"]+)"></a></p>\s*<(h[1-3])>')
    return pattern.sub(lambda m: f'<{m.group(2)} id="{m.group(1)}">', html)


def wrap_footer(html: str) -> str:
    last_hr = max(html.rfind("<hr />"), html.rfind("<hr>"))
    if last_hr == -1:
        return html
    hr_end = html.index(">", last_hr) + 1
    return html[:last_hr] + "<footer>" + html[hr_end:] + "</footer>"


def extract_title(md_text: str) -> str:
    match = re.search(r"^#\s+(.+)$", md_text, re.MULTILINE)
    return match.group(1).strip() if match else "Report"


def build() -> None:
    md_text = SOURCE_MD.read_text()
    title = extract_title(md_text)

    md_text = wrap_asides(md_text)
    body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists", "md_in_html"],
    )

    body = embed_images(body)
    body = wrap_tables(body)
    body = wrap_jump_nav(body)
    body = style_back_to_top(body)
    body = merge_anchor_ids(body)
    body = wrap_footer(body)

    page = PAGE_TEMPLATE.format(title=title, css=CSS, body=body)
    OUTPUT_HTML.write_text(page)
    print(f"Wrote {OUTPUT_HTML} ({len(page):,} bytes)")


if __name__ == "__main__":
    build()
