// Grimoire v1 — § XII The Combo Lab: root organism (rail + report).
// Parts live in gv1-combolab-parts.jsx. Data: window.GV1_COMBO_DATA
// (real spellbook-sync per deck, trimmed — see file header there).
const { useState: useStateCL2, useMemo: useMemoCL2 } = React;

const CL_NEAR_COLLAPSE = 8;
const CL_SYN_COLLAPSE = 6;

// Paste-mode mini-corpus: every distinct curated combo the fleet sync has seen.
// Production matches against the full Spellbook matcher index instead (SCOPE).
let CL_CORPUS = null;
function clCorpus() {
  if (CL_CORPUS) return CL_CORPUS;
  const byId = new Map();
  const D = window.GV1_COMBO_DATA || {};
  for (const slug of Object.keys(D)) {
    for (const c of [...D[slug].included, ...D[slug].nearMisses]) {
      const prev = byId.get(c.id);
      if (!prev || (c.steps && !prev.steps)) byId.set(c.id, c);
    }
  }
  CL_CORPUS = [...byId.values()];
  return CL_CORPUS;
}
function clParseList(text) {
  const names = [];
  for (let line of text.split('\n')) {
    line = line.replace(/\/\/.*$/, '').trim();
    if (!line) continue;
    const m = line.match(/^(\d+)\s*[xX]?\s+(.+)$/);
    names.push((m ? m[2] : line).trim());
  }
  return names;
}
function clMatch(names) {
  const t0 = performance.now();
  const have = new Set(names.map(n => n.toLowerCase()));
  const included = [], near = [];
  for (const c of clCorpus()) {
    const missCards = c.cards.filter(x => !have.has(x.name.toLowerCase())).map(x => x.name);
    const dist = missCards.length + (c.templates ? c.templates.length : 0);
    if (dist === 0) included.push(c);
    else if (dist <= 2) near.push({ ...c, distance: dist, missing: { cards: missCards, templates: c.templates || [] } });
  }
  included.sort((a, b) => b.popularity - a.popularity);
  near.sort((a, b) => a.distance - b.distance || b.popularity - a.popularity);
  return { included, nearMisses: near.slice(0, 16), nearTotal: near.length, ms: performance.now() - t0, corpusSize: clCorpus().length };
}
// Single-card completions over a set of near-misses (same rule as the fleet build).
function clCompletions(nearMisses) {
  const agg = new Map();
  for (const c of nearMisses) {
    if (c.distance !== 1 || c.missing.cards.length !== 1 || c.missing.templates.length) continue;
    const name = c.missing.cards[0];
    const e = agg.get(name) || { name, unlocks: 0, wins: 0, topPopularity: 0, samples: [] };
    e.unlocks++;
    if (clIsWin(c)) e.wins++;
    e.topPopularity = Math.max(e.topPopularity, c.popularity || 0);
    if (e.samples.length < 3) e.samples.push({ partners: c.cards.map(x => x.name).filter(n => n !== name), produce: c.produces[0] || '' });
    agg.set(name, e);
  }
  return [...agg.values()].sort((a, b) => b.unlocks - a.unlocks || b.topPopularity - a.topPopularity).slice(0, 10);
}

// ── exports (plain + markdown) ─────────────────────────────────────────────
function clExport(md, ctx) {
  const { deckLabel, commander, meta, included, tierB, nearMisses, completions } = ctx;
  const B = s => (md ? `**${s}**` : s);
  const H = s => (md ? `\n## ${s}\n` : `\n== ${s.toUpperCase()} ==\n`);
  const two = included.filter(clIsTwoCard).length, wins = included.filter(clIsWin).length;
  const L = [];
  L.push(md ? `# The Grimoire — Combo Lab report` : 'THE GRIMOIRE — COMBO LAB REPORT');
  L.push(`Deck: ${deckLabel}${commander.length ? ` · Commander: ${commander.join(', ')}` : ''}`);
  if (meta) L.push(`Corpus: ${String(meta.corpusVersion).slice(0, 10)} (Commander Spellbook)`);
  L.push(H('Disclosure (bracket / Rule-0)'));
  L.push(`${B(included.length)} curated combos · ${B(two)} two-card infinites · ${B(wins)} win-the-game`);
  L.push(H('Combos present — Tier A · curated'));
  for (const c of included) L.push(`- ${c.cards.map(x => x.name).join(' + ')}${clIsTwoCard(c) ? ' [2-card infinite]' : ''}${clIsWin(c) ? ' [WIN]' : ''} (${clBracket(c.bracketTag)})\n    → ${c.produces.join(', ')}\n    ${c.permalink}`);
  if (!included.length) L.push('(none within corpus coverage)');
  if (tierB) {
    L.push(H('Verified loops — Tier B · computed'));
    for (const f of tierB.corroborated) L.push(`- [Tier A · corroborated] ${f.cards.join(' + ')} — verified under the model`);
    for (const f of tierB.novel) L.push(`- [Tier B · novel] ${f.cards.join(' + ')} — verified under the model`);
    for (const f of tierB.engines) L.push(`- [engine] ${f.cards.join(' + ')} — value engine / near-miss`);
    if (!tierB.corroborated.length && !tierB.novel.length && !tierB.engines.length) L.push('(no loops verified under the model)');
  }
  L.push(H('One–two cards away — Tier A near-misses'));
  for (const c of nearMisses) L.push(`- NEEDS ${c.missing.cards.join(', ')}${c.missing.templates.length ? ` + a ${c.missing.templates.map(t => t.name).join(', a ')}` : ''} → completes ${c.cards.filter(x => !c.missing.cards.includes(x.name)).map(x => x.name).join(' + ')} (${c.produces[0] || ''})`);
  if (completions && completions.length) {
    L.push(H('Complete a near-miss — one card, most combos'));
    for (const p of completions) L.push(`- ${p.name} — unlocks ${p.unlocks} combo${p.unlocks > 1 ? 's' : ''}${p.wins ? ` (${p.wins} win)` : ''}`);
  }
  L.push(md ? `\n---\nCombo data © Commander Spellbook (CC-BY-SA) · card data © Scryfall.` : '\nCombo data (c) Commander Spellbook (CC-BY-SA) · card data (c) Scryfall.');
  return L.join('\n');
}

// ── rail ───────────────────────────────────────────────────────────────────
function ClRail({ mode, setMode, decks, activeSlug, onSelect, toc, onToc, meta, exportCtx, paste }) {
  const [copied, setCopied] = useStateCL2(null);
  const D = window.GV1_COMBO_DATA || {};
  const doExport = (kind) => {
    if (!exportCtx) return;
    const md = kind.endsWith('md');
    const txt = clExport(md, exportCtx);
    if (kind.startsWith('dl')) {
      const a = document.createElement('a');
      const url = URL.createObjectURL(new Blob([txt], { type: md ? 'text/markdown' : 'text/plain' }));
      a.href = url; a.download = `combo-report-${exportCtx.deckLabel.replace(/\s+/g, '-').toLowerCase()}.${md ? 'md' : 'txt'}`;
      a.click(); URL.revokeObjectURL(url);
      return;
    }
    navigator.clipboard.writeText(txt).then(() => { setCopied(kind); setTimeout(() => setCopied(null), 1600); }).catch(() => {});
  };
  return (
    <aside className="gv1-lab-rail" aria-label="Combo Lab controls">
      <div className="gv1-lab-block gv1-lab-modes" role="group" aria-label="Analysis mode">
        <button type="button" className="gv1-lab-mode" aria-pressed={mode === 'fleet'} onClick={() => setMode('fleet')}>
          <span className="gv1-mono-xs gv1-dim gv1-lab-mode-tag">◈ mode i</span>
          <span className="gv1-lab-mode-name">Fleet deck</span>
        </button>
        <button type="button" className="gv1-lab-mode" aria-pressed={mode === 'paste'} onClick={() => setMode('paste')}>
          <span className="gv1-mono-xs gv1-dim gv1-lab-mode-tag">◈ mode ii</span>
          <span className="gv1-lab-mode-name">Paste decklist</span>
        </button>
      </div>

      {mode === 'fleet' ? (
        <div className="gv1-lab-block">
          <div className="gv1-lab-block-head"><span className="gv1-mono-xs gv1-dim">Select a tome</span><span className="gv1-mono-xs gv1-dim">combos</span></div>
          <div className="gv1-lab-decks" role="listbox" aria-label="Fleet decks">
            {decks.map(d => {
              const data = D[d.slug];
              return (
                <button key={d.slug} type="button" role="option" aria-selected={d.slug === activeSlug}
                  className={['gv1-lab-deck', d.slug === activeSlug ? 'gv1-active' : '', !data ? 'gv1-lab-deck-unscribed' : ''].filter(Boolean).join(' ')}
                  onClick={() => onSelect(d.slug)} title={data ? `${d.name} — ${d.cmd}` : `${d.name} — combos not scribed yet`}>
                  <span className="gv1-lab-deck-idx">№{String(d.idx).padStart(2, '0')}</span>
                  <span className="gv1-lab-deck-name">{d.name}</span>
                  <span className="gv1-lab-deck-meta">
                    <span className="gv1-lab-deck-n">{data ? data.counts.included : '—'}</span>
                    <GV1ManaPips colors={d.colors} />
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="gv1-lab-block">
          <div className="gv1-lab-block-head"><span className="gv1-mono-xs gv1-dim">Any decklist · stays in your browser</span></div>
          <div className="gv1-lab-form">
            <label className="gv1-lab-field">
              <span className="gv1-mono-xs gv1-dim">Commander(s) — optional</span>
              <input className="gv1-lab-input" value={paste.cmdr} placeholder="e.g. Meren of Clan Nel Toth" onChange={e => paste.setCmdr(e.target.value)} />
            </label>
            <label className="gv1-lab-field">
              <span className="gv1-mono-xs gv1-dim">Decklist — one card per line, quantities ok</span>
              <textarea className="gv1-lab-textarea" rows={11} value={paste.text} placeholder={'1 Gravecrawler\n1 Phyrexian Altar\n1 Blood Artist\n…'} onChange={e => paste.setText(e.target.value)} />
            </label>
            <div className="gv1-lab-form-foot">
              <button type="button" className="gv1-lab-analyze" disabled={!paste.text.trim()} onClick={paste.analyze}>Analyze ⟶</button>
              <button type="button" className="gv1-lab-more" onClick={paste.loadExample}>Load example</button>
            </div>
            {paste.report && <span className="gv1-lab-note">parse+match {paste.report.ms.toFixed(0)}ms · {paste.report.corpusSize} curated combos in the fleet mini-corpus</span>}
          </div>
        </div>
      )}

      <div className="gv1-lab-block">
        <div className="gv1-lab-block-head"><span className="gv1-mono-xs gv1-dim">Contents</span><span className="gv1-mono-xs gv1-dim">§ XII</span></div>
        <nav className="gv1-lab-toc" aria-label="Report contents">
          {toc.map(t => (
            <button key={t.key} type="button" className="gv1-lab-toc-row" onClick={() => onToc(t.key)}>
              <span className="gv1-lab-toc-folio">{t.folio}</span>
              <span className="gv1-lab-toc-label">{t.label}</span>
              <span className="gv1-lab-toc-n">{t.n}</span>
            </button>
          ))}
        </nav>
      </div>

      <div className="gv1-lab-block">
        <div className="gv1-lab-block-head"><span className="gv1-mono-xs gv1-dim">The three tiers</span></div>
        <dl className="gv1-lab-kv">
          <dt><ClTier t="a" label="A" /></dt><dd>curated · human-verified (Spellbook)</dd>
          <dt><ClTier t="b" label="B" /></dt><dd>computed · verified under the model</dd>
          <dt><ClTier t="c" label="C" /></dt><dd>heuristic · speculative couplings</dd>
        </dl>
      </div>

      <div className="gv1-lab-block">
        <div className="gv1-lab-block-head"><span className="gv1-mono-xs gv1-dim">Scribe the findings</span><span className="gv1-mono-xs gv1-dim">{meta ? String(meta.corpusVersion).slice(0, 10) : '—'}</span></div>
        <div className="gv1-lab-export">
          <button type="button" className="gv1-lab-export-btn" disabled={!exportCtx} onClick={() => doExport('txt')}>{copied === 'txt' ? 'Copied ◆' : 'Copy text'}</button>
          <button type="button" className="gv1-lab-export-btn" disabled={!exportCtx} onClick={() => doExport('md')}>{copied === 'md' ? 'Copied ◆' : 'Copy markdown'}</button>
          <button type="button" className="gv1-lab-export-btn" disabled={!exportCtx} onClick={() => doExport('dl-txt')}>⇣ .txt</button>
          <button type="button" className="gv1-lab-export-btn" disabled={!exportCtx} onClick={() => doExport('dl-md')}>⇣ .md</button>
        </div>
      </div>

      <p className="gv1-lab-smallprint">Combo data © Commander Spellbook (CC-BY-SA) · card data © Scryfall · not affiliated with or endorsed by Wizards of the Coast. Ownership flags read the collection imported in § IX Shopping — nothing leaves the page.</p>
    </aside>
  );
}

// ── root ───────────────────────────────────────────────────────────────────
function GV1ComboLab({ initialMode, initialSlug, initialPaste, initialCommander }) {
  const DECKS = (window.GV1_DATA && window.GV1_DATA.DECKS) || [];
  const D = window.GV1_COMBO_DATA || {};
  const [mode, setMode] = useStateCL2(initialMode || 'fleet');
  const [slug, setSlug] = useStateCL2(initialSlug || 'titan-convergence');
  const [pasteText, setPasteText] = useStateCL2(initialPaste || '');
  const [pasteCmdr, setPasteCmdr] = useStateCL2(initialCommander || '');
  const [pasteReport, setPasteReport] = useStateCL2(() => (initialPaste ? clMatch([...clParseList(initialPaste), ...clParseList(initialCommander || '')]) : null));
  const [showAllNear, setShowAllNear] = useStateCL2(false);
  const [showAllSyn, setShowAllSyn] = useStateCL2(false);
  const [showDeep, setShowDeep] = useStateCL2(false);
  const [maxPriceStr, setMaxPriceStr] = useStateCL2('');
  const [ownedOnly, setOwnedOnly] = useStateCL2(false);
  const [pulse, setPulse] = useStateCL2(null);

  const owned = useMemoCL2(() => {
    try { const raw = localStorage.getItem('grimoire-owned-cards'); if (raw) return new Set(JSON.parse(raw).map(([n]) => String(n).toLowerCase())); } catch (e) {}
    return new Set();
  }, []);

  const deckEntry = DECKS.find(d => d.slug === slug) || null;
  const data = mode === 'fleet' ? D[slug] : null;
  const analyze = () => setPasteReport(clMatch([...clParseList(pasteText), ...clParseList(pasteCmdr)]));
  const loadExample = () => {
    const t = ['1 Gravecrawler', '1 Phyrexian Altar', '1 Blood Artist', '1 Warren Soultrader', '1 Basalt Monolith', '1 Forsaken Monument', '1 Rings of Brighthearth', "1 Ashnod's Altar", '1 Nim Deathmantle', '1 Sol Ring', '1 Command Tower'].join('\n');
    setPasteText(t); setPasteCmdr('Meren of Clan Nel Toth');
    setPasteReport(clMatch([...clParseList(t), 'Meren of Clan Nel Toth']));
  };

  // Assemble the mode-independent report shape the sections render from.
  const included = mode === 'fleet' ? (data ? data.included : []) : (pasteReport ? pasteReport.included : []);
  const nearAll = mode === 'fleet' ? (data ? data.nearMisses : []) : (pasteReport ? pasteReport.nearMisses : []);
  const tierB = mode === 'fleet' && data ? data.tierB : null;
  const synergy = mode === 'fleet' && data ? data.synergy : null;
  const completions = useMemoCL2(() => (mode === 'fleet' ? (data ? data.completions : []) : (pasteReport ? clCompletions(pasteReport.nearMisses) : [])), [mode, data, pasteReport]);
  const commander = mode === 'fleet' ? (data ? data.commander : deckEntry ? [deckEntry.cmd] : []) : clParseList(pasteCmdr);
  const meta = data ? data.meta : null;
  const tierBCount = tierB ? tierB.corroborated.length + tierB.novel.length + tierB.engines.length : 0;
  const hasReport = mode === 'fleet' ? !!data : !!pasteReport;
  const maxPrice = maxPriceStr.trim() && isFinite(Number(maxPriceStr)) && Number(maxPriceStr) > 0 ? Number(maxPriceStr) : null;
  const compShown = ownedOnly ? completions.filter(c => owned.has(c.name.toLowerCase())) : completions;
  const nearShown = showAllNear ? nearAll : nearAll.slice(0, CL_NEAR_COLLAPSE);
  const deepCount = synergy ? synergy.triples.length + synergy.cycles.length : 0;

  const toc = [
    { key: 'disc', folio: '◈', label: 'The Disclosure', n: '' },
    { key: 'a', folio: 'XII·a', label: 'Combos Present', n: hasReport ? included.length : '—' },
    { key: 'b', folio: 'XII·b', label: 'Verified Loops', n: mode === 'fleet' ? (data ? tierBCount : '—') : '·' },
    { key: 'c', folio: 'XII·c', label: 'One–Two Cards Away', n: hasReport ? nearAll.length : '—' },
    { key: 'd', folio: 'XII·d', label: 'Synergy Candidates', n: synergy ? synergy.counts.pairs : mode === 'paste' ? '·' : '—' },
    { key: 'e', folio: 'XII·e', label: 'Complete a Near-Miss', n: hasReport ? compShown.length : '—' },
  ];
  const pulseCls = k => (pulse === k ? ' gv1-lab-pulsing' : '');
  const exportCtx = hasReport ? { deckLabel: mode === 'fleet' ? (deckEntry ? deckEntry.name : slug) : 'Pasted decklist', commander, meta, included, tierB, nearMisses: nearAll, completions: compShown } : null;

  return (
    <div className="gv1-root" data-gv1-screen="combolab" data-screen-label={mode === 'paste' ? '10 Combo Lab · Paste' : '09 Combo Lab'}>
      <GV1Topbar screen="combolab" />
      <header className="gv1-lab-hero">
        <div>
          <div className="gv1-lab-hero-eyebrow">
            <span className="gv1-rune" aria-hidden="true">§ XII</span>
            <span className="gv1-mono-xs gv1-dim">· curated combo detection · commander spellbook · three tiers of certainty</span>
          </div>
          <h2 className="gv1-lab-title">The <em>Combo Lab</em></h2>
        </div>
        <p className="gv1-lab-lede">Every chain the corpus knows about — what's <strong>present</strong>, what's <strong>one card away</strong>, and what would close it. Curated findings are cited; computed findings say which model verified them; heuristics never wear a verified badge.</p>
      </header>

      <div className="gv1-lab-layout">
        <ClRail mode={mode} setMode={setMode} decks={DECKS} activeSlug={slug} onSelect={setSlug}
          toc={toc} onToc={setPulse} meta={meta} exportCtx={exportCtx}
          paste={{ text: pasteText, setText: setPasteText, cmdr: pasteCmdr, setCmdr: setPasteCmdr, analyze, loadExample, report: pasteReport }} />

        {!hasReport ? (
          <div className="gv1-lab-report">
            {mode === 'fleet' ? (
              <div className="gv1-empty gv1-lab-unscribed">
                <span className="gv1-empty-title">Nothing scribed for this tome yet</span>
                <span>No <code>spellbook-combos.json</code> has been committed for {deckEntry ? deckEntry.name : 'this deck'}.</span>
                <span className="gv1-empty-hint">re-run scripts/sync_spellbook_combos.py</span>
              </div>
            ) : (
              <div className="gv1-empty gv1-lab-unscribed">
                <span className="gv1-empty-title">Paste a decklist to consult the corpus</span>
                <span>One card per line, quantities welcome. The match runs entirely in your browser.</span>
                <span className="gv1-empty-hint">or press “load example” for a classic combo pile</span>
              </div>
            )}
          </div>
        ) : (
          <div className="gv1-lab-report">
            <div className={pulseCls('disc').trim()} onAnimationEnd={() => setPulse(null)} style={{ display: 'contents' }}>
              <ClSummary deckEntry={mode === 'fleet' ? deckEntry : null} commander={commander} included={included}
                tierBCount={tierBCount} counts={mode === 'fleet' ? data.counts : { nearMisses: nearAll.length, nearMissesTotal: pasteReport.nearTotal }}
                meta={meta} mode={mode} cardsAnalyzed={mode === 'paste' ? clParseList(pasteText).length + commander.length : 0}
                pulseCls={pulseCls('disc')} secId="gv1-lab-sec-disc" />
            </div>

            <section className="gv1-lab-sec" aria-label="Combos present" onAnimationEnd={() => setPulse(null)}>
              <ClSecHead folio="a" title="Combos Present" note={`${included.length} chains scribed`} pulseCls={pulseCls('a')} secId="gv1-lab-sec-a" />
              <ClFraming tier="a">Every finding below is <strong>human-verified</strong> by Commander Spellbook and cited back to it. Not exhaustive — only combos in the curated corpus are detected.</ClFraming>
              {included.length === 0
                ? <div className="gv1-empty"><span className="gv1-empty-title">No curated combos found</span><span>at any tier, within corpus coverage — the corpus is not exhaustive.</span></div>
                : <div className="gv1-lab-grid2">{included.map(c => <ClComboCard key={c.id} c={c} />)}</div>}
            </section>

            <section className="gv1-lab-sec" aria-label="Verified loops" onAnimationEnd={() => setPulse(null)}>
              <ClSecHead folio="b" title="Verified Loops" note={mode === 'fleet' ? `${tierBCount} under the model` : 'production only'} pulseCls={pulseCls('b')} secId="gv1-lab-sec-b" />
              <ClFraming tier="b">Machine-verified against Laço's loop-closure model — <strong>verified under the model</strong>, never a comprehensive-rules ruling. Deterministic; consumes only human-reviewed or deterministic knowledge (provenance gate).</ClFraming>
              {mode === 'paste'
                ? <div className="gv1-empty"><span>The Tier-B verifier runs client-side in production; this prototype ships fleet results only.</span><span className="gv1-empty-hint">see SCOPE.md — paste-mode tier b/c</span></div>
                : tierBCount === 0
                  ? <div className="gv1-empty"><span>No loops verified under the model — not an exhaustiveness claim; only the modelled loop shapes over covered cards are checked.</span></div>
                  : <div className="gv1-lab-grid2">
                      {tierB.corroborated.map((f, i) => <ClLoopCard key={'c' + i} f={f} kind="corroborated" />)}
                      {tierB.novel.map((f, i) => <ClLoopCard key={'n' + i} f={f} kind="novel" />)}
                      {tierB.engines.map((f, i) => <ClLoopCard key={'e' + i} f={f} kind="engine" />)}
                    </div>}
              {mode === 'fleet' && tierB.capped.length > 0 && (
                <p className="gv1-lab-warn">{tierB.capped.length} candidate loop{tierB.capped.length > 1 ? 's' : ''} held at Tier C — a loop-relevant knowledge-base entry is not yet human-reviewed (provenance gate).</p>
              )}
            </section>

            <section className="gv1-lab-sec" aria-label="Near-misses" onAnimationEnd={() => setPulse(null)}>
              <ClSecHead folio="c" title="One–Two Cards Away" note={mode === 'fleet' ? `top ${nearAll.length} of ${data.counts.nearMisses} stored · ${data.counts.nearMissesTotal.toLocaleString()} qualifying` : `${nearAll.length} shown of ${pasteReport.nearTotal}`} pulseCls={pulseCls('c')} secId="gv1-lab-sec-c" />
              <p className="gv1-lab-note">Still Tier A — curated combos the list is short a piece for. The <span style={{ color: 'var(--gv1-gold-300)' }}>gold name</span> is the piece that's missing.</p>
              {nearAll.length === 0
                ? <div className="gv1-empty"><span>No qualifying near-misses.</span></div>
                : <React.Fragment>
                    <div className="gv1-lab-near">{nearShown.map(c => <ClNearRow key={c.id} c={c} />)}</div>
                    {nearAll.length > CL_NEAR_COLLAPSE && (
                      <button type="button" className="gv1-lab-more" onClick={() => setShowAllNear(v => !v)}>{showAllNear ? 'Show fewer' : `Show all ${nearAll.length}`}</button>
                    )}
                  </React.Fragment>}
            </section>

            <section className="gv1-lab-sec" aria-label="Tier-C synergies" onAnimationEnd={() => setPulse(null)}>
              <ClSecHead folio="d" title="Synergy Candidates" note={synergy ? `${synergy.counts.pairs} pairs ranked · crowd prior ${synergy.crowdPriorApplied ? 'applied' : 'off'}` : 'production only'} pulseCls={pulseCls('d')} secId="gv1-lab-sec-d" />
              <ClFraming tier="c">Speculative signals from a provides / wants coupling graph — <strong>not verified combos</strong>. Every candidate is justified by its matched couplings below; bands stay coarse by design, never a numeric score.</ClFraming>
              {!synergy
                ? <div className="gv1-empty"><span>The Tier-C knowledge base (3.3 MB) is not shipped with this prototype; paste-mode synergies run in production.</span><span className="gv1-empty-hint">see SCOPE.md — paste-mode tier b/c</span></div>
                : <React.Fragment>
                    <div className="gv1-lab-syn-list">{(showAllSyn ? synergy.pairs : synergy.pairs.slice(0, CL_SYN_COLLAPSE)).map((c, i) => <ClSynRow key={i} cand={c} shape="2-card" />)}</div>
                    <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                      {synergy.pairs.length > CL_SYN_COLLAPSE && (
                        <button type="button" className="gv1-lab-more" onClick={() => setShowAllSyn(v => !v)}>{showAllSyn ? 'Show fewer' : `Show all ${synergy.pairs.length} pairs`}</button>
                      )}
                      <button type="button" className="gv1-lab-more" onClick={() => setShowDeep(v => !v)}>{showDeep ? 'Hide triples & 4-cycles' : `Deep couplings — triples & 4-cycles (${deepCount})`}</button>
                    </div>
                    {showDeep && (
                      <div className="gv1-lab-syn-groups">
                        <div>
                          <h4 className="gv1-lab-h3">Triples <span className="gv1-dim">({synergy.triples.length} of {synergy.counts.triples})</span></h4>
                          <div className="gv1-lab-syn-list">{synergy.triples.map((c, i) => <ClSynRow key={i} cand={c} shape="3-card" />)}</div>
                        </div>
                        <div>
                          <h4 className="gv1-lab-h3">4-cycles <span className="gv1-dim">({synergy.cycles.length} of {synergy.counts.cycles})</span></h4>
                          <div className="gv1-lab-syn-list">{synergy.cycles.map((c, i) => <ClSynRow key={i} cand={c} shape="4-cycle" />)}</div>
                        </div>
                      </div>
                    )}
                  </React.Fragment>}
            </section>

            <section className="gv1-lab-sec" aria-label="Complete a near-miss" onAnimationEnd={() => setPulse(null)}>
              <ClSecHead folio="e" title="Complete a Near-Miss" note="one card · most combos unlocked" pulseCls={pulseCls('e')} secId="gv1-lab-sec-e" />
              <ClFraming tier="b">The mechanistic recommendation engine — pool cards that would <strong>close</strong> the near-misses above. A report only: it never edits your deck. Confirm each interaction yourself.</ClFraming>
              <div className="gv1-lab-filters">
                <label className="gv1-lab-field" style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                  <span className="gv1-mono-xs gv1-dim">Max price $</span>
                  <input className="gv1-lab-input" type="number" min="0" step="0.5" placeholder="any" value={maxPriceStr} onChange={e => setMaxPriceStr(e.target.value)} />
                </label>
                <button type="button" className={'gv1-lab-filter-chip' + (ownedOnly ? ' gv1-active' : '')} aria-pressed={ownedOnly}
                  disabled={owned.size === 0} title={owned.size === 0 ? 'Import your collection in § IX Shopping first' : `${owned.size} owned cards on file`}
                  onClick={() => setOwnedOnly(v => !v)}>Owned only</button>
                <span className="gv1-lab-note">{owned.size > 0 ? `${owned.size} owned cards on file — imported in § IX Shopping` : <React.Fragment>no collection on file — <a href="#" onClick={e => { e.preventDefault(); window.gv1NavTo && window.gv1NavTo('shopping'); }}>import in § IX Shopping</a></React.Fragment>}</span>
              </div>
              {compShown.length === 0
                ? <div className="gv1-empty"><span>No single-card completions under the current filters.</span></div>
                : <div className="gv1-lab-comp-list">{compShown.map(c => <ClCompRow key={c.name} comp={c} owned={owned.has(c.name.toLowerCase())} maxPrice={maxPrice} />)}</div>}
              <p className="gv1-lab-note">Prices are live Scryfall (USD). Production adds Cardmarket EUR, a legality gate, and color-identity filtering — see SCOPE.md.</p>
            </section>

            <footer className="gv1-lab-attrib">Combo data © <a href="https://commanderspellbook.com" target="_blank" rel="noreferrer">Commander Spellbook</a> (CC-BY-SA) · card data &amp; imagery © Scryfall · The Grimoire is not affiliated with or endorsed by Wizards of the Coast.</footer>
          </div>
        )}
      </div>
    </div>
  );
}

Object.assign(window, { GV1ComboLab });
