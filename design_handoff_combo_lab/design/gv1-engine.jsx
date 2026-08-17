// Grimoire v1 — Win Conditions & Engine sections
const { useState: useStateWC, useEffect: useEffectWC } = React;

// Hook: subscribe to GV1Cards entry for a name. Lazy-enqueues fetch on first use.
function useCard(name) {
  const [entry, setEntry] = useStateWC(() => (window.GV1Cards ? window.GV1Cards.get(name) : null));
  useEffectWC(() => {
    if (!name || !window.GV1Cards) return;
    const cur = window.GV1Cards.get(name);
    setEntry(cur);
    const unsub = window.GV1Cards.subscribe(name, setEntry);
    if (!cur) window.GV1Cards.enqueue(name);
    return unsub;
  }, [name]);
  return entry;
}

// Stylized mana cost rendering
function ManaCost({ mv }) {
  if (!mv || mv === 'LAND' || mv === '—') {
    return <span className="gv1-mv gv1-mv-land">{mv || '—'}</span>;
  }
  const parts = mv.match(/\{[^}]+\}/g) || [];
  return (
    <span className="gv1-mv">
      {parts.map((p, i) => {
        const sym = p.slice(1, -1);
        const isColorless = sym === 'C';
        const isNumeric = /^\d+$/.test(sym);
        return (
          <span key={i} className={'gv1-mv-pip ' + (isColorless ? 'gv1-mv-c' : isNumeric ? 'gv1-mv-n' : 'gv1-mv-g')}>
            {sym}
          </span>
        );
      })}
    </span>
  );
}

function CardTile({ card, size = 'md' }) {
  // deterministic glyph variant per card name so it looks curated, not random
  const seed = (card.n || '').split('').reduce((a,c) => a + c.charCodeAt(0), 0);
  const variant = seed % 4;
  const live = useCard(card.n);
  const hasImg = live && live.status === 'loaded' && live.image_small;
  // Prefer live mana cost if dataset shipped '—' or empty; fall back to whatever's on the card
  const mvLive = live && live.status === 'loaded' && live.mana_cost ? live.mana_cost : null;
  const mv = (card.mv && card.mv !== '—') ? card.mv : (mvLive || card.mv || '—');
  const priceLive = live && live.status === 'loaded' && live.price ? live.price : null;
  const price = (card.price && card.price !== '—') ? card.price : (priceLive || card.price || '—');
  const typeLine = card.type || (live && live.type_line) || '—';
  return (
    <div className={'gv1-card-tile gv1-card-' + size + (card.gc ? ' gv1-card-gc' : '')} data-card-name={card.n}>
      <div className="gv1-card-tile-art">
        {hasImg && (
          <img
            src={live.image_small}
            alt=""
            className="gv1-card-tile-img"
            loading="lazy"
            draggable="false"
          />
        )}
        {!hasImg && (
          <div className="gv1-card-tile-art-placeholder">
          <svg viewBox="0 0 160 120" width="100%" height="100%" preserveAspectRatio="none" aria-hidden="true">
            <defs>
              <radialGradient id={'g'+seed} cx="50%" cy="55%" r="60%">
                <stop offset="0%" stopColor="rgba(124,200,146,0.12)"/>
                <stop offset="100%" stopColor="rgba(124,200,146,0)"/>
              </radialGradient>
            </defs>
            <rect width="160" height="120" fill={'url(#g'+seed+')'}/>
            {variant === 0 && <>
              <circle cx="80" cy="60" r="30" fill="none" stroke="currentColor" strokeWidth="0.6" opacity="0.25"/>
              <circle cx="80" cy="60" r="20" fill="none" stroke="currentColor" strokeWidth="0.5" opacity="0.35"/>
              <path d="M80 30 L95 60 L80 90 L65 60 Z" fill="none" stroke="currentColor" strokeWidth="0.8" opacity="0.45"/>
              <circle cx="80" cy="60" r="2" fill="currentColor" opacity="0.6"/>
            </>}
            {variant === 1 && <>
              <circle cx="80" cy="60" r="28" fill="none" stroke="currentColor" strokeWidth="0.5" opacity="0.25"/>
              <path d="M52 60 L108 60 M80 32 L80 88" stroke="currentColor" strokeWidth="0.4" opacity="0.3"/>
              <path d="M62 42 L98 78 M98 42 L62 78" stroke="currentColor" strokeWidth="0.3" opacity="0.25"/>
              <circle cx="80" cy="60" r="3" fill="none" stroke="currentColor" strokeWidth="0.8" opacity="0.5"/>
            </>}
            {variant === 2 && <>
              <polygon points="80,28 104,50 104,78 80,100 56,78 56,50" fill="none" stroke="currentColor" strokeWidth="0.6" opacity="0.3"/>
              <polygon points="80,42 92,52 92,72 80,82 68,72 68,52" fill="none" stroke="currentColor" strokeWidth="0.5" opacity="0.4"/>
              <circle cx="80" cy="62" r="1.5" fill="currentColor" opacity="0.5"/>
            </>}
            {variant === 3 && <>
              <circle cx="80" cy="60" r="34" fill="none" stroke="currentColor" strokeWidth="0.4" opacity="0.2"/>
              <g transform="translate(80 60)">
                <path d="M-20 0 L20 0 M0 -20 L0 20" stroke="currentColor" strokeWidth="0.4" opacity="0.35"/>
                <path d="M-14 -14 L14 14 M14 -14 L-14 14" stroke="currentColor" strokeWidth="0.3" opacity="0.25"/>
                <circle r="8" fill="none" stroke="currentColor" strokeWidth="0.5" opacity="0.4"/>
              </g>
            </>}
          </svg>
        </div>
        )}
        <div className="gv1-card-tile-mv"><ManaCost mv={mv} /></div>
        {card.gc && <div className="gv1-card-tile-gc">★</div>}
      </div>
      <div className="gv1-card-tile-body">
        <div className="gv1-card-tile-name">{card.n}</div>
        <div className="gv1-mono-xs gv1-dim gv1-card-tile-type">{typeLine}</div>
        {card.note && <div className="gv1-card-tile-note">{card.note}</div>}
        <div className="gv1-card-tile-foot">
          <span className="gv1-mono-xs gv1-rune">{price}</span>
          <span className="gv1-mono-xs gv1-dim gv1-card-tile-hint">hover ◇</span>
        </div>
      </div>
    </div>
  );
}

function GV1WinCons({ wincons }) {
  if (!wincons || wincons.length === 0) {
    return (
      <section className="gv1-section gv1-wincons">
        <div className="gv1-section-head">
          <span className="gv1-rune" aria-hidden="true">§ II</span>
          <h2 className="gv1-section-title">Win Conditions</h2>
        </div>
        <div className="gv1-empty">No documented win conditions in this deck's dossier yet.</div>
      </section>
    );
  }
  return (
    <section className="gv1-section gv1-wincons">
      <div className="gv1-section-head">
        <span className="gv1-rune" aria-hidden="true">§ II</span>
        <h2 className="gv1-section-title">Win Conditions</h2>
        <span className="gv1-mono-xs gv1-dim">· {wincons.length} scried path{wincons.length===1?'':'s'} to victory</span>
      </div>
      <div className="gv1-wincons-grid">
        {wincons.map((w, i) => (
          <div key={i} className="gv1-wincon">
            <div className="gv1-wincon-head">
              <div className="gv1-mono-xs gv1-dim">WIN · {String(i+1).padStart(2,'0')}</div>
              {w.prob && (
                <div className="gv1-wincon-prob">
                  <span className="gv1-mono-xs gv1-dim">earliest</span>
                  <span className="gv1-serif-md gv1-rune">{w.prob}</span>
                </div>
              )}
            </div>
            <h3 className="gv1-wincon-title">
              <span>{w.title[0]}</span>
              <em>{w.title[1]}</em>
            </h3>
            <p className="gv1-wincon-desc">{w.desc}</p>
            <div className="gv1-wincon-cards">
              {w.cards.map((c, j) => <CardTile key={j} card={c} size="sm" />)}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function GV1Engine({ engine }) {
  const [active, setActive] = useStateWC(0);
  if (!engine || engine.length === 0) {
    return (
      <section className="gv1-section gv1-engine" aria-labelledby="gv1-engine-h">
        <div className="gv1-section-head">
          <span className="gv1-rune" aria-hidden="true">§ III</span>
          <h2 id="gv1-engine-h" className="gv1-section-title">The Engine</h2>
        </div>
        <div className="gv1-empty">No engine categories scribed.</div>
      </section>
    );
  }
  const safeActive = Math.min(active, engine.length - 1);
  const cur = engine[safeActive];
  // Keyboard: arrow keys move between tabs (WAI-ARIA tablist pattern)
  const onTabsKey = (e) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
      e.preventDefault();
      setActive((safeActive + 1) % engine.length);
    } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
      e.preventDefault();
      setActive((safeActive - 1 + engine.length) % engine.length);
    } else if (e.key === 'Home') {
      e.preventDefault(); setActive(0);
    } else if (e.key === 'End') {
      e.preventDefault(); setActive(engine.length - 1);
    }
  };
  return (
    <section className="gv1-section gv1-engine" aria-labelledby="gv1-engine-h">
      <div className="gv1-section-head">
        <span className="gv1-rune" aria-hidden="true">§ III</span>
        <h2 id="gv1-engine-h" className="gv1-section-title">The Engine</h2>
        <span className="gv1-mono-xs gv1-dim">· {engine.reduce((n,e)=>n+e.count,0)} cards across {engine.length} roles</span>
      </div>
      <div className="gv1-engine-shell">
        <aside className="gv1-engine-tabs" role="tablist" aria-label="Engine roles" onKeyDown={onTabsKey}>
          {engine.map((e, i) => (
            <button
              key={i}
              role="tab"
              id={'gv1-engine-tab-' + i}
              aria-selected={i === safeActive}
              aria-controls="gv1-engine-panel"
              tabIndex={i === safeActive ? 0 : -1}
              className={'gv1-engine-tab' + (i===safeActive?' gv1-active':'') + (e.isGameChangers?' gv1-engine-tab-gc':'')}
              onClick={() => setActive(i)}
            >
              <span className="gv1-mono-xs gv1-dim">{String(i+1).padStart(2,'0')}</span>
              <span className="gv1-serif-sm">{e.title}{e.isGameChangers && <span className="gv1-tab-star" aria-hidden="true"> ★</span>}</span>
              <span className="gv1-mono-xs gv1-rune">{e.count}</span>
            </button>
          ))}
        </aside>
        <div
          className="gv1-engine-panel"
          id="gv1-engine-panel"
          role="tabpanel"
          aria-labelledby={'gv1-engine-tab-' + safeActive}
          tabIndex={0}
        >
          <div className="gv1-engine-panel-head">
            <div>
              <div className="gv1-mono-xs gv1-dim">ROLE · {String(safeActive+1).padStart(2,'0')} / {String(engine.length).padStart(2,'0')}{cur.isGameChangers && ' · GAME CHANGERS'}</div>
              <h3 className="gv1-serif-xl">{cur.title}</h3>
            </div>
            <div className="gv1-mono-xs gv1-dim">
              {cur.count} cards · hover for full frame
            </div>
          </div>
          <div className="gv1-engine-cards">
            {cur.cards.map((c, i) => <CardTile key={i} card={c} size="md" />)}
          </div>
        </div>
      </div>
    </section>
  );
}

Object.assign(window, { GV1WinCons, GV1Engine, CardTile, ManaCost, useCard });
