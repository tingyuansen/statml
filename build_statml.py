#!/usr/bin/env python3
"""Build the Statistical Machine Learning for Astronomy reader.

Renders, into docs/, a client-side reader (see docs/reader.html) that shows each
textbook chapter alongside its hands-on tutorial(s):

  * chapters  — LaTeX (kept privately in SOURCE) -> HTML via pandoc; math stays
                raw for KaTeX, citations resolved via citeproc, figures converted
                from PDF to PNG.
  * tutorials — executed Jupyter notebooks -> slim JSON (markdown + code + outputs)
                so every plot shows in the rendered page.

Run:  python3 build_statml.py            (chapters + tutorials + manifest)
      python3 build_statml.py --figures  (also re-convert figures, slow)
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString

ROOT = Path(__file__).parent.resolve()
DOCS = ROOT / "docs"
CONTENT = DOCS / "content"
FIGURES = DOCS / "figures"
SOURCE = Path.home() / "Source_Files_Not_For_Review"   # private LaTeX sources

AUTHOR = "Yuan-Sen Ting"
AFFIL = "The Ohio State University"

# Chapter number -> (title, [tutorial keys]). Tutorial files are
# tutorial_chapter_<key>.ipynb in the repo root.
CHAPTERS = {
    1:  ("Preface and Overview", []),
    2:  ("Bayesian Inference", ["2a", "2b"]),
    3:  ("Statistical Foundations and Summary Statistics", ["3"]),
    4:  ("Linear Regression", ["4a", "4b"]),
    5:  ("Bayesian Linear Regression", ["5"]),
    6:  ("Linear Regression with Input Uncertainties", ["6"]),
    7:  ("Classification and Logistic Regression", ["7"]),
    8:  ("Multi-Class Classification", ["8"]),
    9:  ("Bayesian Logistic Regression", ["9"]),
    10: ("Principal Component Analysis", ["10"]),
    11: ("K-means and Gaussian Mixture Models", ["11a", "11b"]),
    12: ("Sampling and Monte Carlo Methods", ["12"]),
    13: ("Markov Chain Monte Carlo", ["13"]),
    14: ("Gaussian Processes", ["14a", "14b"]),
    15: ("Neural Networks", ["15a", "15b", "15c", "15d"]),
    16: ("Afterword: A Personal Note", []),
}

# Thematic parts (chapter numbers).
PARTS = [
    ("Part I",   "Foundations",          "Probability, Bayesian inference, and the statistics that underpin everything that follows.", [1, 2, 3]),
    ("Part II",  "Regression",           "Linear models from least squares to fully Bayesian treatments, including input uncertainties.", [4, 5, 6]),
    ("Part III", "Classification",       "Logistic regression, multi-class methods, and their Bayesian extensions.", [7, 8, 9]),
    ("Part IV",  "Unsupervised Learning", "Dimensionality reduction and clustering: PCA, K-means, and Gaussian mixtures.", [10, 11]),
    ("Part V",   "Inference at Scale",   "Monte Carlo sampling and Markov chain Monte Carlo for posteriors you cannot write down.", [12, 13]),
    ("Part VI",  "Modern Methods",       "Gaussian processes and neural networks for flexible, expressive modeling.", [14, 15, 16]),
]


# ----------------------------------------------------------------- figures ----
def convert_figures() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(SOURCE.glob("Chapter_*_Fig*.pdf"))
    for pdf in pdfs:
        out = FIGURES / pdf.stem
        subprocess.run(
            ["pdftoppm", "-png", "-r", "200", "-singlefile", str(pdf), str(out)],
            check=False, capture_output=True,
        )
    print(f"  figures: {len(pdfs)} converted")


# ---------------------------------------------------------------- chapters ----
_FIG_RE = re.compile(r'<embed\s+src="(Chapter_\d+_Fig\d+)\.pdf"([^>]*?)\s*/?\s*>')


def _fix_figures(html: str) -> str:
    def sub(m: re.Match) -> str:
        name, rest = m.group(1), m.group(2).strip()
        rest = (" " + rest) if rest else ""
        return f'<img src="figures/{name}.png"{rest} alt="{name}" loading="lazy">'
    return _FIG_RE.sub(sub, html)


def _number_figures(html: str, chapter: int) -> str:
    """Number figures N.1, N.2, ... within the chapter: label captions and
    rewrite cross-reference links to the same numbers."""
    soup = BeautifulSoup(html, "html.parser")
    id_to_num: dict[str, str] = {}
    for i, fig in enumerate(soup.find_all("figure"), 1):
        num = f"{chapter}.{i}"
        fid = fig.get("id")
        if fid:
            id_to_num[fid] = num
        cap = fig.find("figcaption")
        if cap is not None:
            strong = soup.new_tag("strong")
            strong.string = f"Figure {num}. "
            cap.insert(0, strong)
    for a in soup.find_all("a", attrs={"data-reference-type": "ref"}):
        num = id_to_num.get(a.get("data-reference", ""))
        if num:
            a.string = num
    return str(soup)


def _strip_first_h1(html: str) -> str:
    return re.sub(r"<h1\b[^>]*>.*?</h1>\s*", "", html, count=1, flags=re.DOTALL)


def _strip_trailing_colon(h) -> None:
    """Remove a trailing ':' from a heading (preserving inner math/markup)."""
    texts = [t for t in h.descendants if isinstance(t, NavigableString)]
    if not texts:
        return
    last = texts[-1]
    s = str(last).rstrip()
    if s.endswith(":"):
        last.replace_with(NavigableString(s[:-1]))


def _normalize_headings(html: str) -> str:
    """Make the heading hierarchy sensible for the web.

    Pandoc maps \\section->h2, \\subsection->h3, \\subsubsection->h4,
    \\paragraph->h5. The book uses \\paragraph as a lightweight section divider
    (to keep the printed table of contents short). On the web we promote them:
      * directly under a \\section            -> h3 (a subsection)
      * nested under a real \\subsection      -> h4 (kept below it)
      * in the Preface (no \\section at all)  -> h2 (top-level sections)
    "Further Readings" becomes its own section (h2), and trailing colons left
    over from run-in \\paragraph titles are dropped."""
    soup = BeautifulSoup(html, "html.parser")
    heads = soup.find_all(re.compile(r"^h[1-6]$"))
    has_section = any(h.name == "h2" for h in heads)   # h2 == \section
    in_subsection = False
    for h in heads:
        further = bool(re.match(r"\s*further reading", h.get_text(), re.I))
        if h.name == "h2":
            in_subsection = False
        elif h.name == "h3":          # a real \subsection
            in_subsection = True
        elif h.name == "h5":          # \paragraph
            if further or not has_section:
                h.name = "h2"
            elif in_subsection:
                h.name = "h4"
            else:
                h.name = "h3"
        elif h.name == "h6":          # \subparagraph (rare)
            h.name = "h4" if has_section else "h3"
        _strip_trailing_colon(h)
    return str(soup)


# Small text fixes for gaps in the source LaTeX (not edited there since the
# sources are private). Keyed by chapter number.
CHAPTER_FIXES: dict[int, list[tuple[str, str]]] = {
    10: [("shown in Figure to solidify our understanding",
          "shown in the figure below to solidify our understanding")],
}


def _fix_math(html: str) -> str:
    """Normalize display-math environments to KaTeX's non-numbered forms.

    Pandoc wraps amsmath environments inside \\[ … \\]. KaTeX auto-numbers
    equation/align/gather, which (a) draws an equation tag that forces a
    full-width layout (showing a stray rule/scrollbar under the equation) and
    (b) uses its own running counter that does not match the book. We don't
    number equations on the web, so unwrap/convert everything to the plain,
    un-numbered variants. eqnarray and split are unsupported by KaTeX outright."""
    repl = {
        r"\begin{equation*}": "", r"\end{equation*}": "",
        r"\begin{equation}": "",  r"\end{equation}": "",
        r"\begin{align*}": r"\begin{aligned}",   r"\end{align*}": r"\end{aligned}",
        r"\begin{align}": r"\begin{aligned}",     r"\end{align}": r"\end{aligned}",
        r"\begin{eqnarray*}": r"\begin{aligned}", r"\end{eqnarray*}": r"\end{aligned}",
        r"\begin{eqnarray}": r"\begin{aligned}",  r"\end{eqnarray}": r"\end{aligned}",
        r"\begin{gather*}": r"\begin{gathered}",  r"\end{gather*}": r"\end{gathered}",
        r"\begin{gather}": r"\begin{gathered}",   r"\end{gather}": r"\end{gathered}",
        r"\begin{split}": r"\begin{aligned}",     r"\end{split}": r"\end{aligned}",
    }
    for a, b in repl.items():
        html = html.replace(a, b)
    html = re.sub(r"&\s*=\s*&", r"&=", html)        # eqnarray centred &=&
    html = re.sub(r"\\label\{[^}]*\}", "", html)    # KaTeX errors on \label
    return html


def _add_references_heading(html: str) -> str:
    """citeproc emits the bibliography as a bare div; give it a heading."""
    return html.replace(
        '<div class="references', '<h2>References</h2>\n<div class="references', 1
    )


def convert_chapter(num: int) -> str:
    tex = SOURCE / f"Chapter{num}.tex"
    res = subprocess.run(
        ["pandoc", str(tex), "-f", "latex", "-t", "html5",
         "--mathjax", "--citeproc",
         "--bibliography", "Textbook.bib",
         "--bibliography", str(ROOT / "refs_supplement.bib")],
        cwd=str(SOURCE), capture_output=True, text=True,
    )
    if res.returncode != 0:
        print(f"  !! pandoc failed on Chapter{num}: {res.stderr[:200]}")
    html = res.stdout
    for old, new in CHAPTER_FIXES.get(num, []):
        html = html.replace(old, new)
    html = _fix_figures(html)
    html = _fix_math(html)
    html = _number_figures(html, num)
    html = _strip_first_h1(html)
    html = _normalize_headings(html)
    html = _add_references_heading(html)
    return html.strip()


# --------------------------------------------------------------- tutorials ----
def _join(s) -> str:
    return "".join(s) if isinstance(s, list) else (s or "")


def _slim_outputs(outputs: list) -> list:
    out = []
    for o in outputs or []:
        t = o.get("output_type")
        if t == "stream":
            out.append({"output_type": "stream", "name": o.get("name", "stdout"),
                        "text": _join(o.get("text"))})
        elif t == "error":
            out.append({"output_type": "error", "ename": o.get("ename", ""),
                        "evalue": o.get("evalue", ""), "traceback": o.get("traceback", [])})
        elif t in ("execute_result", "display_data"):
            data = o.get("data", {})
            keep = {}
            for k in ("image/png", "image/jpeg", "image/svg+xml", "text/html", "text/plain"):
                if k in data:
                    keep[k] = data[k]
            if keep:
                out.append({"output_type": t, "data": keep, "metadata": {}})
    # merge consecutive same-name streams
    merged = []
    for o in out:
        if (o["output_type"] == "stream" and merged
                and merged[-1].get("output_type") == "stream"
                and merged[-1]["name"] == o["name"]):
            merged[-1]["text"] += o["text"]
        else:
            merged.append(o)
    return merged


def _clean_intro(md: str) -> tuple[str, str | None]:
    """Pull the descriptive title from the first H1 and drop the boilerplate
    preamble (author line, companion note, citation link, copyright) — every
    tutorial opens with a run of italic-only lines before its Introduction."""
    m = re.match(r"\s*#\s+(.+)", md)
    title = m.group(1).lstrip("# ").strip() if m else None
    md = re.sub(r"^\s*#\s+.+\n", "", md, count=1)
    lines = md.split("\n")
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if s == "" or (s.startswith("*") and s.endswith("*") and len(s) > 2):
            i += 1
        else:
            break
    return "\n".join(lines[i:]).strip(), title


def convert_tutorial(key: str) -> tuple[dict, str | None]:
    nb = json.loads((ROOT / f"tutorial_chapter_{key}.ipynb").read_text(encoding="utf-8"))
    cells = []
    title = None
    first_md = True
    for c in nb.get("cells", []):
        ct = c.get("cell_type")
        if ct == "markdown":
            src = _join(c.get("source"))
            if first_md:
                src, title = _clean_intro(src)
                first_md = False
                if not src:
                    continue
            cells.append({"cell_type": "markdown", "source": src})
        elif ct == "code":
            src = _join(c.get("source"))
            outs = _slim_outputs(c.get("outputs"))
            if not src.strip() and not outs:
                continue
            cells.append({"cell_type": "code", "source": src,
                          "execution_count": c.get("execution_count"), "outputs": outs})
    return {"cells": cells}, title


# --------------------------------------------------------------- book-data ----
def build_book_data(tut_titles: dict[str, str]) -> str:
    # reading order: chapter then its tutorials, interleaved
    flat_n = 0
    parts_js = []
    for pname, ptitle, blurb, chap_nums in PARTS:
        chapters = []
        for cn in chap_nums:
            title, tut_keys = CHAPTERS[cn]
            flat_n += 1
            entry = {
                "n": flat_n, "chapter": cn, "type": "chapter",
                "slug": f"chapter{cn:02d}", "title": title,
                "lecturer": AUTHOR, "affil": AFFIL,
                "tutorials": [],
            }
            for k in tut_keys:
                flat_n += 1
                short = f"Tutorial {cn}" if len(tut_keys) == 1 else f"Tutorial {cn}{k[-1]}"
                entry["tutorials"].append({
                    "n": flat_n, "chapter": cn, "type": "tutorial",
                    "slug": f"tutorial_chapter_{k}",
                    "title": tut_titles.get(k) or short, "short": short, "parent": title,
                })
            chapters.append(entry)
        parts_js.append({"name": pname, "title": ptitle, "blurb": blurb, "chapters": chapters})

    book = {
        "title": "Statistical Machine Learning for Astronomy",
        "series": "A Bayesian, uncertainty-aware course with hands-on astronomy tutorials",
        "parts": parts_js,
    }
    body = json.dumps(book, indent=2, ensure_ascii=False)
    return (
        "/* Course manifest — generated by build_statml.py, do not edit by hand. */\n"
        f"window.BOOK = {body};\n\n"
        "// Flatten chapters + their tutorials into one reading order.\n"
        "window.BOOK.flat = [];\n"
        "for (const p of window.BOOK.parts) for (const c of p.chapters) {\n"
        "  window.BOOK.flat.push({ ...c, part: p });\n"
        "  for (const t of c.tutorials) window.BOOK.flat.push({ ...t, part: p });\n"
        "}\n"
        "window.BOOK.byN = Object.fromEntries(window.BOOK.flat.map(c => [c.n, c]));\n"
        "window.BOOK.bySlug = Object.fromEntries(window.BOOK.flat.map(c => [c.slug, c]));\n"
    )


# --------------------------------------------------------------------- main ---
def main() -> None:
    CONTENT.mkdir(parents=True, exist_ok=True)
    if "--figures" in sys.argv:
        convert_figures()

    tut_titles: dict[str, str] = {}
    for num, (title, tut_keys) in CHAPTERS.items():
        html = convert_chapter(num)
        (CONTENT / f"chapter{num:02d}.json").write_text(
            json.dumps({"cells": [{"cell_type": "markdown_html", "html": html}]}, ensure_ascii=False),
            encoding="utf-8")
        for k in tut_keys:
            nb, ttitle = convert_tutorial(k)
            if ttitle:
                tut_titles[k] = ttitle
            (CONTENT / f"tutorial_chapter_{k}.json").write_text(
                json.dumps(nb, ensure_ascii=False), encoding="utf-8")
        kb = (CONTENT / f"chapter{num:02d}.json").stat().st_size // 1024
        print(f"  Chapter {num:>2}: {title[:38]:38} ({kb} KB, {len(tut_keys)} tut: "
              + ", ".join(tut_titles.get(k, k)[:18] for k in tut_keys) + ")")

    (DOCS / "assets" / "book-data.js").write_text(build_book_data(tut_titles), encoding="utf-8")
    print("Wrote chapters, tutorials, and book-data.js")


if __name__ == "__main__":
    main()
