// Port of gv1-engine.jsx GV1WinCons (lines 118–162).

import { CardTile } from '../molecules/CardTile';
import type { DeckWincon } from '../../data/types';

interface WinConsProps {
  wincons: DeckWincon[];
}

export function WinCons({ wincons }: WinConsProps) {
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
        <span className="gv1-mono-xs gv1-dim">
          · {wincons.length} scried path{wincons.length === 1 ? '' : 's'} to victory
        </span>
      </div>
      <div className="gv1-wincons-grid">
        {wincons.map((w, i) => (
          <div key={i} className="gv1-wincon">
            <div className="gv1-wincon-head">
              <div className="gv1-mono-xs gv1-dim">WIN · {String(i + 1).padStart(2, '0')}</div>
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
              {w.cards.map((c, j) => (
                <CardTile key={j} card={c} size="sm" />
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
