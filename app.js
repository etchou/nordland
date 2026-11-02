'use strict';
(() => {
  // Accessible font-size adjustment; affects the active page only.
  let fontSize = 17;
  document.querySelectorAll('[data-font-adjust]').forEach(button => {
    button.addEventListener('click', () => {
      fontSize = Math.max(14, Math.min(22, fontSize + Number(button.dataset.fontAdjust)));
      document.documentElement.style.setProperty('--body-size', `${fontSize}px`);
      document.querySelectorAll('.case-content').forEach(el => { el.style.fontSize = `${Math.max(14, fontSize - 1)}px`; });
    });
  });

  const status = document.querySelector('[data-status]');
  const say = msg => { if (status) status.textContent = msg; };
  const getTemplateText = id => document.getElementById(id)?.content?.textContent || '';
  const copyText = async value => {
    if (!navigator.clipboard?.writeText) throw new Error('Browser clipboard unavailable');
    await navigator.clipboard.writeText(value);
  };
  document.querySelectorAll('[data-copy-template]').forEach(button => {
    button.addEventListener('click', async () => {
      try { await copyText(getTemplateText(button.dataset.copyTemplate));
        const old = button.textContent; button.textContent = 'Copied';
        setTimeout(() => { button.textContent = old; }, 1300);
      } catch { alert('Copy is unavailable in this browser. Use the linked text file instead.'); }
    });
  });
  document.querySelectorAll('[data-print]').forEach(button => {
    button.addEventListener('click', () => window.print());
  });

  if (!document.getElementById('score-form')) return;
  const rubric = window.NORDLAND_RUBRIC || [];
  const form = document.getElementById('score-form');
  const scoreInputs = [...form.querySelectorAll('[data-score]')];
  const dimensionById = new Map(rubric.map(d => [d.id, d]));

  function refresh() {
    let sum = 0;
    let completed = 0;
    scoreInputs.forEach(input => {
      const item = input.closest('.rubric-item');
      const level = input.value;
      const label = item.querySelector('[data-anchor-display]');
      const bar = item.querySelector('[data-score-bar]');
      const d = dimensionById.get(input.dataset.score);
      const chosen = level === '' ? null : Number(level);
      if (chosen !== null) { sum += chosen; completed++; }
      label.textContent = chosen === null ? 'Choose a score to view its evidence-based anchor.' : `${chosen} / 4 — ${d.anchors[chosen]}`;
      bar.style.width = chosen === null ? '0%' : `${chosen * 25}%`;
    });
    document.getElementById('score-total').textContent = `${sum}`;
    document.getElementById('score-complete').textContent = completed === 5
      ? 'All five dimensions rated. Total is a secondary summary.'
      : `${completed} of 5 dimensions rated · provisional total`;
    document.getElementById('score-total').setAttribute('aria-label', `${sum} out of 20`);
  }
  scoreInputs.forEach(input => input.addEventListener('change', refresh));
  refresh();

  function field(name) { return form.querySelector(`[name="${name}"]`)?.value?.trim() || ''; }
  function record() {
    return {
      record_type: 'Nordland evaluator scoring record',
      model_run: field('model_run'),
      assessor: field('assessor'),
      scored_on: field('scored_on'),
      case_record: field('record_used'),
      scores: rubric.map(d => ({
        dimension: d.title,
        score: field(d.id) === '' ? null : Number(field(d.id)),
        rationale: field(`${d.id}_reason`)
      })),
      total_secondary: scoreInputs.every(i => i.value !== '')
        ? scoreInputs.reduce((sum, input) => sum + Number(input.value), 0) : null,
      governing_thesis: field('governing_thesis'),
      consequential_insight: field('consequential_insight'),
      disconfirming_evidence: field('disconfirming_evidence'),
      unexpected_interpretation: field('unexpected_interpretation'),
      assessor_uncertainty: field('assessor_uncertainty')
    };
  }
  function download(text, type, filename) {
    const blob = new Blob([text], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename; document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }
  document.getElementById('export-json').addEventListener('click', () => {
    download(JSON.stringify(record(), null, 2), 'application/json;charset=utf-8', 'Nordland_Scoring_Record.json');
    say('Scoring record exported as JSON. No data was sent to a server.');
  });
  document.getElementById('export-csv').addEventListener('click', () => {
    const r = record();
    const quote = x => `"${String(x ?? '').replace(/"/g, '""')}"`;
    const rows = [['Model run', 'Assessor', 'Date', 'Dimension', 'Score', 'Rationale'], ...r.scores.map(s => [r.model_run, r.assessor, r.scored_on, s.dimension, s.score, s.rationale])];
    download(rows.map(row => row.map(quote).join(',')).join('\r\n') + '\r\n', 'text/csv;charset=utf-8', 'Nordland_Scoring_Record.csv');
    say('Dimension scores exported as CSV. Narrative notes are included in JSON export.');
  });
  document.getElementById('copy-record').addEventListener('click', async () => {
    try { await copyText(JSON.stringify(record(), null, 2)); say('Scoring record copied.'); }
    catch { say('Copy was blocked by the browser. Use Export JSON instead.'); }
  });
  document.getElementById('reset-form').addEventListener('click', () => {
    if (confirm('Clear all scoring fields on this page? Export a copy first if you need one.')) {
      form.reset(); refresh(); say('Scoring form cleared.');
    }
  });
})();
