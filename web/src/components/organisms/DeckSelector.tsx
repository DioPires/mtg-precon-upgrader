// Port of gv1-chrome.jsx GV1DeckSelector (lines 159–231).
// Filter chips are static (mirrors the prototype — DEC-149 P3+ adds filtering).
// DEC-297: brewing decks render at the end of the rail under a divider, with
// a BREWING badge on each pill.

import { Fragment, useEffect, useMemo, useRef, type KeyboardEvent } from 'react';
import { GV1ManaPips } from '../atoms/GV1ManaPips';
import type { DeckStub } from '../../data/types';

interface DeckSelectorProps {
  decks: DeckStub[];
  activeIdx: number;
  onSelect: (idx: number) => void;
}

export function DeckSelector({ decks, activeIdx, onSelect }: DeckSelectorProps) {
  const trackRef = useRef<HTMLDivElement>(null);

  // Stable partition: physical decks first (source order), brewing decks last.
  const ordered = useMemo(() => {
    const phys: DeckStub[] = [];
    const brew: DeckStub[] = [];
    for (const d of decks) {
      if (d.status === 'brewing') brew.push(d);
      else phys.push(d);
    }
    return [...phys, ...brew];
  }, [decks]);
  const brewingCount = ordered.filter((d) => d.status === 'brewing').length;

  useEffect(() => {
    const el = trackRef.current?.querySelector('.gv1-active');
    if (el && (el as HTMLElement).scrollIntoView) {
      (el as HTMLElement).scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
    }
  }, [activeIdx]);

  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) return;
    e.preventDefault();
    const scribed = ordered.filter((d) => d.hasDetail);
    if (!scribed.length) return;
    const curIx = scribed.findIndex((d) => d.idx === activeIdx);
    let nextIx: number;
    if (e.key === 'ArrowRight') nextIx = (curIx + 1 + scribed.length) % scribed.length;
    else if (e.key === 'ArrowLeft') nextIx = (curIx - 1 + scribed.length) % scribed.length;
    else if (e.key === 'Home') nextIx = 0;
    else nextIx = scribed.length - 1;
    onSelect(scribed[nextIx].idx);
  };

  return (
    <nav className="gv1-selector" aria-label="Deck selector" role="tablist">
      <div className="gv1-selector-head">
        <div className="gv1-selector-head-l">
          <span className="gv1-mono-xs gv1-rune">
            <span aria-hidden="true">◈ </span>TOMOS
          </span>
          <span className="gv1-mono-xs gv1-dim">
            — {decks.length} indexed · {decks.filter((d) => d.hasDetail).length} scribed
            {brewingCount > 0 && ` · ${brewingCount} brewing`}
          </span>
        </div>
        <div className="gv1-selector-head-r">
          <span className="gv1-mono-xs gv1-dim">filter:</span>
          <span className="gv1-mono-xs gv1-chip gv1-chip-active">all</span>
          <span className="gv1-mono-xs gv1-chip">mono</span>
          <span className="gv1-mono-xs gv1-chip">multicolor</span>
          <span className="gv1-mono-xs gv1-chip">bracket 4</span>
        </div>
      </div>
      <div className="gv1-selector-track" ref={trackRef} onKeyDown={onKey}>
        {ordered.map((d, i) => {
          const active = d.idx === activeIdx;
          const stub = !d.hasDetail;
          const brewing = d.status === 'brewing';
          const isFirstBrewing =
            brewing && (i === 0 || ordered[i - 1].status !== 'brewing');
          return (
            <Fragment key={d.slug}>
              {isFirstBrewing && (
                <div className="gv1-sel-group-marker" role="presentation">
                  <span className="gv1-mono-xs gv1-dim gv1-sel-group-label">BREWING</span>
                </div>
              )}
              <button
                role="tab"
                aria-selected={active}
                aria-disabled={stub}
                tabIndex={active ? 0 : -1}
                className={
                  'gv1-sel-pill' +
                  (active ? ' gv1-active' : '') +
                  (stub ? ' gv1-stub' : '') +
                  (brewing ? ' gv1-sel-pill-brewing' : '')
                }
                onClick={() => !stub && onSelect(d.idx)}
                title={
                  stub
                    ? 'Not yet scribed — coming soon'
                    : brewing
                      ? `${d.name} — brewing (not physically built)`
                      : `Open ${d.name}`
                }
                type="button"
              >
                <div className="gv1-sel-pill-top">
                  <span className="gv1-mono-xs gv1-dim">№ {String(d.idx).padStart(2, '0')}</span>
                  <GV1ManaPips colors={d.colors} />
                  {brewing && <span className="gv1-mono-xs gv1-brewing-pill">BREWING</span>}
                </div>
                <div className="gv1-sel-pill-name">{d.name}</div>
                <div className="gv1-mono-xs gv1-sel-pill-cmd">
                  {d.cmd}
                  {d.partner ? <> + {d.partner}</> : null}
                </div>
                <div className="gv1-sel-pill-foot">
                  <span className="gv1-mono-xs gv1-sel-pill-bracket">BRACKET {d.bracket}</span>
                </div>
                {active && (
                  <span className="gv1-sel-pill-flag">
                    <span className="gv1-mono-xs">NOW SCRYING</span>
                  </span>
                )}
                {stub && (
                  <span className="gv1-sel-pill-stub">
                    <span className="gv1-mono-xs">
                      <span aria-hidden="true">⬡ </span>unscribed
                    </span>
                  </span>
                )}
              </button>
            </Fragment>
          );
        })}
      </div>
    </nav>
  );
}
