'use strict';
(() => {
  // Accessible font-size adjustment; affects the active page only.
  let fontSize = 17;
  document.querySelectorAll('[data-font-adjust]').forEach(button => {
    button.addEventListener('click', () => {
      fontSize = Math.max(14, Math.min(22, fontSize + Number(button.dataset.fontAdjust)));
      document.documentElement.style.setProperty('--body-size', `${fontSize}px`);
    });
  });

  // Mobile navigation disclosure.
  const toggle = document.querySelector('.nav-toggle');
  const nav = document.getElementById('site-nav');
  if (toggle && nav) {
    const setOpen = open => {
      nav.classList.toggle('is-open', open);
      toggle.setAttribute('aria-expanded', String(open));
      toggle.textContent = open ? 'Close' : 'Menu';
    };
    toggle.addEventListener('click', () => setOpen(!nav.classList.contains('is-open')));
    nav.addEventListener('click', ev => { if (ev.target.closest('a')) setOpen(false); });
    document.addEventListener('click', ev => { if (nav.classList.contains('is-open') && !nav.contains(ev.target) && !toggle.contains(ev.target)) setOpen(false); });
    document.addEventListener('keydown', ev => {
      if (ev.key === 'Escape' && nav.classList.contains('is-open')) { setOpen(false); toggle.focus(); }
    });
  }

  // Scroll-spy for the contents rails.
  document.querySelectorAll('.toc, .case-toc').forEach(rail => {
    const links = [...rail.querySelectorAll('a[href^="#"]')];
    const targets = links.map(a => document.getElementById(a.getAttribute('href').slice(1))).filter(Boolean);
    if (!targets.length) return;
    let ticking = false;
    const mark = () => {
      ticking = false;
      const line = window.innerHeight * 0.3;
      let current = null;
      targets.forEach(t => { if (t.getBoundingClientRect().top <= line) current = t; });
      links.forEach(a => a.setAttribute('aria-current', String(!!current && a.getAttribute('href') === `#${current.id}`)));
    };
    window.addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(mark); } }, { passive: true });
    mark();
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

  // Calibration comparison: one dimension's three rationales at a time.
  const rowButtons = [...document.querySelectorAll('[data-compare]')];
  if (rowButtons.length) {
    const panels = [...document.querySelectorAll('[data-compare-panel]')];
    const show = idx => {
      rowButtons.forEach(b => {
        const on = b.dataset.compare === idx;
        b.setAttribute('aria-pressed', String(on));
        b.closest('tr').classList.toggle('is-active', on);
      });
      panels.forEach(p => { p.hidden = p.dataset.comparePanel !== idx; });
    };
    rowButtons.forEach(b => b.addEventListener('click', () => show(b.dataset.compare)));
    show('0');
  }

  // Calibration responses: accessible tabs.
  const tabs = [...document.querySelectorAll('[role="tab"]')];
  if (tabs.length) {
    const select = (tab, focus) => {
      tabs.forEach(t => {
        const on = t === tab;
        t.setAttribute('aria-selected', String(on));
        t.tabIndex = on ? 0 : -1;
        document.getElementById(t.getAttribute('aria-controls')).hidden = !on;
      });
      if (focus) tab.focus();
    };
    tabs.forEach((tab, i) => {
      tab.addEventListener('click', () => select(tab));
      tab.addEventListener('keydown', ev => {
        const k = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[ev.key];
        if (k) { ev.preventDefault(); select(tabs[(i + k + tabs.length) % tabs.length], true); }
        if (ev.key === 'Home') { ev.preventDefault(); select(tabs[0], true); }
        if (ev.key === 'End') { ev.preventDefault(); select(tabs[tabs.length - 1], true); }
      });
    });
    select(tabs.find(t => t.getAttribute('aria-selected') === 'true') || tabs[0]);
  }

  if (!document.getElementById('score-form')) return;
  const rubric = window.NORDLAND_RUBRIC || [];
  const form = document.getElementById('score-form');
  const scoreOf = id => form.querySelector(`input[name="${id}"]:checked`)?.value ?? '';

  function refresh() {
    let sum = 0;
    let completed = 0;
    rubric.forEach(d => {
      const level = scoreOf(d.id);
      const chosen = level === '' ? null : Number(level);
      if (chosen !== null) { sum += chosen; completed++; }
      form.querySelectorAll(`input[name="${d.id}"]`).forEach(r => r.closest('.level').classList.toggle('is-selected', r.checked));
      const row = document.querySelector(`[data-profile="${d.id}"]`);
      if (row) {
        row.querySelector('[data-profile-score]').textContent = chosen === null ? '–' : String(chosen);
        row.querySelectorAll('.pips i').forEach((pip, k) => pip.classList.toggle('on', chosen !== null && k < chosen));
        row.querySelector('a').setAttribute('aria-label', `${d.roman}. ${d.short}: ${chosen === null ? 'not yet rated' : `${chosen} out of 4`}`);
      }
    });
    const totalEl = document.getElementById('score-total');
    totalEl.textContent = `${sum}`;
    totalEl.setAttribute('aria-label', `${sum} out of 20`);
    document.getElementById('score-complete').textContent = completed === 5
      ? 'All five dimensions rated. Total is a secondary summary.'
      : `${completed} of 5 dimensions rated · provisional total`;
    const dockTotal = document.querySelector('[data-dock-total]');
    if (dockTotal) {
      dockTotal.textContent = `${sum}`;
      document.querySelector('[data-dock-count]').textContent = `${completed} of 5 rated`;
    }
  }
  form.addEventListener('change', ev => { if (ev.target.matches('[data-score]')) refresh(); });
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
        score: scoreOf(d.id) === '' ? null : Number(scoreOf(d.id)),
        rationale: field(`${d.id}_reason`)
      })),
      total_secondary: rubric.every(d => scoreOf(d.id) !== '')
        ? rubric.reduce((sum, d) => sum + Number(scoreOf(d.id)), 0) : null,
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
