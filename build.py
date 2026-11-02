"""Build Nordland's dependency-free GitHub Pages website from stable source names.

Run: python -m pip install -r requirements.txt && python build.py
The prebuilt HTML files may be published directly, without running this script.
All research text is read from the Markdown files in data/; this script only
arranges it into pages. Interface labels are the only text written here.
"""
from pathlib import Path
import html
import json
import re
from bs4 import BeautifulSoup
import mistune

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
md = mistune.create_markdown(plugins=['table', 'strikethrough'])


def e(s):
    return html.escape(str(s), quote=True)


def inline(source):
    """Render a single Markdown fragment without the wrapping paragraph."""
    out = md(source.strip()).strip()
    if out.startswith('<p>') and out.endswith('</p>') and out.count('<p>') == 1:
        out = out[3:-4]
    return out


def prose(source):
    """Readable semantic Markdown converted to HTML, with scrollable tables."""
    soup = BeautifulSoup(md(source), 'html.parser')
    for table in soup.find_all('table'):
        wrapper = soup.new_tag('div', attrs={'class': 'table-scroll', 'role': 'region', 'tabindex': '0',
                                             'aria-label': 'Scrollable data table'})
        table.wrap(wrapper)
    return str(soup)


def md_sections(source, level=2):
    """Split Markdown into an ordered {heading: body} map at the given heading level."""
    marker = '#' * level + ' '
    out = {}
    for chunk in re.split(rf'(?m)^(?={re.escape(marker)})', source):
        if chunk.startswith(marker):
            head, _, body = chunk.partition('\n')
            out[head[len(marker):].strip()] = body.strip()
    return out


ASSET_VERSION = '2'


def base_head(title, description):
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{e(description)}"><meta name="theme-color" content="#faf8f3">
<title>{e(title)} — Nordland Research</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Noto+Serif:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/styles.css?v={ASSET_VERSION}">
<script>document.documentElement.classList.add('js')</script></head>'''


NAV = [
    ('index.html#question', 'Research question', 'home'),
    ('index.html#case', 'The case', 'home'),
    ('index.html#methodology', 'Methodology', 'home'),
    ('index.html#criteria', 'Criteria', 'home'),
    ('evaluation.html#rubric', 'Rubric', 'evaluation'),
    ('evaluation.html#calibration', 'Assessments', 'evaluation'),
    ('evaluation.html#validity', 'Validity', 'evaluation'),
]


def header(current='home'):
    groups = {'home': 'Research', 'evaluation': 'Evaluation'}
    links = []
    last = None
    for href, label, page in NAV:
        if page != last:
            if last is not None:
                links.append('</ul></div>')
            cur = ' aria-current="page"' if page == current else ''
            links.append(f'<div class="nav-group"><a class="nav-group-label" href="{page}.html"{cur}>{groups[page]}</a><ul>')
            last = page
        links.append(f'<li><a href="{href}">{label}</a></li>')
    links.append('</ul></div>')
    return f'''<header class="site-header"><div class="wrap header-inner">
<a class="brand" href="index.html"><span class="brand-name">Nordland</span><span class="brand-sub">Beyond Explanation</span></a>
<button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav">Menu</button>
<nav class="nav" id="site-nav" aria-label="Main site navigation">{''.join(links)}
<a class="nav-case" href="case.html">Read neutral case</a></nav>
<div class="utility" role="group" aria-label="Text size controls"><button type="button" class="font-btn" data-font-adjust="-1" aria-label="Decrease text size">A−</button><button type="button" class="font-btn" data-font-adjust="1" aria-label="Increase text size">A+</button></div>
</div></header>'''


def toc(items, label):
    lis = ''.join(f'<li><a href="#{i}"><span class="toc-num">{n}</span>{t}</a></li>' for n, i, t in items)
    return f'<aside class="toc" aria-label="{e(label)}"><p class="toc-label">{e(label)}</p><ol>{lis}</ol></aside>'


def section_head(num, kicker, title, intro=None, hid=None):
    h = f'<header class="section-head"><p class="kicker"><span class="kicker-num">{num}</span>{kicker}</p><h2{f" id={chr(34)}{hid}{chr(34)}" if hid else ""}>{title}</h2>'
    if intro:
        h += f'<p class="section-intro">{intro}</p>'
    return h + '</header>'


def footer():
    return '''<footer class="site-footer"><div class="wrap footer-inner"><div><a class="brand" href="index.html"><span class="brand-name">Nordland</span></a><p>Beyond Explanation · An open-ended conceptual-reasoning research prototype</p><p>Research: Elaine Chou</p></div>
<div><ul class="footer-links"><li><a href="index.html#methodology">Methodology</a></li><li><a href="evaluation.html">Evaluator materials</a></li><li><a href="case.html">Neutral case record</a></li></ul>
<p>The case is fictional. Illustrative examples are constructed, not experimental findings.</p></div></div></footer>'''


case_src = (DATA / 'Nordland_Case_Record.md').read_text(encoding='utf-8')
eval_src = (DATA / 'Nordland_Evaluator_Interpretations_and_Assessment_Criteria.md').read_text(encoding='utf-8')
method_src = (DATA / 'Nordland_Methodology.md').read_text(encoding='utf-8')
validity_src = (DATA / 'Nordland_Validity_Questions.md').read_text(encoding='utf-8')

# ---------------------------------------------------------------- case page
# Case source is always neutral and preserved in its own original Markdown file.
case_body = case_src.replace('NORDLAND\n\nCase record\n\n', '', 1)
case_headings = ['Record definitions and scope', 'Founding and design', 'Outcomes and public opinion',
                 'Benefit decisions', 'Additional benefit-decision evidence', 'Employment', 'History', 'Essay assignment']
for heading in case_headings:
    case_body = re.sub(rf'(?m)^{re.escape(heading)}\s*$', f'\n## {heading}\n', case_body)
case_body = case_body.replace('Table A1. Benefit offices, 2025\n', '\n**Table A1. Benefit offices, 2025**\n\n')
# Normalize the list blocks so sections 6-8 / 9-12 / 13 / 14-15 stay exact and legible.
for num in range(1, 16):
    case_body = re.sub(rf'(?m)^{num}\. ', f'\n{num}. ', case_body)

case_soup = BeautifulSoup(prose(case_body), 'html.parser')
for h2 in case_soup.find_all('h2'):
    h2['id'] = re.sub(r'[^a-z0-9]+', '-', h2.get_text().lower()).strip('-')
# Mark the stipulation paragraph and the final assignment for distinct typographic treatment.
first_p = case_soup.find('p')
if first_p:
    first_p['class'] = 'case-stipulation'
assignment_h = case_soup.find('h2', id='essay-assignment')
if assignment_h:
    box = case_soup.new_tag('section', attrs={'class': 'case-assignment', 'aria-labelledby': 'essay-assignment'})
    nxt = list(assignment_h.find_next_siblings())
    assignment_h.wrap(box)
    for sib in nxt:
        box.append(sib.extract())
case_html = str(case_soup)
case_toc = ''.join(f'<li><a href="#{h["id"]}">{e(h.get_text())}</a></li>' for h in case_soup.find_all('h2'))

case = base_head('Neutral Case Record', 'Standalone fictional Nordland case record and broad essay assignment') + f'''
<body class="case-page"><a class="skip-link" href="#main">Skip to case record</a>
<header class="case-header"><div class="wrap case-header-inner"><a class="case-brand" href="case.html"><span class="brand-name">Nordland</span><span class="brand-sub">Case record</span></a>
<div class="case-controls"><button class="btn btn-quiet" data-copy-template="case-raw" type="button">Copy complete record</button>
<a class="btn btn-quiet" href="data/Nordland_Case_Record.md" download>Download text</a>
<button class="btn btn-quiet" data-print type="button">Print</button>
<span class="utility" role="group" aria-label="Text size controls"><button class="font-btn" data-font-adjust="-1" aria-label="Decrease text size" type="button">A−</button><button class="font-btn" data-font-adjust="1" aria-label="Increase text size" type="button">A+</button></span></div></div></header>
<main id="main" class="case-main"><div class="case-layout">
<nav class="case-toc" aria-label="Case record sections"><p class="toc-label">Record sections</p><ol>{case_toc}</ol></nav>
<article class="case-document"><header class="case-headline"><h1>Nordland</h1><p>Case record</p></header>
<div class="case-content">{case_html}</div>
<p class="case-note">The standalone page contains the case facts and essay assignment only. It contains no evaluator notes, scoring criteria, or suggested interpretations.</p></article></div></main>
<template id="case-raw">{html.escape(case_src)}</template>
<script src="assets/app.js?v={ASSET_VERSION}" defer></script></body></html>'''
(ROOT / 'case.html').write_text(case, encoding='utf-8')

# ---------------------------------------------------------------- research page
method = md_sections(method_src)
assert list(method) == ['The inquiry', 'What conceptual inquiry adds', 'The open-ended evaluation protocol',
                        'Why the evidence is difficult', 'Limits and next research steps', 'Scholarly foundations'], list(method)


def method_block(name, cls=''):
    return f'<section class="subsection {cls}" aria-labelledby="m-{name[:12].lower().replace(" ", "-")}"><h3 id="m-{name[:12].lower().replace(" ", "-")}">{e(name)}</h3><div class="prose">{prose(method[name])}</div></section>'


# The record's own structure: section headings and the numbered items each contains.
record_structure = []
current = None
for line in case_src.splitlines():
    s = line.strip()
    if s in case_headings:
        current = [s, []]
        record_structure.append(current)
    elif current and re.match(r'^\d+\. ', s):
        current[1].append(int(s.split('.')[0]))
    elif current and s.startswith('Table A1'):
        current[1].append('Table A1')


def item_range(items):
    nums = [i for i in items if isinstance(i, int)]
    rng = '' if not nums else (f'Item {nums[0]}' if len(nums) == 1 else f'Items {nums[0]}–{nums[-1]}')
    if 'Table A1' in items:
        rng += ' · Table A1'
    return rng


structure_rows = ''.join(
    f'<li><span class="ledger-title">{e(t)}</span><span class="ledger-items">{item_range(items)}</span></li>'
    for t, items in record_structure)
stipulation = case_src.split('\n\n')[2].strip()
assignment = case_src.split('Essay assignment', 1)[1].strip()
assert stipulation.startswith('Nordland is a fictional country.')
assert assignment.startswith('Read the Nordland case record.')

home_toc = toc([('1', 'question', 'Research question'), ('2', 'case', 'The Nordland case'),
                ('3', 'methodology', 'Methodology'), ('4', 'criteria', 'Conceptual reasoning criteria')],
               'On this page')

depth_levels = [('0', 'Absent or misleading', 'Central evidence or concepts are distorted.'),
                ('1', 'Superficial', 'Surface observations, slogans, or unsupported certainty.'),
                ('2', 'Developing', 'Some valid distinctions and patterns, not fully integrated.'),
                ('3', 'Strong', 'Well-framed, integrated, and proportionately evidenced.'),
                ('4', 'Exceptional', 'Evidence-responsive insight that substantively changes inquiry or judgment.')]
depth_scale = ''.join(f'<li class="scale-step" data-level="{n}"><span class="scale-num">{n}</span><strong>{t}</strong><p>{d}</p></li>'
                      for n, t, d in depth_levels)

# ---------------------------------------------------------------- rubric (exact, from evaluator source)
rubric_text = re.search(r'## 5\. Assessment criteria.*?(?=\n## 6\.)', eval_src, re.S)
if not rubric_text:
    raise RuntimeError('Could not locate the five-dimension rubric')
rubric_intro = rubric_text.group(0).split('\n\n')[1].strip()
level4_note = re.search(r'(?m)^\*\*Level 4 is not an originality prize\.\*\*.*$', rubric_text.group(0)).group(0)
parts = re.findall(r'(?ms)^### ([IVX]+)\. (.+?)\n(.*?)(?=^### [IVX]+\.|\Z)', rubric_text.group(0))
if len(parts) != 5:
    raise RuntimeError(f'Expected five rubric dimensions, got {len(parts)}')
separation = re.findall(r'(?m)^- \*\*([IVX]+) evaluates the (\w+)\.\*\* (.+)$', eval_src)
assert len(separation) == 5, separation
separation = {r: (word, q) for r, word, q in separation}
rubric = []
for i, (num, title, body) in enumerate(parts):
    anchors = dict((int(level), desc.strip()) for level, desc in
                   re.findall(r'(?m)^\*\*([0-4])\*\*\s*[—–-]\s*(.*?)\s*$', body))
    if len(anchors) != 5:
        raise RuntimeError(f'Missing anchors for {title}: {anchors}')
    short, _, focus = title.partition(' — ')
    rubric.append({'id': f'dimension_{i + 1}', 'roman': num, 'title': title, 'short': short, 'focus': focus,
                   'evaluates': separation[num][0], 'question': separation[num][1], 'anchors': anchors})

# Short descriptors shared by the five rubric dimensions and the five inquiry activities (both from source).
criteria_rows = ''.join(
    f'<tr><th scope="row"><span class="roman">{d["roman"]}</span>{e(d["short"])}</th><td>{e(d["focus"][:1].upper() + d["focus"][1:])}</td>'
    f'<td>{e(d["roman"])} evaluates the {e(d["evaluates"])}. {e(d["question"])}</td></tr>' for d in rubric)

home = base_head('Beyond Explanation', 'A substantive welfare-state paradox and a method for evaluating independent conceptual reasoning') + f'''
<body class="home-page"><a class="skip-link" href="#main">Skip to content</a>{header('home')}
<main id="main">
<section class="hero"><div class="wrap hero-inner">
<p class="eyebrow">A research project by Elaine Chou</p>
<h1>Beyond<br>Explanation.</h1>
<p class="hero-sub">Evaluating conceptual reasoning in AI through the Nordland welfare-state paradox.</p>
<div class="hero-actions"><a class="btn btn-primary" href="#question">Explore the research question</a><a class="btn btn-secondary" href="evaluation.html">Explore the scoring framework</a></div>
</div>
<div class="wrap"><figure class="figures" aria-label="Selected stipulated case outcomes">
<figcaption class="figures-caption">Selected stipulated case outcomes · Nordland case record, 2025</figcaption>
<dl class="figure-grid">
<div class="figure"><dt>National poverty rate</dt><dd class="figure-value">23% <span class="arrow" aria-label="to">→</span> 7%</dd><dd class="figure-note">Before versus after taxes and transfers, 2025</dd></div>
<div class="figure"><dt>Initial claim denials</dt><dd class="figure-value">18.3% <span class="sep">/</span> 8.9%</dd><dd class="figure-note">Minority-background / other claims</dd></div>
<div class="figure"><dt>Full social belonging</dt><dd class="figure-value">52% <span class="sep">/</span> 81%</dd><dd class="figure-note">Minority-background / other survey respondents</dd></div>
<div class="figure"><dt>Support for benefit system</dt><dd class="figure-value">76% <span class="sep">/</span> 79%</dd><dd class="figure-note">Minority-background / other survey respondents</dd></div>
</dl></figure></div></section>

<div class="wrap page-grid">{home_toc}<div class="page-body">

<section class="section" id="question" aria-labelledby="question-title">
{section_head('1', 'The substantive problem', 'What counts as a successful universal welfare state?', hid='question-title')}
<blockquote class="research-question"><p class="rq-label">Primary research question</p><p>“How can a strong welfare state sustain significant inequality despite its commitment to universal social protection?”</p></blockquote>
<div class="two-col"><div class="lede">
<p class="section-intro">Nordland's welfare system substantially reduces poverty. Yet its benefit decisions show patterned differences and its residents report unequal social belonging. Support for the system nevertheless remains high.</p>
<p>These findings are compatible but consequentially in tension. Aggregate redistribution may be effective even when practical access, administrative treatment, or civic membership are unequal. The research asks what this coexistence means—not which single familiar explanation sounds most persuasive.</p>
</div>
<figure class="outcomes" role="group" aria-label="Four different measures that need not move together">
<figcaption class="fig-label">Distinct institutional outcomes</figcaption>
<ul class="outcome-grid"><li><strong>Redistribution</strong><span>Change in poverty</span></li><li><strong>Access</strong><span>Initial benefit decisions</span></li>
<li><strong>Policy support</strong><span>Views of welfare provision</span></li><li><strong>Belonging</strong><span>Feeling part of society</span></li></ul>
<p class="caption">These are not interchangeable measurements. The case does not establish a single causal chain among them.</p></figure></div>
<div class="actions"><a class="btn btn-primary" href="case.html">Read the complete neutral record</a><a class="btn btn-secondary" href="#methodology">Read methodology</a></div>
</section>

<section class="section" id="case" aria-labelledby="case-title">
{section_head('2', 'The Nordland case', 'A fictional, bounded case record', hid='case-title')}
<div class="two-col case-overview">
<div><p class="fig-label">Stipulation</p><p class="stipulation">{e(stipulation)}</p>
<p class="fig-label">Assignment given to the model</p><blockquote class="assignment">{e(assignment)}</blockquote></div>
<div><p class="fig-label">Structure of the record</p><ol class="ledger">{structure_rows}</ol>
<p class="caption">The record is supplied to a model on its own standalone page, without evaluator notes, rubric, or examples.</p>
<div class="actions"><a class="btn btn-primary" href="case.html">Open the neutral case record</a><a class="btn btn-quiet" href="data/Nordland_Case_Record.md" download>Download text</a></div></div>
</div>
{method_block('Why the evidence is difficult', 'subsection-flush')}
</section>

<section class="section" id="methodology" aria-labelledby="methodology-title">
{section_head('3', 'Research design', 'Methodology', 'The model determines the direction of the inquiry. The evaluator judges its intellectual quality without turning the reference analysis into a hidden answer key.', hid='methodology-title')}
{method_block('The inquiry')}
{method_block('The open-ended evaluation protocol', 'protocol')}
<aside class="callout" aria-label="Boundary between materials"><strong>Boundary between materials:</strong> The model-facing record is a standalone factual document. The interpretive notes, scoring rubric, and constructed examples reside separately on the evaluator page and must not be supplied to a model during the initial test.</aside>
{method_block('Limits and next research steps')}
{method_block('Scholarly foundations', 'references')}
<div class="actions"><a class="btn btn-primary" href="evaluation.html">Evaluator notes and scoring</a><a class="btn btn-quiet" href="data/Nordland_Methodology.md" download>Methodology source text</a></div>
</section>

<section class="section" id="criteria" aria-labelledby="criteria-title"><span id="depth" class="anchor-alias"></span>
{section_head('4', 'Depth of inquiry', 'Conceptual reasoning criteria', 'The goal is to assess intellectual work visible in a response—especially whether the model independently finds the question, relationships, and limits that matter.', hid='criteria-title')}
{method_block('What conceptual inquiry adds', 'activities')}
<section class="subsection" aria-labelledby="dims-title"><h3 id="dims-title">Five assessment dimensions</h3>
<div class="table-scroll" role="region" tabindex="0" aria-label="Five assessment dimensions"><table class="criteria-table"><thead><tr><th scope="col">Dimension</th><th scope="col">Intellectual task</th><th scope="col">Score separation</th></tr></thead><tbody>{criteria_rows}</tbody></table></div></section>
<section class="subsection" aria-labelledby="scale-title"><h3 id="scale-title">From description to consequential interpretation</h3>
<ol class="scale">{depth_scale}</ol>
<p class="caption">This scale is used separately for each of five assessment dimensions. It is not a substitute for dimension-specific anchors.</p></section>
<div class="actions"><a class="btn btn-primary" href="evaluation.html#rubric">View the interactive rubric</a></div>
</section>
</div></div></main>{footer()}<script src="assets/app.js?v={ASSET_VERSION}" defer></script></body></html>'''
(ROOT / 'index.html').write_text(home, encoding='utf-8')

# ---------------------------------------------------------------- evaluation page
rubric_blocks = []
for item in rubric:
    levels = ''.join(
        f'<label class="level" data-level="{i}"><input type="radio" name="{item["id"]}" value="{i}" data-score="{item["id"]}">'
        f'<span class="level-num">{i}</span><span class="level-text">{e(item["anchors"][i])}</span></label>' for i in range(5))
    rubric_blocks.append(f'''<fieldset class="dimension" id="fs-{item['id']}" data-dimension="{item['id']}">
<legend><span class="roman">{item['roman']}</span><span class="dim-title">{e(item['short'])}</span><span class="dim-focus">{e(item['focus'])}</span></legend>
<p class="dim-question"><strong>{item['roman']} evaluates the {e(item['evaluates'])}.</strong> {e(item['question'])}</p>
<div class="levels">{levels}</div>
<label class="form-field rationale" for="{item['id']}_reason">Passage-specific evidence and rationale
<textarea id="{item['id']}_reason" name="{item['id']}_reason" rows="2" placeholder="Quote or locate a passage and explain why the score fits."></textarea></label></fieldset>''')

profile_rows = ''.join(
    f'<li data-profile="{d["id"]}"><a href="#fs-{d["id"]}"><span class="roman">{d["roman"]}</span><span class="p-name">{e(d["short"])}</span>'
    f'<span class="pips" aria-hidden="true">{"<i></i>" * 4}</span><span class="p-score" data-profile-score>–</span></a></li>' for d in rubric)

# Appendix A: parse the three constructed calibration responses exactly from the source.
appendix = eval_src.split('## Appendix A', 1)[1]
status_para = re.search(r'(?m)^\*\*Status and safeguards\.\*\*.*$', appendix).group(0)
responses = []
for key, title, body in re.findall(r'(?ms)^### A\.(\d) (Response [ABC] — .+?)\n(.*?)(?=^### A\.\d|\Z)', appendix):
    if key == '4':
        continue
    meta = re.search(r'(?m)^\*\*Illustrative model response \((.+?)\)\*\*', body).group(1)
    quote = '\n'.join(l[2:] if l.startswith('> ') else l[1:] for l in body.splitlines() if l.startswith('>'))
    rows = []
    for line in body.splitlines():
        m = re.match(r'^\| ([IVX]+\. [^|]+?) \| \*\*(\d+) / 4\*\* \| (.+) \|$', line)
        if m:
            rows.append((m.group(1), int(m.group(2)), m.group(3)))
    total = re.search(r'\| \*\*Total \(secondary\)\*\* \| \*\*(\d+) / 20\*\* \| (.+) \|', body)
    note = re.search(r'(?m)^\*\*Calibration note\.\*\*.*$', body).group(0)
    assert len(rows) == 5, (title, rows)
    assert sum(r[1] for r in rows) == int(total.group(1)), title
    letter, _, label = title.partition(' — ')
    responses.append({'letter': letter[-1], 'title': title, 'label': label, 'meta': meta, 'essay': quote,
                      'rows': rows, 'total': int(total.group(1)), 'total_note': total.group(2), 'note': note})
assert [r['letter'] for r in responses] == ['A', 'B', 'C']
how_to_use = re.search(r'(?m)^\*\*How to use the appendix:\*\*.*$', appendix).group(0)

# Cross-check against the A.4 comparison table in the source.
a4 = re.search(r'### A\.4.*?(?=\*\*How to use)', appendix, re.S).group(0)
a4_rows = re.findall(r'(?m)^\| ([IVX]+)\. [^|]+\| (\d) \| (\d) \| (\d) \|$', a4)
assert [tuple(int(x) for x in r[1:]) for r in a4_rows] == [tuple(resp['rows'][i][1] for resp in responses) for i in range(5)], a4_rows

col_labels = {'A': 'A — Weak', 'B': 'B — Competent', 'C': 'C — Exceptional'}


def pips(score):
    return f'<span class="pips" aria-hidden="true">{"".join("<i class=on></i>" if k < score else "<i></i>" for k in range(4))}</span>'


matrix_rows = []
detail_blocks = []
for i, d in enumerate(rubric):
    cells = ''.join(f'<td data-level="{r["rows"][i][1]}"><span class="score-cell"><b>{r["rows"][i][1]}</b>{pips(r["rows"][i][1])}</span></td>' for r in responses)
    matrix_rows.append(f'<tr data-row="{i}"><th scope="row"><button type="button" class="row-btn" data-compare="{i}" aria-controls="compare-detail" aria-pressed="{"true" if i == 0 else "false"}"><span class="roman">{d["roman"]}</span>{e(d["short"])}</button></th>{cells}</tr>')
    cols = ''.join(f'''<div class="rationale-col"><p class="rationale-head"><span>Response {r['letter']}</span><span class="rationale-score" data-level="{r['rows'][i][1]}">{r['rows'][i][1]} / 4</span></p><p>{inline(r['rows'][i][2])}</p></div>''' for r in responses)
    detail_blocks.append(f'<div class="compare-dim" data-compare-panel="{i}"><h4><span class="roman">{d["roman"]}</span>{e(d["short"])} <span class="muted">— rationales for each response</span></h4><div class="rationale-grid">{cols}</div></div>')
totals = ''.join(f'<td><strong>{r["total"]}</strong><span class="muted"> / 20</span></td>' for r in responses)

tabs = ''.join(f'<button type="button" role="tab" id="tab-{r["letter"]}" aria-controls="panel-{r["letter"]}" aria-selected="{"true" if r["letter"] == "A" else "false"}" tabindex="{0 if r["letter"] == "A" else -1}"><span class="tab-letter">{r["letter"]}</span><span class="tab-text"><span>{e(r["label"])}</span><span class="muted">{r["total"]} / 20</span></span></button>' for r in responses)
panels = []
for r in responses:
    score_list = ''.join(f'<li><p class="sl-head"><span>{e(dim)}</span><span class="rationale-score" data-level="{s}">{s} / 4</span></p><p>{inline(expl)}</p></li>' for dim, s, expl in r['rows'])
    panels.append(f'''<div class="response-panel" role="tabpanel" id="panel-{r['letter']}" aria-labelledby="tab-{r['letter']}" tabindex="0">
<h4 class="response-title">{e(r['title'])}</h4>
<div class="response-grid"><div class="essay"><p class="essay-meta">Illustrative model response ({e(r['meta'])})</p><div class="essay-text">{prose(r['essay'])}</div></div>
<div class="assessment"><p class="fig-label">Scores and passage-specific rationales</p><ol class="score-list">{score_list}</ol>
<p class="total-line"><span>Total (secondary)</span><strong>{r['total']} / 20</strong></p><p class="total-note">{inline(r['total_note'])}</p>
<p class="calibration-note">{inline(r['note'])}</p></div></div></div>''')

# Each evaluator reference section is disclosed separately to reduce visual load.
sections = re.split(r'(?m)(?=^## (?:\d+\. |Appendix A))', eval_src)
ref_accordions = []
for section in sections:
    section = section.strip()
    if not section.startswith('## '):
        continue
    heading = section.splitlines()[0][3:]
    ref_accordions.append(f'''<details class="reference-accordion"><summary>{e(heading)}</summary>
<div class="reference-content prose">{prose(section)}</div></details>''')

validity_html = prose(re.sub(r'(?m)^(#{2,3}) ', lambda m: '#' + m.group(1) + ' ', validity_src))

js_rubric = json.dumps([{k: d[k] for k in ('id', 'roman', 'title', 'short', 'anchors')} for d in rubric],
                       ensure_ascii=False).replace('<', '\\u003c')

eval_toc = toc([('5', 'rubric', 'Evaluator rubric'), ('6', 'calibration', 'Illustrative assessments'),
                ('7', 'reference', 'Reference library'), ('8', 'validity', 'Validity')], 'On this page')

evaluation = base_head('Conceptual Depth and Evaluation', 'Interactive five-dimension Nordland scoring rubric, evaluator interpretations, calibration and validity notes') + f'''
<body class="evaluation-page"><a class="skip-link" href="#main">Skip to evaluation</a>{header('evaluation')}
<main id="main"><section class="page-heading"><div class="wrap"><p class="eyebrow">Research evaluation</p><h1>Conceptual depth<br>&amp; assessment.</h1>
<p class="hero-sub">A transparent framework for evaluating self-directed inquiry, consequential interpretations, evidentiary restraint, and substantive judgment.</p>
<div class="evaluator-notice" role="note"><strong>Evaluator-only material.</strong> Never give this page, its rubrics, possible interpretations, or calibration essays to the model before collecting its first response. This page is public for methodological transparency, not access-controlled.</div></div></section>

<div class="wrap page-grid">{eval_toc}<div class="page-body">
<section class="section" id="rubric" aria-labelledby="rubric-title">
{section_head('5', 'Interactive assessment', 'Five-dimension scoring rubric', 'Score each dimension independently from 0–4. The resulting profile carries more information than the total. Every rating of 4 should explain the substantive step beyond level 3.', hid='rubric-title')}
<p class="source-note">{inline(rubric_intro)}</p>
<form id="score-form" autocomplete="off">
<fieldset class="panel scorer-meta"><legend class="visually-hidden">Assessment details</legend>
<label class="form-field">Model / run identifier<input name="model_run" placeholder="Model name and run identifier"></label>
<label class="form-field">Evaluator<input name="assessor" placeholder="Assessor identifier"></label>
<label class="form-field">Assessment date<input name="scored_on" type="date"></label>
<label class="form-field">Record used<input name="record_used" value="Nordland Case Record" aria-label="Case record identifier"></label></fieldset>
<p class="instruction">Assign an independent score based on the response, not on its resemblance to a preferred theory. Select the anchor that best describes each dimension.</p>
<div class="scorer"><div class="rubric-stack">{''.join(rubric_blocks)}
<p class="level4-note">{inline(level4_note)}</p></div>
<aside class="profile" aria-label="Score profile"><div class="profile-inner">
<p class="fig-label">Score profile</p><ol class="profile-list">{profile_rows}</ol>
<div class="profile-total" aria-live="polite"><span class="pt-label">Secondary total</span><span class="pt-value"><span class="total" id="score-total">0</span><span class="denominator"> / 20</span></span><span class="state" id="score-complete">0 of 5 dimensions rated</span></div>
</div></aside></div>
<div class="panel synthesis"><h3>Evaluator synthesis</h3><div class="scorer-notes">
<label class="form-field">Governing thesis observed<textarea name="governing_thesis" rows="3"></textarea></label>
<label class="form-field">Most consequential insight or omission<textarea name="consequential_insight" rows="3"></textarea></label>
<label class="form-field">Disconfirming evidence considered or omitted<textarea name="disconfirming_evidence" rows="3"></textarea></label>
<label class="form-field">Unexpected interpretation and its evaluation<textarea name="unexpected_interpretation" rows="3"></textarea></label>
<label class="form-field wide">Uncertainty or calibration disagreement<textarea name="assessor_uncertainty" rows="3"></textarea></label></div>
<div class="scorer-actions"><button class="btn btn-primary" type="button" id="export-json">Export scoring record (JSON)</button>
<button class="btn btn-secondary" type="button" id="export-csv">Export dimensions (CSV)</button>
<button class="btn btn-secondary" type="button" id="copy-record">Copy record</button>
<button class="btn btn-quiet" type="button" data-print>Print</button>
<button class="btn btn-quiet" type="button" id="reset-form">Clear form</button></div>
<div role="status" class="status-message" data-status aria-live="polite"></div>
<p class="fine-print">Scoring runs entirely in your browser; nothing is transmitted to a server or saved automatically. Export your work before closing the page. Unrated dimensions are omitted from the completed total in JSON.</p></div>
<div class="score-dock" aria-hidden="true"><span>Secondary total</span><strong><span data-dock-total>0</span> / 20</strong><span data-dock-count>0 of 5 rated</span></div>
</form>
</section>

<section class="section" id="calibration" aria-labelledby="calibration-title">
{section_head('6', 'Constructed calibration material', 'Illustrative model assessments', 'These examples are constructed for scorer training. They are <strong>not</strong> outputs from identified AI systems and do not demonstrate experimentally measured capability.', hid='calibration-title')}
<p class="source-note">{inline(status_para)}</p>
<div class="anchoring-note" role="note">{inline(how_to_use)}</div>
<h3 class="sub-h">Compare by dimension</h3>
<p class="instruction">Select a dimension to read the three rationales side by side.</p>
<div class="table-scroll matrix-scroll" role="region" tabindex="0" aria-label="Constructed calibration score comparison"><table class="comparison-table"><thead><tr><th scope="col">Dimension</th>{''.join(f'<th scope="col">{col_labels[r["letter"]]}</th>' for r in responses)}</tr></thead>
<tbody>{''.join(matrix_rows)}<tr class="total-row"><th scope="row">Total / 20</th>{totals}</tr></tbody></table></div>
<div id="compare-detail" class="compare-detail" aria-live="polite">{''.join(detail_blocks)}</div>
<p class="caption">An unexpected but evidence-supported argument can receive the same top score as the exceptional example; repeating its vocabulary does not earn a high rating.</p>
<h3 class="sub-h">Read a response</h3>
<div class="response-viewer"><div class="tablist" role="tablist" aria-label="Constructed calibration responses">{tabs}</div>{''.join(panels)}</div>
</section>

<section class="section" id="reference" aria-labelledby="reference-title">
{section_head('7', 'Assessor reference library', 'Evaluator interpretations, notes &amp; criteria', 'Nonexclusive perspectives, inferential limitations, scoring anchors, assessor protocol, and full constructed calibration responses. These documents guide judgment but never function as a mandatory answer key.', hid='reference-title')}
<div class="accordion-group">{''.join(ref_accordions)}</div>
<p class="download-line"><a href="data/Nordland_Evaluator_Interpretations_and_Assessment_Criteria.md" download>Download full evaluator source text</a></p></section>

<section class="section" id="validity" aria-labelledby="validity-title">
{section_head('8', 'Research integrity', 'Validity questions and next research steps', hid='validity-title')}
<div class="prose validity">{validity_html}</div>
<div class="actions"><a class="btn btn-quiet" href="data/Nordland_Validity_Questions.md" download>Validity notes source text</a><a class="btn btn-secondary" href="index.html#methodology">Return to methodology</a></div></section>
</div></div></main>{footer()}<script>window.NORDLAND_RUBRIC = {js_rubric};</script><script src="assets/app.js?v={ASSET_VERSION}" defer></script>
</body></html>'''
(ROOT / 'evaluation.html').write_text(evaluation, encoding='utf-8')

print('Created index.html, case.html, evaluation.html')
print('Rubric dimensions:', *[d['title'] for d in rubric], sep='\n - ')
print('Calibration totals:', ', '.join(f"{r['letter']}={r['total']}" for r in responses))
print('Source counts:', len(case_src), 'case chars,', len(eval_src), 'evaluator chars')
