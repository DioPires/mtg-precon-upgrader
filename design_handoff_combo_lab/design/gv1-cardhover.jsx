// Grimoire v1 — Card hover popover
// Mounts ONCE at the root. Listens for mouseover/mouseout on any element with
// [data-card-name]. Pops a full-frame Scryfall image next to the cursor with
// a small parchment frame. Caches images by name so repeat hovers are instant.
//
// Usage: render <CardHoverLayer /> once near the root, then sprinkle
//   <span data-card-name={name}>{name}</span>
// (or any element with data-card-name) anywhere in the tree.

const { useEffect: useEffectCH, useState: useStateCH, useRef: useRefCH } = React;

// Scryfall normal-size frame — lazy fallback when GV1Cards hasn't cached yet
const cardFrameUrl = (name) => `https://api.scryfall.com/cards/named?fuzzy=${encodeURIComponent(name)}&format=image&version=normal`;

// Module-level cache: { [nameLower]: 'loading' | 'loaded' | 'error' }
window.__GV1_CARD_CACHE = window.__GV1_CARD_CACHE || {};

function GV1CardHoverLayer() {
  const [card, setCard] = useStateCH(null); // { name, x, y, side }
  const [imgStatus, setImgStatus] = useStateCH('idle'); // 'idle' | 'loading' | 'loaded' | 'error'
  const hoverTimer = useRefCH(null);
  const lastNameRef = useRefCH(null);

  useEffectCH(() => {
    function onOver(e) {
      const t = e.target.closest('[data-card-name]');
      if (!t) return;
      const name = t.getAttribute('data-card-name');
      if (!name) return;
      // Debounce: 120ms before showing
      clearTimeout(hoverTimer.current);
      hoverTimer.current = setTimeout(() => {
        const rect = t.getBoundingClientRect();
        // Choose side based on cursor position (right unless near right edge)
        const vw = window.innerWidth;
        const side = (rect.right + 320 > vw) ? 'left' : 'right';
        const x = side === 'right' ? rect.right + 12 : rect.left - 12;
        const y = Math.max(20, Math.min(rect.top, window.innerHeight - 460));
        lastNameRef.current = name;
        setCard({ name, x, y, side });
        const cacheKey = name.toLowerCase();
        const cached = window.__GV1_CARD_CACHE[cacheKey];
        if (cached === 'loaded') setImgStatus('loaded');
        else if (cached === 'error') setImgStatus('error');
        else setImgStatus('loading');
      }, 140);
    }
    function onOut(e) {
      const related = e.relatedTarget;
      const t = e.target.closest('[data-card-name]');
      if (!t) return;
      // If moving into a child of the same card, ignore
      if (related && t.contains(related)) return;
      clearTimeout(hoverTimer.current);
      setCard(null);
      setImgStatus('idle');
    }
    function onScroll() {
      clearTimeout(hoverTimer.current);
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
      clearTimeout(hoverTimer.current);
    };
  }, []);

  if (!card) return null;
  const cacheKey = card.name.toLowerCase();
  // Prefer the shared cached image if available (saves a Scryfall hit + flash)
  const cached = window.GV1Cards && window.GV1Cards.get(card.name);
  const imgSrc = (cached && cached.status === 'loaded' && cached.image_normal)
    ? cached.image_normal
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
          className={'gv1-cardhover-img' + (imgStatus === 'loaded' ? ' gv1-loaded' : '')}
          onLoad={() => {
            window.__GV1_CARD_CACHE[cacheKey] = 'loaded';
            if (lastNameRef.current === card.name) setImgStatus('loaded');
          }}
          onError={() => {
            window.__GV1_CARD_CACHE[cacheKey] = 'error';
            if (lastNameRef.current === card.name) setImgStatus('error');
          }}
          draggable="false"
        />
      </div>
      <div className="gv1-cardhover-caption gv1-mono-xs gv1-dim">
        ◇ scryfall · normal frame
      </div>
    </div>
  );
}

Object.assign(window, { GV1CardHoverLayer });
