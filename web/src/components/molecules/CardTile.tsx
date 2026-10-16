import { useState } from 'react';
import { useCard } from '../../hooks/useCard';
import { cardCache } from '../../data/cardCache';
import { ManaCost } from '../atoms/ManaCost';

export interface CardTileCard {
  /** Card name (REQUIRED). */
  n: string;
  /** Mana value, e.g. "{2}{R}" or "—"/"LAND". */
  mv?: string;
  /** Type line; falls back to the card entry's type. */
  type?: string;
  /** Editor's note shown below type. */
  note?: string;
  /** Price string, e.g. "$0.42"; falls back to the card entry's price. */
  price?: string;
  /** Game-changer flag — adds star + gold border. */
  gc?: boolean;
}

interface CardTileProps {
  card: CardTileCard;
  size?: 'sm' | 'md' | 'lg';
}

function FallbackGlyph({ seed, variant }: { seed: number; variant: number }) {
  const gradId = `g${seed}`;
  return (
    <svg viewBox="0 0 160 120" width="100%" height="100%" preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <radialGradient id={gradId} cx="50%" cy="55%" r="60%">
          <stop offset="0%" stopColor="rgba(124,200,146,0.12)" />
          <stop offset="100%" stopColor="rgba(124,200,146,0)" />
        </radialGradient>
      </defs>
      <rect width="160" height="120" fill={`url(#${gradId})`} />
      {variant === 0 && (
        <>
          <circle cx="80" cy="60" r="30" fill="none" stroke="currentColor" strokeWidth="0.6" opacity="0.25" />
          <circle cx="80" cy="60" r="20" fill="none" stroke="currentColor" strokeWidth="0.5" opacity="0.35" />
          <path d="M80 30 L95 60 L80 90 L65 60 Z" fill="none" stroke="currentColor" strokeWidth="0.8" opacity="0.45" />
          <circle cx="80" cy="60" r="2" fill="currentColor" opacity="0.6" />
        </>
      )}
      {variant === 1 && (
        <>
          <circle cx="80" cy="60" r="28" fill="none" stroke="currentColor" strokeWidth="0.5" opacity="0.25" />
          <path d="M52 60 L108 60 M80 32 L80 88" stroke="currentColor" strokeWidth="0.4" opacity="0.3" />
          <path d="M62 42 L98 78 M98 42 L62 78" stroke="currentColor" strokeWidth="0.3" opacity="0.25" />
          <circle cx="80" cy="60" r="3" fill="none" stroke="currentColor" strokeWidth="0.8" opacity="0.5" />
        </>
      )}
      {variant === 2 && (
        <>
          <polygon points="80,28 104,50 104,78 80,100 56,78 56,50" fill="none" stroke="currentColor" strokeWidth="0.6" opacity="0.3" />
          <polygon points="80,42 92,52 92,72 80,82 68,72 68,52" fill="none" stroke="currentColor" strokeWidth="0.5" opacity="0.4" />
          <circle cx="80" cy="62" r="1.5" fill="currentColor" opacity="0.5" />
        </>
      )}
      {variant === 3 && (
        <>
          <circle cx="80" cy="60" r="34" fill="none" stroke="currentColor" strokeWidth="0.4" opacity="0.2" />
          <g transform="translate(80 60)">
            <path d="M-20 0 L20 0 M0 -20 L0 20" stroke="currentColor" strokeWidth="0.4" opacity="0.35" />
            <path d="M-14 -14 L14 14 M14 -14 L-14 14" stroke="currentColor" strokeWidth="0.3" opacity="0.25" />
            <circle r="8" fill="none" stroke="currentColor" strokeWidth="0.5" opacity="0.4" />
          </g>
        </>
      )}
    </svg>
  );
}

export function CardTile({ card, size = 'md' }: CardTileProps) {
  // The picture is Scryfall's address from the card entry: card-metadata.json
  // for a deck card (DEC-1102), a lookup for a name that the file lacks.
  const [failedSrc, setFailedSrc] = useState<string | null>(null);

  // Deterministic glyph variant per card name so it looks curated, not random.
  const seed = (card.n || '').split('').reduce((a, c) => a + c.charCodeAt(0), 0);
  const variant = seed % 4;
  const live = useCard(card.n);
  const imgSrc = live?.status === 'loaded'
    ? (live.image_normal || live.image_small || live.image_large || null)
    : null;
  // A new address (after a failed picture, the cache looks the card up again) gets its own try.
  const hasImg = !!imgSrc && imgSrc !== failedSrc;
  const mvLive = live?.status === 'loaded' && live.mana_cost ? live.mana_cost : null;
  const mv = (card.mv && card.mv !== '—') ? card.mv : (mvLive || card.mv || '—');
  const priceLive = live?.status === 'loaded' && live.price ? live.price : null;
  const highlightPrice = !!card.price && card.price !== '—';
  const price = highlightPrice ? card.price! : (priceLive || card.price || '—');
  const typeLine = card.type || live?.type_line || '—';
  const className = ['gv1-card-tile', `gv1-card-${size}`, card.gc ? 'gv1-card-gc' : '']
    .filter(Boolean)
    .join(' ');
  return (
    <div className={className} data-card-name={card.n}>
      <div className="gv1-card-tile-art">
        {hasImg && (
          <img
            src={imgSrc!}
            alt=""
            className="gv1-card-tile-img"
            loading="lazy"
            draggable={false}
            onError={() => {
              setFailedSrc(imgSrc);
              cardCache.imageFailed(card.n);
            }}
          />
        )}
        {!hasImg && (
          <div className="gv1-card-tile-art-placeholder">
            <FallbackGlyph seed={seed} variant={variant} />
          </div>
        )}
        <div className="gv1-card-tile-mv"><ManaCost mv={mv} /></div>
        {card.gc && <div className="gv1-card-tile-gc">★</div>}
      </div>
      <div className="gv1-card-tile-body">
        <div className="gv1-card-tile-name">{card.n}</div>
        <div className="gv1-mono-xs gv1-dim gv1-card-tile-type">{typeLine}</div>
        {card.note && <div className="gv1-card-tile-note">{card.note}</div>}
        <div className="gv1-card-tile-foot">
          <span className="gv1-mono-xs gv1-rune">{price}</span>
          <span className="gv1-mono-xs gv1-dim gv1-card-tile-hint">hover ◇</span>
        </div>
      </div>
    </div>
  );
}
