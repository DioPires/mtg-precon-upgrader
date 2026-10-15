import { useEffect, useRef, useState } from 'react';
import { cardCache } from '../../data/cardCache';

// Mounts ONCE near the React root. Listens for mouseover/mouseout on any element
// with [data-card-name] and pops a Scryfall full frame next to the cursor. The
// frame is `image_large` of the shared cardCache entry (DEC-1102): a deck card's
// entry comes from card-metadata.json at once. For a name with no entry the
// layer puts the name first in the lookup queue and shows the scrying frame
// until the entry arrives.

type ImgStatus = 'loading' | 'loaded' | 'error';
type HoverSide = 'left' | 'right';
interface HoverState {
  name: string;
  x: number;
  y: number;
  side: HoverSide;
}

// Module-level cache: success/failure per picture address. Skips the loading
// flash on repeat hovers — the popover is a derivative of view state, not source of truth.
const imgCache: Record<string, 'loaded' | 'error'> = {};

const HOVER_DELAY_MS = 140;

// Sync with .gv1-cardhover width in styles.css (DEC-169 → 396px).
// Height is approximate (frame + caption); the y-clamp is best-effort.
export const POPOVER_W = 396;
export const POPOVER_H = 580;
export const HOVER_GAP = 12;

interface HoverRect {
  top: number;
  left: number;
  right: number;
}

export interface HoverPosition {
  side: HoverSide;
  x: number;
  y: number;
}

// Pure: pick the side that fits, then clamp x/y so the popover never overflows
// the viewport. For side='right', x is the popover's left edge; for side='left',
// x is the popover's right edge (paired with `right: vw - x` at render time).
export function computeHoverPosition({
  rect,
  vw,
  vh,
}: {
  rect: HoverRect;
  vw: number;
  vh: number;
}): HoverPosition {
  const fitsRight = rect.right + HOVER_GAP + POPOVER_W <= vw;
  const fitsLeft = rect.left - HOVER_GAP - POPOVER_W >= 0;
  let side: HoverSide;
  if (fitsRight) side = 'right';
  else if (fitsLeft) side = 'left';
  else side = vw - rect.right >= rect.left ? 'right' : 'left';

  const rawX = side === 'right' ? rect.right + HOVER_GAP : rect.left - HOVER_GAP;
  const x =
    side === 'right'
      ? Math.min(rawX, vw - POPOVER_W - HOVER_GAP)
      : Math.max(rawX, POPOVER_W + HOVER_GAP);
  const y = Math.max(HOVER_GAP, Math.min(rect.top, vh - POPOVER_H - HOVER_GAP));
  return { side, x, y };
}

export function GV1CardHoverLayer() {
  const [card, setCard] = useState<HoverState | null>(null);
  // Bumped when the hovered card's entry or picture changes.
  const [, setVersion] = useState(0);
  const hoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastNameRef = useRef<string | null>(null);
  const hoveredName = card?.name ?? null;

  useEffect(() => {
    if (!hoveredName) return;
    const unsub = cardCache.subscribe(hoveredName, () => setVersion((v) => v + 1));
    const cur = cardCache.get(hoveredName);
    if (!cur || cur.status === 'error') cardCache.enqueue(hoveredName, { first: true });
    return unsub;
  }, [hoveredName]);

  useEffect(() => {
    function onOver(e: MouseEvent) {
      const target = e.target as Element | null;
      const t = target?.closest?.('[data-card-name]') as HTMLElement | null;
      if (!t) return;
      const name = t.getAttribute('data-card-name');
      if (!name) return;
      if (hoverTimer.current) clearTimeout(hoverTimer.current);
      hoverTimer.current = setTimeout(() => {
        const rect = t.getBoundingClientRect();
        const { side, x, y } = computeHoverPosition({
          rect,
          vw: window.innerWidth,
          vh: window.innerHeight,
        });
        lastNameRef.current = name;
        setCard({ name, x, y, side });
      }, HOVER_DELAY_MS);
    }

    function onOut(e: MouseEvent) {
      const related = e.relatedTarget as Node | null;
      const target = e.target as Element | null;
      const t = target?.closest?.('[data-card-name]') as HTMLElement | null;
      if (!t) return;
      if (related && t.contains(related)) return;
      if (hoverTimer.current) clearTimeout(hoverTimer.current);
      lastNameRef.current = null;
      setCard(null);
    }

    function onScroll() {
      if (hoverTimer.current) clearTimeout(hoverTimer.current);
      lastNameRef.current = null;
      setCard(null);
    }

    document.addEventListener('mouseover', onOver, true);
    document.addEventListener('mouseout', onOut, true);
    window.addEventListener('scroll', onScroll, true);
    return () => {
      document.removeEventListener('mouseover', onOver, true);
      document.removeEventListener('mouseout', onOut, true);
      window.removeEventListener('scroll', onScroll, true);
      if (hoverTimer.current) clearTimeout(hoverTimer.current);
    };
  }, []);

  if (!card) return null;
  const entry = cardCache.get(card.name);
  const imgSrc = entry?.status === 'loaded' ? (entry.image_large || entry.image_normal || null) : null;
  // No address yet: scrying while the lookup is out, unavailable once it failed.
  const imgStatus: ImgStatus = imgSrc
    ? (imgCache[imgSrc] ?? 'loading')
    : entry?.status === 'loaded' || entry?.status === 'error'
      ? 'error'
      : 'loading';
  const shownName = card.name;

  return (
    <div
      className="gv1-cardhover"
      style={{
        position: 'fixed',
        left: card.side === 'right' ? card.x : 'auto',
        right: card.side === 'left' ? (window.innerWidth - card.x) : 'auto',
        top: card.y,
        zIndex: 9999,
        pointerEvents: 'none',
      }}
      aria-hidden="true"
    >
      <div className="gv1-cardhover-frame">
        {imgStatus === 'loading' && (
          <div className="gv1-cardhover-stub">
            <div className="gv1-mono-xs gv1-dim">◆ scrying scryfall ◆</div>
            <div className="gv1-cardhover-stub-name">{card.name}</div>
          </div>
        )}
        {imgStatus === 'error' && (
          <div className="gv1-cardhover-stub gv1-cardhover-error">
            <div className="gv1-mono-xs gv1-dim">◇ frame unavailable</div>
            <div className="gv1-cardhover-stub-name">{card.name}</div>
            <div className="gv1-mono-xs gv1-dim">scryfall returned no match</div>
          </div>
        )}
        {imgSrc && (
          <img
            src={imgSrc}
            alt={card.name}
            className={`gv1-cardhover-img${imgStatus === 'loaded' ? ' gv1-loaded' : ''}`}
            onLoad={() => {
              imgCache[imgSrc] = 'loaded';
              if (lastNameRef.current === shownName) setVersion((v) => v + 1);
            }}
            onError={() => {
              imgCache[imgSrc] = 'error';
              cardCache.imageFailed(shownName);
              if (lastNameRef.current === shownName) setVersion((v) => v + 1);
            }}
            draggable={false}
          />
        )}
      </div>
      <div className="gv1-cardhover-caption gv1-mono-xs gv1-dim">
        ◇ scryfall · large frame
      </div>
    </div>
  );
}
