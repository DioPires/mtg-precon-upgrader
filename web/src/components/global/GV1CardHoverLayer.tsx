import { useEffect, useRef, useState } from 'react';
import { cardCache } from '../../data/cardCache';

// Mounts ONCE near the React root. Listens for mouseover/mouseout on any element
// with [data-card-name] and pops a Scryfall full frame next to the cursor. Uses
// the shared cardCache when available so repeat hovers are instant; otherwise
// falls back to Scryfall's named-card image redirect.

type ImgStatus = 'idle' | 'loading' | 'loaded' | 'error';
type HoverSide = 'left' | 'right';
interface HoverState {
  name: string;
  x: number;
  y: number;
  side: HoverSide;
}

const cardFrameUrl = (name: string) =>
  `https://api.scryfall.com/cards/named?fuzzy=${encodeURIComponent(name)}&format=image&version=large`;

// Module-level cache: success/failure per card name. Skips the loading flash
// on repeat hovers — the popover is a derivative of view state, not source of truth.
const imgCache: Record<string, 'loaded' | 'error'> = {};

const HOVER_DELAY_MS = 140;

export function GV1CardHoverLayer() {
  const [card, setCard] = useState<HoverState | null>(null);
  const [imgStatus, setImgStatus] = useState<ImgStatus>('idle');
  const hoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastNameRef = useRef<string | null>(null);

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
        const vw = window.innerWidth;
        const side: HoverSide = (rect.right + 480 > vw) ? 'left' : 'right';
        const x = side === 'right' ? rect.right + 12 : rect.left - 12;
        const y = Math.max(20, Math.min(rect.top, window.innerHeight - 580));
        lastNameRef.current = name;
        setCard({ name, x, y, side });
        const cached = imgCache[name.toLowerCase()];
        if (cached === 'loaded') setImgStatus('loaded');
        else if (cached === 'error') setImgStatus('error');
        else setImgStatus('loading');
      }, HOVER_DELAY_MS);
    }

    function onOut(e: MouseEvent) {
      const related = e.relatedTarget as Node | null;
      const target = e.target as Element | null;
      const t = target?.closest?.('[data-card-name]') as HTMLElement | null;
      if (!t) return;
      if (related && t.contains(related)) return;
      if (hoverTimer.current) clearTimeout(hoverTimer.current);
      setCard(null);
      setImgStatus('idle');
    }

    function onScroll() {
      if (hoverTimer.current) clearTimeout(hoverTimer.current);
      setCard(null);
      setImgStatus('idle');
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
  const cacheKey = card.name.toLowerCase();
  const cached = cardCache.get(card.name);
  const imgSrc = (cached?.status === 'loaded' && (cached.image_large || cached.image_normal))
    ? (cached.image_large || cached.image_normal)!
    : cardFrameUrl(card.name);

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
        <img
          src={imgSrc}
          alt={card.name}
          className={`gv1-cardhover-img${imgStatus === 'loaded' ? ' gv1-loaded' : ''}`}
          onLoad={() => {
            imgCache[cacheKey] = 'loaded';
            if (lastNameRef.current === card.name) setImgStatus('loaded');
          }}
          onError={() => {
            imgCache[cacheKey] = 'error';
            if (lastNameRef.current === card.name) setImgStatus('error');
          }}
          draggable={false}
        />
      </div>
      <div className="gv1-cardhover-caption gv1-mono-xs gv1-dim">
        ◇ scryfall · large frame
      </div>
    </div>
  );
}
