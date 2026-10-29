#!/usr/bin/env python3
"""Build the Statistical Machine Learning for Astronomy reader.

Renders, into docs/, a client-side reader (see docs/reader.html) that shows each
textbook chapter alongside its hands-on tutorial(s):

  * chapters  — LaTeX (kept privately in SOURCE) -> HTML via pandoc; math stays
                raw for KaTeX. Section, figure and table numbers and every
                cross-reference come from a draft LaTeX run, so they match the
                printed book. Each Further Reading is followed by its entries of
                the book's bibliography. Figures are converted from PDF to PNG.
  * tutorials — executed Jupyter notebooks -> slim JSON (markdown + code + outputs)
                so every plot shows in the rendered page.

Run:  python3 build_statml.py            (chapters + tutorials + manifest)
      python3 build_statml.py --figures  (also re-convert figures, slow)
"""
from __future__ import annotations

import json
import re
import struct
import subprocess
import sys
import tempfile
import unicodedata
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
# tutorials/tutorial_chapter_<key>.ipynb.
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
    13: ("Markov Chain Monte Carlo", ["13a", "13b"]),
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


def reading_order() -> dict[int, int]:
    """Chapter number -> its page n in the reader (each chapter is followed by
    its tutorials, as in build_book_data)."""
    n, pages = 0, {}
    for *_, chap_nums in PARTS:
        for cn in chap_nums:
            n += 1
            pages[cn] = n
            n += len(CHAPTERS[cn][1])
    return pages


# ----------------------------------------------------------------- figures ----
def convert_figures() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(SOURCE.glob("Chapter_*_Fig*.pdf"))
    for pdf in pdfs:
        out = FIGURES / pdf.stem
        subprocess.run(
            ["pdftoppm", "-png", "-r", "300", "-singlefile", str(pdf), str(out)],
            check=False, capture_output=True,
        )
    stale = [p for p in FIGURES.glob("*.png") if not (SOURCE / f"{p.stem}.pdf").exists()]
    for p in stale:
        p.unlink()
    print(f"  figures: {len(pdfs)} converted, {len(stale)} stale removed")


# ------------------------------------------------------------------ labels ----
def book_labels() -> dict[str, tuple[int, str]]:
    """Every \\label of the book -> (chapter, printed number), read from the .aux
    files of one draft LaTeX run (written to a temporary folder, so SOURCE stays
    clean)."""
    labels: dict[str, tuple[int, str]] = {}
    with tempfile.TemporaryDirectory() as tmp:
        res = subprocess.run(
            ["pdflatex", "-interaction=batchmode", "-draftmode",
             f"-output-directory={tmp}", "Textbook.tex"],
            cwd=str(SOURCE), capture_output=True,
        )
        if res.returncode != 0:
            print("  !! LaTeX reported errors; check the book builds (RUNBOOK, section 3)")
        for num in CHAPTERS:
            aux = Path(tmp) / f"Chapter{num}.aux"
            if not aux.exists():
                sys.exit(f"!! LaTeX run gave no {aux.name}; is pdflatex installed?")
            text = aux.read_text(encoding="utf-8", errors="replace")
            for key, val in re.findall(r"\\newlabel\{([^}]+)\}\{\{([^}]*)\}", text):
                labels[key] = (num, val)
    print(f"  labels: {len(labels)} read from LaTeX")
    return labels


# ------------------------------------------------------------ bibliography ----
def _fold(s: str) -> str:
    """LaTeX or Unicode text -> lower-case ASCII, for matching author names."""
    s = re.sub(r"\\natexlab\{(\w)\}", r"\1", s)
    s = re.sub(r"\\[`'^\"~=.cvuHk]\s*\{?(\w)\}?", r"\1", s)   # \"u, \c{c}, \~n
    s = s.replace("~", " ").replace("\\ ", " ")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[{}]", "", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def book_bibliography() -> tuple[dict[str, tuple[str, str]], dict[str, str]]:
    """The printed bibliography (Textbook_refs.tex, in its order): key -> the
    citation as the text writes it, (author, year), and key -> HTML entry."""
    tex = (SOURCE / "Textbook_refs.tex").read_text(encoding="utf-8")
    tex = tex.split(r"\end{thebibliography}")[0]
    parts = re.split(r"\\bibitem\[((?:[^\[\]{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\]\{([^}]+)\}", tex)
    cites: dict[str, tuple[str, str]] = {}
    src = []
    for label, key, body in zip(parts[1::3], parts[2::3], parts[3::3]):
        m = re.match(r"(.*?)\((\d{4}(?:\{\\natexlab\{\w\}\})?)\)", label)
        cites[key] = (_fold(m.group(1)), _fold(m.group(2)))
        body = re.sub(r"\{\\natexlab\{(\w)\}\}", r"\1", body)
        body = re.sub(r"\\penalty0\s*", "", body.replace(r"\newblock", " "))   # '5(2):53', as printed
        src.append(f"BIBKEY{key}BIBKEY\n\n{body.strip()}\n")
    res = subprocess.run(["pandoc", "-f", "latex", "-t", "html5"],
                         input="\n".join(src), capture_output=True, text=True)
    chunks = re.split(r"<p>BIBKEY(.+?)BIBKEY</p>", res.stdout)
    entries = {k: re.sub(r"^\s*<p>|</p>\s*$", "", h.strip())
               for k, h in zip(chunks[1::2], chunks[2::2])}
    print(f"  bibliography: {len(entries)} entries")
    return cites, entries


def chapter_references(num: int, cites: dict, entries: dict) -> str:
    """The works the chapter's Further Reading names, as a References list."""
    tex = (SOURCE / f"Chapter{num}.tex").read_text(encoding="utf-8")
    m = re.search(r"\\paragraph\{Further Reading\}(.*?)(?=\\paragraph\{|\\section|\Z)", tex, re.S)
    if not m:
        return ""
    text = _fold(m.group(1))
    found = []
    for key, (who, year) in cites.items():
        pat = r"(?<![\w-])" + re.escape(who) + r" \((?:\d{4}\w?, )*" + re.escape(year) + r"[,)]"
        found += [(f.start(), f.end(), key) for f in re.finditer(pat, text)]
    # 'Skilling (2006)' inside 'Sivia and Skilling (2006)' is not a citation
    cited = {k for s, e, k in found if not any(s2 < s and e2 >= e for s2, e2, _ in found)}
    items = "\n".join(f'<div class="csl-entry" id="ref-{k}" role="listitem">{entries[k]}</div>'
                      for k in cites if k in cited)
    return ('<h2>References</h2>\n<div class="references csl-bib-body hanging-indent" role="list">\n'
            f"{items}\n</div>")


# ---------------------------------------------------------------- chapters ----
_FIG_RE = re.compile(r'<embed\s+src="(Chapter_\d+_Fig\d+)\.pdf"([^>]*?)\s*/?\s*>')


def _fix_figures(html: str) -> str:
    """PDF embeds -> PNG images. The PNG's pixel size goes in width/height so the
    browser reserves each figure's space before it loads, and a link to a label
    lands on its target."""
    def sub(m: re.Match) -> str:
        name, rest = m.group(1), m.group(2).strip()
        rest = (" " + rest) if rest else ""
        png = FIGURES / f"{name}.png"
        if png.exists():
            with png.open("rb") as f:
                w, h = struct.unpack(">II", f.read(24)[16:24])
            rest += f' width="{w}" height="{h}"'
        return f'<img src="figures/{name}.png"{rest} loading="lazy">'
    return _FIG_RE.sub(sub, html)


def _number_floats(html: str, chapter: int, labels: dict) -> str:
    """Label figure and table captions with the book's numbers ('Figure 2.3.'),
    which are also the alt text of the figure images."""
    soup = BeautifulSoup(html, "html.parser")
    for kind, tag, cap_tag in (("Figure", "figure", "figcaption"), ("Table", "table", "caption")):
        for i, el in enumerate(soup.find_all(tag), 1):
            fid = el.get("id") or (el.parent.get("id") if el.parent else None)
            num = labels.get(fid, (chapter, f"{chapter}.{i}"))[1]
            for img in el.find_all("img"):
                img["alt"] = f"{kind} {num}"
            cap = el.find(cap_tag)
            if cap is not None:
                strong = soup.new_tag("strong")
                strong.string = f"{kind} {num}. "
                cap.insert(0, strong)
    return str(soup)


def _number_sections(html: str, chapter: int, labels: dict) -> str:
    """Prefix \\section (h2) and \\subsection (h3) headings with the book's
    numbers N.k and N.k.j, which the text cites ('Section 2.5.1'). Run before
    _normalize_headings; labelled headings are checked against LaTeX."""
    soup = BeautifulSoup(html, "html.parser")
    sec = sub = 0
    for h in soup.find_all(["h2", "h3"]):
        if h.name == "h2":
            sec, sub = sec + 1, 0
            num = f"{chapter}.{sec}"
        else:
            sub += 1
            num = f"{chapter}.{sec}.{sub}"
        want = labels.get(h.get("id", ""), (chapter, num))[1]
        if want != num:
            print(f"  !! Chapter {chapter}: heading {h.get('id')} is {num} here, {want} in the book")
        span = soup.new_tag("span", attrs={"class": "secnum"})
        span.string = num
        h.insert(0, " ")
        h.insert(0, span)
    return str(soup)


def _resolve_refs(html: str, chapter: int, labels: dict, pages: dict) -> str:
    """Give each \\ref its printed number and link it to its target, in this
    chapter (#label) or in another (reader.html?ch=N#label)."""
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", attrs={"data-reference-type": True}):
        key = a.get("data-reference", "")
        if key not in labels:
            print(f"  !! Chapter {chapter}: unresolved reference {key}")
            continue
        ch, num = labels[key]
        a.string = f"({num})" if a["data-reference-type"] == "eqref" else num
        a["href"] = f"#{key}" if ch == chapter else f"reader.html?ch={pages[ch]}#{key}"
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
    "Further Reading" becomes its own section (h2), and trailing colons left
    over from run-in \\paragraph titles and line breaks set for the printed
    title (\\\\) are dropped."""
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
        for br in h.find_all("br"):
            br.replace_with(" ")
        _strip_trailing_colon(h)
    return str(soup)


_MATH_RE = re.compile(r'<span\s+class="math (display|inline)">(.*?)</span>', re.DOTALL)

# Pandoc wraps amsmath environments inside \[ … \]. KaTeX auto-numbers
# equation/align/gather, which (a) draws an equation tag that forces a
# full-width layout (showing a stray rule/scrollbar under the equation) and
# (b) uses its own running counter that does not match the book. We don't
# number equations on the web, so unwrap/convert everything to the plain,
# un-numbered variants. eqnarray and split are unsupported by KaTeX outright.
_MATH_ENVS = {
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


def _fix_math(html: str, labels: dict) -> str:
    """Normalize math to what KaTeX renders, un-numbered as above.

    The book's print-layout commands go too: KaTeX draws the * of \\\\* (a row
    break that forbids a page break) and does not know \\mbox. The exception
    to un-numbered math is the few labelled equations that the text cites by
    number ('Equation 14.1'): they keep the book's number as a \\tag, with
    align* instead of aligned so that a tag can sit on its own row."""
    def sub(m: re.Match) -> str:
        kind, tex = m.group(1), m.group(2)
        tex = tex.replace("\\\\*", "\\\\").replace(r"\mbox{", r"\text{")
        keys = [k for k in re.findall(r"\\label\{([^}]*)\}", tex) if k in labels]
        envs = dict(_MATH_ENVS)
        if keys:
            envs[r"\begin{align}"], envs[r"\end{align}"] = r"\begin{align*}", r"\end{align*}"
        for a, b in envs.items():
            tex = tex.replace(a, b)
        for k in keys:
            tex = tex.replace(f"\\label{{{k}}}", f"\\tag{{{labels[k][1]}}}")
        tex = re.sub(r"\\label\{[^}]*\}", "", tex)    # KaTeX errors on \label
        anchors = "".join(f'<span id="{k}"></span>' for k in keys[1:])
        anchor = f' id="{keys[0]}"' if keys else ""
        return f'{anchors}<span class="math {kind}"{anchor}>{tex}</span>'
    return _MATH_RE.sub(sub, html)


def convert_chapter(num: int, labels: dict, pages: dict, cites: dict, entries: dict) -> str:
    tex = (SOURCE / f"Chapter{num}.tex").read_text(encoding="utf-8")
    # {\sloppy ... \par} only loosens line breaking in print; pandoc would turn
    # its \par into a paragraph break (splitting a run-in list item)
    tex = re.sub(r"\{\\sloppy\s+(.*?)\\par\}", r"\1", tex, flags=re.DOTALL)
    res = subprocess.run(
        ["pandoc", "-f", "latex", "-t", "html5", "--mathjax"],
        input=tex, cwd=str(SOURCE), capture_output=True, text=True,
    )
    if res.returncode != 0:
        sys.exit(f"!! pandoc failed on Chapter{num}: {res.stderr[:300]}")
    html = res.stdout
    html = _fix_figures(html)
    html = _fix_math(html, labels)
    html = _number_floats(html, num, labels)
    html = _resolve_refs(html, num, labels, pages)
    html = _strip_first_h1(html)
    html = _number_sections(html, num, labels)
    html = _normalize_headings(html)
    html = html.strip() + "\n" + chapter_references(num, cites, entries)
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
    nb = json.loads((ROOT / "tutorials" / f"tutorial_chapter_{key}.ipynb").read_text(encoding="utf-8"))
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
    labels = book_labels()
    cites, entries = book_bibliography()
    pages = reading_order()

    tut_titles: dict[str, str] = {}
    for num, (title, tut_keys) in CHAPTERS.items():
        html = convert_chapter(num, labels, pages, cites, entries)
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

    expected = {"chapter%02d.json" % n for n in CHAPTERS} | {
        f"tutorial_chapter_{k}.json" for _, keys in CHAPTERS.values() for k in keys}
    for stale in sorted(p for p in CONTENT.glob("*.json") if p.name not in expected):
        stale.unlink()
        print(f"  removed stale {stale.name}")

    (DOCS / "assets" / "book-data.js").write_text(build_book_data(tut_titles), encoding="utf-8")
    print("Wrote chapters, tutorials, and book-data.js")


if __name__ == "__main__":
    main()
