"""Build the Nordland research website (static HTML for GitHub Pages).

Authoritative sources are the PDF documents in ``documents/`` (see documents/manifest.json).
The website renders faithful web transcriptions of them from ``content/``:

    content/Nordland_Case_Record.md                                  case evidence (model-facing)
    content/Beyond_Explanation_Methodology.md                        methodology paper
    content/Nordland_Validity_Questions_and_Next_Research_Steps.md   validity memorandum
    content/Nordland_Evaluator_Interpretations_and_Assessment_Criteria.md   evaluator-only rubric

Study data lives in ``data/``:

    data/responses.json            original model outputs with provenance
    data/evaluations.json          dimension-level scores
    data/Nordland_Findings.md      (optional) researcher-written findings

Run from the repository root:

    python -m pip install -r requirements.txt
    python verify_sources.py       # transcriptions match the PDFs
    python build.py                # regenerate every HTML page

The generated HTML files are committed and served as-is; GitHub Pages needs no build step.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path

import mistune
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
DATA = ROOT / "data"
md = mistune.create_markdown(plugins=["table", "strikethrough"])

SITE = "Beyond Explanation"
AUTHOR = "Elaine Chou"

# (slug, number, title, short description, audience tag)
SECTIONS = [
    ("case-record", "01", "Case Record", "The complete, fixed case record and the broad analytical essay prompt supplied to models.", "model"),
    ("methodology", "02", "Methodology", "The research methodology paper, with the validity questions and next research steps.", None),
    ("rubric", "03", "Evaluation Rubric", "Five scoring dimensions with their exact 0–4 anchors, evaluator guidance and illustrative examples.", "evaluator"),
    ("responses", "04", "Model Responses", "Original, unedited model outputs with provenance and test conditions.", None),
    ("evaluations", "05", "Evaluations", "Recorded evaluations, the scoring tool and side-by-side comparison of evaluations.", "evaluator"),
    ("findings", "06", "Findings", "Comparative patterns, limitations and implications.", None),
]
ROMAN = ["I", "II", "III", "IV", "V"]

# The five kinds of material the study keeps separate.
MATERIALS = {
    "evidence": ("Case evidence", "Supplied to models"),
    "interpretation": ("Methodology and interpretation", "Not supplied to models"),
    "criteria": ("Scoring criteria", "Evaluator-only"),
    "illustrative": ("Illustrative example", "Constructed; not a finding"),
    "findings": ("Observations and findings", "From actual model runs"),
}


# --------------------------------------------------------------------------- helpers

def e(value) -> str:
    return html.escape(str(value), quote=True)


def slugify(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "section"


NUMERIC = re.compile(r"^\s*(\*\*)?[-+]?[\d,.]+\s*(%|/\s*\d+)?(\*\*)?\s*$")


def prose(source: str, id_prefix: str = "", demote: int = 0) -> str:
    """Markdown → HTML with scrollable tables, numeric alignment and heading ids."""
    soup = BeautifulSoup(md(source), "html.parser")
    if demote:
        for level in (4, 3, 2, 1):
            for h in soup.find_all(f"h{level}"):
                h.name = f"h{min(level + demote, 6)}"
    for h in soup.find_all(["h2", "h3", "h4"]):
        h["id"] = (id_prefix + "-" if id_prefix else "") + slugify(h.get_text())
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        body_rows = [r for r in rows if r.find_parent("tbody")]
        if body_rows:
            ncols = max(len(r.find_all(["td", "th"])) for r in rows)
            for col in range(ncols):
                cells = [r.find_all(["td", "th"])[col] for r in body_rows if len(r.find_all(["td", "th"])) > col]
                if cells and all(NUMERIC.match(c.get_text()) or c.get_text().strip() in ("", "___") for c in cells):
                    for r in rows:
                        cs = r.find_all(["td", "th"])
                        if len(cs) > col:
                            cs[col]["class"] = cs[col].get("class", []) + ["num"]
                            cs[col].attrs.pop("style", None)
        for r in body_rows:
            if r.get_text().strip().lower().startswith("total"):
                r["class"] = ["total"]
        wrap = soup.new_tag("div", attrs={"class": "table-wrap", "role": "region", "tabindex": "0",
                                          "aria-label": "Scrollable table"})
        table.wrap(wrap)
    for a in soup.find_all("a", href=True):
        if a["href"].startswith("http"):
            a["rel"] = "noopener"
    return str(soup)


def split_h2(source: str) -> dict[str, str]:
    """Split Markdown into {heading: body} on level-2 headings (heading line removed)."""
    out: dict[str, str] = {}
    for block in re.split(r"(?m)^(?=## )", source):
        if block.startswith("## "):
            head_line, _, body = block.partition("\n")
            out[head_line[3:].strip()] = body.strip()
    return out


def find_section(sections: dict[str, str], prefix: str) -> str:
    for k, v in sections.items():
        if k.startswith(prefix):
            return v
    raise KeyError(f"Section starting with {prefix!r} not found")


def load_json(name: str, key: str) -> list:
    path = DATA / name
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get(key, [])


def plain(text: str) -> str:
    """Normalise text for render checks."""
    text = text.replace(" ", " ")
    return re.sub(r"\s+", " ", text).strip()


def assert_rendered(source_md: str, page_html: str, label: str) -> None:
    """Fail the build if any line or table cell of a source document is missing from its page."""
    rendered = plain(BeautifulSoup(page_html, "html.parser").get_text(" "))
    rendered_compact = re.sub(r"\s+", "", rendered)
    for line in source_md.splitlines():
        line = line.strip()
        if not line or re.fullmatch(r"\|?[\s|:-]+\|?", line) or line == "---":
            continue
        is_row = line.startswith("|") or line.count(" | ") >= 2
        pieces = line.strip("|").split("|") if is_row else [line]
        for piece in pieces:
            t = re.sub(r"^(#+|>|-|\d+\.)\s*", "", piece.strip())
            t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
            t = t.replace("**", "").replace("*", "")
            t = plain(t)
            if len(t) > 3 and re.sub(r"\s+", "", t) not in rendered_compact:
                raise RuntimeError(f"{label}: source text missing from rendered page: {t[:90]!r}")


# --------------------------------------------------------------------------- documents

MANIFEST = json.loads((ROOT / "documents" / "manifest.json").read_text(encoding="utf-8"))
DOCS = {d["key"]: d for d in MANIFEST["documents"]}


def verify_documents() -> None:
    for d in DOCS.values():
        for label in ("pdf", "current_archive_file"):
            path = ROOT / d[label]
            if hashlib.sha256(path.read_bytes()).hexdigest() != d["sha256"]:
                raise RuntimeError(f"{d[label]} does not match the SHA-256 recorded in documents/manifest.json")


def size_label(path: Path) -> str:
    n = path.stat().st_size
    return f"{n / 1024:.0f} KB" if n < 1024 * 1024 else f"{n / 1024 / 1024:.1f} MB"


def doc_link(key: str, label: str | None = None) -> str:
    d = DOCS[key]
    return f'<a href="{e(d["pdf"])}" type="application/pdf">{e(label or d["title"])}</a>'


def doc_meta(key: str) -> str:
    d = DOCS[key]
    return f'PDF · {d["pages"]} pages · {size_label(ROOT / d["pdf"])}'


def source_line(key: str, extra: str = "") -> str:
    """'Source document' line used in page heads."""
    return f'{doc_link(key)} <span class="fine-print">({doc_meta(key)})</span>{extra}'


def material_tag(kind: str, note: str | None = None) -> str:
    name, default_note = MATERIALS[kind]
    return (f'<span class="material material--{kind}"><span class="material-name">{e(name)}</span>'
            f'<span class="material-note">{e(note or default_note)}</span></span>')


# --------------------------------------------------------------------------- page chrome

def head(title: str, description: str) -> str:
    full = SITE if title == SITE else f"{title} — {SITE}"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full)}</title>
<meta name="description" content="{e(description)}">
<meta name="theme-color" content="#1b2f4b">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Noto+Serif:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/css/site.css">
</head>"""


def site_header(current: str) -> str:
    items = "".join(
        f'<li><a href="{slug}.html"{" aria-current=\"page\"" if slug == current else ""}>'
        f'<span class="num">{num}</span>{e(title)}</a></li>'
        for slug, num, title, _, _ in SECTIONS
    )
    return f"""<a class="skip-link" href="#main">Skip to content</a>
<header class="site-header">
  <div class="container header-inner">
    <a class="brand" href="index.html"{' aria-current="page"' if current == 'index' else ''}><span class="brand-name">Beyond Explanation</span><span class="brand-sub">The Nordland study</span></a>
    <nav class="site-nav" aria-label="Research sections"><ol>{items}</ol></nav>
  </div>
</header>"""


def site_footer() -> str:
    links = "".join(f'<li><a href="{s}.html">{e(t)}</a></li>' for s, _, t, _, _ in SECTIONS)
    sources = "".join(f"<li>{doc_link(k, label)}</li>" for k, label in [
        ("case-record", "Nordland Case Record"),
        ("methodology", "Beyond Explanation (methodology)"),
        ("evaluator-criteria", "Evaluator Interpretations and Assessment Criteria"),
        ("validity", "Validity Questions and Next Research Steps"),
    ])
    return f"""<footer class="site-footer">
  <div class="container">
    <div class="footer-grid">
      <div><span class="brand-name">Beyond Explanation</span>
        <p>A conceptual-reasoning study built on the Nordland welfare-state paradox. Research by {e(AUTHOR)}.</p>
        <p>Nordland is a fictional country. Illustrative examples are constructed calibration material, not model outputs or experimental results.</p></div>
      <div><h2>Sections</h2><ul>{links}</ul></div>
      <div><h2>Source documents (PDF)</h2><ul>{sources}</ul></div>
    </div>
    <div class="footer-base">Static site · no tracking · scoring tools run entirely in the browser.</div>
  </div>
</footer>"""


def page(slug: str, title: str, description: str, body: str, *, current: str | None = None,
         extra_scripts: str = "", checks: list[tuple[str, str]] | None = None) -> None:
    doc = f"""{head(title, description)}
<body>
{site_header(current or slug)}
<main id="main">
{body}
</main>
{site_footer()}
{extra_scripts}<script src="assets/js/site.js" defer></script>
</body>
</html>
"""
    for source_md, label in checks or []:
        assert_rendered(source_md, doc, label)
    (ROOT / f"{slug}.html").write_text(doc, encoding="utf-8")


def page_head(number: str, title: str, lede: str, meta: list[tuple[str, str]] | None = None,
              materials: list[str] | None = None, extra: str = "") -> str:
    meta_html = ""
    if meta:
        meta_html = '<ul class="page-meta">' + "".join(f"<li><strong>{e(k)}:</strong> {v}</li>" for k, v in meta) + "</ul>"
    mats = ('<div class="material-row" aria-label="Kind of material on this page">' + "".join(material_tag(m) for m in materials) + "</div>") if materials else ""
    return f"""<header class="page-head"><div class="container">
  <p class="eyebrow">Section {number}</p>
  <h1>{e(title)}</h1>
  <p class="lede">{lede}</p>{meta_html}{mats}{extra}
</div></header>"""


def toc(items: list[tuple[str, str, int]], title: str = "On this page") -> str:
    lis = "".join(
        f'<li{" class=\"toc-sub\"" if level > 2 else ""}><a href="#{anchor}">{e(label)}</a></li>'
        for anchor, label, level in items
    )
    return f'<nav class="toc" aria-label="{e(title)}"><p class="toc-title">{e(title)}</p><ol>{lis}</ol></nav>'


def toc_from(html_str: str, levels=("h2", "h3")) -> list[tuple[str, str, int]]:
    soup = BeautifulSoup(html_str, "html.parser")
    return [(h["id"], h.get_text(" ", strip=True), int(h.name[1])) for h in soup.find_all(list(levels)) if h.get("id")]


def doc_layout(toc_html: str, main_html: str) -> str:
    return f'<div class="section"><div class="container doc-layout">{toc_html}<div class="doc-main">{main_html}</div></div></div>'


def notice(title: str, text: str, kind: str = "") -> str:
    cls = f"notice notice--{kind}" if kind else "notice"
    return f'<aside class="{cls}"><strong>{title}</strong><p>{text}</p></aside>'


def site_note(text: str) -> str:
    """An editorial note added by the website, visibly distinct from source-document text."""
    return f'<aside class="site-note"><span class="site-note-label">Website note</span><p>{text}</p></aside>'


def placeholder(title: str, text: str, status: str = "Not yet available") -> str:
    return f'<div class="placeholder"><span class="status">{e(status)}</span><h3>{e(title)}</h3>{text}</div>'


def h2(anchor: str, kicker: str, title: str) -> str:
    return f'<p class="kicker">{e(kicker)}</p><h2 id="{anchor}">{e(title)}</h2>'


def insert_after_heading(html_str: str, heading_id: str, snippet: str) -> str:
    soup = BeautifulSoup(html_str, "html.parser")
    h = soup.find(id=heading_id)
    if h is None:
        raise RuntimeError(f"Heading id {heading_id!r} not found")
    h.insert_after(BeautifulSoup(snippet, "html.parser"))
    return str(soup)


# --------------------------------------------------------------------------- sources

case_src = (CONTENT / "Nordland_Case_Record.md").read_text(encoding="utf-8")
method_src = (CONTENT / "Beyond_Explanation_Methodology.md").read_text(encoding="utf-8")
validity_src = (CONTENT / "Nordland_Validity_Questions_and_Next_Research_Steps.md").read_text(encoding="utf-8")
eval_src = (CONTENT / "Nordland_Evaluator_Interpretations_and_Assessment_Criteria.md").read_text(encoding="utf-8")
findings_path = DATA / "Nordland_Findings.md"
findings_src = findings_path.read_text(encoding="utf-8") if findings_path.exists() else None

responses = load_json("responses.json", "responses")
evaluations = load_json("evaluations.json", "evaluations")

method = split_h2(method_src)
evaluator = split_h2(eval_src)
validity = split_h2(validity_src)


# --------------------------------------------------------------------------- rubric extraction (authoritative: evaluator document §5)

rubric_block = find_section(evaluator, "5. Assessment criteria")
rubric_intro = rubric_block.split("\n### ", 1)[0].strip()
dims = []
for roman, title, body in re.findall(r"(?ms)^### ([IVX]+)\. (.+?)\n(.*?)(?=^### |\Z)", rubric_block):
    anchors = {int(n): d.strip() for n, d in re.findall(r"(?m)^\*\*([0-4])\*\*\s*[—–-]\s*(.+?)\s*$", body)}
    if len(anchors) != 5:
        raise RuntimeError(f"Dimension {roman} is missing anchors")
    name, _, subtitle = title.partition(" — ")
    dims.append({"roman": roman, "title": title.strip(), "name": name.strip(), "subtitle": subtitle.strip(), "anchors": anchors})
if [d["roman"] for d in dims] != ROMAN:
    raise RuntimeError("Expected rubric dimensions I–V")
rubric_coda = re.search(r"(?ms)^\*\*Level 4 is not an originality prize\.\*\*.*?$", rubric_block).group(0)

separation = find_section(evaluator, "6. Score separation")
for roman, text in re.findall(r"(?m)^- \*\*([IVX]+) evaluates[^*]*\*\*\s*(.+)$", separation):
    for d in dims:
        if d["roman"] == roman:
            d["focus"] = text.strip()

eval_title = eval_src.splitlines()[0].lstrip("# ").strip()
eval_label = re.search(r"(?m)^\*\*(Restricted assessor reference)\*\*", eval_src).group(1)
eval_use = re.search(r"(?m)^\*\*Use:\*\*.*$", eval_src).group(0)
eval_relationship = re.search(r"(?m)^\*\*Document relationship:\*\*.*$", eval_src).group(0)


# --------------------------------------------------------------------------- 01 case record

def build_case_record() -> None:
    body = case_src.replace("NORDLAND\n\nCase record\n\n", "", 1)
    headings = ["Record definitions and scope", "Founding and design", "Outcomes and public opinion",
                "Benefit decisions", "Additional benefit-decision evidence", "Employment", "History", "Essay assignment"]
    for h in headings:
        body = re.sub(rf"(?m)^{re.escape(h)}\s*$", f"\n## {h}\n", body)
    body = body.replace("Table A1. Benefit offices, 2025\n", "\nTable A1. Benefit offices, 2025\n\n")
    for n in range(1, 16):
        body = re.sub(rf"(?m)^{n}\. ", f"\n{n}. ", body)
    soup = BeautifulSoup(prose(body, "case"), "html.parser")
    for p in soup.find_all("p"):
        if p.get_text().startswith("Table A1."):
            p["class"] = ["table-title"]
            p["id"] = "table-a1"
            nxt = p.find_next_sibling("div")
            if nxt:
                nxt["aria-labelledby"] = "table-a1"
                del nxt["aria-label"]
    assignment = soup.find("h2", string="Essay assignment")
    box = soup.new_tag("div", attrs={"class": "assignment"})
    for sib in list(assignment.find_next_siblings()):
        box.append(sib.extract())
    assignment.insert_after(box)

    d = DOCS["case-record"]
    doc = f"""{head("Case Record", "The complete Nordland Case Record and essay assignment, exactly as supplied to models.")}
<body class="case-body">
<a class="skip-link" href="#record">Skip to case record</a>
<div class="case-bar"><div class="container">
  <a class="back" href="index.html">← Beyond Explanation · Section 01</a>
  <div class="actions">
    <button class="btn btn--ghost" type="button" data-copy-template="case-raw">Copy record text</button>
    <a class="btn btn--ghost" href="{e(d['pdf'])}" type="application/pdf">Open PDF</a>
    <a class="btn btn--ghost" href="content/Nordland_Case_Record.md" download>Download text</a>
    <button class="btn btn--ghost" type="button" data-print>Print</button>
  </div>
</div></div>
<main id="main">
<article class="case-doc container" id="record" aria-labelledby="case-title">
  <aside class="case-frame" aria-label="About this page">This page reproduces the complete Nordland Case Record, including the essay assignment, exactly as supplied to models. The PDF ({doc_meta('case-record')}) and the copy and download controls provide the same text.</aside>
  <header><h1 id="case-title">Nordland</h1><p>Case record</p></header>
  <div class="prose">{soup}</div>
</article>
</main>
<template id="case-raw">{html.escape(case_src)}</template>
<div class="status-message visually-hidden" data-status role="status" aria-live="polite"></div>
<script src="assets/js/site.js" defer></script>
</body>
</html>
"""
    assert_rendered(case_src.replace("NORDLAND\n\nCase record\n\n", "", 1), doc, "Case Record")
    # The model-facing page must link only to the case record itself.
    linked = set(re.findall(r'href="(documents/[^"]+)"', doc))
    if linked != {d["pdf"]}:
        raise RuntimeError(f"Case Record page links to other documents: {linked}")
    (ROOT / "case-record.html").write_text(doc, encoding="utf-8")


# --------------------------------------------------------------------------- home + chart

def chart_data() -> dict:
    """Figures quoted from the case record; each is checked against the source text."""
    required = ["23% of residents", "after taxes and transfers, 7%", "34% before and 13% after",
                "denied at a rate of 18.3%", "at 8.9%", "76% of minority respondents", "79% of other respondents",
                "52% of minority respondents", "81% of other respondents"]
    for phrase in required:
        if phrase not in case_src:
            raise RuntimeError(f"Chart figure no longer matches case record: {phrase!r}")
    return {
        "poverty": [
            ("All residents", "Case record ¶2", 23, 7),
            ("Minority-background residents", "Case record ¶2", 34, 13),
        ],
        "groups": [
            ("Initial benefit claims denied", "Claims, 2025 · ¶6", 18.3, 8.9),
            ("“The benefit system is good for Nordland”", "Survey agreement · ¶3", 76, 79),
            ("“I feel fully part of Nordland society”", "Survey agreement · ¶3", 52, 81),
        ],
    }


def fmt(v: float) -> str:
    return f"{v:g}%"


def dot_row(label: str, sub: str, a: float, b: float, a_cls: str, b_cls: str, a_name: str, b_name: str) -> str:
    lo, hi = min(a, b), max(a, b)
    return f"""<div class="dp-row">
  <div class="dp-label">{e(label)}<span class="dp-values"><span class="swatch swatch--{a_cls}" aria-hidden="true"></span>{e(a_name)} {fmt(a)}<span class="sep">·</span><span class="swatch swatch--{b_cls}" aria-hidden="true"></span>{e(b_name)} {fmt(b)}</span><span class="dp-sub">{e(sub)}</span></div>
  <div class="dp-track" aria-hidden="true">
    <span class="dp-link" style="left:{lo}%;width:{hi - lo}%"></span>
    <span class="dp-dot dp-dot--{a_cls}" style="left:{a}%" data-tip="{e(label)}|{e(a_name)}: {fmt(a)}"></span>
    <span class="dp-dot dp-dot--{b_cls}" style="left:{b}%" data-tip="{e(label)}|{e(b_name)}: {fmt(b)}"></span>
  </div>
</div>"""


def paradox_figure() -> str:
    d = chart_data()
    axis = '<div class="dp-axis" aria-hidden="true"><span></span><div>' + "".join(
        f'<span style="left:{v}%">{v}%</span>' for v in (0, 25, 50, 75, 100)) + "</div></div>"
    pov = "".join(dot_row(l, s, a, b, "before", "after", "Before", "After") for l, s, a, b in d["poverty"])
    grp = "".join(dot_row(l, s, a, b, "minority", "other", "Minority background", "Other") for l, s, a, b in d["groups"])
    table_rows = "".join(f"<tr><th scope=\"row\">{e(l)}</th><td>Before / after transfers</td><td class=\"num\">{fmt(a)}</td><td class=\"num\">{fmt(b)}</td></tr>" for l, _, a, b in d["poverty"])
    table_rows += "".join(f"<tr><th scope=\"row\">{e(l)}</th><td>Minority background / other</td><td class=\"num\">{fmt(a)}</td><td class=\"num\">{fmt(b)}</td></tr>" for l, _, a, b in d["groups"])
    return f"""<figure class="figure" data-chart aria-labelledby="fig-title" aria-describedby="fig-note">
  <p class="figure-title" id="fig-title">The record in five measures</p>
  <p class="figure-sub">Percentages stated in the Nordland Case Record, 2025. All values on a common 0–100% scale.</p>
  <div class="dp-panel">
    <p class="dp-panel-title">Poverty rate, before and after taxes and transfers</p>
    <ul class="legend"><li><span class="swatch swatch--before"></span>Before</li><li><span class="swatch swatch--after"></span>After</li></ul>
    {axis}{pov}
  </div>
  <div class="dp-panel">
    <p class="dp-panel-title">Minority-background and other groups</p>
    <ul class="legend"><li><span class="swatch swatch--minority"></span>Minority background</li><li><span class="swatch swatch--other"></span>Other</li></ul>
    {axis}{grp}
  </div>
  <div class="chart-tip" role="presentation"></div>
  <figcaption id="fig-note">The measures come from different sources and units (residents’ incomes, filed claims and survey respondents), which the record states are not person-level linked. Placing them on one scale shows their coexistence; it does not imply a relationship between them.</figcaption>
  <details><summary>View as table</summary>
    <div class="table-wrap" role="region" tabindex="0" aria-label="Figure data"><table>
      <thead><tr><th scope="col">Measure</th><th scope="col">Comparison</th><th scope="col" class="num">First</th><th scope="col" class="num">Second</th></tr></thead>
      <tbody>{table_rows}</tbody></table></div>
  </details>
</figure>"""


def quote_from(source: str, sentence: str) -> str:
    """Return a sentence only if it appears verbatim in the source document."""
    if sentence not in source:
        raise RuntimeError(f"Quoted sentence not found in source: {sentence[:70]!r}")
    return sentence


def build_home() -> None:
    n_resp, n_eval = len(responses), len(evaluations)
    index = "".join(
        f"""<li><a href="{slug}.html"><span class="num">{num}</span><span class="title">{e(title)}<span class="tags">{
            '<span class="tag tag--model">Model-facing</span>' if tag == 'model' else
            '<span class="tag tag--evaluator">Evaluator</span>' if tag == 'evaluator' else ''}{
            '<span class="tag tag--pending">Pending</span>' if (slug == 'responses' and not n_resp) or (slug == 'evaluations' and not n_eval) or (slug == 'findings' and not findings_src) else ''
        }</span></span><span class="desc">{e(desc)}</span><span class="arrow" aria-hidden="true">→</span></a></li>"""
        for slug, num, title, desc, tag in SECTIONS
    )
    abstract = find_section(method, "Abstract")
    lede = " ".join(quote_from(abstract, s) for s in [
        "In the fictional record, universal benefits substantially reduce poverty, yet claims filed by minority-background applicants are denied at roughly twice the rate of other claims.",
        "Minority-background residents report weaker social belonging even as support for the welfare system remains high.",
    ])
    sec1 = find_section(method, "1 Research problem")
    primary_note = " ".join(quote_from(sec1, s) for s in [
        "A satisfactory inquiry must treat the state’s measurable redistributive achievement as seriously as its patterned unequal outcomes.",
        "Neither fact cancels the other.",
    ])
    embedded = quote_from(sec1, "Can a model confronted with this paradox determine what most needs to be understood; distinguish central issues from incidental detail; infer potentially consequential patterns across disparate evidence; and produce an interpretation that is both original, where warranted, and disciplined by the record?")
    embedded_note = " ".join(quote_from(sec1, s) for s in [
        "Nordland remains the intellectual problem.",
        "AI evaluation asks how well a model reasons about it.",
        "The assessor defines standards of intellectual quality, not the direction or conclusion of the analysis.",
    ])
    no_findings = quote_from(abstract, "no experimental findings are reported.")

    materials_rows = [
        ("evidence", "The fixed fictional record: stipulated facts, measurements and study designs, followed by the broad essay assignment.",
         '<a href="case-record.html">Case Record</a>', doc_link("case-record", "Nordland Case Record"), "Yes, and nothing else"),
        ("interpretation", "The research problem, the principal interpretive possibilities, the evaluation protocol and the validity questions.",
         '<a href="methodology.html">Methodology</a>; reference analysis on <a href="rubric.html#reference">Rubric</a>',
         f'{doc_link("methodology", "Beyond Explanation")}; {doc_link("validity", "Validity Questions")}; {doc_link("evaluator-criteria", "Evaluator Interpretations")} §1–3, §9', "No"),
        ("criteria", "The five dimensions, their 0–4 anchors, evidentiary guardrails, protocol and scoring record.",
         '<a href="rubric.html">Evaluation Rubric</a>; <a href="score.html">scoring tool</a>',
         f'{doc_link("evaluator-criteria", "Evaluator Interpretations and Assessment Criteria")} §4–8', "No"),
        ("illustrative", "Three constructed essays with explained scores, and the methodology’s illustrative anchors. Written for calibration.",
         '<a href="rubric.html#calibration">Rubric, Appendix A</a>; <a href="methodology.html#appendix-illustrative-nordland-anchors-assessor-calibration">Methodology, Appendix</a>',
         f'{doc_link("evaluator-criteria", "Evaluator Interpretations")} Appendix A; {doc_link("methodology", "Beyond Explanation")} Appendix', "No"),
        ("findings", "Unedited model outputs, their scores and the conclusions drawn from them.",
         '<a href="responses.html">Model Responses</a>, <a href="evaluations.html">Evaluations</a>, <a href="findings.html">Findings</a>',
         "Data files in this repository", "Not applicable"),
    ]
    mat_table = "".join(
        f'<tr><th scope="row">{material_tag(k)}</th><td>{desc}</td><td>{where}</td><td>{src}</td><td>{given}</td></tr>'
        for k, desc, where, src, given in materials_rows)
    sources = "".join(
        f"""<li><span class="src-title">{doc_link(k)}</span><span class="src-meta">{e(role)} · {doc_meta(k)}</span></li>"""
        for k, role in [("case-record", "Case evidence · model-facing"),
                        ("methodology", "Research methodology"),
                        ("validity", "Validity questions and next research steps"),
                        ("evaluator-criteria", "Evaluator-only rubric, reference analysis and Appendix A")])
    status = f"""<dl class="status-list">
  <div><dt>Case record</dt><dd>Fixed<small>Neutral record and prompt</small></dd></div>
  <div><dt>Model responses</dt><dd>{n_resp}<small>{'collected' if n_resp else 'Collection not yet begun'}</small></dd></div>
  <div><dt>Evaluations</dt><dd>{n_eval}<small>{'scored records' if n_eval else 'No scored responses yet'}</small></dd></div>
  <div><dt>Findings</dt><dd>{'Published' if findings_src else 'Pending'}<small>{'See section 06' if findings_src else 'Reported after evaluation'}</small></dd></div>
</dl>"""
    body = f"""<section class="hero"><div class="container">
  <p class="eyebrow">The Nordland study · Conceptual reasoning in AI</p>
  <h1>Beyond Explanation</h1>
  <p class="lede">{e(lede)}</p>
  <div class="btn-row"><a class="btn" href="case-record.html">Read the case record</a><a class="btn btn--ghost" href="methodology.html">Read the methodology</a></div>
  <p class="hero-byline">Research by {e(AUTHOR)}</p>
</div></section>

<section class="section"><div class="container">
  <div class="section-head"><p class="kicker">Research questions</p><h2>Two questions, inseparable by design</h2></div>
  <div class="question-grid">
    <div class="question"><p class="label">Primary · The welfare-state paradox</p>
      <blockquote>How can a strong welfare state sustain significant inequality despite its commitment to universal social protection?</blockquote>
      <p>{e(primary_note)}</p></div>
    <div class="question question--secondary"><p class="label">Embedded · Conceptual reasoning in AI</p>
      <blockquote>{e(embedded)}</blockquote>
      <p>{e(embedded_note)}</p></div>
  </div>
  <p class="fine-print">Quoted from {doc_link("methodology", "Beyond Explanation")}, §1.</p>
</div></section>

<section class="section section--white"><div class="container">
  <div class="section-head"><p class="kicker">The paradox in the record</p><h2>Achievement and disparity, side by side</h2>
  <p>Poverty falls substantially for every group, and support for the benefit system is nearly equal. Initial claim denials and the sense of belonging diverge.</p></div>
  {paradox_figure()}
</div></section>

<section class="section"><div class="container">
  <div class="section-head"><p class="kicker">The research record</p><h2>Six sections</h2>
  <p>The study is published as a sequence, from the evidence given to models through to what the evaluations show.</p></div>
  <ol class="section-index">{index}</ol>
</div></section>

<section class="section section--white"><div class="container">
  <div class="section-head"><p class="kicker">Separation of materials</p><h2>Five kinds of material, kept apart</h2>
  <p>Models receive only the case record. Each page of this site is labelled with the kind of material it contains.</p></div>
  <div class="table-wrap" role="region" tabindex="0" aria-label="Kinds of material"><table class="materials-table">
    <thead><tr><th scope="col">Material</th><th scope="col">What it contains</th><th scope="col">On this site</th><th scope="col">Source document</th><th scope="col">Given to models</th></tr></thead>
    <tbody>{mat_table}</tbody></table></div>
  <p class="fine-print">Evaluator-only documents are published here for methodological transparency and are not access-controlled. They must not be supplied to a model before its response is collected.</p>
</div></section>

<section class="section"><div class="container">
  <div class="section-head"><p class="kicker">Source documents</p><h2>The authoritative documents</h2>
  <p>The website reproduces these documents in full. Each PDF is the current authoritative version.</p></div>
  <ul class="source-list">{sources}</ul>
</div></section>

<section class="section section--white"><div class="container">
  <div class="section-head"><p class="kicker">Study status</p><h2>Where the research stands</h2>
  <p>This is a single-case pilot of a research method; as the methodology states, {e(no_findings)} Counts below are generated from the published data files.</p></div>
  {status}
</div></section>"""
    page("index", SITE, "The Nordland study: a welfare-state paradox and an evaluation of conceptual reasoning in AI models.", body)


# --------------------------------------------------------------------------- 02 methodology (+ validity)

def method_tabs(current: str) -> str:
    tabs = [("methodology", "Research methodology"), ("validity", "Validity questions and next research steps")]
    items = "".join(f'<li><a href="{s}.html"{" aria-current=\"page\"" if s == current else ""}>{e(t)}</a></li>' for s, t in tabs)
    return f'<nav class="doc-tabs" aria-label="Methodology documents"><ol>{items}</ol></nav>'


def build_methodology() -> None:
    title_line, byline = method_src.splitlines()[0].lstrip("# ").strip(), method_src.splitlines()[2].strip()
    body_md = method_src.split("\n", 3)[3]
    content = prose(body_md, "")
    # Label the parts of the paper by kind of material.
    labels = {
        "2-1-the-fixed-fictional-record": material_tag("interpretation", "Includes assessor-facing notes; the case record itself carries none"),
        "2-3-the-principal-interpretive-possibilities": material_tag("interpretation", "Not supplied to models"),
        "2-5-evidence-that-could-distinguish-the-accounts": material_tag("interpretation", "Not supplied to models"),
        "4-4-assessment-rubric-five-dimensions-scored-0-4": material_tag("criteria", "Methodology summary") + site_note(
            'This section summarises the rubric in the methodology paper’s own wording. Scoring uses the exact anchors in '
            f'{doc_link("evaluator-criteria", "Evaluator Interpretations and Assessment Criteria")} §5, reproduced on the '
            '<a href="rubric.html#dimensions">Evaluation Rubric</a> page.'),
        "appendix-illustrative-nordland-anchors-assessor-calibration": material_tag("illustrative", "Assessor calibration; not a finding"),
    }
    for hid, snippet in labels.items():
        content = insert_after_heading(content, hid, snippet)
    items = toc_from(content, ("h2", "h3"))
    main = method_tabs("methodology") + content
    body = page_head("02", "Methodology",
                     f'<cite class="doc-cite">{e(title_line)}</cite>',
                     [("Author", e(byline.split("|")[-1].strip())), ("Document", e(byline.split("|")[0].strip()))],
                     materials=["interpretation"],
                     extra=f'<p class="source-line"><strong>Source document:</strong> {source_line("methodology")}</p>')
    body += doc_layout(toc(items), main)
    page("methodology", "Methodology", "Beyond Explanation: the research methodology of the Nordland conceptual-reasoning study.", body,
         checks=[(body_md, "Methodology"), (title_line, "Methodology title")])


def build_validity() -> None:
    title_line = validity_src.splitlines()[0].lstrip("# ").strip()
    doc_kind = validity_src.splitlines()[2].strip()
    body_md = validity_src.split("\n", 3)[3]
    content = prose(body_md, "")
    items = toc_from(content, ("h2",))
    main = method_tabs("validity") + content
    body = page_head("02", "Validity Questions and Next Research Steps",
                     "The research planning memorandum that audits whether the case and the scoring measure what the study claims, and sets out the next research steps.",
                     [("Document", e(doc_kind))],
                     materials=["interpretation"],
                     extra=f'<p class="source-line"><strong>Source document:</strong> {source_line("validity")}</p>')
    body += doc_layout(toc(items, "Contents"), main)
    page("validity", "Validity Questions", "Validity questions and next research steps for the Nordland conceptual-reasoning study.", body,
         current="methodology", checks=[(body_md, "Validity"), (title_line.split(": ", 1)[1], "Validity title")])


# --------------------------------------------------------------------------- 03 rubric

def build_rubric() -> None:
    matrix_head = "".join(f'<th scope="col" class="lvl">{n}</th>' for n in range(5))
    matrix_rows = "".join(
        f'<tr><th scope="row">{d["roman"]}. {e(d["name"])}</th>' + "".join(f"<td>{e(d['anchors'][i])}</td>" for i in range(5)) + "</tr>"
        for d in dims)
    matrix = (f'<div class="table-wrap" role="region" tabindex="0" aria-label="Scoring anchor matrix"><table class="anchor-matrix">'
              f'<caption>Scoring anchors by dimension and level (0–4)</caption><thead><tr><th scope="col">Dimension</th>{matrix_head}</tr></thead>'
              f"<tbody>{matrix_rows}</tbody></table></div>"
              '<p class="table-note">Summary view of the anchors listed in full below. Scroll horizontally on small screens.</p>')
    dim_html = "".join(
        f"""<div class="dimension" id="dim-{d['roman'].lower()}">
  <div class="dimension-head"><h3><span class="roman">{d['roman']}.</span> {e(d['name'])} — {e(d['subtitle'])}</h3></div>
  <dl class="anchor-list">{''.join(f'<dt>{i}<span class="dash"> —</span></dt><dd>{e(d["anchors"][i])}</dd>' for i in range(5))}</dl>
</div>""" for d in dims)

    appendix = find_section(evaluator, "Appendix A")
    appendix = appendix.split("\n---", 1)[0].strip()       # the closing "Document relationship" note is shown at the top
    app_intro, *app_parts = re.split(r"(?m)^(?=### )", appendix)
    calib = []
    for part in app_parts:
        title, _, body = part.partition("\n")
        title = title[4:].strip()
        m = re.search(r"\*\*Total \(secondary\)\*\* \| \*\*(\d+ / 20)\*\*", body)
        meta = f"Illustrative · {m.group(1)}" if m else "Illustrative"
        calib.append(f'<details class="disclosure calibration-essay"><summary>{e(title)}<span class="summary-meta">{meta}</span></summary>'
                     f'<div class="disclosure-body">{material_tag("illustrative", "Constructed; not a model output or experimental result")}'
                     f'<div class="prose">{prose(body, "cal-" + slugify(title)[:12], demote=1)}</div></div></details>')

    reference = []
    for prefix in ["1. Purpose", "2. The substantive problem", "3. Nonexclusive", "9. Interpretive conclusions"]:
        heading = next(k for k in evaluator if k.startswith(prefix))
        reference.append(f'<details class="disclosure"><summary>{e(heading)}</summary><div class="disclosure-body prose">'
                         f'{prose(find_section(evaluator, prefix), "ref-" + slugify(heading)[:18], demote=1)}</div></details>')

    def sec_title(prefix: str) -> str:
        return next(k for k in evaluator if k.startswith(prefix))

    sections = [
        ("dimensions", "§5", sec_title("5."), "criteria",
         prose(rubric_intro) + matrix + dim_html + f'<div class="prose">{prose(rubric_coda)}</div>'),
        ("separation", "§6", sec_title("6."), "criteria", prose(separation)),
        ("guardrails", "§4", sec_title("4."), "criteria", prose(find_section(evaluator, "4. Evidentiary guardrails"))),
        ("protocol", "§7", sec_title("7."), "criteria", prose(find_section(evaluator, "7. Evaluator protocol"))),
        ("scoring-record", "§8", sec_title("8."), "criteria",
         prose(find_section(evaluator, "8. Scoring record")) +
         site_note('An interactive version of this scoring record, with JSON and CSV export, is on the <a href="score.html">Score a response</a> page.')),
        ("reference", "§1–3, §9", "Reference analysis", "interpretation", "".join(reference)),
        ("calibration", "Appendix A", sec_title("Appendix A"), "illustrative",
         prose(app_intro) + "".join(calib) +
         site_note('The methodology paper has a separate appendix of illustrative level 2–4 anchors: '
                   '<a href="methodology.html#appendix-illustrative-nordland-anchors-assessor-calibration">Methodology, Appendix</a>.')),
    ]
    items = [(a, re.sub(r"^\d+\.\s*", "", t), 2) for a, _, t, _, _ in sections]
    main = (f'<aside class="notice notice--evaluator"><strong>{e(eval_label)}</strong>'
            f'{prose(eval_use)}{prose(eval_relationship)}</aside>')
    for a, k, t, kind, b in sections:
        main += (f'<section aria-labelledby="{a}" class="rubric-section">'
                 f'<p class="kicker">Rubric document · {e(k)}</p><h2 id="{a}">{e(t)}</h2>{material_tag(kind)}'
                 f'<div class="prose-wide">{b}</div></section><hr>')
    main = main.rsplit("<hr>", 1)[0]
    body = page_head("03", "Evaluation Rubric",
                     "Five independent dimensions of intellectual work, each scored from 0 to 4, with the exact criteria and anchors from the authoritative rubric document. The five-score profile is the primary result; the total out of 20 is a secondary summary.",
                     [("Audience", "Evaluators only"), ("Scale", "Ordinal 0–4 per dimension"), ("Total", "Secondary, out of 20")],
                     materials=["criteria", "interpretation", "illustrative"],
                     extra=f'<p class="source-line"><strong>Source document:</strong> {source_line("evaluator-criteria")}</p>')
    body += doc_layout(toc(items), main)
    full_body = eval_src.split("\n", 1)[1]
    page("rubric", "Evaluation Rubric", "The five-dimension, 0–4 rubric for evaluating model essays on the Nordland case, with evaluator guidance and illustrative examples.", body,
         checks=[(full_body, "Rubric")])


# --------------------------------------------------------------------------- response and evaluation records

PROVENANCE = [
    ("model", "Model name"), ("model_version", "Model version"), ("provider", "Provider"),
    ("run_date", "Test date"), ("interface", "Interface / API"), ("decoding_settings", "Generation settings"),
    ("length_limits", "Length limits"), ("tools_available", "Tools available"),
    ("case_prompt_identifier", "Case/prompt identifier"), ("collected_by", "Collected by"),
]

SYNTHESIS = [
    ("governing_thesis", "Governing thesis observed"),
    ("consequential_insight", "Most consequential insight or omission"),
    ("disconfirming_evidence", "Disconfirming evidence the model considered or overlooked"),
    ("explanation_for_4s", "Explanation for each score of 4"),
    ("unexpected_interpretation", "Unexpected interpretation (if any) and disposition"),
    ("assessor_uncertainty", "Assessor confidence / unresolved calibration issue"),
]

ASSIGNMENT = re.search(r"(?ms)^Essay assignment\s*\n+(.+)$", case_src).group(1).strip()
CASE_ID = f"Nordland Case Record and essay assignment (PDF SHA-256 {DOCS['case-record']['sha256'][:12]})"


def text_of(markdown: str) -> str:
    return plain(BeautifulSoup(md(markdown), "html.parser").get_text(" "))


def response_record(base: dict, markdown: str) -> dict:
    text = text_of(markdown)
    return {**base,
            "output_markdown": markdown,
            "output_html": prose(markdown, base["id"].lower()),
            "output_text": text,
            "word_count": len(re.findall(r"\S+", text)),
            "sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest()}


def illustrative_examples() -> tuple[list[dict], list[dict]]:
    """The three constructed essays and their explained scores, read from Appendix A of the rubric document."""
    appendix = find_section(evaluator, "Appendix A").split("\n---", 1)[0]
    status = re.search(r"(?m)^\*\*Status and safeguards\.\*\*.*$", appendix).group(0)
    out_r, out_e = [], []
    for part in re.split(r"(?m)^(?=### A\.\d)", appendix)[1:]:
        head_line, _, body = part.partition("\n")
        m = re.match(r"### (A\.\d) (Response ([A-Z])) — (.+)", head_line)
        if not m:
            continue                                   # A.4 is the cross-response table
        section, name, letter, label = m.groups()
        stated = re.search(r"\*\*Illustrative model response \((.+?)\)\*\*", body).group(1)
        essay = "\n".join(l[1:].strip() for l in body.splitlines() if l.startswith(">")).strip()
        rid = f"ILL-{letter}"
        out_r.append(response_record({
            "id": rid, "kind": "illustrative", "title": f"{name} — {label}",
            "source": f"Appendix A, §{section}", "source_doc": "evaluator-criteria",
            "stated_length": stated, "status_note": status,
        }, essay))
        scores = {}
        for roman, score, rationale in re.findall(r"(?m)^\| (I|II|III|IV|V)\. [^|]+\| \*\*(\d) / 4\*\* \| (.+?) \|\s*$", body):
            scores[roman] = {"score": int(score), "rationale": rationale.strip(), "excerpts": [], "weaknesses": ""}
        total = re.search(r"(?m)^\| \*\*Total \(secondary\)\*\* \| \*\*(\d+) / 20\*\* \| (.+?) \|\s*$", body)
        note = re.search(r"(?m)^\*\*Calibration note\.\*\* (.+)$", body).group(1)
        if sorted(scores) != sorted(ROMAN) or sum(s["score"] for s in scores.values()) != int(total.group(1)):
            raise RuntimeError(f"Appendix {section}: dimension scores do not add up to the stated total")
        out_e.append({
            "id": f"EV-{rid}", "response_id": rid, "evaluation_kind": "illustrative",
            "evaluator": "Rubric document, Appendix A", "date": "",
            "source": f"Appendix A, §{section}: Scores and passage-specific rationales",
            "scores": scores, "total_secondary": int(total.group(1)),
            "overall_summary": total.group(2).strip(), "calibration_note": note,
        })
    if [r["id"] for r in out_r] != ["ILL-A", "ILL-B", "ILL-C"]:
        raise RuntimeError("Expected three illustrative responses in Appendix A")
    return out_r, out_e


def experimental_records() -> tuple[list[dict], list[dict]]:
    """Genuine model outputs and their evaluations from data/, validated for traceability."""
    recs = []
    for r in responses:
        if not r.get("id") or not r.get("output_markdown", "").strip():
            raise RuntimeError("Each response in data/responses.json needs an id and output_markdown")
        recs.append(response_record({**{k: r.get(k) for k, _ in PROVENANCE}, "id": r["id"], "kind": "experimental",
                                     "title": r.get("model") or r["id"], "notes": r.get("notes", "")},
                                    r["output_markdown"]))
    ids = {r["id"] for r in recs}
    if len(ids) != len(recs):
        raise RuntimeError("Duplicate response ids in data/responses.json")
    evs = []
    for i, ev in enumerate(evaluations, 1):
        if ev.get("response_id") not in ids:
            raise RuntimeError(f"Evaluation {i} refers to unknown response {ev.get('response_id')!r}")
        scores = {}
        for roman in ROMAN:
            s = (ev.get("scores") or {}).get(roman) or {}
            v = s.get("score")
            if v is not None and v not in (0, 1, 2, 3, 4):
                raise RuntimeError(f"Evaluation {i}: dimension {roman} score {v!r} is not 0–4")
            ex = s.get("excerpts") or []
            scores[roman] = {"score": v, "rationale": s.get("rationale", ""), "weaknesses": s.get("weaknesses", ""),
                             "excerpts": [ex] if isinstance(ex, str) else ex}
        vals = [scores[r]["score"] for r in ROMAN]
        total = sum(vals) if None not in vals else None
        if ev.get("total_secondary") not in (None, total):
            raise RuntimeError(f"Evaluation {i}: stated total {ev.get('total_secondary')} does not equal the dimension scores")
        evs.append({**ev, "id": ev.get("id") or f"EV-{ev['response_id']}-{i}", "evaluation_kind": "experimental",
                    "scores": scores, "total_secondary": total})
    return recs, evs


ILL_RESPONSES, ILL_EVALS = illustrative_examples()
EXP_RESPONSES, EXP_EVALS = experimental_records()
ALL_RESPONSES = EXP_RESPONSES + ILL_RESPONSES
ALL_EVALS = EXP_EVALS + ILL_EVALS


def site_data_script() -> str:
    """Everything the browser tools need, embedded in the page so the site works without a server."""
    data = {
        "rubric": {
            "document": DOCS["evaluator-criteria"]["title"], "section": "§5",
            "pdf": DOCS["evaluator-criteria"]["pdf"], "sha256": DOCS["evaluator-criteria"]["sha256"],
            "level4_note": re.sub(r"\*\*", "", rubric_coda),
            "dimensions": [{"roman": d["roman"], "name": d["name"], "subtitle": d["subtitle"], "focus": d.get("focus", ""),
                            "anchors": {str(k): v for k, v in d["anchors"].items()}} for d in dims],
        },
        "case_prompt": {"identifier": CASE_ID, "assignment": ASSIGNMENT, "pdf": DOCS["case-record"]["pdf"]},
        "responses": [{k: v for k, v in r.items() if k != "output_markdown"} for r in ALL_RESPONSES],
        "evaluations": ALL_EVALS,
    }
    raw = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/json" id="nordland-data">{raw}</script>\n'


def kind_tag(kind: str) -> str:
    return material_tag("findings", "Genuine experimental output") if kind == "experimental" else \
        material_tag("illustrative", "Constructed calibration example; not a model output")


def eval_tabs(current: str) -> str:
    tabs = [("evaluations", "Recorded evaluations"), ("score", "Score a response"), ("compare", "Compare evaluations")]
    items = "".join(f'<li><a href="{s}.html"{" aria-current=\"page\"" if s == current else ""}>{e(t)}</a></li>' for s, t in tabs)
    return f'<nav class="doc-tabs" aria-label="Evaluation tools"><ol>{items}</ol></nav>'


def score_bars(scores: dict, label: str) -> str:
    """Static horizontal bar chart of a five-dimension profile (0–4 scale)."""
    rows, aria = [], []
    for d in dims:
        v = (scores.get(d["roman"]) or {}).get("score")
        aria.append(f'{d["roman"]} {d["name"]}: {"not scored" if v is None else f"{v} of 4"}')
        rows.append(f'<div class="bar-row"><span class="bar-label">{d["roman"]}. {e(d["name"])}</span>'
                    f'<span class="bar-track{" is-empty" if v is None else ""}"><span class="bar-fill" style="width:{0 if v is None else v * 25}%"></span></span>'
                    f'<span class="bar-value">{"—" if v is None else v}</span></div>')
    return f'<div class="bars" role="img" aria-label="{e(label)}: {e("; ".join(aria))}">{"".join(rows)}<div class="bar-scale" aria-hidden="true"><span></span><span class="ticks"><span>0</span><span>1</span><span>2</span><span>3</span><span>4</span></span><span></span></div></div>'


# --------------------------------------------------------------------------- 04 responses

def provenance_list(r: dict) -> str:
    if r["kind"] == "illustrative":
        rows = [("Model", "None. A constructed calibration example"),
                ("Source", f'{r["source"]}, {doc_link("evaluator-criteria", "Evaluator Interpretations and Assessment Criteria")}'),
                ("Prompt", "The same broad Nordland essay assignment"),
                ("Test date and settings", "Not applicable"),
                ("Stated length", e(r["stated_length"])),
                ("Words (counted)", str(r["word_count"]))]
        return "".join(f"<div><dt>{e(k)}</dt><dd>{v}</dd></div>" for k, v in rows)
    rows = [(label, r.get(k)) for k, label in PROVENANCE] + [("Words (counted)", r["word_count"])]
    return "".join(f"<div><dt>{e(k)}</dt><dd>{e(v) if v not in (None, '') else '<span class=muted>Not recorded</span>'}</dd></div>" for k, v in rows)


def response_article(r: dict) -> str:
    n_ev = sum(1 for ev in ALL_EVALS if ev["response_id"] == r["id"])
    first = next((ev["id"] for ev in ALL_EVALS if ev["response_id"] == r["id"]), None)
    ev_link = (f'<a href="evaluations.html#ev-{e(first)}">{n_ev} recorded evaluation{"s" if n_ev != 1 else ""}</a>' if n_ev
               else '<span class="muted">No recorded evaluations</span>')
    notes = f'<p class="fine-print">Collection notes: {e(r["notes"])}</p>' if r.get("notes") else ""
    status = f'<div class="record-status">{prose(r["status_note"])}</div>' if r.get("status_note") else ""
    return f"""<article class="record record--{r['kind']}" id="{e(r['id'])}" aria-labelledby="{e(r['id'])}-title">
  <div class="record-head"><div>{kind_tag(r['kind'])}<h3 id="{e(r['id'])}-title">{e(r['title'])}</h3></div><span class="id">{e(r['id'])}</span></div>
  <dl class="provenance">{provenance_list(r)}</dl>
  <div class="verbatim">
    <p class="verbatim-label">{'Full response · wording preserved from the source document' if r['kind'] == 'illustrative' else 'Full original response · unedited'}</p>
    <div class="prose response-text">{r['output_html']}</div>
  </div>
  <div class="record-foot">{status}{notes}
    <div class="record-actions"><a class="btn" href="score.html#evaluate-{e(r['id'])}">Score this response</a>
    <a class="btn btn--ghost" href="compare.html">Compare</a><span class="fine-print">{ev_link} · Text SHA-256 {r['sha256'][:12]}</span></div>
  </div>
</article>"""


def build_responses() -> None:
    sec42 = find_section(method, "4 Evaluation methodology")
    rules = "\n".join(re.search(rf"(?m)^- \*\*{re.escape(k)}\*\*.*$", sec42).group(0)
                      for k in ["Stable case and prompt.", "Transparent run metadata.", "Unassisted first response."])
    if EXP_RESPONSES:
        experimental = "".join(response_article(r) for r in EXP_RESPONSES)
    else:
        experimental = placeholder("No experimental responses have been collected",
            "<p>No model has yet been run on the Nordland Case Record for this study. Genuine outputs will appear here, in full and unedited, "
            "with the model name and version, test date, generation settings and the exact prompt used.</p>"
            "<p>Responses are added to <code>data/responses.json</code> and the site is regenerated with <code>python build.py</code>.</p>",
            "No records")
    illustrative = "".join(response_article(r) for r in ILL_RESPONSES)
    main = f"""<section aria-labelledby="conditions">{h2("conditions", "4.1", "Prompt and test conditions")}{material_tag("evidence")}
<p>Every experimental run receives the same input: the complete <a href="case-record.html">Nordland Case Record</a>, ending with this essay assignment, and nothing else.</p>
<blockquote class="assignment-quote"><p>{e(ASSIGNMENT)}</p></blockquote>
<p class="fine-print">Case/prompt identifier: {e(CASE_ID)} · {doc_link("case-record", "Open the PDF")}</p>
<div class="quoted-rules"><p class="kicker">From the methodology, §4.2</p>{prose(rules)}</div>
</section><hr>
<section aria-labelledby="experimental">{h2("experimental", "4.2", "Experimental responses")}{material_tag("findings", "Genuine model outputs")}
<p>Outputs collected from identified AI models under the conditions above. Ordinary and unsuccessful responses are recorded as well as strong ones.</p>
{experimental}</section><hr>
<section aria-labelledby="illustrative">{h2("illustrative", "4.3", "Illustrative examples")}{material_tag("illustrative")}
<p>The three constructed essays from Appendix A of {doc_link("evaluator-criteria", "Nordland: Evaluator Interpretations and Assessment Criteria")}, reproduced so that the scoring and comparison tools can be learned and calibrated. They are not experimental results.</p>
{illustrative}</section>"""
    items = [("conditions", "Prompt and test conditions", 2), ("experimental", "Experimental responses", 2)] + \
            [(r["id"], r["id"], 3) for r in EXP_RESPONSES] + [("illustrative", "Illustrative examples", 2)] + \
            [(r["id"], r["title"].split(" — ")[0], 3) for r in ILL_RESPONSES]
    body = page_head("04", "Model Responses",
                     "Complete model responses to the Nordland essay assignment, each with its provenance and test conditions. Genuine experimental outputs and constructed illustrative examples are kept in separate, labelled groups.",
                     [("Experimental responses", str(len(EXP_RESPONSES))), ("Illustrative examples", str(len(ILL_RESPONSES)))],
                     materials=["findings", "illustrative"])
    body += doc_layout(toc(items), main)
    page("responses", "Model Responses", "Complete model responses to the Nordland case, with provenance and test conditions.", body,
         checks=[(r["output_markdown"], r["id"]) for r in ALL_RESPONSES] + [(ASSIGNMENT, "Assignment")])


# --------------------------------------------------------------------------- 05 evaluations

def score_of(ev: dict, roman: str):
    s = (ev.get("scores") or {}).get(roman) or {}
    return s.get("score")


def evaluation_article(ev: dict) -> str:
    resp = next(r for r in ALL_RESPONSES if r["id"] == ev["response_id"])
    rows = []
    for d in dims:
        s = ev["scores"].get(d["roman"]) or {}
        v = s.get("score")
        excerpts = "".join(f"<li>{e(x)}</li>" for x in s.get("excerpts") or [])
        rows.append(f"""<tr><th scope="row">{d['roman']}. {e(d['name'])}</th><td class="num">{'—' if v is None else f'{v}/4'}</td>
<td>{e(s.get('rationale', ''))}{f'<p class="cell-label">Supporting excerpts</p><ul class="excerpts">{excerpts}</ul>' if excerpts else ''}{f'<p class="cell-label">Weaknesses or uncertainty</p><p>{e(s["weaknesses"])}</p>' if s.get('weaknesses') else ''}
<p class="cell-anchor">{'' if v is None else f'Anchor {v}: {e(d["anchors"][v])}'}</p></td></tr>""")
    total = ev.get("total_secondary")
    extra = "".join(f"<dt>{e(lbl)}</dt><dd>{e(ev[k])}</dd>" for k, lbl in [("overall_summary", "Overall evaluation summary")] + SYNTHESIS + [("calibration_note", "Calibration note")] if ev.get(k))
    meta = " · ".join(x for x in [ev.get("evaluator"), ev.get("date"), "blind to model" if ev.get("blind_to_model") else "", ev.get("source", "")] if x)
    return f"""<article class="record record--{ev['evaluation_kind']}" id="ev-{e(ev['id'])}">
  <div class="record-head"><div>{kind_tag(ev['evaluation_kind']) if ev['evaluation_kind'] == 'illustrative' else material_tag('findings', 'Evaluation of a genuine output')}
  <h3>Evaluation of <a href="responses.html#{e(resp['id'])}">{e(resp['title'])}</a></h3></div><span class="id">{e(meta)}</span></div>
  <div class="eval-grid"><div>{score_bars(ev['scores'], 'Score profile')}<p class="eval-total"><span>Total (secondary)</span> <strong>{'—' if total is None else total}</strong> / 20</p></div>
  <div class="table-wrap" role="region" tabindex="0" aria-label="Scores, rationales and anchors"><table class="eval-table"><thead><tr><th scope="col">Dimension</th><th scope="col" class="num">Score</th><th scope="col">Evaluator rationale and evidence</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></div>
  {f'<dl class="notes-list">{extra}</dl>' if extra else ''}
</article>"""


def build_evaluations() -> None:
    if EXP_EVALS:
        experimental = "".join(evaluation_article(ev) for ev in EXP_EVALS)
    else:
        experimental = placeholder("No experimental evaluations have been recorded",
            "<p>Evaluations of genuine model outputs will appear here once responses have been collected and independently scored. "
            "Each will show its five dimension scores, the evaluator’s passage-specific rationale and supporting excerpts, and the rubric anchor for each score.</p>"
            '<p>To record one, score a response on the <a href="score.html">Score a response</a> tab, download the JSON, and add it to <code>data/evaluations.json</code> in the repository.</p>',
            "No records")
    illustrative = "".join(evaluation_article(ev) for ev in ILL_EVALS)
    main = (eval_tabs("evaluations") +
            f'<section aria-labelledby="ev-experimental">{h2("ev-experimental", "5.1", "Evaluations of experimental responses")}{material_tag("findings")}{experimental}</section><hr>'
            f'<section aria-labelledby="ev-illustrative">{h2("ev-illustrative", "5.2", "Illustrative calibration judgments")}{material_tag("illustrative")}'
            f'<p>The explained scores for the three constructed essays, from Appendix A of the rubric document. The document describes them as “proposed calibration judgments, not validated performance measurements.”</p>'
            f'{illustrative}</section>')
    if "proposed calibration judgments, not validated performance measurements" not in eval_src:
        raise RuntimeError("Appendix A status wording changed")
    body = page_head("05", "Evaluations",
                     "Dimension-level scores with documented rationales, each traceable to its response, the rubric anchor and the evaluator’s evidence. The five-score profile is the primary result; the total out of 20 is a secondary summary.",
                     [("Experimental evaluations", str(len(EXP_EVALS))), ("Illustrative calibration judgments", str(len(ILL_EVALS))),
                      ("Rubric", f'{doc_link("evaluator-criteria", "Evaluator Interpretations and Assessment Criteria")} §5')],
                     materials=["findings", "illustrative"])
    body += doc_layout(toc([("ev-experimental", "Experimental evaluations", 2), ("ev-illustrative", "Illustrative calibration judgments", 2)]), main)
    page("evaluations", "Evaluations", "Recorded evaluations of model responses to the Nordland case, traceable to response, rubric and evidence.", body)


def build_score() -> None:
    dims_html = []
    for d in dims:
        r = d["roman"]
        options = "".join(
            f'<label class="anchor-option"><input type="radio" name="score_{r}" value="{i}" data-dim="{r}">'
            f'<span class="anchor-level">{i}</span><span class="anchor-text">{e(d["anchors"][i])}</span></label>' for i in range(5))
        dims_html.append(f"""<fieldset class="dim-card" id="dim-{r}" data-dim="{r}">
  <legend><span class="roman">{r}.</span> {e(d['name'])} — {e(d['subtitle'])}</legend>
  <p class="dim-focus">{e(d.get('focus', ''))}</p>
  <div class="anchor-options" role="radiogroup" aria-label="Score for {e(d['name'])}, 0 to 4">{options}</div>
  <button type="button" class="link-btn" data-clear-score="{r}">Clear score</button>
  <div class="dim-fields">
    <label class="field" for="rationale_{r}">Evaluator rationale<span class="hint">Cite specific passages and give a one- or two-sentence reason. For a 4, state the step beyond level 3.</span>
      <textarea id="rationale_{r}" data-field="rationale" data-dim="{r}" rows="3"></textarea></label>
    <div class="field">
      <label for="excerpts_{r}">Supporting excerpts from the response<span class="hint">Paste exact wording, one excerpt per paragraph (separate with a blank line), or select text in the response and use the button.</span></label>
      <textarea id="excerpts_{r}" data-field="excerpts" data-dim="{r}" rows="3"></textarea>
      <div class="excerpt-tools"><button type="button" class="btn btn--ghost btn--small" data-add-selection="{r}">Add selected response text</button><span class="excerpt-check" data-excerpt-check="{r}" aria-live="polite"></span></div>
    </div>
    <label class="field" for="weaknesses_{r}">Weaknesses, uncertainty or unresolved questions
      <textarea id="weaknesses_{r}" data-field="weaknesses" data-dim="{r}" rows="2"></textarea></label>
  </div>
  <ul class="dim-warnings" data-warnings="{r}" aria-live="polite"></ul>
</fieldset>""")
    synth = "".join(f'<label class="field" for="{k}">{e(lbl)}<textarea id="{k}" data-meta="{k}" rows="2"></textarea></label>' for k, lbl in SYNTHESIS)
    main = eval_tabs("score") + f"""
<noscript><p class="notice">The scoring tool needs JavaScript. The rubric itself is on the <a href="rubric.html">Evaluation Rubric</a> page.</p></noscript>
{notice("How evaluations are saved",
        "Your work stays in this browser: a draft is kept in local storage until you clear it, and nothing is sent anywhere. "
        "Nothing you do here changes the published site or the GitHub repository. To keep an evaluation, download the JSON record and the readable report. "
        "To publish it, add the JSON record to <code>data/evaluations.json</code> in the repository and rebuild.")}
<form id="score-tool" class="score-tool" autocomplete="off" novalidate>
  <div class="tool-setup">
    <label class="field" for="response_select">Response to score
      <select id="response_select" data-meta="response_id"></select></label>
    <div class="selected-kind" id="selected-kind" aria-live="polite"></div>
  </div>
  <div class="tool-layout">
    <section class="tool-response" aria-labelledby="response-heading">
      <details class="response-panel" open><summary id="response-heading">Response text</summary>
        <div class="response-meta" id="response-meta"></div>
        <div class="prose response-text" id="response-text" tabindex="0" aria-label="Full response text"></div>
      </details>
    </section>
    <div class="tool-form">
      <fieldset class="meta-card"><legend>Scoring record</legend>
        <div class="scorer-meta">
          <label class="field" for="case_prompt_identifier">Case/prompt identifier<input id="case_prompt_identifier" data-meta="case_prompt_identifier"></label>
          <label class="field" for="model_run">Model and run identifier<input id="model_run" data-meta="model_run"></label>
          <label class="field" for="evaluator">Evaluator<input id="evaluator" data-meta="evaluator" placeholder="Name or assessor identifier"></label>
          <label class="field" for="date">Date<input id="date" type="date" data-meta="date"></label>
          <label class="check"><input type="checkbox" id="blind_to_model" data-meta="blind_to_model"> Scored blind to model identity</label>
        </div>
      </fieldset>
      <p class="fine-print">{e(re.sub(r"[*]", "", rubric_coda))} Anchors are quoted from {doc_link("evaluator-criteria", "the rubric document")} §5.</p>
      {''.join(dims_html)}
      <section class="summary-card" aria-labelledby="summary-heading">
        <h3 id="summary-heading">Evaluation summary</h3>
        <div id="score-chart"></div>
        <p class="eval-total" aria-live="polite"><span>Total (secondary)</span> <strong id="score-total">—</strong> / 20 <span class="state" id="score-state"></span></p>
        <label class="field" for="overall_summary">Overall evaluation summary<textarea id="overall_summary" data-meta="overall_summary" rows="4"></textarea></label>
        <div class="synthesis">{synth}</div>
        <ul class="dim-warnings" id="record-warnings" aria-live="polite"></ul>
        <div class="btn-row">
          <button class="btn" type="button" id="download-json">Download JSON record</button>
          <button class="btn btn--ghost" type="button" id="download-report">Download readable report</button>
          <label class="btn btn--ghost file-btn" for="import-json">Load a JSON record</label>
          <input type="file" id="import-json" accept="application/json,.json" class="visually-hidden">
          <button class="btn btn--ghost" type="button" id="clear-form">Clear form</button>
        </div>
        <p class="status-message" id="tool-status" role="status" aria-live="polite"></p>
      </section>
    </div>
  </div>
</form>"""
    body = page_head("05", "Score a Response",
                     "Score any published response on the five official dimensions. Scores, anchors, rationales and supporting excerpts are recorded together so every score can be traced to its evidence.",
                     [("Rubric", f'{doc_link("evaluator-criteria", "Evaluator Interpretations and Assessment Criteria")} §5'), ("Scoring", "Manual; nothing is scored automatically")],
                     materials=["criteria"])
    body += f'<div class="section"><div class="container">{main}</div></div>'
    page("score", "Score a Response", "Interactive scoring tool for the Nordland rubric.", body, current="evaluations",
         extra_scripts=site_data_script() + '<script src="assets/js/evaluation.js" defer></script>\n',
         checks=[(f"{d['anchors'][i]}", f"anchor {d['roman']}{i}") for d in dims for i in range(5)])


def build_compare() -> None:
    main = eval_tabs("compare") + f"""
<noscript><p class="notice">The comparison tool needs JavaScript. Recorded evaluations are listed on the <a href="evaluations.html">Recorded evaluations</a> tab.</p></noscript>
{notice("Reading a comparison",
        "The five-score profile is the primary result; the total out of 20 is a secondary summary. A higher total is not, by itself, evidence of better conceptual reasoning. "
        "Read the evaluators’ rationales and evidence for each dimension before drawing conclusions. Differences are explained only by what evaluators wrote; this tool does not generate explanations or scores.")}
<div class="compare-setup">
  <fieldset class="compare-pick"><legend>Responses to compare (choose two or more)</legend><div id="compare-options"></div></fieldset>
  <div class="compare-load">
    <p class="fine-print">Add evaluations you have downloaded but not yet published. They are used only in this browser session and are labelled as unpublished.</p>
    <label class="btn btn--ghost file-btn" for="compare-import">Load evaluation JSON files</label>
    <input type="file" id="compare-import" accept="application/json,.json" multiple class="visually-hidden">
    <p class="status-message" id="compare-status" role="status" aria-live="polite"></p>
  </div>
</div>
<div id="compare-output" aria-live="polite"></div>
<div class="btn-row"><button class="btn btn--ghost" type="button" id="download-comparison">Download comparison report</button></div>"""
    body = page_head("05", "Compare Evaluations",
                     "Set two or more responses side by side: dimension scores, totals, the evaluators’ reasoning for each score, and agreement between evaluators where more than one evaluation exists.",
                     [("Basis", "Recorded evaluations and files you load")], materials=["findings", "illustrative"])
    body += f'<div class="section"><div class="container">{main}</div></div>'
    page("compare", "Compare Evaluations", "Compare evaluations of Nordland model responses dimension by dimension.", body, current="evaluations",
         extra_scripts=site_data_script() + '<script src="assets/js/evaluation.js" defer></script>\n')


# --------------------------------------------------------------------------- 06 findings

def build_findings() -> None:
    sec5 = find_section(method, "5 Validity")
    threats = re.search(r"(?ms)^### 5\.3 .*?\n(.*?)(?=^### )", sec5).group(1).strip()
    establish = re.search(r"(?ms)^### 5\.4 .*?\n(.*?)(?=^### )", sec5).group(1).strip()
    boundary = re.search(r"(?m)^> \*\*Research boundary:\*\*.*$", validity_src).group(0)
    abstract = find_section(method, "Abstract")
    no_findings = quote_from(abstract, "The study measures observable written performance, including independent problem formulation and substantive judgment, rather than hidden cognition; no experimental findings are reported.")

    if evaluations:
        models: dict[str, list] = {}
        resp_model = {r["id"]: r.get("model", "—") for r in responses}
        for ev in evaluations:
            models.setdefault(resp_model.get(ev.get("response_id"), "—"), []).append(ev)
        rows = ""
        for model, evs in models.items():
            cells = ""
            for r in ROMAN:
                vals = [score_of(ev, r) for ev in evs if score_of(ev, r) is not None]
                cells += f'<td class="num">{(sum(vals) / len(vals)):.1f}</td>' if vals else '<td class="num">—</td>'
            rows += f'<tr><th scope="row">{e(model)}</th><td class="num">{len(evs)}</td>{cells}</tr>'
        profile = (f'<div class="table-wrap" role="region" tabindex="0" aria-label="Mean scores by model"><table><caption>Mean dimension scores by model (descriptive)</caption>'
                   f'<thead><tr><th scope="col">Model</th><th scope="col" class="num">Evaluations</th>{"".join(f"<th scope=col class=num>{r}</th>" for r in ROMAN)}</tr></thead>'
                   f'<tbody>{rows}</tbody></table></div><p class="table-note">Generated from <code>data/evaluations.json</code>. Descriptive only; small samples support no inferential claims.</p>')
    else:
        profile = ""

    if findings_src:
        patterns = prose(findings_src, "f")
    else:
        patterns = placeholder("Comparative findings have not been written",
            "<p>No model responses have yet been collected or evaluated, so this study reports no comparative patterns, scores or conclusions. "
            "When evaluations exist, this section will compare dimension profiles across models and runs, describe where reasoning succeeded or failed, "
            "and report agreement between independent assessors where available.</p>"
            "<p>Researcher-written findings are added in <code>data/Nordland_Findings.md</code>.</p>", "Placeholder · awaiting evaluation")
    implications = placeholder("Implications will follow the findings",
        "<p>Implications for the welfare-state question and for evaluating conceptual reasoning in AI will be drawn only from completed evaluations, within the research boundary below.</p>",
        "Placeholder")
    limitations = (
        f'<p class="kicker">From the methodology, §5.4 What this research can establish</p><div class="prose">{prose(establish)}</div>'
        f'<p class="kicker">From the methodology, §5.3 Principal threats to validity</p><div class="prose">{prose(threats)}</div>'
        f'<p class="kicker">From the validity memorandum</p><div class="prose">{prose(boundary)}</div>'
        + site_note('The full set of validity questions (V01–V25), the next research steps and the post-prototype research program are on the '
                    '<a href="validity.html">Validity Questions and Next Research Steps</a> page.')
    )
    sections = [
        ("patterns", "6.1", "Comparative patterns", "findings", profile + patterns),
        ("limitations", "6.2", "Limitations", "interpretation", limitations),
        ("implications", "6.3", "Implications", "findings", implications),
    ]
    main = notice("Current status", e(no_findings) + f' ({doc_link("methodology", "Beyond Explanation")}, Abstract)')
    main += "".join(f'<section aria-labelledby="{a}">{h2(a, k, t)}{material_tag(kind)}{b}</section><hr>' for a, k, t, kind, b in sections).rsplit("<hr>", 1)[0]
    body = page_head("06", "Findings",
                     "What the evaluations show across models, the limits on what this pilot can establish, and the implications for both research questions.",
                     [("Status", "Findings pending" if not findings_src else "Published")],
                     materials=["findings"])
    body += doc_layout(toc([(a, t, 2) for a, _, t, _, _ in sections]), main)
    page("findings", "Findings", "Comparative findings, limitations and implications of the Nordland conceptual-reasoning study.", body,
         checks=[(establish, "Findings §5.4"), (threats, "Findings §5.3"), (boundary, "Findings boundary")])


# --------------------------------------------------------------------------- legacy redirects

def build_redirects() -> None:
    for old, new in [("case.html", "case-record.html"), ("evaluation.html", "rubric.html")]:
        (ROOT / old).write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Moved — {SITE}</title>
<meta name="robots" content="noindex"><meta http-equiv="refresh" content="0; url={new}"><link rel="canonical" href="{new}"></head>
<body><p>This page has moved to <a href="{new}">{new}</a>.</p></body></html>
""", encoding="utf-8")


def check_no_version_labels() -> None:
    """No version numbers or draft labels in any generated page's visible text or titles."""
    pattern = re.compile(r"\b(?:[vV]\d+(?:[._]\d+)+|[Vv]ersion \d|[Dd]raft \d|DRAFT)\b")
    for f in ROOT.glob("*.html"):
        text = BeautifulSoup(f.read_text(encoding="utf-8"), "html.parser")
        visible = text.get_text(" ") + " " + " ".join(a.get("href", "") for a in text.find_all("a"))
        m = pattern.search(visible)
        if m:
            raise RuntimeError(f"{f.name}: version or draft label in page content: {m.group(0)!r}")


if __name__ == "__main__":
    verify_documents()
    build_case_record()
    build_home()
    build_methodology()
    build_validity()
    build_rubric()
    build_responses()
    build_evaluations()
    build_score()
    build_compare()
    build_findings()
    build_redirects()
    check_no_version_labels()
    print("Built: index, case-record, methodology, validity, rubric, responses, evaluations, score, compare, findings (+ redirects case.html, evaluation.html)")
    print(f"Responses: {len(responses)} · Evaluations: {len(evaluations)} · Findings file: {'yes' if findings_src else 'no'}")
