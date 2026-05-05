// Port of gv1-engine.jsx GV1Engine (lines 164–242).
// Behaviour: WAI-ARIA tablist sidebar with Arrow/Home/End keyboard navigation.

import { useState, type KeyboardEvent } from 'react';
import { CardTile } from '../molecules/CardTile';
import type { DeckEngineSection } from '../../data/types';

interface EngineProps {
  engine: DeckEngineSection[];
}

export function Engine({ engine }: EngineProps) {
  const [active, setActive] = useState(0);

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

  const onTabsKey = (e: KeyboardEvent<HTMLElement>) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
      e.preventDefault();
      setActive((safeActive + 1) % engine.length);
    } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
      e.preventDefault();
      setActive((safeActive - 1 + engine.length) % engine.length);
    } else if (e.key === 'Home') {
      e.preventDefault();
      setActive(0);
    } else if (e.key === 'End') {
      e.preventDefault();
      setActive(engine.length - 1);
    }
  };

  const totalCards = engine.reduce((n, e) => n + e.count, 0);

  return (
    <section className="gv1-section gv1-engine" aria-labelledby="gv1-engine-h">
      <div className="gv1-section-head">
        <span className="gv1-rune" aria-hidden="true">§ III</span>
        <h2 id="gv1-engine-h" className="gv1-section-title">The Engine</h2>
        <span className="gv1-mono-xs gv1-dim">
          · {totalCards} cards across {engine.length} roles
        </span>
      </div>
      <div className="gv1-engine-shell">
        <aside
          className="gv1-engine-tabs"
          role="tablist"
          aria-label="Engine roles"
          onKeyDown={onTabsKey}
        >
          {engine.map((e, i) => (
            <button
              key={i}
              role="tab"
              id={'gv1-engine-tab-' + i}
              aria-selected={i === safeActive}
              aria-controls="gv1-engine-panel"
              tabIndex={i === safeActive ? 0 : -1}
              className={
                'gv1-engine-tab' +
                (i === safeActive ? ' gv1-active' : '') +
                (e.isGameChangers ? ' gv1-engine-tab-gc' : '')
              }
              onClick={() => setActive(i)}
              type="button"
            >
              <span className="gv1-mono-xs gv1-dim">{String(i + 1).padStart(2, '0')}</span>
              <span className="gv1-serif-sm">
                {e.title}
                {e.isGameChangers && (
                  <span className="gv1-tab-star" aria-hidden="true"> ★</span>
                )}
              </span>
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
              <div className="gv1-mono-xs gv1-dim">
                ROLE · {String(safeActive + 1).padStart(2, '0')} /{' '}
                {String(engine.length).padStart(2, '0')}
                {cur.isGameChangers && ' · GAME CHANGERS'}
              </div>
              <h3 className="gv1-serif-xl">{cur.title}</h3>
            </div>
            <div className="gv1-mono-xs gv1-dim">{cur.count} cards · hover for full frame</div>
          </div>
          <div className="gv1-engine-cards">
            {cur.cards.map((c, i) => (
              <CardTile key={i} card={c} size="md" />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
