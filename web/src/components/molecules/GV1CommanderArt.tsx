import { useState } from 'react';
import { cardCache } from '../../data/cardCache';
import { useCard } from '../../hooks/useCard';

type Status = 'loading' | 'loaded' | 'error';

interface GV1CommanderArtProps {
  name: string;
  slug: string;
}

export function GV1CommanderArt({ name, slug }: GV1CommanderArtProps) {
  // `art_crop` from the card entry (DEC-1102). A commander that the file lacks
  // is looked up before the other cards of the page.
  const entry = useCard(name, { first: true });
  const [loadedSrc, setLoadedSrc] = useState<string | null>(null);
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const src = entry?.status === 'loaded' ? entry.art_crop || null : null;
  const status: Status =
    src && src === loadedSrc
      ? 'loaded'
      : entry?.status === 'error' || (entry?.status === 'loaded' && !src) || (src && src === failedSrc)
        ? 'error'
        : 'loading';
  const glowId = `cmd-glow-${slug}`;
  return (
    <div className="gv1-cmd-art">
      <div className="gv1-cmd-art-inner">
        {src && status !== 'error' && (
          <img
            key={`${slug}-${src}`}
            src={src}
            alt={name}
            className={`gv1-cmd-art-img${status === 'loaded' ? ' gv1-loaded' : ''}`}
            onLoad={() => setLoadedSrc(src)}
            onError={() => {
              setFailedSrc(src);
              cardCache.imageFailed(name);
            }}
            draggable={false}
          />
        )}
        {status !== 'loaded' && (
          <div className="gv1-cmd-art-fallback">
            <svg viewBox="0 0 300 420" width="100%" height="100%" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
              <defs>
                <radialGradient id={glowId} cx="50%" cy="40%" r="70%">
                  <stop offset="0%" stopColor="rgba(124,200,146,0.18)" />
                  <stop offset="60%" stopColor="rgba(124,200,146,0.04)" />
                  <stop offset="100%" stopColor="rgba(124,200,146,0)" />
                </radialGradient>
              </defs>
              <rect width="300" height="420" fill={`url(#${glowId})`} />
              <g transform="translate(150 180)" stroke="currentColor" fill="none">
                <circle r="120" strokeWidth="0.6" opacity="0.2" />
                <circle r="90" strokeWidth="0.5" opacity="0.3" />
                <circle r="60" strokeWidth="0.6" opacity="0.5" />
                <circle r="30" strokeWidth="0.5" opacity="0.4" />
                <path d="M0 -100 L60 0 L0 100 L-60 0 Z" strokeWidth="1" />
                <path d="M-85 -85 L85 85 M85 -85 L-85 85" strokeWidth="0.3" opacity="0.3" />
                <circle r="3" fill="currentColor" opacity="0.8" />
              </g>
              <text
                x="150"
                y="395"
                textAnchor="middle"
                fontSize="8"
                fill="currentColor"
                fontFamily="JetBrains Mono, monospace"
                opacity="0.5"
                letterSpacing="2"
              >
                {status === 'loading' ? '◆ SCRYING SCRYFALL ◆' : '◇ FRAME UNAVAILABLE ◇'}
              </text>
            </svg>
          </div>
        )}
      </div>
      <div className="gv1-cmd-art-corners">
        <span></span><span></span><span></span><span></span>
      </div>
      <div className="gv1-cmd-art-caption">
        <span className="gv1-mono-xs gv1-dim">
          ◇ scryfall.com · art_crop
        </span>
      </div>
    </div>
  );
}
