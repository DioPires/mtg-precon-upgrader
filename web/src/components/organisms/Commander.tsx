// Port of gv1-chrome.jsx GV1Commander (lines 290–358).

import { GV1CommanderArt } from '../molecules/GV1CommanderArt';
import { GV1ManaPips } from '../atoms/GV1ManaPips';
import type { DeckFull } from '../../data/types';

interface CommanderProps {
  deck: DeckFull;
}

export function Commander({ deck }: CommanderProps) {
  const hasPartner = !!deck.partner;
  return (
    <section className="gv1-commander">
      <div className={'gv1-cmd-grid' + (hasPartner ? ' gv1-cmd-grid-partner' : '')}>
        <div className={'gv1-cmd-art-stack' + (hasPartner ? ' gv1-cmd-art-stack-dual' : '')}>
          <GV1CommanderArt name={deck.commander} slug={deck.slug} />
          {hasPartner && (
            <GV1CommanderArt name={deck.partner!} slug={`${deck.slug}-partner`} />
          )}
        </div>

        <div className="gv1-cmd-body">
          <div className="gv1-cmd-eyebrow">
            <span className="gv1-mono-xs gv1-rune">
              ◆ TOMUS №{String(deck.idx).padStart(2, '0')}
            </span>
            <span className="gv1-mono-xs gv1-dim">· NOW SCRYING ·</span>
            <span className="gv1-mono-xs gv1-dim">BRACKET {deck.bracket}</span>
          </div>

          <h1 className="gv1-cmd-deckname">{deck.deckName}</h1>

          <div className="gv1-cmd-commander-row">
            <GV1ManaPips colors={deck.colors} />
            <span className="gv1-cmd-commander-name" data-card-name={deck.commander}>
              {deck.commander}
            </span>
            {hasPartner && (
              <>
                <span className="gv1-cmd-commander-amp" aria-hidden="true">+</span>
                <span className="gv1-cmd-commander-name" data-card-name={deck.partner}>
                  {deck.partner}
                </span>
              </>
            )}
            <span className="gv1-mono-xs gv1-dim">· {deck.type}</span>
          </div>

          {deck.flavor && <p className="gv1-cmd-flavor">{deck.flavor}</p>}

          <div className="gv1-cmd-oracle">
            <div className="gv1-mono-xs gv1-dim gv1-cmd-label">DOSSIER</div>
            <div className="gv1-cmd-oracle-body">
              {deck.oracle.map((line, i) => (
                <p key={i}>{line}</p>
              ))}
            </div>
          </div>

          <div className="gv1-cmd-stats">
            <div className="gv1-cmd-stat">
              <div className="gv1-mono-xs gv1-dim">BRACKET</div>
              <div className="gv1-serif-lg">{deck.bracket}</div>
            </div>
            <div className="gv1-cmd-stat">
              <div className="gv1-mono-xs gv1-dim">BUDGET</div>
              <div className="gv1-serif-lg gv1-rune">{deck.price}</div>
            </div>
            {deck.composition && (
              <div className="gv1-cmd-stat">
                <div className="gv1-mono-xs gv1-dim">AVG CMC</div>
                <div className="gv1-serif-lg">{deck.composition.avgCmc}</div>
              </div>
            )}
            {deck.composition && (
              <div className="gv1-cmd-stat">
                <div className="gv1-mono-xs gv1-dim">LANDS</div>
                <div className="gv1-serif-lg">{deck.composition.lands}</div>
              </div>
            )}
            {deck.health && (
              <div className="gv1-cmd-stat">
                <div className="gv1-mono-xs gv1-dim">HEALTH</div>
                <div className="gv1-serif-lg">
                  {Math.round(deck.health.score)}
                  <span className="gv1-dim gv1-serif-sm"> / 100 · {deck.health.grade}</span>
                </div>
              </div>
            )}
          </div>

          {deck.strategy && (
            <div className="gv1-cmd-strat">
              <div className="gv1-mono-xs gv1-dim gv1-cmd-label">STRATEGY · IN THE DECK</div>
              <p>{deck.strategy}</p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
