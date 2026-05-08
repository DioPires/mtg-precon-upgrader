// Renders the deck's token outputs (e.g. Eldrazi Spawn, Servo, Saproling).
// Data is precomputed by scripts/compute_tokens.py from Scryfall `all_parts`.
// Producer names get [data-card-name] so GV1CardHoverLayer pops the real card frame.

import type { DeckToken } from '../../data/types';

interface TokensProps {
  tokens: DeckToken[];
}

export function Tokens({ tokens }: TokensProps) {
  if (!tokens || tokens.length === 0) return null;

  return (
    <section className="gv1-section gv1-tokens">
      <div className="gv1-section-head">
        <span className="gv1-rune" aria-hidden="true">§ V</span>
        <h2 className="gv1-section-title">Tokens</h2>
        <span className="gv1-mono-xs gv1-dim">
          · {tokens.length} {tokens.length === 1 ? 'token' : 'tokens'} created by this deck
        </span>
      </div>
      <div className="gv1-tokens-grid">
        {tokens.map((t, i) => {
          const hasPT =
            t.power != null && t.power !== '' && t.toughness != null && t.toughness !== '';
          return (
            <article key={(t.scryfall_id || t.name) + i} className="gv1-token-card">
              {t.image_uri ? (
                <img
                  className="gv1-token-img"
                  src={t.image_uri}
                  alt={`${t.name} token`}
                  loading="lazy"
                  draggable={false}
                />
              ) : (
                <div className="gv1-token-img gv1-token-img-stub" aria-hidden="true">
                  <span className="gv1-mono-xs gv1-dim">◇ no frame</span>
                </div>
              )}
              <div className="gv1-token-name">{t.name}</div>
              <div className="gv1-token-meta gv1-mono-xs gv1-dim">
                {t.type_line || 'Token'}
                {hasPT && (
                  <span className="gv1-token-pt">
                    {' '}· {t.power}/{t.toughness}
                  </span>
                )}
              </div>
              {t.produced_by.length > 0 && (
                <div className="gv1-token-producers gv1-mono-xs gv1-dim">
                  Created by:{' '}
                  {t.produced_by.map((p, j) => (
                    <span key={p + j}>
                      <span
                        className="gv1-token-producer"
                        data-card-name={p}
                        tabIndex={0}
                        role="button"
                      >
                        {p}
                      </span>
                      {j < t.produced_by.length - 1 ? ', ' : ''}
                    </span>
                  ))}
                </div>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
