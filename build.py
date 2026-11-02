"""Build Nordland's dependency-free GitHub Pages website from stable source names.

Run: python -m pip install -r requirements.txt && python build.py
The prebuilt HTML files may be published directly, without running this script.
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


def prose(source):
    """Readable semantic Markdown converted to HTML, with scrollable tables."""
    soup = BeautifulSoup(md(source), 'html.parser')
    for table in soup.find_all('table'):
        wrapper = soup.new_tag('div', attrs={'class': 'table-scroll', 'role':'region', 'tabindex':'0', 'aria-label':'Scrollable data table'})
        table.wrap(wrapper)
    return str(soup)


def base_head(title, description):
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{e(description)}"><meta name="theme-color" content="#152c3c">
<title>{e(title)} — Nordland Research</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/styles.css"></head>'''


def header(current='home'):
    return f'''<header class="site-header"><div class="wrap header-inner">
<a class="brand" href="index.html">Nordland <span>Beyond Explanation</span></a>
<nav class="nav" aria-label="Main site navigation">
<a href="index.html" {'aria-current="page"' if current=='home' else ''}>Research &amp; method</a>
<a href="evaluation.html" {'aria-current="page"' if current=='evaluation' else ''}>Conceptual depth &amp; rubric</a>
<a class="nav-primary" href="case.html">Read neutral case</a></nav>
<div class="utility" aria-label="Text size controls"><button type="button" class="font-btn" data-font-adjust="-1" aria-label="Decrease text size">A−</button>
<button type="button" class="font-btn" data-font-adjust="1" aria-label="Increase text size">A+</button></div>
</div></header>'''


def footer():
    return '''<footer class="site-footer"><div class="wrap footer-inner"><div><a class="brand" href="index.html">Nordland</a><div>Beyond Explanation · An open-ended conceptual-reasoning research prototype</div><div>Research: Elaine Chou</div></div>
<div><a href="index.html#methodology">Methodology</a> · <a href="evaluation.html">Evaluator materials</a> · <a href="case.html">Neutral case record</a>
<p>The case is fictional. Illustrative examples are constructed, not experimental findings.</p></div></div></footer>'''


case_src = (DATA / 'Nordland_Case_Record.md').read_text(encoding='utf-8')
eval_src = (DATA / 'Nordland_Evaluator_Interpretations_and_Assessment_Criteria.md').read_text(encoding='utf-8')
method_src = (DATA / 'Nordland_Methodology.md').read_text(encoding='utf-8')
validity_src = (DATA / 'Nordland_Validity_Questions.md').read_text(encoding='utf-8')

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

case_html = prose(case_body)
case = base_head('Neutral Case Record', 'Standalone fictional Nordland case record and broad essay assignment') + f'''
<body class="case-page"><a class="skip-link" href="#main">Skip to case record</a>
<header class="case-header"><div class="wrap"><a href="case.html">Nordland · Case record</a>
<div class="case-controls"><button class="btn btn-secondary" data-copy-template="case-raw" type="button">Copy complete record</button>
<a class="btn btn-secondary" href="data/Nordland_Case_Record.md" download>Download text</a>
<button class="btn btn-secondary" data-print type="button">Print</button>
<button class="font-btn" data-font-adjust="-1" aria-label="Decrease text size" type="button">A−</button>
<button class="font-btn" data-font-adjust="1" aria-label="Increase text size" type="button">A+</button></div></div></header>
<main id="main" class="case-main"><div class="case-headline"><h1>Nordland</h1><p>Case record</p></div>
<article class="case-content">{case_html}</article>
<p class="case-note">The standalone page contains the case facts and essay assignment only. It contains no evaluator notes, scoring criteria, or suggested interpretations.</p></main>
<template id="case-raw">{html.escape(case_src)}</template>
<script src="assets/app.js" defer></script></body></html>'''
(ROOT / 'case.html').write_text(case, encoding='utf-8')

# Research page. Explanatory analysis belongs here and is never part of the participant case.
home = base_head('Beyond Explanation', 'A substantive welfare-state paradox and a method for evaluating independent conceptual reasoning') + f'''
<body><a class="skip-link" href="#main">Skip to content</a>{header('home')}
<main id="main"><section class="hero"><div class="wrap"><div class="eyebrow">A research project by Elaine Chou</div>
<h1>Beyond<br>Explanation.</h1>
<p class="hero-sub">Evaluating conceptual reasoning in AI through the Nordland welfare-state paradox.</p>
<div class="hero-actions"><a class="btn-light" href="#question">Explore the research question</a><a class="btn-outline" href="evaluation.html">Explore the scoring framework</a></div>
</div></section>
<div class="wrap"><div class="metric-grid" aria-label="Selected stipulated case outcomes">
<div class="metric"><div class="metric-desc">National poverty rate</div><strong>23% <span class="arrow">→</span> 7%</strong><small>Before versus after taxes and transfers, 2025</small></div>
<div class="metric"><div class="metric-desc">Initial claim denials</div><strong>18.3% / 8.9%</strong><small>Minority-background / other claims</small></div>
<div class="metric"><div class="metric-desc">Full social belonging</div><strong>52% / 81%</strong><small>Minority-background / other survey respondents</small></div>
<div class="metric"><div class="metric-desc">Support for benefit system</div><strong>76% / 79%</strong><small>Minority-background / other survey respondents</small></div>
</div></div>
<section class="section" id="question"><div class="wrap two-col"><div><p class="kicker">The substantive problem</p>
<h2>What counts as a successful universal welfare state?</h2>
<p class="section-intro">Nordland's welfare system substantially reduces poverty. Yet its benefit decisions show patterned differences and its residents report unequal social belonging. Support for the system nevertheless remains high.</p>
<p>These findings are compatible but consequentially in tension. Aggregate redistribution may be effective even when practical access, administrative treatment, or civic membership are unequal. The research asks what this coexistence means—not which single familiar explanation sounds most persuasive.</p>
<div class="method-links"><a class="btn" href="case.html">Read the complete neutral record</a><a class="btn btn-secondary" href="#methodology">Read methodology</a></div>
</div><aside><div class="quote-panel">“How can a strong welfare state sustain significant inequality despite its commitment to universal social protection?”</div>
<div class="diagram" role="group" aria-label="Four different measures that need not move together">
<div class="eyebrow" style="margin-bottom:16px">Distinct institutional outcomes</div>
<div class="diagram-grid"><div class="node"><strong>Redistribution</strong><span>Change in poverty</span></div><div class="node"><strong>Access</strong><span>Initial benefit decisions</span></div>
<div class="node"><strong>Policy support</strong><span>Views of welfare provision</span></div><div class="node"><strong>Belonging</strong><span>Feeling part of society</span></div></div>
<p class="caption">These are not interchangeable measurements. The case does not establish a single causal chain among them.</p></div></aside></div></section>
<section class="section" style="background:#eef2ef" id="depth"><div class="wrap"><p class="kicker">Depth of inquiry</p><h2>From description to consequential interpretation</h2>
<p class="section-intro">The goal is to assess intellectual work visible in a response—especially whether the model independently finds the question, relationships, and limits that matter.</p>
<div class="depth-grid">
<div class="depth-card"><span class="level">0</span><strong>Absent or misleading</strong><p>Central evidence or concepts are distorted.</p></div>
<div class="depth-card"><span class="level">1</span><strong>Superficial</strong><p>Surface observations, slogans, or unsupported certainty.</p></div>
<div class="depth-card"><span class="level">2</span><strong>Developing</strong><p>Some valid distinctions and patterns, not fully integrated.</p></div>
<div class="depth-card"><span class="level">3</span><strong>Strong</strong><p>Well-framed, integrated, and proportionately evidenced.</p></div>
<div class="depth-card"><span class="level">4</span><strong>Exceptional</strong><p>Evidence-responsive insight that substantively changes inquiry or judgment.</p></div>
</div><p style="font-size:13px;color:var(--ink-soft);margin-top:20px">This scale is used separately for each of five assessment dimensions. It is not a substitute for dimension-specific anchors.</p>
<a class="btn" href="evaluation.html#rubric">View the interactive rubric</a></div></section>
<section class="section" id="methodology"><div class="wrap"><p class="kicker">Research design</p><h2>Methodology</h2>
<p class="section-intro">The model determines the direction of the inquiry. The evaluator judges its intellectual quality without turning the reference analysis into a hidden answer key.</p>
<div class="method-body prose">{prose(method_src)}</div>
<div class="callout"><strong>Boundary between materials:</strong> The model-facing record is a standalone factual document. The interpretive notes, scoring rubric, and constructed examples reside separately on the evaluator page and must not be supplied to a model during the initial test.</div>
<div class="method-links"><a class="btn" href="evaluation.html">Evaluator notes and scoring</a><a class="btn btn-secondary" href="data/Nordland_Methodology.md" download>Methodology source text</a></div>
</div></section></main>{footer()}<script src="assets/app.js" defer></script></body></html>'''
(ROOT / 'index.html').write_text(home, encoding='utf-8')

# Extract the current five exact rubric dimensions from the evaluator source.
rubric_text = re.search(r'## 5\. Assessment criteria.*?(?=\n## 6\.)', eval_src, re.S)
if not rubric_text:
    raise RuntimeError('Could not locate the five-dimension rubric')
parts = re.findall(r'(?ms)^### ([IVX]+)\. (.+?)\n(.*?)(?=^### [IVX]+\.|\Z)', rubric_text.group(0))
if len(parts) != 5:
    raise RuntimeError(f'Expected five rubric dimensions, got {len(parts)}')
rubric=[]
for i,(num, title, body) in enumerate(parts):
    anchors = dict((int(level), desc.strip().rstrip('  ')) for level,desc in
                   re.findall(r'(?m)^\*\*([0-4])\*\*\s*[—–-]\s*(.*?)\s*$',body))
    if len(anchors) != 5:raise RuntimeError(f'Missing anchors for {title}: {anchors}')
    rubric.append({'id':f'dimension_{i+1}', 'roman':num, 'title':title, 'anchors':anchors})

rubric_cards=[]
for item in rubric:
    options='<option value="">Choose 0–4</option>' + ''.join(f'<option value="{i}">{i} / 4</option>' for i in range(5))
    anchor_dl=''.join(f'<dt>{i}</dt><dd>{e(item["anchors"][i])}</dd>' for i in range(5))
    rubric_cards.append(f'''<section class="rubric-item" aria-labelledby="title-{item['id']}">
<div class="rubric-item-title"><div><h3 id="title-{item['id']}">{item['roman']}. {e(item['title'])}</h3>
<p class="rubric-diagnostic">Assign an independent score based on the response, not on its resemblance to a preferred theory.</p></div>
<div class="score-controls"><label for="{item['id']}" class="visually-hidden">Score for {e(item['title'])}</label>
<select id="{item['id']}" data-score="{item['id']}" name="{item['id']}" aria-label="Score for {e(item['title'])}">{options}</select></div></div>
<div class="anchor-display" data-anchor-display aria-live="polite">Choose a score to view its anchor.</div><div class="bar" aria-hidden="true"><span data-score-bar></span></div>
<label class="form-field" for="{item['id']}_reason">Passage-specific evidence and rationale
<textarea id="{item['id']}_reason" name="{item['id']}_reason" rows="2" placeholder="Quote or locate a passage and explain why the score fits."></textarea></label>
<details class="anchors"><summary>Read all five scoring anchors</summary><dl>{anchor_dl}</dl></details></section>''')

# Each evaluator reference section is disclosed separately to reduce visual load.
sections=re.split(r'(?m)(?=^## (?:\d+\. |Appendix A))', eval_src)
ref_accordions=[]
for section in sections:
    section=section.strip()
    if not section.startswith('## '):continue
    heading=section.splitlines()[0][3:]
    ref_accordions.append(f'''<details class="reference-accordion"><summary>{e(heading)}</summary>
<div class="reference-content prose">{prose(section)}</div></details>''')

compare_rows=[('Critical analysis',1,3,4),('Conceptual reasoning',1,3,4),('Consequential patterns',1,3,4),('Evidentiary discipline',0,3,4),('Substantive judgment',1,3,4)]
compare_tbody=''.join(f'<tr><td>{e(label)}</td><td>{a}</td><td>{b}</td><td>{c}</td></tr>' for label,a,b,c in compare_rows)
js_rubric=json.dumps(rubric,ensure_ascii=False).replace('<','\\u003c')

evaluation=base_head('Conceptual Depth and Evaluation', 'Interactive five-dimension Nordland scoring rubric, evaluator interpretations, calibration and validity notes')+f'''
<body><a class="skip-link" href="#main">Skip to evaluation</a>{header('evaluation')}
<main id="main"><section class="page-heading"><div class="wrap"><div class="eyebrow">Research evaluation</div><h1>Conceptual depth<br>&amp; assessment.</h1>
<p>A transparent framework for evaluating self-directed inquiry, consequential interpretations, evidentiary restraint, and substantive judgment.</p></div></section>
<section class="section" id="rubric"><div class="wrap"><p class="kicker">Interactive assessment</p><h2>Five-dimension scoring rubric</h2>
<p class="section-intro">Score each dimension independently from 0–4. The resulting profile carries more information than the total. Every rating of 4 should explain the substantive step beyond level 3.</p>
<div class="evaluator-notice"><strong>Evaluator-only material.</strong> Never give this page, its rubrics, possible interpretations, or calibration essays to the model before collecting its first response. This page is public for methodological transparency, not access-controlled.</div>
<form id="score-form" autocomplete="off"><div class="scorer-top"><div class="panel scorer-meta">
<label class="form-field">Model / run identifier<input name="model_run" placeholder="Model name and run identifier"></label>
<label class="form-field">Evaluator<input name="assessor" placeholder="Assessor identifier"></label>
<label class="form-field">Assessment date<input name="scored_on" type="date"></label>
<label class="form-field">Record used<input name="record_used" value="Nordland Case Record" aria-label="Case record identifier"></label>
</div><div class="score-summary" aria-live="polite"><div>Secondary total</div><div class="total" id="score-total">0</div><div class="denominator">out of 20</div><div class="state" id="score-complete">0 of 5 dimensions rated</div></div></div>
<div class="rubric-stack">{''.join(rubric_cards)}</div>
<div class="panel" style="margin-top:18px"><h3>Evaluator synthesis</h3><div class="scorer-notes">
<label class="form-field">Governing thesis observed<textarea name="governing_thesis" rows="3"></textarea></label>
<label class="form-field">Most consequential insight or omission<textarea name="consequential_insight" rows="3"></textarea></label>
<label class="form-field">Disconfirming evidence considered or omitted<textarea name="disconfirming_evidence" rows="3"></textarea></label>
<label class="form-field">Unexpected interpretation and its evaluation<textarea name="unexpected_interpretation" rows="3"></textarea></label>
<label class="form-field" style="grid-column:1/-1">Uncertainty or calibration disagreement<textarea name="assessor_uncertainty" rows="3"></textarea></label></div>
<div class="scorer-actions"><button class="btn" type="button" id="export-json">Export scoring record (JSON)</button>
<button class="btn btn-secondary" type="button" id="export-csv">Export dimensions (CSV)</button>
<button class="btn btn-secondary" type="button" id="copy-record">Copy record</button>
<button class="btn btn-secondary" type="button" data-print>Print</button>
<button class="btn btn-secondary" type="button" id="reset-form">Clear form</button></div>
<div role="status" class="status-message" data-status aria-live="polite"></div>
<p style="font-size:12px;color:var(--ink-soft)">Scoring runs entirely in your browser; nothing is transmitted to a server or saved automatically. Export your work before closing the page. Unrated dimensions are omitted from the completed total in JSON.</p></div></form>
</div></section>
<section class="section" style="background:#eef2ef" id="calibration"><div class="wrap"><p class="kicker">Constructed calibration material</p><h2>Three contrasting illustrative responses</h2>
<p class="section-intro">These examples are constructed for scorer training. They are <strong>not</strong> outputs from identified AI systems and do not demonstrate experimentally measured capability.</p>
<div class="table-scroll" role="region" tabindex="0" aria-label="Constructed calibration score comparison"><table class="comparison-table"><thead><tr><th scope="col">Dimension</th><th scope="col">A — Weak</th><th scope="col">B — Competent</th><th scope="col">C — Exceptional</th></tr></thead>
<tbody>{compare_tbody}<tr><th scope="row">Total / 20</th><td><strong>4</strong></td><td><strong>15</strong></td><td><strong>20</strong></td></tr></tbody></table></div>
<p style="font-size:14px;color:var(--ink-soft)">An unexpected but evidence-supported argument can receive the same top score as the exceptional example; repeating its vocabulary does not earn a high rating.</p>
<p><a class="btn" href="#reference">Read the full illustrative essays and rationales</a></p></div></section>
<section class="section" id="reference"><div class="wrap"><p class="kicker">Assessor reference library</p><h2>Evaluator interpretations, notes &amp; criteria</h2>
<p class="section-intro">Nonexclusive perspectives, inferential limitations, scoring anchors, assessor protocol, and full constructed calibration responses. These documents guide judgment but never function as a mandatory answer key.</p>
{''.join(ref_accordions)}<p><a href="data/Nordland_Evaluator_Interpretations_and_Assessment_Criteria.md" download>Download full evaluator source text</a></p></div></section>
<section class="section" style="background:#eef2ef" id="validity"><div class="wrap"><p class="kicker">Research integrity</p><h2>Validity questions and next research steps</h2>
<div class="method-body prose">{prose(validity_src)}</div>
<div class="method-links"><a class="btn btn-secondary" href="data/Nordland_Validity_Questions.md" download>Validity notes source text</a><a class="btn" href="index.html#methodology">Return to methodology</a></div></div></section>
</main>{footer()}<script>window.NORDLAND_RUBRIC = {js_rubric};</script><script src="assets/app.js" defer></script>
</body></html>'''
(ROOT/'evaluation.html').write_text(evaluation,encoding='utf-8')

print('Created index.html, case.html, evaluation.html')
print('Rubric dimensions:',*[d['title'] for d in rubric],sep='\n - ')
print('Source counts:',len(case_src),'case chars,',len(eval_src),'evaluator chars')
