// Port of design_handoff_grimoire/prototype/gv1-mobile.jsx GV1Mobile.
// Per-deck mobile artboard wrapped in iPhone-bezel layout.

import { CardTile } from '../molecules/CardTile';
import type { DeckFull } from '../../data/types';

interface MobileProps {
  deck: DeckFull;
}

export function Mobile({ deck }: MobileProps) {
  const wincon = deck.wincons?.[0] || null;
  const curve = deck.curve && deck.curve.length ? deck.curve : null;
  const maxN = curve ? Math.max(1, ...curve.map((c) => c.n)) : 1;

  const nameWords = deck.deckName.split(' ');
  const lastWord = nameWords.length > 1 ? nameWords[nameWords.length - 1] : null;
  const headWords = nameWords.length > 1 ? nameWords.slice(0, -1).join(' ') : null;

  return (
    <div className="gv1-mobile">
      <div className="gv1-mobile-status">
        <span className="gv1-mono-xs">9:41</span>
        <span className="gv1-mono-xs gv1-rune">◈ grimoire</span>
        <span className="gv1-mono-xs" aria-hidden="true">◉ ◉ ◉</span>
      </div>
      <div className="gv1-mobile-head">
        <div className="gv1-mono-xs gv1-dim">
          № {String(deck.idx).padStart(2, '0')} · BRACKET {deck.bracket}
        </div>
        <h1 className="gv1-serif-xl">
          {lastWord ? (
            <>
              <span>{headWords} </span>
              <em>{lastWord}</em>
            </>
          ) : (
            <em>{deck.deckName}</em>
          )}
        </h1>
        <div className="gv1-mono-xs gv1-rune" data-card-name={deck.commander}>
          {deck.commander} · ◇
        </div>
        <div className="gv1-mobile-tabs" role="tablist" aria-label="Deck sections">
          <button type="button" role="tab" aria-selected="true" className="gv1-active">Engine</button>
          <button type="button" role="tab" aria-selected="false">Wins</button>
          <button type="button" role="tab" aria-selected="false">Combos</button>
          <button type="button" role="tab" aria-selected="false">List</button>
        </div>
      </div>
      <div className="gv1-mobile-body">
        {wincon && (
          <div className="gv1-mobile-block">
            <div className="gv1-mono-xs gv1-dim">
              WIN · 01 / {String(deck.wincons.length).padStart(2, '0')}
            </div>
            <h3 className="gv1-serif-md">
              <span>{wincon.title[0]}</span>
              <em>{wincon.title[1]}</em>
            </h3>
            <p className="gv1-wincon-desc gv1-mobile-desc">{wincon.desc}</p>
            {wincon.prob && (
              <div className="gv1-mobile-prob">
                <span className="gv1-mono-xs gv1-dim">EARLIEST WIN</span>
                <span className="gv1-serif-lg gv1-rune">{wincon.prob}</span>
              </div>
            )}
          </div>
        )}
        {wincon && wincon.cards && wincon.cards.length > 0 && (
          <div className="gv1-mobile-block">
            <div className="gv1-mono-xs gv1-dim">KEY CARDS</div>
            <div className="gv1-mobile-cards">
              {wincon.cards.slice(0, 2).map((c, i) => (
                <CardTile key={i} card={c} size="sm" />
              ))}
            </div>
          </div>
        )}
        {curve && (
          <div className="gv1-mobile-block gv1-mobile-curve-block">
            <div className="gv1-mono-xs gv1-dim">ROLE DISTRIBUTION</div>
            <div className="gv1-curve gv1-curve-sm">
              {curve.map((c, i) => (
                <div key={i} className={'gv1-curve-col' + (c.peak ? ' gv1-peak' : '')}>
                  <div className="gv1-curve-bar-wrap">
                    <div
                      className="gv1-curve-bar"
                      style={{ height: (c.n / maxN) * 100 + '%' }}
                    />
                  </div>
                  <div className="gv1-curve-l gv1-mono-xs gv1-dim">{c.cmc}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
      <div className="gv1-mobile-nav">
        <span className="gv1-rune" aria-hidden="true">◈</span>
        <span className="gv1-mono-xs">shelf</span>
        <span className="gv1-mono-xs"><span aria-hidden="true">⦿ </span>scry</span>
        <span className="gv1-mono-xs gv1-dim"><span aria-hidden="true">▦ </span>list</span>
        <span className="gv1-mono-xs gv1-dim" aria-label="Settings">⚙</span>
      </div>
    </div>
  );
}
