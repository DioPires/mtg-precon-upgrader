// Grimoire v1 — Codex Overview (cross-deck dashboard)
// The second desktop artboard. Compares all 12 decks at a glance.
// Distinct from the guide: this is the meta-view — pick any deck.

const { useState: useStateCO } = React;

function GV1Codex({ decks }) {
  const [sortKey, setSortKey] = useStateCO('idx');
  const [filter, setFilter] = useStateCO('all'); // all | mono | multi | bracket4

  let rows = decks.slice();
  if (filter === 'mono')      rows = rows.filter(d => (d.colors || '').length <= 1);
  if (filter === 'multi')     rows = rows.filter(d => (d.colors || '').length >= 2);
  if (filter === 'bracket4')  rows = rows.filter(d => (d.bracket || '').includes('IV'));

  const cmpNum = (k) => (a, b) => (b[k] || 0) - (a[k] || 0);
  if (sortKey === 'health') rows.sort((a,b) => (b.health?.score||0) - (a.health?.score||0));
  else if (sortKey === 'cmc') rows.sort((a,b) => (a.composition?.avgCmc||99) - (b.composition?.avgCmc||99));
  else if (sortKey === 'wincons') rows.sort((a,b) => (b.wincons?.length||0) - (a.wincons?.length||0));
  else if (sortKey === 'combos') rows.sort((a,b) => (b.combos?.length||0) - (a.combos?.length||0));
  else rows.sort((a,b) => a.idx - b.idx);

  // Aggregate stats for top strip
  const total = decks.length;
  const avgHealth = Math.round(decks.reduce((s,d)=>s+(d.health?.score||0),0) / total);
  const avgCmc = (decks.reduce((s,d)=>s+(d.composition?.avgCmc||0),0) / total).toFixed(2);
  const totalWincons = decks.reduce((s,d)=>s+(d.wincons?.length||0),0);
  const totalCombos = decks.reduce((s,d)=>s+(d.combos?.length||0),0);
  const totalCards = decks.reduce((s,d)=>s+(d.composition?.totalCards||0),0);
  const bracketCounts = decks.reduce((acc, d) => {
    const b = d.bracket || '?'; acc[b] = (acc[b]||0)+1; return acc;
  }, {});

  return (
    <div className="gv1-root" data-screen-label="02 Codex" data-gv1-screen="codex">
      <GV1Topbar screen="codex" />
      <section className="gv1-codex">
        <div className="gv1-codex-head">
          <div className="gv1-codex-eyebrow">
            <span className="gv1-rune" aria-hidden="true">◈</span>
            <span className="gv1-mono-xs">CODEX · OVERVIEW</span>
            <span className="gv1-mono-xs gv1-dim">— the entire grimoire, in one breath</span>
          </div>
          <h1 className="gv1-codex-title">The <em>Codex</em></h1>
          <p className="gv1-codex-sub">
            All {total} scribed tomes side by side. Sort, filter, and scry across the shelf.
          </p>
        </div>

        <div className="gv1-codex-stats">
          <div className="gv1-codex-stat">
            <div className="gv1-mono-xs gv1-dim">SHELVED</div>
            <div className="gv1-serif-xxl">{total}</div>
            <div className="gv1-mono-xs gv1-dim">tomes · {totalCards} cards</div>
          </div>
          <div className="gv1-codex-stat">
            <div className="gv1-mono-xs gv1-dim">AVG HEALTH</div>
            <div className="gv1-serif-xxl">{avgHealth}</div>
            <div className="gv1-mono-xs gv1-rune">across the shelf</div>
          </div>
          <div className="gv1-codex-stat">
            <div className="gv1-mono-xs gv1-dim">AVG CMC</div>
            <div className="gv1-serif-xxl">{avgCmc}</div>
            <div className="gv1-mono-xs gv1-dim">mana value mean</div>
          </div>
          <div className="gv1-codex-stat">
            <div className="gv1-mono-xs gv1-dim">WIN PATHS</div>
            <div className="gv1-serif-xxl">{totalWincons}</div>
            <div className="gv1-mono-xs gv1-dim">{totalCombos} combos charted</div>
          </div>
          <div className="gv1-codex-stat">
            <div className="gv1-mono-xs gv1-dim">BRACKETS</div>
            <div className="gv1-codex-stat-brackets">
              {Object.entries(bracketCounts).sort().map(([b,n]) => (
                <div key={b} className="gv1-codex-bracket-row">
                  <span className="gv1-mono-xs gv1-rune">{b}</span>
                  <span className="gv1-serif-md">{n}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="gv1-codex-toolbar">
          <div className="gv1-codex-toolbar-l">
            <span className="gv1-mono-xs gv1-dim">sort:</span>
            {[['idx','№'],['health','health'],['cmc','cmc'],['wincons','wins'],['combos','combos']].map(([k,l]) => (
              <button key={k} className={'gv1-mono-xs gv1-chip' + (sortKey===k ? ' gv1-chip-active' : '')} onClick={() => setSortKey(k)}>{l}</button>
            ))}
          </div>
          <div className="gv1-codex-toolbar-r">
            <span className="gv1-mono-xs gv1-dim">filter:</span>
            {[['all','all'],['mono','mono'],['multi','multicolor'],['bracket4','bracket IV']].map(([k,l]) => (
              <button key={k} className={'gv1-mono-xs gv1-chip' + (filter===k ? ' gv1-chip-active' : '')} onClick={() => setFilter(k)}>{l}</button>
            ))}
          </div>
        </div>

        <div className="gv1-codex-grid">
          {rows.map((d, i) => <GV1CodexCard key={d.slug} deck={d} rank={i+1} />)}
        </div>
      </section>
    </div>
  );
}

function GV1CodexCard({ deck, rank }) {
  const score = deck.health?.score || 0;
  const grade = deck.health?.grade || '—';
  const wincons = deck.wincons?.length || 0;
  const combos = deck.combos?.length || 0;
  const upg = deck.upg?.length || 0;
  const cmc = deck.composition?.avgCmc;
  const lands = deck.composition?.lands;
  return (
    <article className="gv1-codex-card">
      <div className="gv1-codex-card-head">
        <div className="gv1-codex-card-num">
          <span className="gv1-mono-xs gv1-dim">№ {String(deck.idx).padStart(2,'0')}</span>
          <span className="gv1-mono-xs gv1-dim">RANK {String(rank).padStart(2,'0')}</span>
        </div>
        <GV1ManaPips colors={deck.colors} />
      </div>
      <h3 className="gv1-codex-card-title">{deck.deckName}</h3>
      <div className="gv1-codex-card-cmd" data-card-name={deck.commander}>{deck.commander}</div>
      <div className="gv1-codex-card-type gv1-mono-xs gv1-dim">{deck.type}</div>

      <div className="gv1-codex-card-health">
        <div className="gv1-codex-health-meter">
          <div className="gv1-codex-health-bar" style={{width: Math.min(100,score)+'%'}}/>
          <div className="gv1-codex-health-grid">
            {[20,40,60,80].map(n => <span key={n} style={{left: n+'%'}}/>)}
          </div>
        </div>
        <div className="gv1-codex-card-health-meta">
          <span className="gv1-mono-xs gv1-dim">HEALTH</span>
          <span className="gv1-serif-md">{Math.round(score)}</span>
          <span className="gv1-mono-xs gv1-rune">· {grade}</span>
        </div>
      </div>

      <div className="gv1-codex-card-stats">
        <div><div className="gv1-mono-xs gv1-dim">BRKT</div><div className="gv1-serif-md">{deck.bracket}</div></div>
        <div><div className="gv1-mono-xs gv1-dim">CMC</div><div className="gv1-serif-md">{cmc ?? '—'}</div></div>
        <div><div className="gv1-mono-xs gv1-dim">LANDS</div><div className="gv1-serif-md">{lands ?? '—'}</div></div>
        <div><div className="gv1-mono-xs gv1-dim">$</div><div className="gv1-serif-md gv1-rune">{deck.price}</div></div>
      </div>

      <div className="gv1-codex-card-bars">
        <GV1CodexBar label="WINS" n={wincons} max={6}/>
        <GV1CodexBar label="COMBOS" n={combos} max={8}/>
        <GV1CodexBar label="SWAPS" n={upg} max={12}/>
      </div>

      <div className="gv1-codex-card-foot">
        <span className="gv1-mono-xs gv1-dim">tomus № {String(deck.idx).padStart(2,'0')}</span>
        <span className="gv1-mono-xs gv1-rune">open<span aria-hidden="true"> ◇</span></span>
      </div>
    </article>
  );
}

function GV1CodexBar({ label, n, max }) {
  const pct = Math.min(100, (n / max) * 100);
  return (
    <div className="gv1-codex-bar-row">
      <span className="gv1-mono-xs gv1-dim gv1-codex-bar-l">{label}</span>
      <div className="gv1-codex-bar-track">
        <div className="gv1-codex-bar-fill" style={{width: pct+'%'}}/>
      </div>
      <span className="gv1-mono-xs gv1-codex-bar-n">{n}</span>
    </div>
  );
}

Object.assign(window, { GV1Codex, GV1CodexCard });
