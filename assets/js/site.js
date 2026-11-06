'use strict';
/* Nordland — shared browser behaviour. Progressive enhancement only:
   every page is fully readable without JavaScript. */
(() => {
  const status = document.querySelector('[data-status]');
  const say = msg => { if (status) status.textContent = msg; };

  const copyText = async text => {
    if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
    await navigator.clipboard.writeText(text);
  };

  /* Copy a <template>'s raw text (used for the exact case record). */
  document.querySelectorAll('[data-copy-template]').forEach(button => {
    button.addEventListener('click', async () => {
      const text = document.getElementById(button.dataset.copyTemplate)?.content?.textContent || '';
      const label = button.textContent;
      try {
        await copyText(text);
        button.textContent = 'Copied';
        say('Case record copied to clipboard.');
      } catch {
        button.textContent = 'Copy unavailable — use Download';
      }
      setTimeout(() => { button.textContent = label; }, 1800);
    });
  });

  document.querySelectorAll('[data-print]').forEach(b => b.addEventListener('click', () => window.print()));

  /* Contents rail: highlight the section currently in view. */
  const tocLinks = [...document.querySelectorAll('.toc a[href^="#"]')];
  if (tocLinks.length && 'IntersectionObserver' in window) {
    const byId = new Map(tocLinks.map(a => [decodeURIComponent(a.hash.slice(1)), a]));
    const targets = [...byId.keys()].map(id => document.getElementById(id)).filter(Boolean);
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        tocLinks.forEach(a => a.classList.remove('is-active'));
        byId.get(entry.target.id)?.classList.add('is-active');
      });
    }, { rootMargin: '-15% 0px -75% 0px' });
    targets.forEach(t => observer.observe(t));
  }

  /* Chart tooltips (values are also printed in text and in a table). */
  document.querySelectorAll('[data-chart]').forEach(figure => {
    const tip = figure.querySelector('.chart-tip');
    if (!tip) return;
    figure.querySelectorAll('[data-tip]').forEach(dot => {
      dot.addEventListener('mouseenter', () => {
        const [title, value] = dot.dataset.tip.split('|');
        tip.replaceChildren(Object.assign(document.createElement('strong'), { textContent: title }), document.createTextNode(value));
        const f = figure.getBoundingClientRect();
        const d = dot.getBoundingClientRect();
        const x = Math.min(Math.max(d.left + d.width / 2 - f.left, 130), f.width - 130);
        tip.style.left = `${x}px`;
        tip.style.top = `${d.top - f.top}px`;
        tip.classList.add('is-visible');
      });
      dot.addEventListener('mouseleave', () => tip.classList.remove('is-visible'));
    });
  });

  /* ---------- Scoring instrument (evaluations page) ---------- */
  const form = document.getElementById('score-form');
  if (!form) return;
  const rubric = new Map((window.NORDLAND_RUBRIC || []).map(d => [d.roman, d]));
  const selects = [...form.querySelectorAll('[data-score]')];
  const val = name => form.elements[name]?.value?.trim() ?? '';

  function refresh() {
    let sum = 0, done = 0;
    selects.forEach(select => {
      const row = select.closest('.score-row');
      const d = rubric.get(select.dataset.score);
      const anchor = row.querySelector('[data-anchor]');
      if (select.value === '') {
        anchor.textContent = 'No score selected.';
      } else {
        const n = Number(select.value);
        sum += n; done += 1;
        anchor.textContent = `${n} — ${d?.anchors?.[n] ?? ''}`;
      }
    });
    document.getElementById('score-total').textContent = String(sum);
    document.getElementById('score-state').textContent = done === 5
      ? 'All five dimensions scored'
      : `${done} of 5 dimensions scored · provisional`;
  }
  selects.forEach(s => s.addEventListener('change', refresh));
  refresh();

  /* Produces one record in the data/evaluations.json format. */
  function record() {
    const scores = {};
    selects.forEach(s => {
      const r = s.dataset.score;
      scores[r] = { score: s.value === '' ? null : Number(s.value), rationale: val(`rationale_${r}`) };
    });
    const values = Object.values(scores).map(s => s.score);
    return {
      case_prompt_identifier: val('case_prompt_identifier'),
      response_id: val('response_id'),
      model_run: val('model_run'),
      evaluator: val('evaluator'),
      date: val('date'),
      blind_to_model: form.elements.blind_to_model.checked,
      scores,
      total_secondary: values.every(v => v !== null) ? values.reduce((a, b) => a + b, 0) : null,
      governing_thesis: val('governing_thesis'),
      consequential_insight: val('consequential_insight'),
      disconfirming_evidence: val('disconfirming_evidence'),
      explanation_for_4s: val('explanation_for_4s'),
      unexpected_interpretation: val('unexpected_interpretation'),
      assessor_uncertainty: val('assessor_uncertainty')
    };
  }
  const fileStem = () => `Nordland_Evaluation_${(val('response_id') || 'unassigned').replace(/[^\w-]+/g, '_')}`;
  function download(text, type, filename) {
    const url = URL.createObjectURL(new Blob([text], { type }));
    const a = Object.assign(document.createElement('a'), { href: url, download: filename });
    document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }

  document.getElementById('export-json').addEventListener('click', () => {
    download(JSON.stringify(record(), null, 2), 'application/json;charset=utf-8', `${fileStem()}.json`);
    say('Exported JSON. Nothing was sent to a server.');
  });
  document.getElementById('export-csv').addEventListener('click', () => {
    const r = record();
    const q = x => `"${String(x ?? '').replace(/"/g, '""')}"`;
    const rows = [['Response', 'Evaluator', 'Date', 'Dimension', 'Score', 'Rationale'],
      ...Object.entries(r.scores).map(([roman, s]) => [r.response_id, r.evaluator, r.date, `${roman}. ${rubric.get(roman)?.name ?? ''}`, s.score, s.rationale])];
    download(rows.map(row => row.map(q).join(',')).join('\r\n') + '\r\n', 'text/csv;charset=utf-8', `${fileStem()}.csv`);
    say('Exported CSV of dimension scores. Synthesis notes are in the JSON export.');
  });
  document.getElementById('copy-record').addEventListener('click', async () => {
    try { await copyText(JSON.stringify(record(), null, 2)); say('Record copied as JSON.'); }
    catch { say('Copy was blocked by the browser. Use Export JSON instead.'); }
  });
  document.getElementById('reset-form').addEventListener('click', () => {
    if (confirm('Clear every field in this form? Export first if you need a copy.')) {
      form.reset(); refresh(); say('Form cleared.');
    }
  });
})();
