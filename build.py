"""Build the Nordland research website (static HTML for GitHub Pages).

All research content lives in ``data/``:

    data/Nordland_Case_Record.md                                   model-facing (neutral)
    data/Nordland_Methodology.md                                   research design
    data/Nordland_Validity_Questions.md                            validity questions
    data/Nordland_Evaluator_Interpretations_and_Assessment_Criteria.md   evaluator-only
    data/responses.json                                            collected model outputs
    data/evaluations.json                                          dimension-level scores
    data/Nordland_Findings.md   (optional)                         researcher-written findings

Run from the repository root:

    python -m pip install -r requirements.txt
    python build.py

The generated HTML files are committed and served as-is; GitHub Pages needs no build step.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

import mistune
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
md = mistune.create_markdown(plugins=["table", "strikethrough"])

SITE = "Beyond Explanation"
AUTHOR = "Elaine Chou"

# (slug, number, title, short description, audience tag)
SECTIONS = [
    ("case-record", "01", "Case Record", "The fixed, neutral evidence and the broad essay prompt supplied to models.", "model"),
    ("methodology", "02", "Methodology", "Research questions, study design, conceptual reasoning evaluation and validity questions.", None),
    ("rubric", "03", "Evaluation Rubric", "Five scoring dimensions, 0–4 anchors, evaluator guidance and calibration examples.", "evaluator"),
    ("responses", "04", "Model Responses", "Original, unedited model outputs with provenance and test conditions.", None),
    ("evaluations", "05", "Evaluations", "Dimension-level scores, documented rationales and the scoring instrument.", "evaluator"),
    ("findings", "06", "Findings", "Comparative patterns, limitations and implications.", None),
]
ROMAN = ["I", "II", "III", "IV", "V"]


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
    for h in soup.find_all(["h2", "h3"]):
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
    return str(soup)


def split_h2(source: str) -> dict[str, str]:
    """Split Markdown into {heading: body} on level-2 headings (heading line removed)."""
    out: dict[str, str] = {}
    for block in re.split(r"(?m)^(?=## )", source):
        if block.startswith("## "):
            head, _, body = block.partition("\n")
            out[head[3:].strip()] = body.strip()
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


# --------------------------------------------------------------------------- page chrome

def head(title: str, description: str, *, robots: str | None = None) -> str:
    full = SITE if title == SITE else f"{title} — {SITE}"
    robots_tag = f'<meta name="robots" content="{robots}">' if robots else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full)}</title>
<meta name="description" content="{e(description)}">
<meta name="theme-color" content="#1b2f4b">
{robots_tag}
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
    sources = "".join(
        f'<li><a href="data/{f}">{e(label)}</a></li>'
        for f, label in [
            ("Nordland_Case_Record.md", "Case record (Markdown)"),
            ("Nordland_Methodology.md", "Methodology (Markdown)"),
            ("Nordland_Evaluator_Interpretations_and_Assessment_Criteria.md", "Evaluator criteria (Markdown)"),
            ("responses.json", "Model responses (JSON)"),
            ("evaluations.json", "Evaluations (JSON)"),
        ]
    )
    return f"""<footer class="site-footer">
  <div class="container">
    <div class="footer-grid">
      <div><span class="brand-name">Beyond Explanation</span>
        <p>A conceptual-reasoning study built on the Nordland welfare-state case. Research by {e(AUTHOR)}.</p>
        <p>Nordland is a fictional country. Constructed calibration examples are not model outputs or experimental results.</p></div>
      <div><h2>Sections</h2><ul>{links}</ul></div>
      <div><h2>Source files</h2><ul>{sources}</ul></div>
    </div>
    <div class="footer-base">Static site · no tracking · scoring tools run entirely in the browser.</div>
  </div>
</footer>"""


def page(slug: str, title: str, description: str, body: str, extra_scripts: str = "") -> None:
    doc = f"""{head(title, description)}
<body>
{site_header(slug)}
<main id="main">
{body}
</main>
{site_footer()}
{extra_scripts}<script src="assets/js/site.js" defer></script>
</body>
</html>
"""
    (ROOT / f"{slug}.html").write_text(doc, encoding="utf-8")


def page_head(number: str, title: str, lede: str, meta: list[tuple[str, str]] | None = None) -> str:
    meta_html = ""
    if meta:
        meta_html = '<ul class="page-meta">' + "".join(f"<li><strong>{e(k)}:</strong> {v}</li>" for k, v in meta) + "</ul>"
    return f"""<header class="page-head"><div class="container">
  <p class="eyebrow">Section {number}</p>
  <h1>{e(title)}</h1>
  <p class="lede">{lede}</p>{meta_html}
</div></header>"""


def toc(items: list[tuple[str, str, int]], title: str = "On this page") -> str:
    lis = "".join(
        f'<li{" class=\"toc-sub\"" if level > 2 else ""}><a href="#{anchor}">{e(label)}</a></li>'
        for anchor, label, level in items
    )
    return f'<nav class="toc" aria-label="{e(title)}"><p class="toc-title">{e(title)}</p><ol>{lis}</ol></nav>'


def doc_layout(toc_html: str, main_html: str) -> str:
    return f'<div class="section"><div class="container doc-layout">{toc_html}<div class="doc-main">{main_html}</div></div></div>'


def notice(title: str, text: str, kind: str = "") -> str:
    cls = f"notice notice--{kind}" if kind else "notice"
    return f'<aside class="{cls}"><strong>{title}</strong><p>{text}</p></aside>'


def placeholder(title: str, text: str, status: str = "Not yet available") -> str:
    return f'<div class="placeholder"><span class="status">{e(status)}</span><h3>{e(title)}</h3>{text}</div>'


def h2(anchor: str, kicker: str, title: str) -> str:
    return f'<p class="kicker">{e(kicker)}</p><h2 id="{anchor}">{e(title)}</h2>'


# --------------------------------------------------------------------------- sources

case_src = (DATA / "Nordland_Case_Record.md").read_text(encoding="utf-8")
method_src = (DATA / "Nordland_Methodology.md").read_text(encoding="utf-8")
validity_src = (DATA / "Nordland_Validity_Questions.md").read_text(encoding="utf-8")
eval_src = (DATA / "Nordland_Evaluator_Interpretations_and_Assessment_Criteria.md").read_text(encoding="utf-8")
findings_path = DATA / "Nordland_Findings.md"
findings_src = findings_path.read_text(encoding="utf-8") if findings_path.exists() else None

responses = load_json("responses.json", "responses")
evaluations = load_json("evaluations.json", "evaluations")

method = split_h2(method_src)
evaluator = split_h2(eval_src)


# --------------------------------------------------------------------------- rubric extraction

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

    # Integrity: every visible sentence of the record must be in the source.
    rendered = re.sub(r"\s+", " ", soup.get_text(" "))
    for line in body.splitlines():
        s = re.sub(r"^(\d+\.|#+)\s*", "", line.strip())
        if s and "|" not in s and re.sub(r"\s+", " ", s) not in rendered:
            raise RuntimeError(f"Case text missing from render: {s[:70]}")

    doc = f"""{head("Case Record", "The neutral Nordland case record and essay assignment, exactly as supplied to models.")}
<body class="case-body">
<a class="skip-link" href="#record">Skip to case record</a>
<div class="case-bar"><div class="container">
  <a class="back" href="index.html">← Beyond Explanation · Section 01</a>
  <div class="actions">
    <button class="btn btn--ghost" type="button" data-copy-template="case-raw">Copy record text</button>
    <a class="btn btn--ghost" href="data/Nordland_Case_Record.md" download>Download .md</a>
    <button class="btn btn--ghost" type="button" data-print>Print</button>
  </div>
</div></div>
<main id="main">
<article class="case-doc container" id="record" aria-labelledby="case-title">
  <aside class="case-frame" aria-label="About this page">This page reproduces the complete case record and essay assignment supplied to models, without interpretation, scoring criteria or evaluator notes. The copy and download controls provide the exact source text.</aside>
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
  <p class="figure-sub">Percentages stated in the Nordland case record, 2025. All values on a common 0–100% scale.</p>
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
  <figcaption id="fig-note">The measures come from different sources and units — residents’ incomes, filed claims and survey respondents — that the record states are not person-level linked. Placing them on one scale shows their coexistence; it does not imply a relationship between them.</figcaption>
  <details><summary>View as table</summary>
    <div class="table-wrap" role="region" tabindex="0" aria-label="Figure data"><table>
      <thead><tr><th scope="col">Measure</th><th scope="col">Comparison</th><th scope="col" class="num">First</th><th scope="col" class="num">Second</th></tr></thead>
      <tbody>{table_rows}</tbody></table></div>
  </details>
</figure>"""


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
    status = f"""<dl class="status-list">
  <div><dt>Case record</dt><dd>Fixed<small>Neutral record and prompt</small></dd></div>
  <div><dt>Model responses</dt><dd>{n_resp}<small>{'collected' if n_resp else 'Collection not yet begun'}</small></dd></div>
  <div><dt>Evaluations</dt><dd>{n_eval}<small>{'scored records' if n_eval else 'No scored responses yet'}</small></dd></div>
  <div><dt>Findings</dt><dd>{'Published' if findings_src else 'Pending'}<small>{'See section 06' if findings_src else 'Reported after evaluation'}</small></dd></div>
</dl>"""
    body = f"""<section class="hero"><div class="container">
  <p class="eyebrow">The Nordland study · Conceptual reasoning in AI</p>
  <h1>Beyond Explanation</h1>
  <p class="lede">A universal welfare state sharply reduces poverty, yet minority residents face higher benefit denials and report a weaker sense of belonging. This study asks how that paradox should be understood — and how well AI models can work that out for themselves.</p>
  <div class="btn-row"><a class="btn" href="case-record.html">Read the case record</a><a class="btn btn--ghost" href="methodology.html">Read the methodology</a></div>
  <p class="hero-byline">Research by {e(AUTHOR)}</p>
</div></section>

<section class="section"><div class="container">
  <div class="section-head"><p class="kicker">Research questions</p><h2>Two questions, inseparable by design</h2></div>
  <div class="question-grid">
    <div class="question"><p class="label">Primary · The welfare-state paradox</p>
      <blockquote>How can a strong welfare state sustain significant inequality despite its commitment to universal social protection?</blockquote>
      <p>Nordland’s redistributive achievements, unequal initial benefit-denial rates, high public support and weaker minority belonging can coexist. Their coexistence is not a logical contradiction; it is a problem about what counts as universality, access, fairness and institutional success.</p></div>
    <div class="question question--secondary"><p class="label">Secondary · Conceptual reasoning in AI</p>
      <blockquote>Can an AI model identify what most needs to be understood, discover consequential relationships, weigh competing interpretations and reach a defensible judgment — without being told the route?</blockquote>
      <p>Models receive only the neutral record and a broad prompt. Their essays are assessed on five separate dimensions of intellectual work, not on agreement with an expected answer.</p></div>
  </div>
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
  <div class="section-head"><p class="kicker">Separation of materials</p><h2>What models see, and what they do not</h2>
  <p>The integrity of the test depends on keeping the neutral case apart from the materials used to judge responses.</p></div>
  <div class="materials">
    <div class="model"><p class="label">Supplied to models</p><h3>Case record and prompt</h3>
      <p>Stipulated facts, measurements and study designs, followed by a broad essay assignment. No interpretations, theories, examples or rubric.</p>
      <p><a class="text-link" href="case-record.html">Case record</a></p></div>
    <div class="evaluator"><p class="label">Evaluator-only</p><h3>Interpretation and assessment</h3>
      <ul><li>Nonexclusive reference interpretations and evidentiary guardrails</li>
      <li>Five-dimension rubric with 0–4 anchors and protocol</li>
      <li>Three constructed calibration essays with explained scores</li></ul>
      <p>Published for methodological transparency, not access-controlled. Never supply these pages to a model before its first response is collected.</p>
      <p><a class="text-link" href="rubric.html">Evaluation rubric</a></p></div>
  </div>
</div></section>

<section class="section"><div class="container">
  <div class="section-head"><p class="kicker">Study status</p><h2>Where the research stands</h2>
  <p>This is a single-case pilot of a research method. Counts below are generated from the published data files.</p></div>
  {status}
</div></section>"""
    page("index", SITE, "The Nordland study: a welfare-state paradox and an evaluation of conceptual reasoning in AI models.", body)


# --------------------------------------------------------------------------- 02 methodology

def build_methodology() -> None:
    validity_body = re.sub(r"(?m)^## .*\n", "", validity_src, count=1)
    parts = [
        ("research-questions", "Research questions", find_section(method, "The inquiry")),
        ("conceptual-reasoning", "Conceptual reasoning evaluation", find_section(method, "What conceptual inquiry adds")),
        ("study-design", "Study design and protocol", find_section(method, "The open-ended evaluation protocol")),
        ("evidence", "Why the evidence is difficult", find_section(method, "Why the evidence is difficult")),
        ("validity", "Validity questions", validity_body),
        ("foundations", "Scholarly foundations", find_section(method, "Scholarly foundations")),
    ]
    items, html_parts = [], []
    for i, (anchor, title, src) in enumerate(parts, 1):
        body_html = prose(src, anchor)
        items.append((anchor, title, 2))
        for m in re.finditer(r'<h3 id="([^"]+)">(.*?)</h3>', body_html):
            items.append((m.group(1), re.sub("<[^>]+>", "", m.group(2)), 3))
        html_parts.append(f'<section class="prose" aria-labelledby="{anchor}">{h2(anchor, f"2.{i}", title)}{body_html}</section>')
    html_parts.insert(3, notice("Separation of materials",
        "The model-facing record is a standalone factual document. Interpretive notes, the rubric and constructed examples reside separately "
        'in the <a href="rubric.html">evaluator materials</a> and must not be supplied to a model during the initial test.'))
    html_parts.append('<p class="fine-print">Limitations and next research steps are reported with the <a href="findings.html#limitations">Findings</a>. '
                      'Source text: <a href="data/Nordland_Methodology.md">methodology</a>, <a href="data/Nordland_Validity_Questions.md">validity questions</a>. '
                      'The office-table arithmetic is independently checked by <code>verify_case.py</code>.</p>')
    body = page_head("02", "Methodology",
                     "How the study is designed: the questions it asks, the protocol for collecting unassisted responses, what conceptual reasoning means here, and the validity questions the project must answer.",
                     [("Design", "Single fictional case, open-ended essay"), ("Scoring", "Five dimensions, 0–4 each")])
    body += doc_layout(toc(items), "".join(html_parts))
    page("methodology", "Methodology", "Research questions, study design, conceptual reasoning evaluation and validity questions for the Nordland study.", body)


# --------------------------------------------------------------------------- 03 rubric

def build_rubric() -> None:
    matrix_head = "".join(f'<th scope="col">{n}<small>{lbl}</small></th>' for n, lbl in
                          [(0, "Absent / misleading"), (1, "Superficial"), (2, "Developing"), (3, "Strong"), (4, "Exceptional")])
    matrix_rows = "".join(
        f'<tr><th scope="row">{d["roman"]}. {e(d["name"])}</th>' + "".join(f"<td>{e(d['anchors'][i])}</td>" for i in range(5)) + "</tr>"
        for d in dims)
    matrix = (f'<div class="table-wrap" role="region" tabindex="0" aria-label="Scoring anchor matrix"><table class="anchor-matrix">'
              f'<caption>Scoring anchors by dimension and level</caption><thead><tr><th scope="col">Dimension</th>{matrix_head}</tr></thead>'
              f"<tbody>{matrix_rows}</tbody></table></div>"
              '<p class="table-note">Level labels summarise the general depth scale; the dimension-specific anchors govern scoring. Scroll horizontally on small screens.</p>')
    dim_html = "".join(
        f"""<div class="dimension" id="dim-{d['roman'].lower()}">
  <div class="dimension-head"><span class="roman">{d['roman']}</span><h3>{e(d['name'])}</h3></div>
  <p class="focus"><em>{e(d['subtitle'].capitalize())}.</em> {e(d.get('focus', ''))}</p>
  <dl class="anchor-list">{''.join(f'<dt>{i}</dt><dd>{e(d["anchors"][i])}</dd>' for i in range(5))}</dl>
</div>""" for d in dims)

    # Calibration essays: Appendix A split into its responses.
    appendix = find_section(evaluator, "Appendix A")
    app_intro, *app_parts = re.split(r"(?m)^(?=### )", appendix)
    calib = []
    for part in app_parts:
        title, _, body = part.partition("\n")
        title = title[4:].strip()
        meta = ""
        m = re.search(r"\*\*Total \(secondary\)\*\* \| \*\*(\d+ / 20)\*\*", body)
        if m:
            meta = f"Constructed · {m.group(1)}"
        calib.append(f'<details class="disclosure calibration-essay"><summary>{e(title)}<span class="summary-meta">{meta}</span></summary>'
                     f'<div class="disclosure-body prose">{prose(body, "cal-" + slugify(title)[:12], demote=1)}</div></details>')

    reference = []
    for prefix, label in [("1. Purpose", "Purpose and evaluation boundary"), ("2. The substantive problem", "The substantive problem: a reference framing"),
                          ("3. Nonexclusive", "Nonexclusive evaluator interpretations"), ("9. Interpretive conclusions", "Interpretive conclusions that may be defensible")]:
        reference.append(f'<details class="disclosure"><summary>{e(label)}</summary><div class="disclosure-body prose">'
                         f'{prose(find_section(evaluator, prefix), "ref-" + slugify(label)[:16], demote=1)}</div></details>')

    sections = [
        ("dimensions", "3.1", "Five scoring dimensions",
         prose(rubric_intro) + matrix + dim_html + f'<div class="prose">{prose(rubric_coda)}</div>'),
        ("separation", "3.2", "Keeping the dimensions separate", prose(separation)),
        ("guardrails", "3.3", "Evidentiary guardrails", prose(find_section(evaluator, "4. Evidentiary guardrails"))),
        ("protocol", "3.4", "Evaluator protocol", prose(find_section(evaluator, "7. Evaluator protocol"))),
        ("scoring-record", "3.5", "Scoring record template",
         prose(find_section(evaluator, "8. Scoring record")) +
         '<p class="fine-print">An interactive version of this record, with JSON and CSV export, is on the <a href="evaluations.html#instrument">Evaluations</a> page.</p>'),
        ("reference", "3.6", "Reference analysis",
         '<p>Plausible, nonexclusive interpretations and evidentiary limits. A reference for expert judgment, <strong>not an answer key</strong>.</p>' + "".join(reference)),
        ("calibration", "3.7", "Calibration examples",
         notice("Constructed, not collected.", "These three essays were written to illustrate performance levels for scorer training. "
                "They are not outputs from an identified AI system and are not experimental results. Real model outputs appear only under "
                '<a href="responses.html">Model Responses</a>.') + prose(app_intro) + "".join(calib)),
    ]
    items = [(a, t, 2) for a, _, t, _ in sections]
    main = notice("Evaluator-only material.",
                  "Do not give this page, its rubric, interpretations or calibration essays to a model before its first response is collected. "
                  "It is public for methodological transparency and is not access-controlled.", "evaluator")
    main += "".join(f'<section aria-labelledby="{a}" class="rubric-section">{h2(a, k, t)}<div class="prose-wide">{b}</div></section><hr>' for a, k, t, b in sections)
    main = main.rsplit("<hr>", 1)[0]
    main += '<p class="fine-print">Full source text: <a href="data/Nordland_Evaluator_Interpretations_and_Assessment_Criteria.md">Evaluator Interpretations and Assessment Criteria (Markdown)</a>.</p>'
    body = page_head("03", "Evaluation Rubric",
                     "Five independent dimensions of intellectual work, each scored from 0 to 4. The five-score profile is the primary result; the total out of 20 is a secondary summary.",
                     [("Audience", "Evaluators only"), ("Scale", "Ordinal 0–4 per dimension"), ("Total", "Secondary, out of 20")])
    body += doc_layout(toc(items), main)
    page("rubric", "Evaluation Rubric", "The five-dimension, 0–4 rubric used to evaluate model essays on the Nordland case, with evaluator guidance.", body)


# --------------------------------------------------------------------------- 04 responses

PROVENANCE = [
    ("model", "Model"), ("model_version", "Model version / snapshot"), ("provider", "Provider"),
    ("run_date", "Run date"), ("interface", "Interface / API"), ("settings", "Settings"),
    ("tools_available", "Tools available"), ("case_record_version", "Case record version"),
    ("collected_by", "Collected by"), ("word_count", "Word count"),
]


def build_responses() -> None:
    if responses:
        records = []
        for r in responses:
            prov = "".join(f"<div><dt>{e(label)}</dt><dd>{e(r.get(k) if r.get(k) not in (None, '') else '—')}</dd></div>" for k, label in PROVENANCE)
            notes = f'<div class="verbatim" style="border-top:1px solid var(--line)"><p class="verbatim-label">Collection notes</p><p>{e(r["notes"])}</p></div>' if r.get("notes") else ""
            records.append(f"""<article class="record" id="{e(r['id'])}">
  <div class="record-head"><h3>{e(r.get('model') or 'Model')} </h3><span class="id">{e(r['id'])}</span></div>
  <dl class="provenance">{prov}</dl>
  <div class="verbatim"><p class="verbatim-label">Original output · unedited</p><div class="prose">{prose(r.get('output_markdown', ''), r['id'])}</div></div>
  {notes}
</article>""")
        content = "".join(records)
    else:
        rows = "".join(f"<tr><th scope=\"row\">{e(label)}</th><td>—</td></tr>" for _, label in PROVENANCE)
        content = placeholder("No model responses have been collected yet",
            "<p>When collection begins, each run will be published here in full: the unedited output, together with its provenance and test conditions. "
            "Ordinary and unsuccessful responses are recorded as well as strong ones.</p>"
            "<p>Responses are added to <code>data/responses.json</code> and the page is regenerated with <code>python build.py</code>.</p>",
            "Placeholder · awaiting data")
        content += f"""<h3>Provenance recorded for every run</h3>
<p>Each published response will carry the following fields, following the evaluator protocol (Section 3.4).</p>
<div class="table-wrap" role="region" tabindex="0" aria-label="Provenance fields"><table><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>{rows}
<tr><th scope="row">Prompt supplied</th><td>Case record and essay assignment, unmodified</td></tr></tbody></table></div>"""
    main = f"""{notice("Test conditions",
        'Every model receives the same input: the <a href="case-record.html">neutral case record</a> and its broad essay assignment (≤ 1,500 words; charts, tables and diagrams permitted). '
        'No evaluator interpretations, rubric or examples are supplied. Outputs are published without editing.')}
<p class="fine-print">The three essays on the Rubric page are <a href="rubric.html#calibration">constructed calibration examples</a>, not model responses, and are deliberately not listed here.</p>
{content}"""
    body = page_head("04", "Model Responses",
                     "Original model outputs to the Nordland essay assignment, each published with its provenance and test conditions.",
                     [("Responses collected", str(len(responses))), ("Prompt", "Fixed, identical for every run")])
    body += f'<div class="section"><div class="container"><div class="measure-wide">{main}</div></div></div>'
    page("responses", "Model Responses", "Original model outputs to the Nordland case, with provenance and test conditions.", body)


# --------------------------------------------------------------------------- 05 evaluations

def score_of(ev: dict, roman: str):
    s = (ev.get("scores") or {}).get(roman) or {}
    return s.get("score")


def build_evaluations() -> None:
    by_id = {r["id"]: r for r in responses}
    if evaluations:
        head_cells = "".join(f'<th scope="col" class="num" title="{e(d["name"])}">{d["roman"]}</th>' for d in dims)
        rows = []
        for ev in evaluations:
            resp = by_id.get(ev.get("response_id"), {})
            scores = [score_of(ev, r) for r in ROMAN]
            total = sum(scores) if all(s is not None for s in scores) else None
            cells = "".join(f'<td class="num">{"—" if s is None else s}</td>' for s in scores)
            rows.append(f'<tr><th scope="row"><a href="#ev-{e(ev.get("response_id"))}-{e(slugify(ev.get("evaluator", "")))}">{e(ev.get("response_id"))}</a></th>'
                        f'<td>{e(resp.get("model", "—"))}</td><td>{e(ev.get("evaluator", "—"))}</td>{cells}<td class="num"><strong>{"—" if total is None else total}</strong></td></tr>')
        summary = (f'<div class="table-wrap" role="region" tabindex="0" aria-label="Score profiles"><table><caption>Dimension-level score profiles</caption>'
                   f'<thead><tr><th scope="col">Response</th><th scope="col">Model</th><th scope="col">Evaluator</th>{head_cells}<th scope="col" class="num">Total / 20</th></tr></thead>'
                   f'<tbody>{"".join(rows)}</tbody></table></div>')
        details = []
        for ev in evaluations:
            dim_rows = "".join(
                f'<tr><th scope="row">{d["roman"]}. {e(d["name"])}</th><td class="num">{"—" if score_of(ev, d["roman"]) is None else score_of(ev, d["roman"])}</td>'
                f'<td>{e(((ev.get("scores") or {}).get(d["roman"]) or {}).get("rationale", ""))}</td></tr>' for d in dims)
            notes = "".join(f"<dt>{e(lbl)}</dt><dd>{e(ev[k])}</dd>" for k, lbl in SYNTHESIS if ev.get(k))
            details.append(f"""<article class="record" id="ev-{e(ev.get('response_id'))}-{e(slugify(ev.get('evaluator', '')))}">
  <div class="record-head"><h3>Evaluation of <a href="responses.html#{e(ev.get('response_id'))}">{e(ev.get('response_id'))}</a></h3>
  <span class="id">{e(ev.get('evaluator', ''))} · {e(ev.get('date', ''))}{' · blind to model' if ev.get('blind_to_model') else ''}</span></div>
  <div class="verbatim"><div class="table-wrap" role="region" tabindex="0" aria-label="Scores and rationales"><table><thead><tr><th scope="col">Dimension</th><th scope="col" class="num">Score</th><th scope="col">Passage-specific rationale</th></tr></thead><tbody>{dim_rows}</tbody></table></div>
  {f'<dl class="anchor-list" style="margin-left:0">{notes}</dl>' if notes else ''}</div>
</article>""")
        content = summary + "".join(details)
    else:
        content = placeholder("No evaluations have been recorded yet",
            "<p>Scores will appear here once model responses have been collected and independently assessed. Each evaluation will show the five dimension scores, "
            "a passage-specific rationale for each, the secondary total, and the evaluator’s synthesis notes.</p>"
            "<p>The scores attached to the three constructed calibration essays are training illustrations, not evaluations, and are shown only on the "
            '<a href="rubric.html#calibration">Rubric</a> page.</p>', "Placeholder · awaiting data")

    options = '<option value="">—</option>' + "".join(f'<option value="{i}">{i}</option>' for i in range(5))
    score_rows = "".join(f"""<div class="score-row" data-dim="{d['roman']}">
  <div><h4>{d['roman']}. {e(d['name'])}</h4><p class="fine-print" style="margin:4px 0 0">{e(d.get('focus', ''))}</p></div>
  <label class="field">Score (0–4)<select name="score_{d['roman']}" data-score="{d['roman']}">{options}</select></label>
  <p class="anchor-now" data-anchor aria-live="polite">No score selected.</p>
  <label class="field field--rationale">Passage-specific evidence and rationale<span class="hint">Quote or locate the passage; for a 4, state the step beyond level 3.</span>
    <textarea name="rationale_{d['roman']}" rows="3"></textarea></label>
</div>""" for d in dims)
    synth = "".join(f'<label class="field">{e(lbl)}<textarea name="{k}" rows="3"></textarea></label>' for k, lbl in SYNTHESIS)
    instrument = f"""<form class="scorer" id="score-form" autocomplete="off" novalidate>
  <div class="scorer-meta">
    <label class="field">Response ID<input name="response_id" placeholder="e.g. R-001"></label>
    <label class="field">Evaluator<input name="evaluator" placeholder="Assessor identifier"></label>
    <label class="field">Date<input name="date" type="date"></label>
    <label class="check"><input type="checkbox" name="blind_to_model"> Scored blind to model identity</label>
  </div>
  {score_rows}
  <div class="score-total" aria-live="polite"><div><div class="fine-print">Secondary total</div><span class="total" id="score-total">0</span> <span class="fine-print">/ 20</span></div><span class="state" id="score-state">0 of 5 dimensions scored</span></div>
  <div class="synthesis">{synth}</div>
  <div class="btn-row scorer-actions">
    <button class="btn" type="button" id="export-json">Export JSON</button>
    <button class="btn btn--ghost" type="button" id="export-csv">Export CSV</button>
    <button class="btn btn--ghost" type="button" id="copy-record">Copy JSON</button>
    <button class="btn btn--ghost" type="button" id="reset-form">Clear form</button>
  </div>
  <p class="status-message" data-status role="status" aria-live="polite"></p>
  <p class="fine-print">Scoring runs entirely in your browser; nothing is transmitted or saved automatically. The JSON export matches the record format in <code>data/evaluations.json</code>.</p>
</form>"""
    main = (f'<section aria-labelledby="scores">{h2("scores", "5.1", "Recorded evaluations")}{content}</section><hr>'
            f'<section aria-labelledby="instrument">{h2("instrument", "5.2", "Scoring instrument")}'
            + notice("Evaluator-only.", "Score each dimension independently, citing specific passages. Score unseen responses before consulting the calibration examples. "
                     'Anchors are from the <a href="rubric.html#dimensions">rubric</a>.', "evaluator")
            + instrument + "</section>")
    body = page_head("05", "Evaluations",
                     "Dimension-level scores for each collected response, with documented evaluator rationales. The five-score profile is the primary result.",
                     [("Evaluations recorded", str(len(evaluations))), ("Protocol", '<a href="rubric.html#protocol">Section 3.4</a>')])
    body += doc_layout(toc([("scores", "Recorded evaluations", 2), ("instrument", "Scoring instrument", 2)]), main)
    rubric_js = json.dumps([{"roman": d["roman"], "name": d["name"], "anchors": d["anchors"]} for d in dims], ensure_ascii=False).replace("<", "\\u003c")
    page("evaluations", "Evaluations", "Dimension-level scores and evaluator rationales for model responses to the Nordland case.", body,
         f"<script>window.NORDLAND_RUBRIC = {rubric_js};</script>\n")


SYNTHESIS = [
    ("governing_thesis", "Governing thesis observed"),
    ("consequential_insight", "Most consequential insight or omission"),
    ("disconfirming_evidence", "Disconfirming evidence considered or overlooked"),
    ("unexpected_interpretation", "Unexpected interpretation and disposition"),
    ("assessor_uncertainty", "Assessor confidence / unresolved calibration issue"),
]


# --------------------------------------------------------------------------- 06 findings

def build_findings() -> None:
    limits = find_section(method, "Limits and next research steps")
    boundary = re.search(r"(?m)^\*\*Reporting boundary:\*\*.*$", validity_src).group(0)

    if evaluations:
        models = {}
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
            "and report agreement between independent assessors.</p>"
            "<p>Researcher-written findings are added in <code>data/Nordland_Findings.md</code>.</p>", "Placeholder · awaiting evaluation")
    implications = placeholder("Implications will follow the findings",
        "<p>Implications for the welfare-state question and for evaluating conceptual reasoning in AI will be drawn only from completed evaluations, within the reporting boundary below.</p>",
        "Placeholder")
    sections = [
        ("patterns", "6.1", "Comparative patterns", profile + patterns),
        ("limitations", "6.2", "Limitations", f'<div class="prose">{prose(limits)}{prose(boundary)}</div>'),
        ("implications", "6.3", "Implications", implications),
    ]
    main = "".join(f'<section aria-labelledby="{a}">{h2(a, k, t)}{b}</section><hr>' for a, k, t, b in sections).rsplit("<hr>", 1)[0]
    body = page_head("06", "Findings",
                     "What the evaluations show across models, the limits on what this pilot can establish, and the implications for both research questions.",
                     [("Status", "Findings pending" if not findings_src else "Published")])
    body += doc_layout(toc([(a, t, 2) for a, _, t, _ in sections]), main)
    page("findings", "Findings", "Comparative findings, limitations and implications of the Nordland conceptual-reasoning study.", body)


# --------------------------------------------------------------------------- legacy redirects

def build_redirects() -> None:
    for old, new in [("case.html", "case-record.html"), ("evaluation.html", "rubric.html")]:
        (ROOT / old).write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Moved — {SITE}</title>
<meta name="robots" content="noindex"><meta http-equiv="refresh" content="0; url={new}"><link rel="canonical" href="{new}"></head>
<body><p>This page has moved to <a href="{new}">{new}</a>.</p></body></html>
""", encoding="utf-8")


if __name__ == "__main__":
    build_case_record()
    build_home()
    build_methodology()
    build_rubric()
    build_responses()
    build_evaluations()
    build_findings()
    build_redirects()
    print("Built: index, case-record, methodology, rubric, responses, evaluations, findings (+ redirects case.html, evaluation.html)")
    print(f"Responses: {len(responses)} · Evaluations: {len(evaluations)} · Findings file: {'yes' if findings_src else 'no'}")
