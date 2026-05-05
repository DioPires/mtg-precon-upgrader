// Port of gv1-chrome.jsx GV1Hero (lines 75–132).
// The prototype reads `window.GV1_DATA.DECKS`; in the React port the counts come in as props
// so the component is pure (no global state).

interface HeroProps {
  deckCount: number;
  scribedCount: number;
  /** ISO-ish display date for the UPDATED stat. */
  updated?: string;
  /** Bracket range string for the BRACKET stat. */
  bracketRange?: string;
}

const NUMBER_WORDS = [
  'zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
  'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen',
  'eighteen', 'nineteen', 'twenty',
];

export function Hero({
  deckCount,
  scribedCount,
  updated = '22 · IV · 26',
  bracketRange = 'III–V',
}: HeroProps) {
  const word = NUMBER_WORDS[deckCount] || String(deckCount);
  return (
    <header className="gv1-hero">
      <div className="gv1-hero-grid-overlay" />
      <div className="gv1-hero-inner">
        <div className="gv1-hero-sigil">
          <svg viewBox="0 0 120 120" width="120" height="120" aria-hidden="true">
            <circle cx="60" cy="60" r="56" fill="none" stroke="currentColor" strokeWidth="0.8" opacity="0.4" />
            <circle cx="60" cy="60" r="44" fill="none" stroke="currentColor" strokeWidth="0.6" opacity="0.3" />
            <circle cx="60" cy="60" r="30" fill="none" stroke="currentColor" strokeWidth="0.6" opacity="0.5" />
            <path d="M60 8 L60 112 M8 60 L112 60" stroke="currentColor" strokeWidth="0.5" opacity="0.3" />
            <path d="M60 20 L78 60 L60 100 L42 60 Z" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.7" />
            <circle cx="60" cy="60" r="4" fill="currentColor" opacity="0.9" />
            <text x="60" y="14" textAnchor="middle" fontSize="5" fill="currentColor" fontFamily="JetBrains Mono, monospace" opacity="0.6">N</text>
            <text x="60" y="113" textAnchor="middle" fontSize="5" fill="currentColor" fontFamily="JetBrains Mono, monospace" opacity="0.6">S</text>
            <text x="9" y="62" textAnchor="middle" fontSize="5" fill="currentColor" fontFamily="JetBrains Mono, monospace" opacity="0.6">W</text>
            <text x="112" y="62" textAnchor="middle" fontSize="5" fill="currentColor" fontFamily="JetBrains Mono, monospace" opacity="0.6">E</text>
          </svg>
        </div>
        <div className="gv1-eyebrow">
          <span className="gv1-rune">◆</span>
          <span className="gv1-mono-xs">TOMOS · IX</span>
          <span className="gv1-dim gv1-mono-xs">
            · curated from EDHREC · Commander Spellbook · MTGGoldfish
          </span>
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
            <div className="gv1-serif-lg">
              {deckCount} <span className="gv1-dim">decks · {scribedCount} scribed</span>
            </div>
          </div>
          <div className="gv1-hero-meta-item">
            <div className="gv1-mono-xs gv1-dim">BRACKET</div>
            <div className="gv1-serif-lg">{bracketRange}</div>
          </div>
          <div className="gv1-hero-meta-item">
            <div className="gv1-mono-xs gv1-dim">UPDATED</div>
            <div className="gv1-serif-lg">{updated}</div>
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
