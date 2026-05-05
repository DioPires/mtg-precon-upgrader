// Port of gv1-perf.jsx GV1Combos (lines 4–54).

import { CardTile } from '../molecules/CardTile';
import type { DeckCombo } from '../../data/types';

interface CombosProps {
  combos: DeckCombo[];
}

export function Combos({ combos }: CombosProps) {
  if (!combos || combos.length === 0) {
    return (
      <section className="gv1-section gv1-combos">
        <div className="gv1-section-head">
          <span className="gv1-rune" aria-hidden="true">§ IV</span>
          <h2 className="gv1-section-title">Combos & Interactions</h2>
        </div>
        <div className="gv1-empty">No synergies scribed yet.</div>
      </section>
    );
  }
  return (
    <section className="gv1-section gv1-combos">
      <div className="gv1-section-head">
        <span className="gv1-rune" aria-hidden="true">§ IV</span>
        <h2 className="gv1-section-title">Combos & Interactions</h2>
        <span className="gv1-mono-xs gv1-dim">· cited chains and soft-locks</span>
      </div>
      <div className="gv1-combo-grid">
        {combos.map((c, i) => (
          <div key={i} className="gv1-combo">
            <div className="gv1-combo-head">
              <svg
                className="gv1-combo-glyph"
                viewBox="0 0 40 40"
                width="36"
                height="36"
                aria-hidden="true"
              >
                <circle cx="20" cy="20" r="18" fill="none" stroke="currentColor" strokeWidth="0.6" opacity="0.4" />
                <circle cx="20" cy="20" r="13" fill="none" stroke="currentColor" strokeWidth="0.5" opacity="0.3" />
                <path d="M20 4 L26 20 L20 36 L14 20 Z" fill="none" stroke="currentColor" strokeWidth="1" />
                <circle cx="20" cy="20" r="2" fill="currentColor" />
              </svg>
              <div>
                <div className="gv1-mono-xs gv1-dim">{c.tag}</div>
                <h3 className="gv1-combo-title">
                  <span>{c.title[0]}</span>
                  <em>{c.title[1]}</em>
                </h3>
              </div>
            </div>
            <p className="gv1-combo-desc">{c.desc}</p>
            <div className="gv1-combo-cards">
              {c.cards.map((cc, j) => (
                <CardTile key={j} card={cc} size="sm" />
              ))}
            </div>
            <div className="gv1-combo-src">
              <span className="gv1-mono-xs gv1-dim">SOURCE</span>
              <span className="gv1-mono-xs gv1-rune">{c.src}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
