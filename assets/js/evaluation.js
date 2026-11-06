'use strict';
/* Nordland evaluation tools: scoring workspace (score.html) and comparison (compare.html).
   Everything runs in the browser. Nothing is sent to a server, nothing is written to GitHub,
   and no score is ever assigned automatically: every score comes from an evaluator's choice. */
(() => {
  const DATA = JSON.parse(document.getElementById('nordland-data')?.textContent || '{}');
  const DIMS = ['I', 'II', 'III', 'IV', 'V'];
  const SCHEMA = 'nordland-evaluation';
  const DRAFT_KEY = 'nordland-evaluation-draft';
  const META = ['response_id', 'case_prompt_identifier', 'model_run', 'evaluator', 'date', 'blind_to_model',
    'overall_summary', 'governing_thesis', 'consequential_insight', 'disconfirming_evidence', 'explanation_for_4s',
    'unexpected_interpretation', 'assessor_uncertainty'];
  const SYNTHESIS_LABELS = {
    overall_summary: 'Overall evaluation summary',
    governing_thesis: 'Governing thesis observed',
    consequential_insight: 'Most consequential insight or omission',
    disconfirming_evidence: 'Disconfirming evidence the model considered or overlooked',
    explanation_for_4s: 'Explanation for each score of 4',
    unexpected_interpretation: 'Unexpected interpretation (if any) and disposition',
    assessor_uncertainty: 'Assessor confidence / unresolved calibration issue'
  };

  /* ---------------------------------------------------------------- core (pure functions) */
  const Core = {
    DIMS,
    /** Normalise text for verbatim comparison: quotes, dashes and whitespace only; case is kept. */
    normalize(s) {
      return String(s ?? '')
        .replace(/[‘’‛′]/g, "'")
        .replace(/[“”‟″]/g, '"')
        .replace(/[‐-―−]/g, '-')
        .replace(/\s+/g, ' ')
        .trim();
    },
    /** Split an excerpts field into separate excerpts (blank-line separated); strip wrapping quotes. */
    splitExcerpts(text) {
      if (Array.isArray(text)) return text.map(t => String(t).trim()).filter(Boolean);
      return String(text ?? '').split(/\n\s*\n/).map(t => t.trim().replace(/^["“'‘]+|["”'’]+$/g, '').trim()).filter(Boolean);
    },
    /** Is the excerpt present, word for word, in the response text? */
    excerptFound(excerpt, responseText) {
      const ex = Core.normalize(excerpt).replace(/^\.{3}|\.{3}$|…/g, '').trim();
      return ex.length > 0 && Core.normalize(responseText).includes(ex);
    },
    /** Secondary total: only defined when all five dimensions are scored. */
    totals(scores) {
      const vals = DIMS.map(d => scores?.[d]?.score).filter(v => v !== null && v !== undefined && v !== '');
      const sum = vals.reduce((a, b) => a + Number(b), 0);
      return { sum, scored: vals.length, complete: vals.length === 5, total: vals.length === 5 ? sum : null };
    },
    isScore(v) { return v === null || (Number.isInteger(v) && v >= 0 && v <= 4); },
    /** Integrity checks drawn from the rubric document. Returns {level, dim, message} items. */
    validate(rec, response) {
      const out = [];
      if (!rec.response_id) out.push({ level: 'error', dim: null, message: 'Choose the response being scored.' });
      if (!String(rec.evaluator || '').trim()) out.push({ level: 'warning', dim: null, message: 'Name the evaluator so the record is attributable.' });
      for (const d of DIMS) {
        const s = rec.scores?.[d] || {};
        if (!Core.isScore(s.score ?? null)) out.push({ level: 'error', dim: d, message: `Dimension ${d}: the score must be a whole number from 0 to 4.` });
        if (s.score !== null && s.score !== undefined && !String(s.rationale || '').trim())
          out.push({ level: 'warning', dim: d, message: `Dimension ${d}: give a passage-specific reason for this score (rubric document §7, step 3).` });
        if (s.score === 4 && !String(s.rationale || '').trim())
          out.push({ level: 'warning', dim: d, message: `Dimension ${d}: a score of 4 requires a short, passage-specific explanation of how the response exceeded level 3.` });
        if (response) {
          const missing = Core.splitExcerpts(s.excerpts).filter(x => !Core.excerptFound(x, response.output_text));
          if (missing.length) out.push({ level: 'warning', dim: d, message: `Dimension ${d}: ${missing.length} excerpt${missing.length > 1 ? 's do' : ' does'} not appear word for word in the response.` });
        }
      }
      const t = Core.totals(rec.scores);
      if (!t.complete) out.push({ level: 'info', dim: null, message: `${t.scored} of 5 dimensions scored. The total is reported only when all five are scored.` });
      return out;
    },
    /** Agreement among evaluators on one dimension. Null when fewer than two scores exist. */
    agreement(values) {
      const v = values.filter(x => Number.isInteger(x));
      if (v.length < 2) return null;
      const range = Math.max(...v) - Math.min(...v);
      return { n: v.length, min: Math.min(...v), max: Math.max(...v), range,
        status: range === 0 ? 'agree' : range === 1 ? 'adjacent' : 'disagree' };
    },
    /** Validate and normalise an imported record (exported by this tool or from data/evaluations.json). */
    normalizeRecord(obj) {
      if (!obj || typeof obj !== 'object' || Array.isArray(obj)) throw new Error('The file does not contain an evaluation record.');
      if (!obj.scores || typeof obj.scores !== 'object') throw new Error('The record has no "scores" object.');
      const scores = {};
      for (const d of DIMS) {
        const s = obj.scores[d] || {};
        let v = s.score;
        if (v === '' || v === undefined) v = null;
        if (typeof v === 'string' && /^[0-4]$/.test(v)) v = Number(v);
        if (!Core.isScore(v)) throw new Error(`Dimension ${d} has an invalid score (${JSON.stringify(s.score)}). Scores must be 0–4 or empty.`);
        scores[d] = { score: v, rationale: String(s.rationale ?? ''), excerpts: Core.splitExcerpts(s.excerpts ?? []), weaknesses: String(s.weaknesses ?? '') };
      }
      const rec = { schema: SCHEMA, scores };
      for (const k of META) rec[k] = k === 'blind_to_model' ? Boolean(obj[k]) : String(obj[k] ?? '');
      rec.evaluation_kind = obj.evaluation_kind || '';
      rec.total_secondary = Core.totals(scores).total;
      if (obj.total_secondary !== undefined && obj.total_secondary !== null && obj.total_secondary !== rec.total_secondary)
        throw new Error(`The stated total (${obj.total_secondary}) does not equal the sum of the dimension scores.`);
      return rec;
    },
    /** Accept a single record, a list, or {evaluations: [...]}. */
    parseImport(text) {
      let parsed;
      try { parsed = JSON.parse(text); } catch { throw new Error('The file is not valid JSON.'); }
      const list = Array.isArray(parsed) ? parsed : Array.isArray(parsed?.evaluations) ? parsed.evaluations : [parsed];
      if (!list.length) throw new Error('The file contains no evaluation records.');
      return list.map(Core.normalizeRecord);
    },
    /** A readable Markdown report of one evaluation, with its traceability information. */
    report(rec, ctx) {
      const { rubric, response, now } = ctx;
      const t = Core.totals(rec.scores);
      const L = [];
      L.push(`# Nordland evaluation report`, '');
      L.push(`- Response: ${response ? `${response.id}, ${response.title}` : rec.response_id || 'not specified'}`);
      if (response) {
        L.push(`- Response type: ${response.kind === 'illustrative' ? 'Illustrative example (constructed calibration essay; not a model output)' : 'Experimental model output'}`);
        L.push(`- Response text SHA-256: ${response.sha256}`);
      }
      L.push(`- Case/prompt identifier: ${rec.case_prompt_identifier || 'not recorded'}`);
      L.push(`- Model and run identifier: ${rec.model_run || 'not recorded'}`);
      L.push(`- Evaluator: ${rec.evaluator || 'not recorded'}`);
      L.push(`- Date: ${rec.date || 'not recorded'}`);
      L.push(`- Scored blind to model identity: ${rec.blind_to_model ? 'yes' : 'no'}`);
      L.push(`- Rubric: ${rubric.document}, ${rubric.section} (PDF SHA-256 ${rubric.sha256})`);
      L.push(`- Report generated: ${now}`, '');
      L.push('## Score profile', '', '| Dimension | Score |', '|---|---|');
      for (const d of rubric.dimensions) {
        const v = rec.scores[d.roman]?.score;
        L.push(`| ${d.roman}. ${d.name} | ${v === null || v === undefined ? 'not scored' : `${v} / 4`} |`);
      }
      L.push(`| Total (secondary) | ${t.complete ? `${t.total} / 20` : `incomplete (${t.scored} of 5 scored)`} |`, '');
      L.push('The five-score profile is the primary result; the total is a secondary summary.', '');
      for (const d of rubric.dimensions) {
        const s = rec.scores[d.roman] || {};
        L.push(`## ${d.roman}. ${d.name} — ${d.subtitle}`, '');
        if (s.score === null || s.score === undefined) L.push('Score: not scored', '');
        else L.push(`Score: ${s.score} / 4`, '', `Anchor ${s.score}: ${d.anchors[String(s.score)]}`, '');
        L.push(`Evaluator rationale: ${s.rationale?.trim() || 'none recorded'}`, '');
        const ex = Core.splitExcerpts(s.excerpts);
        if (ex.length) {
          L.push('Supporting excerpts:');
          for (const x of ex) L.push(`- “${x}”${response ? (Core.excerptFound(x, response.output_text) ? ' (found in the response)' : ' (NOT found word for word in the response)') : ''}`);
          L.push('');
        } else L.push('Supporting excerpts: none recorded', '');
        L.push(`Weaknesses, uncertainty or unresolved questions: ${s.weaknesses?.trim() || 'none recorded'}`, '');
      }
      L.push('## Synthesis', '');
      for (const [k, label] of Object.entries(SYNTHESIS_LABELS)) L.push(`**${label}:** ${String(rec[k] || '').trim() || 'none recorded'}`, '');
      const flags = Core.validate(rec, response).filter(f => f.level !== 'info');
      if (flags.length) { L.push('## Open checks', ''); for (const f of flags) L.push(`- ${f.message}`); L.push(''); }
      L.push('---', '', 'Saved from the Nordland scoring tool. This file is not stored in the GitHub repository unless someone adds it there.');
      return L.join('\n');
    }
  };
  window.NordlandCore = Core;

  /* ---------------------------------------------------------------- shared helpers */
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const responses = DATA.responses || [];
  const byId = new Map(responses.map(r => [r.id, r]));
  const rubric = DATA.rubric || { dimensions: [] };
  const dimInfo = new Map(rubric.dimensions.map(d => [d.roman, d]));
  const storage = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); return true; } catch { return false; } },
    del(k) { try { localStorage.removeItem(k); } catch { /* unavailable */ } }
  };
  function download(text, type, name) {
    const url = URL.createObjectURL(new Blob([text], { type }));
    const a = Object.assign(document.createElement('a'), { href: url, download: name });
    document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }
  const stamp = () => new Date().toISOString().replace(/\.\d+Z$/, 'Z');
  const fileStem = rec => `Nordland_Evaluation_${(rec.response_id || 'unassigned').replace(/[^\w-]+/g, '_')}_${(rec.evaluator || 'evaluator').replace(/[^\w-]+/g, '_')}`;
  function bars(scores, label) {
    const rows = rubric.dimensions.map(d => {
      const v = scores?.[d.roman]?.score;
      const has = Number.isInteger(v);
      return `<div class="bar-row"><span class="bar-label">${d.roman}. ${esc(d.name)}</span>` +
        `<span class="bar-track${has ? '' : ' is-empty'}"><span class="bar-fill" style="width:${has ? v * 25 : 0}%"></span></span>` +
        `<span class="bar-value">${has ? v : '—'}</span></div>`;
    }).join('');
    const aria = rubric.dimensions.map(d => { const v = scores?.[d.roman]?.score; return `${d.roman} ${d.name}: ${Number.isInteger(v) ? `${v} of 4` : 'not scored'}`; }).join('; ');
    return `<div class="bars" role="img" aria-label="${esc(label)}: ${esc(aria)}">${rows}<div class="bar-scale" aria-hidden="true"><span></span><span class="ticks"><span>0</span><span>1</span><span>2</span><span>3</span><span>4</span></span><span></span></div></div>`;
  }
  const kindLabel = k => k === 'illustrative' ? 'Illustrative example' : 'Experimental output';

  /* ---------------------------------------------------------------- scoring workspace */
  const tool = $('#score-tool');
  if (tool) {
    const select = $('#response_select');
    const status = $('#tool-status');
    const say = m => { status.textContent = m; };
    const groups = [['experimental', 'Experimental responses'], ['illustrative', 'Illustrative examples (constructed, for calibration)']];
    select.innerHTML = '<option value="">Choose a response…</option>' + groups.map(([k, label]) => {
      const items = responses.filter(r => r.kind === k);
      return `<optgroup label="${esc(label)}">${items.length ? items.map(r => `<option value="${esc(r.id)}">${esc(r.id)} · ${esc(r.title)}</option>`).join('') : '<option disabled>None recorded yet</option>'}</optgroup>`;
    }).join('');

    function read() {
      const rec = { schema: SCHEMA, scores: {} };
      for (const k of META) {
        const el = $(`[data-meta="${k}"]`, tool);
        rec[k] = !el ? '' : el.type === 'checkbox' ? el.checked : el.value.trim();
      }
      for (const d of DIMS) {
        const chosen = $(`input[name="score_${d}"]:checked`, tool);
        rec.scores[d] = {
          score: chosen ? Number(chosen.value) : null,
          rationale: $(`[data-field="rationale"][data-dim="${d}"]`, tool).value.trim(),
          excerpts: Core.splitExcerpts($(`[data-field="excerpts"][data-dim="${d}"]`, tool).value),
          weaknesses: $(`[data-field="weaknesses"][data-dim="${d}"]`, tool).value.trim()
        };
      }
      const r = byId.get(rec.response_id);
      rec.evaluation_kind = r ? (r.kind === 'illustrative' ? 'calibration-practice' : 'experimental') : '';
      rec.response_sha256 = r?.sha256 || '';
      rec.rubric = { document: rubric.document, section: rubric.section, sha256: rubric.sha256 };
      rec.total_secondary = Core.totals(rec.scores).total;
      return rec;
    }
    function write(rec) {
      for (const k of META) {
        const el = $(`[data-meta="${k}"]`, tool);
        if (!el) continue;
        if (el.type === 'checkbox') el.checked = Boolean(rec[k]); else el.value = rec[k] ?? '';
      }
      for (const d of DIMS) {
        const s = rec.scores?.[d] || {};
        $$(`input[name="score_${d}"]`, tool).forEach(i => { i.checked = s.score !== null && s.score !== undefined && Number(i.value) === s.score; });
        $(`[data-field="rationale"][data-dim="${d}"]`, tool).value = s.rationale || '';
        $(`[data-field="excerpts"][data-dim="${d}"]`, tool).value = Core.splitExcerpts(s.excerpts).join('\n\n');
        $(`[data-field="weaknesses"][data-dim="${d}"]`, tool).value = s.weaknesses || '';
      }
      showResponse(rec.response_id);
    }
    function showResponse(id) {
      const r = byId.get(id);
      $('#response-text').innerHTML = r ? r.output_html : '<p class="muted">Choose a response to show its full text here.</p>';
      $('#response-meta').innerHTML = !r ? '' :
        `<p><strong>${esc(r.id)}</strong> · ${esc(kindLabel(r.kind))} · ${r.word_count} words · text SHA-256 ${esc(r.sha256.slice(0, 12))}</p>` +
        (r.kind === 'illustrative' ? `<p>${esc(r.source)} of the rubric document. Constructed for calibration; not a model output.</p>`
          : `<p>${esc([r.model, r.model_version, r.run_date].filter(Boolean).join(' · ') || 'Model details not recorded')}</p>`);
      $('#selected-kind').innerHTML = !r ? '' : r.kind === 'illustrative'
        ? '<p class="kind-note kind-note--illustrative"><strong>Illustrative example.</strong> Scoring it is calibration practice. Compare your scores with Appendix A only after scoring, to reduce anchoring.</p>'
        : '<p class="kind-note kind-note--experimental"><strong>Experimental output.</strong> Score independently and cite passages for every dimension.</p>';
      const cp = $('#case_prompt_identifier');
      if (r && !cp.value) cp.value = r.kind === 'illustrative' ? `${DATA.case_prompt.identifier}; ${r.source}` : (r.case_prompt_identifier || DATA.case_prompt.identifier);
      const mr = $('#model_run');
      if (r && !mr.value) mr.value = r.kind === 'illustrative' ? `${r.id} (constructed; no model)` : [r.model, r.model_version, r.run_date].filter(Boolean).join(' / ');
    }
    function render() {
      const rec = read();
      const r = byId.get(rec.response_id);
      $('#score-chart').innerHTML = bars(rec.scores, 'Score profile');
      const t = Core.totals(rec.scores);
      $('#score-total').textContent = t.complete ? String(t.total) : '—';
      $('#score-state').textContent = t.complete ? '· all five dimensions scored' : `· ${t.scored} of 5 scored; total shown when complete`;
      const flags = Core.validate(rec, r);
      for (const d of DIMS) {
        const card = $(`#dim-${d}`);
        card.classList.toggle('is-scored', rec.scores[d].score !== null);
        $(`[data-warnings="${d}"]`).innerHTML = flags.filter(f => f.dim === d && f.level !== 'info').map(f => `<li>${esc(f.message)}</li>`).join('');
        const ex = rec.scores[d].excerpts;
        const found = r ? ex.filter(x => Core.excerptFound(x, r.output_text)).length : 0;
        $(`[data-excerpt-check="${d}"]`).textContent = !ex.length ? '' : !r ? `${ex.length} excerpt${ex.length > 1 ? 's' : ''}` :
          `${found} of ${ex.length} excerpt${ex.length > 1 ? 's' : ''} found word for word in the response`;
        $(`[data-excerpt-check="${d}"]`).classList.toggle('is-warning', Boolean(r) && found < ex.length);
      }
      $('#record-warnings').innerHTML = flags.filter(f => !f.dim).map(f => `<li class="${f.level}">${esc(f.message)}</li>`).join('');
      return rec;
    }
    let saveTimer;
    function persist() {
      clearTimeout(saveTimer);
      saveTimer = setTimeout(() => {
        const ok = storage.set(DRAFT_KEY, JSON.stringify(read()));
        say(ok ? `Draft kept in this browser at ${new Date().toLocaleTimeString()}. It is not saved to GitHub; download the JSON record to keep it.`
          : 'This browser is not keeping a draft. Download the JSON record to keep your work.');
      }, 400);
    }
    tool.addEventListener('input', () => { render(); persist(); });
    tool.addEventListener('change', e => {
      if (e.target === select) { showResponse(select.value); history.replaceState(null, '', select.value ? `#evaluate-${select.value}` : location.pathname); }
      render(); persist();
    });
    $$('[data-clear-score]', tool).forEach(b => b.addEventListener('click', () => {
      $$(`input[name="score_${b.dataset.clearScore}"]`, tool).forEach(i => { i.checked = false; });
      render(); persist();
    }));
    $$('[data-add-selection]', tool).forEach(b => b.addEventListener('click', () => {
      const sel = window.getSelection();
      const text = sel ? sel.toString().trim() : '';
      const panel = $('#response-text');
      if (!text || !sel.anchorNode || !panel.contains(sel.anchorNode)) { say('Select a passage in the response text first, then press the button.'); return; }
      const ta = $(`[data-field="excerpts"][data-dim="${b.dataset.addSelection}"]`, tool);
      ta.value = [ta.value.trim(), text].filter(Boolean).join('\n\n');
      render(); persist(); say('Added the selected passage as an excerpt.');
    }));
    $('#download-json').addEventListener('click', () => {
      const rec = { ...read(), exported_at: stamp() };
      if (!rec.response_id) { say('Choose the response being scored before downloading.'); return; }
      download(JSON.stringify(rec, null, 2) + '\n', 'application/json;charset=utf-8', `${fileStem(rec)}.json`);
      say('Downloaded the JSON record. It exists only on your computer until it is added to the repository.');
    });
    $('#download-report').addEventListener('click', () => {
      const rec = read();
      if (!rec.response_id) { say('Choose the response being scored before downloading.'); return; }
      download(Core.report(rec, { rubric, response: byId.get(rec.response_id), now: stamp() }), 'text/markdown;charset=utf-8', `${fileStem(rec)}.md`);
      say('Downloaded the readable report (Markdown).');
    });
    $('#import-json').addEventListener('change', async e => {
      const file = e.target.files?.[0];
      e.target.value = '';
      if (!file) return;
      try {
        const recs = Core.parseImport(await file.text());
        const rec = recs[0];
        if (rec.response_id && !byId.has(rec.response_id)) say(`Loaded, but response ${rec.response_id} is not published on this site, so excerpts cannot be checked.`);
        write(rec); render(); persist();
        if (!rec.response_id || byId.has(rec.response_id)) say(`Loaded ${file.name}${recs.length > 1 ? ` (first of ${recs.length} records)` : ''}.`);
      } catch (err) { say(`Could not load ${file.name}: ${err.message}`); }
    });
    const clearBtn = $('#clear-form');
    let armed = null;
    clearBtn.addEventListener('click', () => {
      if (!armed) {
        clearBtn.textContent = 'Press again to clear everything';
        armed = setTimeout(() => { clearBtn.textContent = 'Clear form'; armed = null; }, 4000);
        return;
      }
      clearTimeout(armed); armed = null; clearBtn.textContent = 'Clear form';
      tool.reset(); storage.del(DRAFT_KEY); showResponse(''); render(); say('Form cleared and draft removed from this browser.');
    });

    // Start: a response named in the address (#evaluate-ID), else the saved draft.
    const fromHash = location.hash.startsWith('#evaluate-') ? decodeURIComponent(location.hash.slice(10)) : '';
    let draft = null;
    try { draft = JSON.parse(storage.get(DRAFT_KEY) || 'null'); } catch { draft = null; }
    if (draft && (!fromHash || draft.response_id === fromHash)) {
      try { write(Core.normalizeRecord(draft)); say('Restored your draft from this browser.'); } catch { storage.del(DRAFT_KEY); }
    } else if (fromHash && byId.has(fromHash)) {
      select.value = fromHash; showResponse(fromHash);
      if (draft) say('A draft for another response is kept in this browser; it will be replaced when you edit this one.');
    } else showResponse('');
    render();
  }

  /* ---------------------------------------------------------------- comparison */
  const out = $('#compare-output');
  if (out) {
    const loaded = [];   // records loaded from files in this session (unpublished)
    const published = (DATA.evaluations || []).map(ev => ({ ...ev, origin: ev.evaluation_kind === 'illustrative' ? 'Illustrative calibration judgment' : 'Published evaluation' }));
    const pool = () => published.concat(loaded);
    const opts = $('#compare-options');
    const status = $('#compare-status');
    const counts = id => pool().filter(ev => ev.response_id === id).length;
    function renderOptions() {
      const checked = new Set($$('input', opts).filter(i => i.checked).map(i => i.value));
      const first = !opts.children.length;
      opts.innerHTML = [['experimental', 'Experimental responses'], ['illustrative', 'Illustrative examples']].map(([k, label]) => {
        const items = responses.filter(r => r.kind === k);
        return `<div class="pick-group"><p class="pick-label">${label}</p>${items.length ? items.map(r => {
          const n = counts(r.id);
          const on = first ? (n > 0) : checked.has(r.id);
          return `<label class="check"><input type="checkbox" value="${esc(r.id)}"${on ? ' checked' : ''}> ${esc(r.id)} · ${esc(r.title)} <span class="muted">(${n} evaluation${n === 1 ? '' : 's'})</span></label>`;
        }).join('') : '<p class="muted">None recorded yet.</p>'}</div>`;
      }).join('');
    }
    function selected() { return $$('input:checked', opts).map(i => byId.get(i.value)).filter(Boolean); }
    function evalLabel(ev, i) { return `${ev.evaluator || 'Unnamed evaluator'}${ev.date ? `, ${ev.date}` : ''}${ev.origin === 'Loaded from file (unpublished)' ? ' · unpublished' : ''}` || `Evaluation ${i + 1}`; }

    function build() {
      const rs = selected();
      if (rs.length < 2) {
        out.innerHTML = '<div class="placeholder"><span class="status">Choose responses</span><h3>Select at least two responses</h3><p>Choose two or more responses above. Responses without evaluations are shown with empty scores.</p></div>';
        return null;
      }
      const cols = rs.map(r => ({ r, evs: pool().filter(ev => ev.response_id === r.id) }));
      const anyIll = rs.some(r => r.kind === 'illustrative');
      const anyExp = rs.some(r => r.kind === 'experimental');
      let html = '';
      if (anyIll && anyExp) html += '<p class="kind-note kind-note--illustrative"><strong>Mixed comparison.</strong> Illustrative examples are constructed calibration essays. Comparing them with experimental outputs shows rubric calibration, not model performance.</p>';
      else if (anyIll) html += '<p class="kind-note kind-note--illustrative"><strong>Illustrative examples only.</strong> These are constructed calibration essays and their proposed calibration judgments, not experimental results.</p>';

      // 1. Dimension-level and overall scores
      const head = cols.map(c => `<th scope="col">${esc(c.r.id)}<span class="th-sub">${esc(c.r.title.split(' — ')[1] || c.r.title)} · ${esc(kindLabel(c.r.kind))}</span></th>`).join('');
      const cell = (evs, d) => !evs.length ? '<td class="muted">No evaluation</td>' :
        `<td>${evs.map((ev, i) => { const v = ev.scores?.[d]?.score; return `<div class="cmp-score"><span class="mini-track"><span class="mini-fill" style="width:${Number.isInteger(v) ? v * 25 : 0}%"></span></span><strong>${Number.isInteger(v) ? v : '—'}</strong><span class="muted">${esc(evs.length > 1 ? evalLabel(ev, i) : '')}</span></div>`; }).join('')}</td>`;
      const rows = rubric.dimensions.map(d => `<tr><th scope="row">${d.roman}. ${esc(d.name)}</th>${cols.map(c => cell(c.evs, d.roman)).join('')}</tr>`).join('');
      const totals = `<tr class="total"><th scope="row">Total (secondary)</th>${cols.map(c => `<td>${c.evs.length ? c.evs.map(ev => { const t = Core.totals(ev.scores); return `<div>${t.complete ? `<strong>${t.total}</strong> / 20` : `incomplete (${t.scored}/5)`}</div>`; }).join('') : '<span class="muted">—</span>'}</td>`).join('')}</tr>`;
      html += `<section aria-labelledby="cmp-scores"><h3 id="cmp-scores">Dimension and overall scores</h3>
        <div class="table-wrap" role="region" tabindex="0" aria-label="Score comparison"><table class="cmp-table"><thead><tr><th scope="col">Dimension</th>${head}</tr></thead><tbody>${rows}${totals}</tbody></table></div>
        <p class="table-note">Bars show each score on the 0–4 scale. Totals are a secondary summary and do not by themselves show better conceptual reasoning.</p></section>`;

      // 2. Evaluator agreement — only where a response has more than one evaluation
      const multi = cols.filter(c => c.evs.length > 1);
      html += '<section aria-labelledby="cmp-agree"><h3 id="cmp-agree">Evaluator agreement</h3>';
      if (!multi.length) html += '<p class="muted">Agreement cannot be assessed: each selected response has at most one evaluation. Agreement is reported only when two or more evaluations of the same response exist.</p>';
      else {
        html += '<p>Agreement on each dimension among evaluations of the same response: exact agreement, adjacent scores (one point apart), or disagreement (two or more points apart).</p>';
        html += multi.map(c => `<div class="table-wrap" role="region" tabindex="0" aria-label="Agreement for ${esc(c.r.id)}"><table><caption>${esc(c.r.id)} · ${c.evs.length} evaluations</caption><thead><tr><th scope="col">Dimension</th><th scope="col">Scores</th><th scope="col">Range</th><th scope="col">Status</th></tr></thead><tbody>${
          rubric.dimensions.map(d => { const vals = c.evs.map(ev => ev.scores?.[d.roman]?.score); const a = Core.agreement(vals);
            return `<tr><th scope="row">${d.roman}. ${esc(d.name)}</th><td>${vals.map(v => Number.isInteger(v) ? v : '—').join(', ')}</td><td>${a ? a.range : '—'}</td><td>${a ? `<span class="agree agree--${a.status}">${{ agree: 'Agree', adjacent: 'Adjacent', disagree: 'Disagree' }[a.status]}</span>` : 'Not enough scores'}</td></tr>`; }).join('')
        }</tbody></table></div>`).join('');
      }
      html += '</section>';

      // 3. Basis for each score: the evaluators' own reasoning, dimension by dimension
      html += `<section aria-labelledby="cmp-basis"><h3 id="cmp-basis">Basis for each score</h3>
        <p>What each evaluator wrote, dimension by dimension. Where scores differ, these rationales and excerpts are the explanation of the difference; the tool adds none of its own.</p>`;
      for (const d of rubric.dimensions) {
        const vals = cols.flatMap(c => c.evs.map(ev => ev.scores?.[d.roman]?.score)).filter(Number.isInteger);
        const spread = vals.length > 1 ? Math.max(...vals) - Math.min(...vals) : 0;
        html += `<details class="disclosure cmp-dim"${spread ? ' open' : ''}><summary>${d.roman}. ${esc(d.name)}<span class="summary-meta">${vals.length > 1 ? (spread ? `Scores differ by up to ${spread}` : 'Same score') : ''}</span></summary><div class="disclosure-body"><div class="cmp-basis">${
          cols.map(c => `<div class="basis-col"><p class="basis-head">${esc(c.r.id)}</p>${c.evs.length ? c.evs.map((ev, i) => { const s = ev.scores?.[d.roman] || {};
            const ex = Core.splitExcerpts(s.excerpts);
            return `<div class="basis-item"><p class="basis-score"><strong>${Number.isInteger(s.score) ? `${s.score} / 4` : 'Not scored'}</strong> <span class="muted">${esc(evalLabel(ev, i))} · ${esc(ev.origin)}</span></p>
              ${Number.isInteger(s.score) ? `<p class="cell-anchor">Anchor ${s.score}: ${esc(d.anchors[String(s.score)])}</p>` : ''}
              <p>${esc(s.rationale || 'No rationale recorded.')}</p>
              ${ex.length ? `<p class="cell-label">Supporting excerpts</p><ul class="excerpts">${ex.map(x => `<li>${esc(x)} <span class="${Core.excerptFound(x, c.r.output_text) ? 'ok' : 'warn'}">${Core.excerptFound(x, c.r.output_text) ? '(found in response)' : '(not found word for word)'}</span></li>`).join('')}</ul>` : ''}
              ${s.weaknesses ? `<p class="cell-label">Weaknesses or uncertainty</p><p>${esc(s.weaknesses)}</p>` : ''}</div>`; }).join('') : '<p class="muted">No evaluation recorded.</p>'}</div>`).join('')
        }</div></div></details>`;
      }
      html += '</section>';

      // 4. Overall summaries
      html += `<section aria-labelledby="cmp-summary"><h3 id="cmp-summary">Overall evaluation summaries</h3><div class="cmp-basis">${
        cols.map(c => `<div class="basis-col"><p class="basis-head">${esc(c.r.id)}</p>${c.evs.length ? c.evs.map((ev, i) => `<div class="basis-item"><p class="muted">${esc(evalLabel(ev, i))}</p><p>${esc(ev.overall_summary || 'No overall summary recorded.')}</p>${ev.calibration_note ? `<p class="cell-label">Calibration note</p><p>${esc(ev.calibration_note)}</p>` : ''}</div>`).join('') : '<p class="muted">No evaluation recorded.</p>'}</div>`).join('')
      }</div></section>`;
      out.innerHTML = html;
      return cols;
    }
    function reportMd(cols) {
      const L = ['# Nordland evaluation comparison', '', `Generated: ${stamp()}`, `Rubric: ${rubric.document}, ${rubric.section}`, '',
        'The five-score profile is the primary result; the total out of 20 is a secondary summary. A higher total is not, by itself, evidence of better conceptual reasoning.', ''];
      L.push(`| Dimension | ${cols.map(c => c.r.id).join(' | ')} |`, `|---|${cols.map(() => '---').join('|')}|`);
      for (const d of rubric.dimensions) L.push(`| ${d.roman}. ${d.name} | ${cols.map(c => c.evs.map(ev => ev.scores?.[d.roman]?.score ?? '—').join(', ') || 'no evaluation').join(' | ')} |`);
      L.push(`| Total (secondary) | ${cols.map(c => c.evs.map(ev => Core.totals(ev.scores).total ?? 'incomplete').join(', ') || '—').join(' | ')} |`, '');
      for (const c of cols) {
        L.push(`## ${c.r.id}: ${c.r.title} (${kindLabel(c.r.kind)})`, '');
        if (!c.evs.length) { L.push('No evaluation recorded.', ''); continue; }
        for (const ev of c.evs) {
          L.push(`### ${ev.evaluator || 'Unnamed evaluator'}${ev.date ? `, ${ev.date}` : ''} (${ev.origin})`, '');
          for (const d of rubric.dimensions) { const s = ev.scores?.[d.roman] || {}; L.push(`- ${d.roman}. ${d.name}: ${s.score ?? 'not scored'}. ${s.rationale || 'No rationale recorded.'}`); }
          L.push('', `Overall summary: ${ev.overall_summary || 'none recorded'}`, '');
        }
      }
      return L.join('\n');
    }
    opts.addEventListener('change', build);
    $('#compare-import').addEventListener('change', async e => {
      const files = [...(e.target.files || [])];
      e.target.value = '';
      const msgs = [];
      for (const f of files) {
        try {
          const recs = Core.parseImport(await f.text());
          for (const rec of recs) {
            if (!byId.has(rec.response_id)) { msgs.push(`${f.name}: response ${rec.response_id || '(none)'} is not published on this site, so it was not added.`); continue; }
            loaded.push({ ...rec, id: `LOADED-${loaded.length + 1}`, origin: 'Loaded from file (unpublished)' });
            msgs.push(`${f.name}: added an unpublished evaluation of ${rec.response_id}.`);
          }
        } catch (err) { msgs.push(`${f.name}: ${err.message}`); }
      }
      status.textContent = msgs.join(' ');
      renderOptions(); build();
    });
    $('#download-comparison').addEventListener('click', () => {
      const cols = build();
      if (!cols) { status.textContent = 'Select at least two responses first.'; return; }
      download(reportMd(cols) + '\n', 'text/markdown;charset=utf-8', 'Nordland_Evaluation_Comparison.md');
      status.textContent = 'Downloaded the comparison report (Markdown).';
    });
    renderOptions(); build();
  }
})();
