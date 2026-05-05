// Port of gv1-mobile.jsx GV1Decklist (lines 3–36).

import { ManaCost } from '../atoms/ManaCost';
import type { DeckListGroup } from '../../data/types';

interface DecklistProps {
  list: DeckListGroup[];
}

export function Decklist({ list }: DecklistProps) {
  const total = list.reduce((n, g) => n + g.cards.length, 0);
  return (
    <section className="gv1-section gv1-decklist">
      <div className="gv1-section-head">
        <span className="gv1-rune" aria-hidden="true">§ VII</span>
        <h2 className="gv1-section-title">The Manifest</h2>
        <span className="gv1-mono-xs gv1-dim">
          · {total} cards · {list.length} roles · sorted by function
        </span>
      </div>
      <div className="gv1-decklist-cols">
        {list.map((grp, i) => (
          <div key={i} className="gv1-dl-group">
            <div className="gv1-dl-group-head">
              <span className="gv1-serif-sm">{grp.name}</span>
              <span className="gv1-mono-xs gv1-dim">{grp.cards.length}</span>
            </div>
            <ul className="gv1-dl-list">
              {grp.cards.map((c, j) => (
                <li
                  key={j}
                  className={'gv1-dl-row' + (c.gc ? ' gv1-dl-gc' : '')}
                  data-card-name={c.n}
                >
                  <span className="gv1-dl-name">
                    {c.gc && <span className="gv1-dl-star">★</span>}
                    {c.n}
                  </span>
                  <span className="gv1-dl-mv">
                    <ManaCost mv={c.mv} />
                  </span>
                  <span className="gv1-dl-price gv1-mono-xs gv1-rune">{c.price}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}
