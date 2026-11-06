// Browser tests for the Nordland research site.
// Run from the repository root:  (cd tests && npm install && npm test)
// Requires Playwright with Chromium (preinstalled in the build environment) and Python 3 to serve the site.
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const AXE = readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
const PAGES = ['index', 'case-record', 'methodology', 'validity', 'rubric', 'responses', 'evaluations', 'score', 'compare', 'findings'];
const PORT = 8800 + Math.floor(Math.random() * 100);
const BASE = `http://localhost:${PORT}/`;

let passed = 0, failed = 0;
const results = [];
function check(name, cond, detail = '') {
  if (cond) { passed++; results.push(`  ok    ${name}`); }
  else { failed++; results.push(`  FAIL  ${name}${detail ? ` — ${detail}` : ''}`); }
}
const section = t => results.push(`\n${t}`);

const server = spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1'], { cwd: ROOT, stdio: 'ignore' });
await new Promise(r => setTimeout(r, 800));
const browser = await chromium.launch();

try {
  const data = JSON.parse(readFileSync(path.join(ROOT, 'score.html'), 'utf8').match(/<script type="application\/json" id="nordland-data">(.*?)<\/script>/s)[1].replace(/<\\\//g, '</'));
  const evalSrc = readFileSync(path.join(ROOT, 'content/Nordland_Evaluator_Interpretations_and_Assessment_Criteria.md'), 'utf8');

  /* ------------------------------------------------------------ data integrity */
  section('Data integrity');
  const ill = data.responses.filter(r => r.kind === 'illustrative');
  check('three illustrative responses (Appendix A)', ill.map(r => r.id).join() === 'ILL-A,ILL-B,ILL-C');
  check('no experimental responses invented', data.responses.filter(r => r.kind === 'experimental').length === JSON.parse(readFileSync(path.join(ROOT, 'data/responses.json'), 'utf8')).responses.length);
  check('no experimental evaluations invented', data.evaluations.filter(e => e.evaluation_kind === 'experimental').length === JSON.parse(readFileSync(path.join(ROOT, 'data/evaluations.json'), 'utf8')).evaluations.length);
  const a4 = evalSrc.split('### A.4')[1];
  const table = Object.fromEntries([...a4.matchAll(/^\| (I{1,3}|IV|V)\. [^|]+\| (\d) \| (\d) \| (\d) \|$/gm)].map(m => [m[1], [m[2], m[3], m[4]].map(Number)]));
  for (const [i, id] of ['ILL-A', 'ILL-B', 'ILL-C'].entries()) {
    const ev = data.evaluations.find(e => e.response_id === id);
    const scores = ['I', 'II', 'III', 'IV', 'V'].map(d => ev.scores[d].score);
    check(`${id} scores match the Appendix A.4 comparison table`, scores.every((v, k) => v === table[['I', 'II', 'III', 'IV', 'V'][k]][i]), scores.join(','));
  }
  check('illustrative totals 4 / 15 / 20', ['ILL-A', 'ILL-B', 'ILL-C'].map(id => data.evaluations.find(e => e.response_id === id).total_secondary).join() === '4,15,20');
  for (const d of data.rubric.dimensions) for (const lvl of ['0', '1', '2', '3', '4'])
    if (!evalSrc.includes(`**${lvl}** — ${d.anchors[lvl]}`)) check(`anchor ${d.roman}/${lvl} quoted exactly from the rubric document`, false);
  check('all 25 anchors quoted exactly from the rubric document', data.rubric.dimensions.every(d => ['0', '1', '2', '3', '4'].every(l => evalSrc.includes(`**${l}** — ${d.anchors[l]}`))));
  check('essay text preserved word for word', ill.every(r => {
    const words = r.output_text.split(/\s+/).slice(0, 25).join(' ');
    return evalSrc.replace(/\*/g, '').replace(/\s+/g, ' ').includes(words.replace(/\*/g, ''));
  }));

  /* ------------------------------------------------------------ core functions */
  section('Scoring calculations and validation (NordlandCore)');
  const page = await browser.newPage();
  await page.goto(BASE + 'score.html');
  const core = await page.evaluate(() => {
    const C = window.NordlandCore; const s = (...v) => Object.fromEntries(['I', 'II', 'III', 'IV', 'V'].map((d, i) => [d, { score: v[i] ?? null }]));
    const tryErr = f => { try { f(); return null; } catch (e) { return e.message; } };
    return {
      partial: C.totals(s(3, 2, null, 4, null)),
      full: C.totals(s(0, 1, 2, 3, 4)),
      zeros: C.totals(s(0, 0, 0, 0, 0)),
      agree: C.agreement([3, 3])?.status, adjacent: C.agreement([2, 3, 3])?.status, disagree: C.agreement([1, 4])?.status,
      single: C.agreement([3]), withNull: C.agreement([3, null]),
      found: C.excerptFound('“most important question” in Nordland', 'The "most important question" in Nordland is…'),
      foundDash: C.excerptFound('distinct dimensions—redistributive effect', 'distinct dimensions — redistributive effect'.replace(' — ', '–')),
      notFound: C.excerptFound('an invented sentence', 'The essay text.'),
      bad5: tryErr(() => C.normalizeRecord({ scores: { I: { score: 5 } } })),
      badTotal: tryErr(() => C.normalizeRecord({ scores: { I: { score: 1 }, II: { score: 1 }, III: { score: 1 }, IV: { score: 1 }, V: { score: 1 } }, total_secondary: 9 })),
      strNum: C.normalizeRecord({ scores: { I: { score: '3' } } }).scores.I.score,
      badJson: tryErr(() => C.parseImport('{not json')),
      list: C.parseImport(JSON.stringify({ evaluations: [{ scores: {} }, { scores: {} }] })).length,
      four: C.validate({ response_id: 'X', evaluator: 'E', scores: { ...s(null, null, null, 4, null) } }).map(f => f.message),
      excerptsSplit: C.splitExcerpts('“First passage.”\n\nSecond passage.\n\n  '),
    };
  });
  check('partial profile has no total, sums scored dimensions', core.partial.total === null && core.partial.sum === 9 && core.partial.scored === 3);
  check('complete profile totals correctly (0+1+2+3+4 = 10)', core.full.total === 10 && core.full.complete);
  check('all-zero profile totals 0, not empty', core.zeros.total === 0);
  check('agreement: exact / adjacent / disagree', core.agree === 'agree' && core.adjacent === 'adjacent' && core.disagree === 'disagree');
  check('agreement not computed with fewer than two scores', core.single === null && core.withNull === null);
  check('excerpt match tolerates quote styles', core.found === true);
  check('excerpt match tolerates dash styles', core.foundDash === true);
  check('excerpt not in response is flagged', core.notFound === false);
  check('import rejects a score outside 0–4', /invalid score/.test(core.bad5 || ''), core.bad5);
  check('import rejects a total that does not match the scores', /does not equal/.test(core.badTotal || ''), core.badTotal);
  check('import accepts a numeric string score', core.strNum === 3);
  check('import rejects invalid JSON', /not valid JSON/.test(core.badJson || ''));
  check('import accepts {evaluations: [...]}', core.list === 2);
  check('a 4 without rationale raises the rubric warning', core.four.some(m => /score of 4 requires a short, passage-specific explanation/.test(m)));
  check('excerpts split on blank lines, quotes stripped', JSON.stringify(core.excerptsSplit) === JSON.stringify(['First passage.', 'Second passage.']));

  /* ------------------------------------------------------------ scoring workflow */
  section('Scoring workflow, export, draft and import');
  const ctx = await browser.newContext({ acceptDownloads: true, viewport: { width: 1366, height: 900 } });
  const p = await ctx.newPage();
  const errors = [];
  p.on('pageerror', e => errors.push(e.message));
  await p.goto(BASE + 'score.html#evaluate-ILL-B');
  check('deep link selects the response', await p.inputValue('#response_select') === 'ILL-B');
  check('full response text displayed', (await p.textContent('#response-text')).includes('My provisional conclusion is that Nordland has genuine redistributive achievements'));
  check('illustrative status shown', /Illustrative example/.test(await p.textContent('#selected-kind')));
  check('total empty before scoring', (await p.textContent('#score-total')).trim() === '—');
  const pick = { I: 3, II: 2, III: 3, IV: 4, V: 1 };
  for (const [d, v] of Object.entries(pick)) await p.check(`input[name="score_${d}"][value="${v}"]`);
  check('total updates to 13 when all five are scored', (await p.textContent('#score-total')).trim() === '13');
  const widths = await p.$$eval('#score-chart .bar-fill', els => els.map(e => e.style.width));
  check('bar chart widths follow scores (75/50/75/100/25%)', widths.join() === '75%,50%,75%,100%,25%', widths.join());
  check('chart has a text alternative', /IV Evidentiary discipline: 4 of 4/.test(await p.getAttribute('#score-chart .bars', 'aria-label')));
  check('score of 4 without rationale is flagged', /score of 4 requires/.test(await p.textContent('[data-warnings="IV"]')));
  await p.fill('#rationale_IV', 'Precisely bounds the trial: “Translation improved this outcome in the trial; it did not eliminate the gap”.');
  check('flag clears once a rationale is written', !/score of 4 requires/.test(await p.textContent('[data-warnings="IV"]')));
  await p.fill('#excerpts_IV', 'Language access offers firmer evidence for a narrower conclusion.\n\nAn invented passage that is not in the essay.');
  check('excerpt verification counts matches', /1 of 2 excerpts found/.test(await p.textContent('[data-excerpt-check="IV"]')));
  // Add selected text from the response panel
  await p.evaluate(() => {
    const el = [...document.querySelectorAll('#response-text p')].find(x => x.textContent.includes('Office 12'));
    const range = document.createRange(); range.selectNodeContents(el.firstChild ? el : el);
    const text = el.firstChild; const i = text.textContent.indexOf('Office 12');
    range.setStart(text, i); range.setEnd(text, i + 'Office 12\'s relatively small disparity despite interviews'.length);
    const sel = getSelection(); sel.removeAllRanges(); sel.addRange(range);
  });
  await p.click('[data-add-selection="III"]');
  check('selected response text is added as an excerpt', (await p.inputValue('#excerpts_III')).includes("Office 12's relatively small disparity despite interviews"));
  check('added excerpt verifies as found', /1 of 1 excerpt found/.test(await p.textContent('[data-excerpt-check="III"]')));
  await p.fill('#evaluator', 'Test evaluator');
  await p.fill('#weaknesses_II', 'Unclear whether the belonging distinction is developed.');
  await p.fill('#overall_summary', 'Test summary.');
  const [dl] = await Promise.all([p.waitForEvent('download'), p.click('#download-json')]);
  const rec = JSON.parse(readFileSync(await dl.path(), 'utf8'));
  check('JSON download named after response and evaluator', dl.suggestedFilename() === 'Nordland_Evaluation_ILL-B_Test_evaluator.json', dl.suggestedFilename());
  check('JSON record holds all five scores and the total', ['I', 'II', 'III', 'IV', 'V'].map(d => rec.scores[d].score).join() === '3,2,3,4,1' && rec.total_secondary === 13);
  check('JSON record is traceable (response hash, rubric hash, kind)',
    rec.response_sha256 === data.responses.find(r => r.id === 'ILL-B').sha256 && rec.rubric.sha256 === data.rubric.sha256 && rec.evaluation_kind === 'calibration-practice');
  check('JSON record keeps excerpts and weaknesses', rec.scores.IV.excerpts.length === 2 && rec.scores.II.weaknesses.startsWith('Unclear'));
  const [dl2] = await Promise.all([p.waitForEvent('download'), p.click('#download-report')]);
  const report = readFileSync(await dl2.path(), 'utf8');
  const ivAnchor = data.rubric.dimensions.find(d => d.roman === 'IV').anchors['4'];
  check('report quotes the exact anchor for each score', report.includes(`Anchor 4: ${ivAnchor}`));
  check('report marks excerpts found and not found', report.includes('(found in the response)') && report.includes('(NOT found word for word in the response)'));
  check('report states the total as secondary', /Total \(secondary\) \| 13 \/ 20/.test(report));
  check('report says it is not stored in GitHub', /not stored in the GitHub repository/.test(report));
  await p.reload();
  await p.waitForTimeout(200);
  check('draft is restored after reload (browser only)', (await p.textContent('#score-total')).trim() === '13' && await p.inputValue('#evaluator') === 'Test evaluator');
  check('status explains the draft is browser-only', /this browser/.test(await p.textContent('#tool-status')));
  await p.click('#clear-form');
  check('clear asks for confirmation first', (await p.textContent('#clear-form')).includes('Press again'));
  await p.click('#clear-form');
  check('clear empties the form', (await p.textContent('#score-total')).trim() === '—' && await p.inputValue('#evaluator') === '');
  await p.setInputFiles('#import-json', { name: 'record.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(rec)) });
  await p.waitForTimeout(200);
  check('import restores a downloaded record', (await p.textContent('#score-total')).trim() === '13' && await p.inputValue('#response_select') === 'ILL-B' && (await p.inputValue('#excerpts_IV')).includes('narrower conclusion'));
  await p.setInputFiles('#import-json', { name: 'bad.json', mimeType: 'application/json', buffer: Buffer.from('{"scores":{"I":{"score":7}}}') });
  await p.waitForTimeout(200);
  check('invalid import is refused with a reason', /Could not load bad\.json: Dimension I has an invalid score/.test(await p.textContent('#tool-status')));
  check('invalid import leaves the form unchanged', (await p.textContent('#score-total')).trim() === '13');
  check('keyboard: score radios reachable and operable', await p.evaluate(() => {
    const r = document.querySelector('input[name="score_I"][value="0"]'); r.focus(); return document.activeElement === r;
  }));
  await p.keyboard.press('ArrowDown');
  check('arrow key changes a score', await p.isChecked('input[name="score_I"][value="1"]') || await p.isChecked('input[name="score_I"][value="4"]'));
  check('no script errors on the scoring page', errors.length === 0, errors.join(' | '));

  /* ------------------------------------------------------------ comparison */
  section('Comparison');
  const c = await ctx.newPage();
  const cerr = []; c.on('pageerror', e => cerr.push(e.message));
  await c.goto(BASE + 'compare.html');
  const checkedIds = await c.$$eval('#compare-options input:checked', els => els.map(e => e.value));
  check('responses with evaluations preselected', checkedIds.join() === 'ILL-A,ILL-B,ILL-C', checkedIds.join());
  const ivRow = await c.$$eval('.cmp-table tbody tr', rows => rows.find(r => r.textContent.includes('Evidentiary discipline')).querySelectorAll('td strong'));
  const ivScores = await c.$$eval('.cmp-table tbody tr', rows => [...rows.find(r => r.textContent.includes('IV. Evidentiary')).querySelectorAll('td strong')].map(s => s.textContent));
  check('dimension IV scores shown as 0 / 3 / 4', ivScores.join() === '0,3,4', ivScores.join());
  const totals = await c.$$eval('.cmp-table tr.total td strong', els => els.map(e => e.textContent));
  check('totals shown as 4 / 15 / 20', totals.join() === '4,15,20', totals.join());
  check('illustrative-only comparison is labelled', /Illustrative examples only/.test(await c.textContent('#compare-output')));
  check('agreement withheld when only one evaluation per response', /Agreement cannot be assessed/.test(await c.textContent('#compare-output')));
  check('rationales shown as the basis for differences', (await c.textContent('#compare-output')).includes('wrongly treats observational office differences as a causal result'));
  check('caution about totals is shown', /A higher total is not, by itself, evidence of better conceptual reasoning/.test(await c.textContent('main')));
  const second = { ...rec, evaluator: 'Second evaluator', scores: { ...rec.scores, I: { ...rec.scores.I, score: 1 }, II: { ...rec.scores.II, score: 3 } } };
  delete second.total_secondary;
  await c.setInputFiles('#compare-import', [
    { name: 'first.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(rec)) },
    { name: 'second.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(second)) },
    { name: 'orphan.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify({ ...rec, response_id: 'NOT-PUBLISHED' })) },
  ]);
  await c.waitForTimeout(200);
  check('loaded files are labelled unpublished', /added an unpublished evaluation of ILL-B/.test(await c.textContent('#compare-status')));
  check('records for unpublished responses are refused', /NOT-PUBLISHED is not published/.test(await c.textContent('#compare-status')));
  const agreeText = await c.textContent('#compare-output');
  check('agreement table appears once multiple evaluations exist', /ILL-B · 3 evaluations/.test(agreeText));
  const statuses = await c.$$eval('#cmp-agree ~ .table-wrap tbody tr, #compare-output section:nth-of-type(2) tbody tr', rows => rows.map(r => r.lastElementChild.textContent));
  // ILL-B now has three evaluations: Appendix A (3,3,3,3,3), first file (3,2,3,4,1), second file (1,3,3,4,1).
  check('agreement statuses computed per dimension', statuses.join() === 'Disagree,Adjacent,Agree,Adjacent,Disagree', statuses.join(','));
  const [dl3] = await Promise.all([c.waitForEvent('download'), c.click('#download-comparison')]);
  const cmpReport = readFileSync(await dl3.path(), 'utf8');
  check('comparison report downloads with scores and rationales', cmpReport.includes('| IV. Evidentiary discipline |') && cmpReport.includes('Second evaluator'));
  await c.uncheck('#compare-options input[value="ILL-A"]');
  await c.uncheck('#compare-options input[value="ILL-C"]');
  check('fewer than two responses gives a neutral prompt', /Select at least two responses/.test(await c.textContent('#compare-output')));
  check('no script errors on the comparison page', cerr.length === 0, cerr.join(' | '));

  /* ------------------------------------------------------------ navigation */
  section('Navigation and links');
  const nav = await browser.newPage();
  let bad = [];
  const seen = new Set();
  for (const n of PAGES) {
    await nav.goto(BASE + n + '.html');
    const links = await nav.$$eval('a[href]', as => as.map(a => a.getAttribute('href')));
    for (const h of links) {
      if (/^(https?:|mailto:)/.test(h)) continue;
      const [pth, frag] = h.split('#');
      const target = pth || `${n}.html`;
      const key = `${target}#${frag || ''}`;
      if (seen.has(key)) continue; seen.add(key);
      const r = await nav.request.get(BASE + target);
      if (!r.ok()) { bad.push(`${n}: ${h} (${r.status()})`); continue; }
      if (frag && !frag.startsWith('evaluate-') && !(await r.text()).includes(`id="${frag}"`)) bad.push(`${n}: missing anchor ${h}`);
    }
  }
  check(`all internal links and anchors resolve (${seen.size} checked)`, bad.length === 0, bad.join('; '));
  await nav.goto(BASE + 'responses.html');
  await nav.click('#ILL-C >> text=Score this response');
  await nav.waitForLoadState();
  check('"Score this response" opens the tool on that response', nav.url().endsWith('score.html#evaluate-ILL-C') && await nav.inputValue('#response_select') === 'ILL-C');
  for (const [pg, tab] of [['evaluations', 'Recorded evaluations'], ['score', 'Score a response'], ['compare', 'Compare evaluations']]) {
    await nav.goto(BASE + pg + '.html');
    check(`${pg}: section nav and tab marked current`, await nav.textContent('.site-nav a[aria-current="page"]') === '05Evaluations' && await nav.textContent('.doc-tabs a[aria-current="page"]') === tab);
  }

  /* ------------------------------------------------------------ accessibility */
  section('Accessibility (axe-core, WCAG 2 A/AA)');
  const ax = await browser.newPage();
  for (const n of PAGES) {
    await ax.goto(BASE + n + (n === 'score' ? '.html#evaluate-ILL-A' : '.html'), { waitUntil: 'networkidle' });
    await ax.addScriptTag({ content: AXE });
    const res = await ax.evaluate(async () => (await window.axe.run(document, { runOnly: ['wcag2a', 'wcag2aa'] })).violations
      .map(v => ({ id: v.id, impact: v.impact, n: v.nodes.length, target: v.nodes[0]?.target?.join(' ') })));
    check(`${n}: no WCAG A/AA violations`, res.length === 0, res.map(v => `${v.id} [${v.impact}] ×${v.n} e.g. ${v.target}`).join('; '));
  }

  /* ------------------------------------------------------------ responsive layout */
  section('Responsive layout (no horizontal page scroll)');
  for (const [w, h, label] of [[390, 844, 'phone'], [820, 1180, 'tablet'], [1366, 900, 'desktop']]) {
    const rp = await browser.newPage({ viewport: { width: w, height: h } });
    const over = [];
    for (const n of PAGES) {
      await rp.goto(BASE + n + (n === 'score' ? '.html#evaluate-ILL-C' : '.html'), { waitUntil: 'networkidle' });
      const ov = await rp.evaluate(() => document.documentElement.scrollWidth - innerWidth);
      if (ov > 0) over.push(`${n} (+${ov}px)`);
    }
    check(`${label} ${w}px: all pages fit`, over.length === 0, over.join(', '));
    await rp.close();
  }
} catch (err) {
  failed++; results.push(`  FAIL  test run aborted: ${err.stack}`);
} finally {
  await browser.close();
  server.kill();
}
console.log(results.join('\n'));
console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
