// Grimoire v1 — Chrome: top bar, hero, deck gallery, sticky nav
const { useState, useEffect, useRef } = React;

// Top-nav targets — every artboard's root carries `data-gv1-screen="<id>"`
// and lives inside a `[data-dc-slot="<slotId>"]` from DesignCanvas. Clicking
// a nav item focuses the corresponding artboard via the canvas's own
// .dc-expand button (same affordance as the artboard label's focus icon).
// This keeps the canvas's internal pan/zoom state untouched.
//
// NOTE: there is no 'Mobile' nav entry — mobile is the same Guide rendered
// for a phone viewport, not a separate destination. The mobile artboard in
// the canvas is a design-review preview; in the shipped app, viewport width
// would decide whether to mount the desktop or mobile guide.
const GV1_NAV_ITEMS = [
  { id: 'guide',    slot: 'guide',    label: 'Guide',    rune: 'I',    section: 'grimoire' },
  { id: 'codex',    slot: 'perf',     label: 'Codex',    rune: 'II',   section: 'grimoire' },
  { id: 'scrying',  slot: 'scrying',  label: 'Scrying',  rune: 'VIII', section: 'stubs', stub: true },
  { id: 'shopping', slot: 'shopping', label: 'Shopping', rune: 'IX',   section: 'real' },
  { id: 'compare',  slot: 'compare',  label: 'Compare',  rune: 'X',    section: 'real' },
  { id: 'combolab', slot: 'combolab', label: 'Combos',   rune: 'XII',  section: 'real' },
];

// Public nav helper — invoked by topbar nav buttons. Finds the artboard
// in the canvas DOM and clicks its focus button. Falls back to a vertical
// scroll if focus mode is unavailable.
window.gv1NavTo = function gv1NavTo(slotId) {
  const slot = document.querySelector(`[data-dc-slot="${slotId}"]`);
  if (!slot) return;
  const expand = slot.querySelector('.dc-expand');
  if (expand) { expand.click(); return; }
  slot.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
};

function GV1Topbar({ screen }) {
  return (
    <header className="gv1-topbar" role="banner">
      <div className="gv1-topbar-left">
        <span className="gv1-sigil-sm" aria-hidden="true">◈</span>
        <span className="gv1-mono-xs">grimoire@commander:~$</span>
        <span className="gv1-mono-xs gv1-dim">// {(window.GV1_DATA?.DECK_FULL?.length || 0)} decks indexed</span>
      </div>
      <nav className="gv1-topbar-nav" role="navigation" aria-label="Surfaces">
        {GV1_NAV_ITEMS.map((item) => {
          const active = item.id === screen;
          const cls = [
            'gv1-nav-item',
            active ? 'gv1-active' : '',
            item.stub ? 'gv1-nav-stub' : '',
          ].filter(Boolean).join(' ');
          return (
            <button
              key={item.id}
              type="button"
              className={cls}
              onClick={() => window.gv1NavTo(item.slot)}
              aria-current={active ? 'page' : undefined}
              title={item.stub ? `${item.label} — stub (no interactions)` : item.label}
            >
              <span className="gv1-mono-xs gv1-dim gv1-nav-rune" aria-hidden="true">§{item.rune}</span>
              <span className="gv1-mono-xs gv1-nav-label">{item.label}</span>
              {item.stub && <span className="gv1-mono-xs gv1-nav-stubmark" aria-hidden="true">⚠</span>}
            </button>
          );
        })}
      </nav>
      <div className="gv1-topbar-right">
        <span className="gv1-mono-xs gv1-dim" aria-hidden="true">⌘K</span>
        <span className="gv1-mono-xs">search</span>
        <span className="gv1-mono-xs gv1-dim gv1-sep" aria-hidden="true">│</span>
        <span className="gv1-mono-xs gv1-rune"><span aria-hidden="true">▲ </span>sync · 04/22</span>
      </div>
    </header>
  );
}

function GV1Hero() {
  const deckCount = (window.GV1_DATA && window.GV1_DATA.DECKS && window.GV1_DATA.DECKS.length) || 12;
  const scribedCount = (window.GV1_DATA && window.GV1_DATA.DECKS && window.GV1_DATA.DECKS.filter(d => d.hasDetail).length) || deckCount;
  // english number for body copy (1–20)
  const numWords = ['zero','one','two','three','four','five','six','seven','eight','nine','ten','eleven','twelve','thirteen','fourteen','fifteen','sixteen','seventeen','eighteen','nineteen','twenty'];
  const word = numWords[deckCount] || String(deckCount);
  return (
    <header className="gv1-hero">
      <div className="gv1-hero-grid-overlay" />
      <div className="gv1-hero-inner">
        <div className="gv1-hero-sigil">
          <svg viewBox="0 0 120 120" width="120" height="120" aria-hidden="true">
            <circle cx="60" cy="60" r="56" fill="none" stroke="currentColor" strokeWidth="0.8" opacity="0.4"/>
            <circle cx="60" cy="60" r="44" fill="none" stroke="currentColor" strokeWidth="0.6" opacity="0.3"/>
            <circle cx="60" cy="60" r="30" fill="none" stroke="currentColor" strokeWidth="0.6" opacity="0.5"/>
            <path d="M60 8 L60 112 M8 60 L112 60" stroke="currentColor" strokeWidth="0.5" opacity="0.3"/>
            <path d="M60 20 L78 60 L60 100 L42 60 Z" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.7"/>
            <circle cx="60" cy="60" r="4" fill="currentColor" opacity="0.9"/>
            <text x="60" y="14" textAnchor="middle" fontSize="5" fill="currentColor" fontFamily="JetBrains Mono, monospace" opacity="0.6">N</text>
            <text x="60" y="113" textAnchor="middle" fontSize="5" fill="currentColor" fontFamily="JetBrains Mono, monospace" opacity="0.6">S</text>
            <text x="9" y="62" textAnchor="middle" fontSize="5" fill="currentColor" fontFamily="JetBrains Mono, monospace" opacity="0.6">W</text>
            <text x="112" y="62" textAnchor="middle" fontSize="5" fill="currentColor" fontFamily="JetBrains Mono, monospace" opacity="0.6">E</text>
          </svg>
        </div>
        <div className="gv1-eyebrow">
          <span className="gv1-rune">◆</span>
          <span className="gv1-mono-xs">TOMOS · IX</span>
          <span className="gv1-dim gv1-mono-xs">· curated from EDHREC · Commander Spellbook · MTGGoldfish</span>
        </div>
        <h1 className="gv1-hero-title">
          The <em>Grimoire</em>
        </h1>
        <p className="gv1-hero-sub">
          A compendium of {word} commander decks, scried, simulated, and shelved.
          Each tome documents engine, win conditions, and the path from $0 to optimal.
        </p>
        <div className="gv1-hero-meta">
          <div className="gv1-hero-meta-item">
            <div className="gv1-mono-xs gv1-dim">CODEX</div>
            <div className="gv1-serif-lg">{deckCount} <span className="gv1-dim">decks · {scribedCount} scribed</span></div>
          </div>
          <div className="gv1-hero-meta-item">
            <div className="gv1-mono-xs gv1-dim">BRACKET</div>
            <div className="gv1-serif-lg">III–IV</div>
          </div>
          <div className="gv1-hero-meta-item">
            <div className="gv1-mono-xs gv1-dim">UPDATED</div>
            <div className="gv1-serif-lg">22 · IV · 26</div>
          </div>
          <div className="gv1-hero-meta-item">
            <div className="gv1-mono-xs gv1-dim">ENGINE</div>
            <div className="gv1-serif-lg gv1-rune">scrying.v2</div>
          </div>
        </div>
      </div>
    </header>
  );
}

// Mana color → pip config
const GV1_COLOR_MAP = {
  '⚪': { fill: '#f5efd8', stroke: '#d4cea8', letter: 'W' },
  '🔵': { fill: '#a8c8e8', stroke: '#6a98c0', letter: 'U' },
  '⚫': { fill: '#3a3028', stroke: '#1a1410', letter: 'B' },
  '🔴': { fill: '#e8a898', stroke: '#c06848', letter: 'R' },
  '🟢': { fill: '#98c8a8', stroke: '#487a58', letter: 'G' },
  '◇': { fill: '#b8b0a0', stroke: '#807868', letter: 'C' },
};
function GV1ManaPips({ colors }) {
  const chars = Array.from(colors || '');
  return (
    <span className="gv1-pips" role="img" aria-label={`Color identity: ${chars.length} colors`}>
      {chars.map((c, i) => {
        const cfg = GV1_COLOR_MAP[c] || GV1_COLOR_MAP['◇'];
        return (
          <span key={i} className="gv1-pip" aria-hidden="true" style={{background: cfg.fill, borderColor: cfg.stroke, color: cfg.letter === 'B' ? '#d8d0c0' : '#1a1410'}}>
            {cfg.letter}
          </span>
        );
      })}
    </span>
  );
}

function GV1DeckSelector({ decks, activeIdx, onSelect }) {
  const trackRef = useRef(null);
  // Scroll active pill into view on change
  useEffect(() => {
    const el = trackRef.current?.querySelector('.gv1-active');
    if (el && el.scrollIntoView) {
      el.scrollIntoView({behavior: 'smooth', block: 'nearest', inline: 'center'});
    }
  }, [activeIdx]);
  // Keyboard nav: ←/→ moves through scribed decks (skips stubs)
  const onKey = (e) => {
    if (!['ArrowLeft','ArrowRight','Home','End'].includes(e.key)) return;
    e.preventDefault();
    const scribed = decks.filter(d => d.hasDetail);
    if (!scribed.length) return;
    const curIx = scribed.findIndex(d => d.idx === activeIdx);
    let nextIx;
    if (e.key === 'ArrowRight') nextIx = (curIx + 1 + scribed.length) % scribed.length;
    else if (e.key === 'ArrowLeft') nextIx = (curIx - 1 + scribed.length) % scribed.length;
    else if (e.key === 'Home') nextIx = 0;
    else nextIx = scribed.length - 1;
    onSelect && onSelect(scribed[nextIx].idx);
  };
  return (
    <nav className="gv1-selector" aria-label="Deck selector" role="tablist">
      <div className="gv1-selector-head">
        <div className="gv1-selector-head-l">
          <span className="gv1-mono-xs gv1-rune"><span aria-hidden="true">◈ </span>TOMOS</span>
          <span className="gv1-mono-xs gv1-dim">— {decks.length} indexed · {decks.filter(d=>d.hasDetail).length} scribed</span>
        </div>
        <div className="gv1-selector-head-r">
          <span className="gv1-mono-xs gv1-dim">filter:</span>
          <span className="gv1-mono-xs gv1-chip gv1-chip-active">all</span>
          <span className="gv1-mono-xs gv1-chip">mono</span>
          <span className="gv1-mono-xs gv1-chip">multicolor</span>
          <span className="gv1-mono-xs gv1-chip">bracket IV</span>
        </div>
      </div>
      <div className="gv1-selector-track" ref={trackRef} onKeyDown={onKey}>
        {decks.map((d, i) => {
          const active = d.idx === activeIdx;
          const stub = !d.hasDetail;
          return (
            <button
              key={d.slug}
              role="tab"
              aria-selected={active}
              aria-disabled={stub}
              tabIndex={active ? 0 : -1}
              className={'gv1-sel-pill' + (active ? ' gv1-active' : '') + (stub ? ' gv1-stub' : '')}
              onClick={() => !stub && onSelect && onSelect(d.idx)}
              title={stub ? 'Not yet scribed — coming soon' : `Open ${d.name}`}
              type="button"
            >
              <div className="gv1-sel-pill-top">
                <span className="gv1-mono-xs gv1-dim">№ {String(d.idx).padStart(2,'0')}</span>
                <GV1ManaPips colors={d.colors} />
              </div>
              <div className="gv1-sel-pill-name">{d.name}</div>
              <div className="gv1-mono-xs gv1-sel-pill-cmd">{d.cmd}</div>
              <div className="gv1-sel-pill-foot">
                <span className="gv1-mono-xs gv1-sel-pill-bracket">BRACKET {d.bracket}</span>
                <span className="gv1-mono-xs gv1-dim">{d.price}</span>
              </div>
              {active && <span className="gv1-sel-pill-flag"><span className="gv1-mono-xs">NOW SCRYING</span></span>}
              {stub && <span className="gv1-sel-pill-stub"><span className="gv1-mono-xs"><span aria-hidden="true">⬡ </span>unscribed</span></span>}
            </button>
          );
        })}
      </div>
    </nav>
  );
}

// Commander art with Scryfall fallback
function GV1CommanderArt({ name, slug }) {
  const [status, setStatus] = useState('loading'); // loading | loaded | error
  const src = `https://api.scryfall.com/cards/named?fuzzy=${encodeURIComponent(name)}&format=image&version=art_crop`;
  // Reset status when switching decks
  useEffect(() => { setStatus('loading'); }, [slug]);
  return (
    <div className="gv1-cmd-art">
      <div className="gv1-cmd-art-inner">
        {status !== 'error' && (
          <img
            key={slug}
            src={src}
            alt={name}
            className={'gv1-cmd-art-img' + (status === 'loaded' ? ' gv1-loaded' : '')}
            onLoad={() => setStatus('loaded')}
            onError={() => setStatus('error')}
            draggable="false"
          />
        )}
        {status !== 'loaded' && (
          <div className="gv1-cmd-art-fallback">
            <svg viewBox="0 0 300 420" width="100%" height="100%" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
              <defs>
                <radialGradient id={'cmd-glow-' + slug} cx="50%" cy="40%" r="70%">
                  <stop offset="0%" stopColor="rgba(124,200,146,0.18)"/>
                  <stop offset="60%" stopColor="rgba(124,200,146,0.04)"/>
                  <stop offset="100%" stopColor="rgba(124,200,146,0)"/>
                </radialGradient>
              </defs>
              <rect width="300" height="420" fill={`url(#cmd-glow-${slug})`}/>
              <g transform="translate(150 180)" stroke="currentColor" fill="none">
                <circle r="120" strokeWidth="0.6" opacity="0.2"/>
                <circle r="90" strokeWidth="0.5" opacity="0.3"/>
                <circle r="60" strokeWidth="0.6" opacity="0.5"/>
                <circle r="30" strokeWidth="0.5" opacity="0.4"/>
                <path d="M0 -100 L60 0 L0 100 L-60 0 Z" strokeWidth="1"/>
                <path d="M-85 -85 L85 85 M85 -85 L-85 85" strokeWidth="0.3" opacity="0.3"/>
                <circle r="3" fill="currentColor" opacity="0.8"/>
              </g>
              <text x="150" y="395" textAnchor="middle" fontSize="8" fill="currentColor" fontFamily="JetBrains Mono, monospace" opacity="0.5" letterSpacing="2">
                {status === 'loading' ? '◆ SCRYING SCRYFALL ◆' : '◇ FRAME UNAVAILABLE ◇'}
              </text>
            </svg>
          </div>
        )}
      </div>
      <div className="gv1-cmd-art-corners">
        <span></span><span></span><span></span><span></span>
      </div>
      <div className="gv1-cmd-art-caption">
        <span className="gv1-mono-xs gv1-dim">◇ scryfall.com · art_crop</span>
      </div>
    </div>
  );
}

function GV1Commander({ deck }) {
  return (
    <section className="gv1-commander">
      <div className="gv1-cmd-grid">
        <GV1CommanderArt name={deck.commander} slug={deck.slug} />

        <div className="gv1-cmd-body">
          <div className="gv1-cmd-eyebrow">
            <span className="gv1-mono-xs gv1-rune">◆ TOMUS №{String(deck.idx).padStart(2,'0')}</span>
            <span className="gv1-mono-xs gv1-dim">· NOW SCRYING ·</span>
            <span className="gv1-mono-xs gv1-dim">BRACKET {deck.bracket}</span>
          </div>

          <h1 className="gv1-cmd-deckname">{deck.deckName}</h1>

          <div className="gv1-cmd-commander-row">
            <GV1ManaPips colors={deck.colors} />
            <span className="gv1-cmd-commander-name" data-card-name={deck.commander}>{deck.commander}</span>
            <span className="gv1-mono-xs gv1-dim">· {deck.type}</span>
          </div>

          <p className="gv1-cmd-flavor">{deck.flavor}</p>

          <div className="gv1-cmd-oracle">
            <div className="gv1-mono-xs gv1-dim gv1-cmd-label">DOSSIER</div>
            <div className="gv1-cmd-oracle-body">
              {deck.oracle.map((line, i) => <p key={i}>{line}</p>)}
            </div>
          </div>

          <div className="gv1-cmd-stats">
            <div className="gv1-cmd-stat">
              <div className="gv1-mono-xs gv1-dim">BRACKET</div>
              <div className="gv1-serif-lg">{deck.bracket}</div>
            </div>
            <div className="gv1-cmd-stat">
              <div className="gv1-mono-xs gv1-dim">BUDGET</div>
              <div className="gv1-serif-lg gv1-rune">{deck.price}</div>
            </div>
            {deck.composition && (
              <div className="gv1-cmd-stat">
                <div className="gv1-mono-xs gv1-dim">AVG CMC</div>
                <div className="gv1-serif-lg">{deck.composition.avgCmc}</div>
              </div>
            )}
            {deck.composition && (
              <div className="gv1-cmd-stat">
                <div className="gv1-mono-xs gv1-dim">LANDS</div>
                <div className="gv1-serif-lg">{deck.composition.lands}</div>
              </div>
            )}
            {deck.health && (
              <div className="gv1-cmd-stat">
                <div className="gv1-mono-xs gv1-dim">HEALTH</div>
                <div className="gv1-serif-lg">{Math.round(deck.health.score)}<span className="gv1-dim gv1-serif-sm"> / 100 · {deck.health.grade}</span></div>
              </div>
            )}
          </div>

          <div className="gv1-cmd-strat">
            <div className="gv1-mono-xs gv1-dim gv1-cmd-label">STRATEGY · IN THE DECK</div>
            <p>{deck.strategy}</p>
          </div>
        </div>
      </div>
    </section>
  );
}

Object.assign(window, { GV1Topbar, GV1Hero, GV1DeckSelector, GV1ManaPips, GV1Commander, GV1CommanderArt });
