// Grimoire v1 — § XII The Combo Lab
// Lab-bench surface: control rail (mode · deck · contents · corpus · export)
// + report column (disclosure → Tier A → Tier B → near-misses → Tier C →
// completions). Fleet mode renders GV1_COMBO_DATA (real per-deck spellbook
// sync); paste mode matches any list against the fleet mini-corpus in-browser.
const { useState: useStateLab, useMemo: useMemoLab } = React;

const CL_BRACKETS = { E: 'Exhibition', C: 'Core', P: 'Powerful', O: 'Oddball', S: 'Spicy', R: 'Ruthless', B: 'Banned' };
const CL_WIN = /wins? the game|loses? the game/i;
const clPieces = c => c.cards.length + (c.templates ? c.templates.length : 0);
const clIsWin = c => c.produces.some(p => CL_WIN.test(p));
const clIsTwoCard = c => clPieces(c) === 2 && c.produces.some(p => /infinite/i.test(p));
const clBracket = t => CL_BRACKETS[t] || t || '—';
const clLoopLabel = f =>
  f.loopClass === 'infinite' ? `infinite loop (k=0)`
  : f.loopClass === 'engine' ? `per-turn value engine (k=${f.k == null ? '?' : f.k})`
  : f.closes ? 'closed loop' : 'candidate loop · not strictly closed';

// ── tiny pieces ────────────────────────────────────────────────────────────
function ClTier({ t, label }) {
  return <span className={`gv1-lab-tier gv1-lab-tier-${t}`}>{label || (t === 'a' ? 'Tier A · Curated' : t === 'b' ? 'Tier B · Computed' : 'Tier C · Heuristic')}</span>;
}
function ClArt({ name, w }) {
  const e = window.useCard(name);
  return (
    <span className="gv1-lab-art" style={w ? { width: w } : null} data-card-name={name} title={name}>
      {e && e.status === 'loaded' && e.image_small
        ? <img src={e.image_small} alt={name} loading="lazy" />
        : e && e.status === 'error'
          ? <span className="gv1-lab-art-fallback" aria-hidden="true">◇</span>
          : <span className="gv1-skeleton" style={{ position: 'absolute', inset: 0 }} />}
    </span>
  );
}
function ClChain({ items, templates }) {
  const n = items.length + (templates ? templates.length : 0);
  return (
    <p className="gv1-lab-chain">
      {items.map((c, i) => (
        <React.Fragment key={c.name + i}>
          <span data-card-name={c.name}>{c.name}</span>
          {c.cmdr && <span className="gv1-lab-cmdr"> cmdr</span>}
          {i < n - 1 && <span className="gv1-lab-chain-sep">+</span>}
        </React.Fragment>
      ))}
      {(templates || []).map((t, i) => (
        <React.Fragment key={'t' + i}>
          <span className="gv1-lab-tpl" title={t.query}>{t.name}</span>
          {items.length + i < n - 1 && <span className="gv1-lab-chain-sep">+</span>}
        </React.Fragment>
      ))}
    </p>
  );
}
function ClResults({ produces }) {
  if (!produces || !produces.length) return null;
  return (
    <div className="gv1-lab-results">
      {produces.map((p, i) => (
        <span key={i} className={'gv1-lab-result' + (/infinite/i.test(p) ? ' gv1-lab-result-inf' : '')}>{/infinite/i.test(p) ? '∞ ' : ''}{p.replace(/^Infinite /i, '').replace(/^Near-infinite /i, 'near-∞ ')}</span>
      ))}
    </div>
  );
}
function ClSecHead({ folio, title, note, pulseCls, secId }) {
  return (
    <div className={'gv1-lab-sec-head' + (pulseCls || '')} id={secId}>
      <span className="gv1-lab-sec-folio" aria-hidden="true">§ XII·{folio}</span>
      <h3 className="gv1-lab-sec-title">{title}</h3>
      {note && <span className="gv1-lab-sec-note">{note}</span>}
    </div>
  );
}
function ClFraming({ tier, children }) {
  return (
    <div className={'gv1-lab-framing' + (tier === 'b' ? ' gv1-lab-framing-b' : tier === 'c' ? ' gv1-lab-framing-c' : '')}>
      <ClTier t={tier} />
      <p>{children}</p>
    </div>
  );
}

// ── Tier A finding card ────────────────────────────────────────────────────
function ClComboCard({ c }) {
  const win = clIsWin(c), two = clIsTwoCard(c);
  const pr = c.prerequisites || { easy: '', notable: '' };
  const hasDetail = !!(c.steps || pr.easy || pr.notable || c.manaNeeded);
  return (
    <article className="gv1-lab-combo">
      <div className="gv1-lab-combo-head">
        <ClTier t="a" label="Tier A" />
        {win && <span className="gv1-lab-flag gv1-lab-flag-win">Win</span>}
        {two && <span className="gv1-lab-flag">2-card infinite</span>}
        <span className="gv1-lab-flag" style={{ border: 'none', padding: 0 }}>{clBracket(c.bracketTag)}</span>
        {c.popularity > 0 && <span className="gv1-lab-pop" title="Decks running this on Commander Spellbook">{c.popularity.toLocaleString()} decks</span>}
      </div>
      <ClChain items={c.cards.map(x => ({ name: x.name, cmdr: x.mustBeCommander }))} templates={c.templates} />
      <ClResults produces={c.produces} />
      {hasDetail && (
        <details className="gv1-lab-steps">
          <summary>Steps &amp; prerequisites</summary>
          <div className="gv1-lab-steps-body">
            {(c.manaNeeded || pr.easy || pr.notable) && (
              <div>
                <span className="gv1-lab-steps-label">Prerequisites</span>
                {c.manaNeeded && <p className="gv1-lab-prose">Mana: {c.manaNeeded}</p>}
                {pr.easy && <p className="gv1-lab-prose">{pr.easy}</p>}
                {pr.notable && <p className="gv1-lab-prose">{pr.notable}</p>}
              </div>
            )}
            {c.steps && (
              <div>
                <span className="gv1-lab-steps-label">Steps · curated by Commander Spellbook</span>
                {c.steps.split('\n').map((line, i) => (
                  <div key={i} className="gv1-lab-step"><span className="gv1-lab-step-n">{String(i + 1).padStart(2, '0')}</span><p>{line}</p></div>
                ))}
              </div>
            )}
          </div>
        </details>
      )}
      <div className="gv1-lab-combo-foot">
        <a className="gv1-lab-link" href={c.permalink} target="_blank" rel="noreferrer">Why? — Commander Spellbook ↗</a>
      </div>
    </article>
  );
}

// ── Tier B loop card ───────────────────────────────────────────────────────
const CL_LOOP_FLAG = { corroborated: 'Also curated · Tier A', novel: 'Novel — verified by the model', engine: 'Value engine / near-miss' };
function ClLoopCard({ f, kind }) {
  const leak = (f.deficit || []).filter(d => d.shortfall != null);
  return (
    <article className="gv1-lab-combo">
      <div className="gv1-lab-combo-head">
        <ClTier t={kind === 'corroborated' ? 'a' : 'b'} label={kind === 'corroborated' ? 'Tier A' : 'Tier B'} />
        <span className="gv1-lab-flag">{CL_LOOP_FLAG[kind]}</span>
        <span className="gv1-lab-pop">{clLoopLabel(f)}</span>
      </div>
      <ClChain items={f.cards.map(n => ({ name: n }))} />
      <ClResults produces={f.resultTypes.map(r => r.replace(/_/g, ' ').replace(/:/g, ' · '))} />
      {leak.length > 0 && (
        <div>
          <span className="gv1-lab-leak">Leaks {leak.map(d => `${d.shortfall} ${d.resource}/iteration`).join(', ')}</span>
          {leak[0].note && <p className="gv1-lab-leak-note">{leak[0].note}</p>}
        </div>
      )}
      <details className="gv1-lab-steps">
        <summary>Loop trace &amp; provenance</summary>
        <div className="gv1-lab-steps-body">
          {(f.prerequisites.ordering || []).length > 0 && (
            <div>
              <span className="gv1-lab-steps-label">Trace · one iteration</span>
              {f.prerequisites.ordering.map((line, i) => (
                <div key={i} className="gv1-lab-step"><span className="gv1-lab-step-n">{String(i + 1).padStart(2, '0')}</span><p>{line}</p></div>
              ))}
            </div>
          )}
          <div>
            <span className="gv1-lab-steps-label">Prerequisites</span>
            <p className="gv1-lab-prose">Minimum starting mana: {f.prerequisites.minInitialMana}{f.prerequisites.guards.length > 0 ? ` · guards: ${f.prerequisites.guards.map(g => g.replace(/_/g, ' ')).join(', ')}` : ''}</p>
            {f.prerequisites.note && <p className="gv1-lab-prose" style={{ fontStyle: 'italic', color: 'var(--gv1-ink-dim)' }}>{f.prerequisites.note}</p>}
          </div>
          {f.provenance && <p className="gv1-lab-note">ontology {f.provenance.ontologyVersion} · extractor {f.provenance.extractorVersion} · {f.provenance.gate}</p>}
        </div>
      </details>
    </article>
  );
}

// ── near-miss ledger row ───────────────────────────────────────────────────
function ClNearRow({ c }) {
  const missSet = new Set(c.missing.cards);
  const present = c.cards.filter(x => !missSet.has(x.name));
  return (
    <div className="gv1-lab-near-row">
      <span className={'gv1-lab-dist' + (c.distance > 1 ? ' gv1-lab-dist-2' : '')} title={`${c.distance} piece${c.distance > 1 ? 's' : ''} short`}>−{c.distance}</span>
      <span className="gv1-lab-needs">
        {c.missing.cards.map((n, i) => <React.Fragment key={n}>{i > 0 && ', '}<span data-card-name={n}>{n}</span></React.Fragment>)}
        {c.missing.templates.map((t, i) => <React.Fragment key={'t' + i}>{(c.missing.cards.length > 0 || i > 0) && ', '}<span className="gv1-lab-tpl" title={t.query}>a {t.name}</span></React.Fragment>)}
      </span>
      <span className="gv1-lab-near-with">
        completes {present.map((x, i) => <React.Fragment key={x.name}>{i > 0 && ' + '}<span data-card-name={x.name}>{x.name}</span></React.Fragment>)}
        <span className="gv1-lab-near-produce">→ {c.produces.slice(0, 2).join(' · ')}{c.produces.length > 2 ? ` · +${c.produces.length - 2}` : ''}</span>
      </span>
      <span className="gv1-lab-near-end">
        {c.popularity > 0 && <span className="gv1-lab-pop">{c.popularity.toLocaleString()} decks</span>}
        <a className="gv1-lab-link" href={c.permalink} target="_blank" rel="noreferrer">spellbook ↗</a>
      </span>
    </div>
  );
}

// ── Tier C synergy row ─────────────────────────────────────────────────────
function ClSynRow({ cand, shape }) {
  return (
    <div className="gv1-lab-syn">
      <div className="gv1-lab-syn-head">
        <ClTier t="c" label="Tier C" />
        <span className={'gv1-lab-flag' + (cand.band === 'strong' ? ' gv1-lab-band-strong' : '')}>{cand.band}</span>
        <span className="gv1-lab-syn-cards">
          {cand.cards.map((n, i) => <React.Fragment key={n}>{i > 0 && <span className="gv1-lab-chain-sep">+</span>}<span data-card-name={n}>{n}</span></React.Fragment>)}
        </span>
        <span className="gv1-lab-econ">{shape && <span className="gv1-lab-flag" style={{ border: 'none', padding: 0 }}>{shape}</span>}</span>
      </div>
      <ul className="gv1-lab-edges">
        {cand.edges.map((e, i) => (
          <li key={i} className="gv1-lab-edge">{e.from}<span className="gv1-arrow">⟶</span>{e.to} <span className="gv1-lab-edge-label">· {e.label}</span></li>
        ))}
      </ul>
    </div>
  );
}

// ── completion row ─────────────────────────────────────────────────────────
function ClCompRow({ comp, owned, maxPrice }) {
  const e = window.useCard(comp.name.split(' // ')[0]);
  const price = e && e.price ? parseFloat(e.price.replace(/[^0-9.]/g, '')) : null;
  if (maxPrice != null && price != null && price > maxPrice) return null;
  const s = comp.samples[0];
  return (
    <div className="gv1-lab-comp">
      <ClArt name={comp.name.split(' // ')[0]} w={58} />
      <div>
        <div className="gv1-lab-comp-name"><span data-card-name={comp.name.split(' // ')[0]}>{comp.name}</span>{owned && <span className="gv1-lab-pop gv1-lab-owned-tag" style={{ marginLeft: 10 }}>· owned</span>}</div>
        {s && <div className="gv1-lab-comp-sample">with {s.partners.join(' + ')} → {s.produce}{comp.samples.length > 1 ? ` — and ${comp.unlocks - 1} more` : ''}</div>}
      </div>
      <div className="gv1-lab-comp-end">
        <span className="gv1-lab-comp-unlocks">+{comp.unlocks}</span>
        <span className="gv1-lab-stat-sub">combo{comp.unlocks > 1 ? 's' : ''} unlocked</span>
        <span className="gv1-lab-pop">{e && e.price ? e.price : '· no price yet'}{comp.wins > 0 ? ` · ${comp.wins} win` : ''}</span>
      </div>
    </div>
  );
}

// ── the disclosure (summary band) ──────────────────────────────────────────
function ClSummary({ deckEntry, commander, included, tierBCount, counts, meta, mode, cardsAnalyzed, pulseCls, secId }) {
  const two = included.filter(clIsTwoCard).length;
  const wins = included.filter(clIsWin).length;
  const tags = useMemoLab(() => {
    const m = new Map();
    for (const c of included) m.set(c.bracketTag, (m.get(c.bracketTag) || 0) + 1);
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  }, [included]);
  return (
    <section className={'gv1-lab-summary' + (pulseCls || '')} id={secId} aria-label="Bracket and Rule-0 disclosure">
      <div className="gv1-lab-summary-head">
        <h3 className="gv1-lab-summary-deck">{deckEntry ? deckEntry.name : 'Pasted decklist'}</h3>
        {deckEntry && window.GV1ManaPips && <GV1ManaPips colors={deckEntry.colors} />}
        <span className="gv1-lab-note">{commander.join(' · ') || 'no commander declared'}</span>
        <span className="gv1-lab-summary-spacer" />
        <span className="gv1-mono-xs gv1-dim">bracket / rule-0 disclosure</span>
      </div>
      <div className="gv1-lab-stats">
        <div className="gv1-lab-stat"><span className="gv1-lab-stat-n">{included.length}</span><span className="gv1-lab-stat-sub">curated combos</span></div>
        <div className={'gv1-lab-stat' + (two > 0 ? ' gv1-lab-stat-hot' : '')}><span className="gv1-lab-stat-n">{two}</span><span className="gv1-lab-stat-sub">two-card infinites</span></div>
        <div className="gv1-lab-stat"><span className="gv1-lab-stat-n">{wins}</span><span className="gv1-lab-stat-sub">win the game</span></div>
        {mode === 'fleet'
          ? <div className="gv1-lab-stat"><span className="gv1-lab-stat-n">{tierBCount}</span><span className="gv1-lab-stat-sub">verified loops</span></div>
          : <div className="gv1-lab-stat"><span className="gv1-lab-stat-n">{cardsAnalyzed}</span><span className="gv1-lab-stat-sub">cards analyzed</span></div>}
        <div className="gv1-lab-stat"><span className="gv1-lab-stat-n">{counts.nearMissesTotal != null ? counts.nearMissesTotal.toLocaleString() : counts.nearMisses}</span><span className="gv1-lab-stat-sub">near-misses in corpus</span></div>
      </div>
      <div className="gv1-lab-summary-foot">
        <span className="gv1-lab-note">A <span className="gv1-rune">goldfish</span> is assumed — no opposing interaction. Absence is not proof: only corpus combos are detected.</span>
        <span className="gv1-lab-summary-spacer" />
        {tags.length > 0 && <span className="gv1-lab-note">spellbook tags: {tags.map(([t, n]) => `${clBracket(t)} ×${n}`).join(' · ')}</span>}
        {meta && <span className="gv1-lab-note" title={meta.corpusVersion}>corpus {String(meta.corpusVersion).slice(0, 10)}</span>}
      </div>
    </section>
  );
}

Object.assign(window, { ClArt, ClTier, ClChain, ClResults, ClSecHead, ClFraming, ClComboCard, ClLoopCard, ClNearRow, ClSynRow, ClCompRow, ClSummary, clIsWin, clIsTwoCard, clBracket, CL_BRACKETS });
