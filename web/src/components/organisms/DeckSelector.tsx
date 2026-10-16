// Port of gv1-chrome.jsx GV1DeckSelector (lines 159–231).
// Filter chips are static (mirrors the prototype — DEC-149 P3+ adds filtering).
// DEC-297: brewing decks render at the end of the rail under a divider, with
// a BREWING badge on each pill.

import { Fragment, useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react';
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

  // DEC-1008: centre the active pill by scrolling the track itself. Calling
  // scrollIntoView on the pill also scrolls every scrollable ancestor, and
  // `.gv1-root` was one while it was `overflow: hidden` — the whole page slid
  // sideways for pills the track could not centre on its own. It still is one
  // where `overflow: clip` falls back to `hidden` (DEC-1019).
  //
  // DEC-1063: WebKit can mount the selector before the page's stylesheets
  // apply. Until they do the track's `overflow-x` computes to `visible`: it
  // is not a scroll container, `scrollTo` cannot move it, and its rect is the
  // unstyled one (tall enough to scroll a short page). Read nothing then and
  // return false; the size observer below asks again.
  const centreActive = useCallback(() => {
    const track = trackRef.current;
    const el = track?.querySelector<HTMLElement>('.gv1-active');
    if (!track || !el || !track.scrollTo) return true;
    if (getComputedStyle(track).overflowX === 'visible') return false;
    const t = track.getBoundingClientRect();
    const p = el.getBoundingClientRect();
    track.scrollTo({
      left: track.scrollLeft + (p.left + p.width / 2) - (t.left + t.width / 2),
      behavior: 'smooth',
    });
    // Still bring the rail into view when a deck is opened from a scrolled
    // page: scroll the page by the least amount, as `block: 'nearest'` would.
    // Not `track.scrollIntoView` (DEC-1048): Chromium moves its sequential
    // focus starting point to the element, so the first Tab from load skipped
    // the topbar and landed on the active pill.
    const below = t.bottom - document.documentElement.clientHeight;
    const dy = t.top < 0 ? t.top : below > 0 ? Math.min(below, t.top) : 0;
    if (dy) window.scrollBy({ top: dy, behavior: 'smooth' });
    return true;
  }, []);
  const centrePending = useRef(false);
  useEffect(() => {
    centrePending.current = !centreActive();
  }, [activeIdx, centreActive]);

  // DEC-1048: the right-edge fade means "more pills this way". Drop it while
  // the track is scrolled to its end, or when the track does not overflow.
  const [atEnd, setAtEnd] = useState(false);
  const updateAtEnd = useCallback(() => {
    const track = trackRef.current;
    if (track) setAtEnd(track.scrollLeft + track.clientWidth >= track.scrollWidth - 1);
  }, []);
  // DEC-1063: follow the track's own size too. It changes with no scroll and
  // no window resize when the styles reach a selector that mounted without
  // them (the unstyled track does not overflow), and when the selector is
  // narrowed around it. jsdom has no ResizeObserver.
  //
  // The same size change is when a centring that found the track unstyled
  // can run. Only that one: once the pill has been centred on a styled track,
  // a size change must not pull back a rail the user has scrolled.
  useEffect(() => {
    updateAtEnd();
    window.addEventListener('resize', updateAtEnd);
    const track = trackRef.current;
    const sized =
      track && typeof ResizeObserver !== 'undefined'
        ? new ResizeObserver(() => {
            if (centrePending.current) centrePending.current = !centreActive();
            updateAtEnd();
          })
        : null;
    if (track) sized?.observe(track);
    return () => {
      window.removeEventListener('resize', updateAtEnd);
      sized?.disconnect();
    };
  }, [updateAtEnd, centreActive, ordered.length]);

  // DEC-1135: a key switch moves focus to the pill that it picks, as the
  // WAI-ARIA tabs pattern does. The key handler names the deck; the focus
  // waits until that pill renders as active (tabIndex 0). A click leaves
  // focus on the clicked pill, and a route change that no key started
  // clears the name (DEC-1146 below says when it moves focus).
  // `preventScroll`: the centring above scrolls the track, and a focus
  // scroll would also move `.gv1-root` (DEC-1008).
  const focusActive = useCallback(() => {
    trackRef.current?.querySelector<HTMLElement>('.gv1-active')?.focus({ preventScroll: true });
  }, []);
  const keyTarget = useRef<number | null>(null);

  // DEC-1146: a deck change that no key started (browser Back or Forward)
  // moves focus to the active pill in two cases. (a) The element that had
  // focus left the page with the old deck (each deck mounts its own
  // Apothecary): focus fell to `body`, and Chromium's next Tab would start
  // where that element was. (b) Focus is on a pill that is no longer active.
  // After the commit, a removed element and "nothing had focus" both read as
  // `body`, so the render that brings the new deck reads the element first.
  // The first render reads nothing: a page load moves no focus (DEC-1048).
  const renderedIdx = useRef(activeIdx);
  const focusBefore = useRef<Element | null>(null);
  if (renderedIdx.current !== activeIdx) {
    renderedIdx.current = activeIdx;
    focusBefore.current = document.activeElement;
  }
  useEffect(() => {
    const before = focusBefore.current;
    focusBefore.current = null;
    if (keyTarget.current === activeIdx) focusActive();
    else if (before && strayed(before, trackRef.current)) focusActive();
    keyTarget.current = null;
  }, [activeIdx, focusActive]);

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
    const next = scribed[nextIx].idx;
    // The key picked the deck already open: its pill renders as active now.
    if (next === activeIdx) focusActive();
    else keyTarget.current = next;
    onSelect(next);
  };

  return (
    <nav
      className="gv1-selector"
      aria-label="Deck selector"
      role="tablist"
      data-at-end={atEnd || undefined}
    >
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
      <div
        className="gv1-selector-track"
        ref={trackRef}
        onKeyDown={onKey}
        onScroll={updateAtEnd}
      >
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

// DEC-1146: case (a) or case (b) after a deck change. A click switch is
// neither: the press focused the clicked pill, which is the active one now.
function strayed(before: Element, track: HTMLElement | null): boolean {
  const now = document.activeElement;
  const left = !before.isConnected && (!now || now === document.body);
  const onOldPill = !!now && !!track?.contains(now) && !now.classList.contains('gv1-active');
  return left || onOldPill;
}
