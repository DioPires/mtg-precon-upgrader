// Port of design_handoff_grimoire/prototype/gv1-scrying.jsx (GV1Scrying).
//
// Three sub-sections wrapped in one organism:
//   § VIII.A  HandSimulator   — London mulligan flow, 5-badge assessment.
//   § VIII.B  SwapAnalyzer    — cut/add picker, 7-category live delta panel.
//   § VIII.C  SimulationBaseline — KPIs, mana curve, land histogram, mulligan stats.
//
// Pure shuffle/mulligan/delta math lives in `web/src/lib/scrying.ts` (testable).
// Card metadata via `useCard` (Scryfall cache); decklist-wide stats read
// `cardCache.get` directly without subscribing.

import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { cardCache, type CardEntry } from '../../data/cardCache';
import { isGameChanger } from '../../data/gameChangers';
import { useCard } from '../../hooks/useCard';
import { Glyph, GlyphText } from '../atoms/Glyph';
import {
  bottomCountFor,
  computeSwapDelta,
  countLandsInHand,
  fmtManaCost,
  keptHandSize,
  shuffleArr,
  type DerivedType,
  type SwapDelta,
  type SynergyLike,
} from '../../lib/scrying';
import type {
  DeckFull,
  RawDecklistCard,
  RawSimManaTurn,
  RawSimulation,
} from '../../data/types';

const SCRY_COLOR_NAMES: Record<string, string> = {
  W: 'White',
  U: 'Blue',
  B: 'Black',
  R: 'Red',
  G: 'Green',
  C: 'Colorless',
};

// A screen reader hears "to" for each → of the swap delta, also in the gcDetail
// strings of lib/scrying.ts (DEC-1190).
const ARROW_TO = { '→': 'to' } as const;

function deriveTypeShort(typeLine: string | undefined, fallback: string | undefined): string {
  const tl = (typeLine || fallback || '').toLowerCase();
  if (tl.includes('land')) return 'Land';
  if (tl.includes('creature')) return 'Creature';
  if (tl.includes('planeswalker')) return 'Planeswalker';
  if (tl.includes('artifact')) return 'Artifact';
  if (tl.includes('enchantment')) return 'Enchantment';
  if (tl.includes('instant')) return 'Instant';
  if (tl.includes('sorcery')) return 'Sorcery';
  return fallback || 'Other';
}

/* ============================================================
 * § VIII.A  HAND SIMULATOR
 * ──────────────────────────────────────────────────────────── */

interface HandSimCardProps {
  card: RawDecklistCard;
  selectable: boolean;
  idx: number;
  onSelect: (idx: number) => void;
}

function HandSimCard({ card, selectable, idx, onSelect }: HandSimCardProps) {
  const meta = useCard(card.name);
  const cmc = meta?.cmc != null ? Math.floor(meta.cmc) : null;
  const typeShort = deriveTypeShort(meta?.type_line, card.type);
  const img = meta?.image_normal || meta?.image_small || '';

  const inner = (
    <>
      <div className={'gv1-scry-card-img' + (img ? '' : ' is-loading')}>
        {img ? <img src={img} alt={card.name} loading="eager" /> : null}
      </div>
      <div className="gv1-scry-card-meta">
        <span>{typeShort}</span>
        <span className="gv1-scry-cmc">{cmc != null ? cmc : '—'}</span>
      </div>
      <div className="gv1-scry-card-name">{card.name}</div>
    </>
  );

  if (selectable) {
    return (
      <button
        type="button"
        className="gv1-scry-card gv1-scry-card-selectable"
        onClick={() => onSelect(idx)}
        data-card-name={card.name}
        aria-label={'Bottom ' + card.name}
      >
        {inner}
      </button>
    );
  }
  return (
    <li className="gv1-scry-card" data-card-name={card.name}>
      {inner}
    </li>
  );
}

type HandPhase = 'empty' | 'drawn' | 'bottoming' | 'kept';

interface AssessCell {
  label: string;
  value: string;
  detail?: string;
  rating: 'good' | 'fair' | 'poor' | 'info';
}

interface HandSimulatorProps {
  deck: DeckFull;
  onLandsChange: (lands: number | null) => void;
}

function HandSimulator({ deck, onLandsChange }: HandSimulatorProps) {
  // Physical copies (99 for prod decks) — basics with quantity>1 must be
  // represented N times in the shuffle pool. See DEC-176.
  const decklist = deck.physicalDecklist;
  const sim = deck.sim;

  const [phase, setPhase] = useState<HandPhase>('empty');
  const [hand, setHand] = useState<RawDecklistCard[]>([]);
  const [mulligans, setMulligans] = useState(0);
  const [bottomed, setBottomed] = useState<RawDecklistCard[]>([]);

  // Reset on deck switch.
  useEffect(() => {
    setPhase('empty');
    setHand([]);
    setMulligans(0);
    setBottomed([]);
    onLandsChange(null);
  }, [deck.slug, onLandsChange]);

  // Surface current hand-land-count to the parent so the histogram can mark it.
  useEffect(() => {
    if (phase === 'drawn' || phase === 'kept') {
      onLandsChange(countLandsInHand(hand, (n) => cardCache.get(n)));
    } else {
      onLandsChange(null);
    }
  }, [hand, phase, onLandsChange]);

  function draw() {
    if (!decklist.length) return;
    const shuf = shuffleArr(decklist);
    setHand(shuf.slice(0, 7));
    setMulligans(0);
    setBottomed([]);
    setPhase('drawn');
    // Pre-warm Scryfall cache for everything we just drew.
    shuf.slice(0, 7).forEach((c) => cardCache.enqueue(c.name));
  }

  function mulligan() {
    if (!decklist.length) return;
    const next = mulligans + 1;
    const shuf = shuffleArr(decklist);
    const newHand = shuf.slice(0, 7);
    const numToBottom = bottomCountFor(next);
    setMulligans(next);
    setBottomed([]);
    if (numToBottom >= 7) {
      setHand([]);
      setPhase('kept');
    } else if (numToBottom > 0) {
      setHand(newHand);
      setPhase('bottoming');
    } else {
      setHand(newHand);
      setPhase('drawn');
    }
    newHand.forEach((c) => cardCache.enqueue(c.name));
  }

  function bottomCard(idx: number) {
    if (phase !== 'bottoming') return;
    const card = hand[idx];
    const newHand = hand.filter((_, i) => i !== idx);
    const newBottom = [...bottomed, card];
    const need = bottomCountFor(mulligans);
    setHand(newHand);
    setBottomed(newBottom);
    if (newBottom.length >= need) setPhase('kept');
  }

  function keep() {
    setPhase('kept');
  }

  const phaseLabel =
    phase === 'empty'
      ? 'awaiting draw'
      : phase === 'drawn'
        ? 'opening hand drawn — keep or mulligan'
        : phase === 'bottoming'
          ? `bottom ${bottomCountFor(mulligans) - bottomed.length} more`
          : `kept · ${mulligans} mulligan${mulligans !== 1 ? 's' : ''}`;

  const assessment = useMemo<AssessCell[] | null>(() => {
    if (!hand.length) return null;
    if (phase !== 'drawn' && phase !== 'kept') return null;

    let lands = 0;
    let ramp = 0;
    let castableT3 = 0;
    let totalNonLand = 0;
    hand.forEach((card) => {
      const meta = cardCache.get(card.name);
      if (!meta) return;
      const tl = (meta.type_line || card.type || '').toLowerCase();
      if (tl.includes('land')) {
        lands++;
        return;
      }
      totalNonLand++;
      if (meta.cmc != null && meta.cmc <= 3) castableT3++;
      if (meta.cmc != null && meta.cmc <= 2 && (tl.includes('artifact') || tl.includes('creature'))) {
        ramp++;
      }
    });

    const out: AssessCell[] = [];
    out.push({
      label: 'Lands',
      value: `${lands} of 7`,
      rating: lands >= 2 && lands <= 4 ? 'good' : lands === 1 || lands === 5 ? 'fair' : 'poor',
    });
    out.push({
      label: 'Castable by T3',
      value: `${castableT3} / ${totalNonLand}`,
      rating: castableT3 >= 2 ? 'good' : castableT3 >= 1 ? 'fair' : 'poor',
    });
    if (ramp > 0) {
      out.push({
        label: 'Ramp / rocks',
        value: `${ramp} piece${ramp > 1 ? 's' : ''}`,
        detail: 'low-MV heuristic',
        rating: ramp >= 2 ? 'good' : 'fair',
      });
    }

    if (sim?.commanderTiming?.byTurn && sim.commanderTiming.cmc != null) {
      const cmdCmc = sim.commanderTiming.cmc;
      const cmdTurn = Math.max(1, cmdCmc - ramp);
      const pct = sim.commanderTiming.byTurn[String(cmdTurn)] ?? null;
      out.push({
        label: 'Commander on curve',
        value: `~T${cmdTurn}`,
        detail: pct != null ? `${pct.toFixed(0)}% of sims by T${cmdTurn}` : undefined,
        rating: cmdTurn <= cmdCmc ? 'good' : cmdTurn <= cmdCmc + 1 ? 'fair' : 'poor',
      });
    }

    if (sim?.openingHand?.landDistribution) {
      const pct = sim.openingHand.landDistribution[String(lands)];
      if (pct != null) {
        out.push({
          label: 'Land odds',
          value: `${pct.toFixed(1)}%`,
          detail: `of ${(sim.metadata?.numGames ?? 0).toLocaleString()} hands have ${lands} land${lands !== 1 ? 's' : ''}`,
          rating: 'info',
        });
      }
    }
    return out;
  }, [hand, phase, sim]);

  return (
    <section className="gv1-section">
      <div className="gv1-section-head">
        <span className="gv1-mono-xs gv1-dim">VIII · A</span>
        <h3 className="gv1-serif-xl">Hand Simulator</h3>
        <span className="gv1-mono-xs gv1-dim">· {decklist.length} card pool · London mulligan</span>
      </div>

      <div className="gv1-scry-handsim">
        <div className="gv1-scry-controls">
          {phase === 'empty' && (
            <button type="button" className="gv1-scry-btn gv1-scry-btn-primary" onClick={draw}>
              Draw 7
            </button>
          )}
          {phase === 'drawn' && (
            <>
              <button type="button" className="gv1-scry-btn gv1-scry-btn-primary" onClick={keep}>
                Keep
              </button>
              <button type="button" className="gv1-scry-btn" onClick={mulligan}>
                Mulligan
              </button>
            </>
          )}
          {phase === 'bottoming' && (
            <span className="gv1-scry-instruction">
              Click {bottomCountFor(mulligans) - bottomed.length} card
              {bottomCountFor(mulligans) - bottomed.length !== 1 ? 's' : ''} to put on bottom
            </span>
          )}
          {phase === 'kept' && (
            <>
              <button type="button" className="gv1-scry-btn gv1-scry-btn-primary" onClick={draw}>
                New hand
              </button>
              {mulligans > 0 && (
                <span className="gv1-mono-xs gv1-dim">
                  Kept {keptHandSize(mulligans)} ·{' '}
                  {mulligans === 1 ? 'free mulligan' : `${mulligans} mulligans`}
                </span>
              )}
            </>
          )}
          <span className="gv1-scry-phase" data-phase={phase}>
            <span className="gv1-scry-phase-dot" aria-hidden="true" />
            <span>{phaseLabel}</span>
          </span>
        </div>

        {phase === 'empty' && (
          <div className="gv1-scry-empty">
            Draw an opening hand to evaluate it against{' '}
            {(sim?.metadata?.numGames ?? 0).toLocaleString()} simulated games.
          </div>
        )}

        {phase !== 'empty' && hand.length > 0 && (
          <ul className="gv1-scry-hand" role="list">
            {hand.map((card, i) => (
              <HandSimCard
                key={card.name + ':' + i}
                card={card}
                idx={i}
                selectable={phase === 'bottoming'}
                onSelect={bottomCard}
              />
            ))}
          </ul>
        )}

        {bottomed.length > 0 && (
          <div className="gv1-scry-bottomed-row">
            <span className="gv1-scry-bottomed-label">Bottomed</span>
            {bottomed.map((c, i) => (
              <span key={i} className="gv1-scry-bottomed-name" data-card-name={c.name}>
                {c.name}
              </span>
            ))}
          </div>
        )}

        {phase === 'kept' && hand.length === 0 && (
          <div className="gv1-scry-empty">Mulliganed to zero. Try a new hand.</div>
        )}

        {assessment && assessment.length > 0 && (
          <div className="gv1-scry-assess" role="list">
            {assessment.map((cell, i) => (
              <div
                key={i}
                className="gv1-scry-assess-cell"
                data-rating={cell.rating}
                role="listitem"
              >
                <div className="gv1-scry-assess-label">{cell.label}</div>
                <div className="gv1-scry-assess-value">{cell.value}</div>
                {cell.detail && <div className="gv1-scry-assess-detail">{cell.detail}</div>}
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

/* ============================================================
 * § VIII.B  SWAP ANALYZER
 * ──────────────────────────────────────────────────────────── */

interface SwapCardDisplayProps {
  card: { name: string; type?: string };
  onClear: () => void;
  isAdd?: boolean;
}

function SwapCardDisplay({ card, onClear, isAdd }: SwapCardDisplayProps) {
  const meta = useCard(card.name);
  const img = meta?.image_normal || meta?.image_small || '';
  const tl = meta?.type_line || card.type || '';
  const mc = meta?.mana_cost || '';
  return (
    <div className="gv1-scry-swap-card" data-card-name={card.name}>
      <div className="gv1-scry-swap-card-img">
        {img ? <img src={img} alt={card.name} loading="eager" /> : null}
      </div>
      <div className="gv1-scry-swap-card-info">
        <span className="gv1-scry-swap-card-name">{card.name}</span>
        <span className="gv1-scry-swap-card-type">{tl}</span>
        {mc && <span className="gv1-scry-swap-card-mana">{fmtManaCost(mc)}</span>}
      </div>
      <button
        type="button"
        className="gv1-scry-swap-clear"
        onClick={onClear}
        aria-label={(isAdd ? 'Clear add' : 'Clear cut') + ': ' + card.name}
      >
        ×
      </button>
    </div>
  );
}

interface SwapAnalyzerProps {
  deck: DeckFull;
  /** All decks from useAllDecks — used as the cross-deck search pool for adds. */
  allDecks: DeckFull[];
}

interface SearchResult {
  name: string;
  type_line: string;
  cmc: number | undefined;
  mana_cost: string;
}

function SwapAnalyzer({ deck, allDecks }: SwapAnalyzerProps) {
  const decklist = deck.rawDecklist;
  const synergies: SynergyLike[] = deck.synergies;
  const gameChangers = deck.gameChangers;

  const [cutCard, setCutCard] = useState<RawDecklistCard | null>(null);
  const [addCard, setAddCard] = useState<{ name: string; type?: string } | null>(null);
  const [searchQ, setSearchQ] = useState('');
  const searchRef = useRef<HTMLInputElement>(null);

  // Subscribe to the chosen cards so the delta refreshes once Scryfall metadata loads.
  const cutMeta = useCard(cutCard?.name);
  const addMeta = useCard(addCard?.name);

  // Reset on deck switch.
  useEffect(() => {
    setCutCard(null);
    setAddCard(null);
    setSearchQ('');
  }, [deck.slug]);

  const cutOptions = useMemo<Record<string, string[]>>(() => {
    const groups: Record<string, string[]> = {};
    decklist.forEach((c) => {
      const t = c.type || 'Other';
      (groups[t] ||= []).push(c.name);
    });
    Object.keys(groups).forEach((k) => groups[k].sort());
    return groups;
  }, [decklist]);

  // Bump on a slow tick while searching so newly-loaded cache entries surface in results.
  const [, bumpSearch] = useState(0);
  useEffect(() => {
    if (!searchQ || searchQ.length < 2) return;
    const t = setInterval(() => bumpSearch((n) => n + 1), 700);
    return () => clearInterval(t);
  }, [searchQ]);

  const searchResults = useMemo<SearchResult[]>(() => {
    const q = searchQ.trim().toLowerCase();
    if (q.length < 2) return [];
    const inDeck = new Set(decklist.map((c) => c.name.toLowerCase()));
    const results: SearchResult[] = [];
    const seen = new Set<string>();
    const pool = new Set<string>();
    allDecks.forEach((d) => d.rawDecklist.forEach((c) => pool.add(c.name)));
    pool.forEach((name) => {
      if (results.length >= 30) return;
      const lower = name.toLowerCase();
      if (seen.has(lower)) return;
      if (inDeck.has(lower)) return;
      if (!lower.includes(q)) return;
      seen.add(lower);
      const meta = cardCache.get(name);
      results.push({
        name,
        type_line: meta?.type_line || '',
        cmc: meta?.cmc,
        mana_cost: meta?.mana_cost || '',
      });
    });
    return results.slice(0, 30);
  }, [searchQ, deck.slug, allDecks]); // eslint-disable-line react-hooks/exhaustive-deps

  function selectCut(name: string) {
    const card = decklist.find((c) => c.name === name);
    if (card) {
      setCutCard(card);
      cardCache.enqueue(card.name);
    }
  }
  function selectAdd(name: string) {
    setAddCard({ name });
    setSearchQ('');
    cardCache.enqueue(name);
  }

  const delta = useMemo<SwapDelta | null>(() => {
    if (!cutCard || !addCard) return null;
    return computeSwapDelta({
      cutCard: { name: cutCard.name, type: cutCard.type },
      addCard: { name: addCard.name, type: addCard.type },
      cutMeta: cutMeta ?? null,
      addMeta: addMeta ?? null,
      decklist,
      metaFor: (n: string): Partial<CardEntry> | null => cardCache.get(n),
      synergies,
      isGameChanger,
      gameChangers,
    });
  }, [cutCard, addCard, cutMeta, addMeta, decklist, synergies, gameChangers]);

  return (
    <section className="gv1-section">
      <div className="gv1-section-head">
        <span className="gv1-mono-xs gv1-dim">VIII · B</span>
        <h3 className="gv1-serif-xl">Swap Analyzer</h3>
        <span className="gv1-mono-xs gv1-dim">· what changes if you cut X for Y?</span>
      </div>

      <div className="gv1-scry-swap">
        {/* CUT slot */}
        <div className="gv1-scry-swap-side">
          <span className="gv1-scry-swap-label">Cut</span>
          <div className={'gv1-scry-swap-slot' + (cutCard ? ' is-filled' : '')}>
            {cutCard ? (
              <SwapCardDisplay card={cutCard} onClear={() => setCutCard(null)} />
            ) : (
              <div className="gv1-scry-swap-picker">
                <select
                  className="gv1-scry-select"
                  defaultValue=""
                  aria-label="Select a card to cut"
                  onChange={(e) => {
                    selectCut(e.target.value);
                    e.target.value = '';
                  }}
                >
                  <option value="" disabled>
                    Select a card to cut…
                  </option>
                  {Object.keys(cutOptions)
                    .sort()
                    .map((type) => (
                      <optgroup key={type} label={type}>
                        {cutOptions[type].map((name) => (
                          <option key={name} value={name}>
                            {name}
                          </option>
                        ))}
                      </optgroup>
                    ))}
                </select>
                <span className="gv1-scry-search-hint">
                  Choose any card from the {deck.physicalDecklist.length}-card list
                </span>
              </div>
            )}
          </div>
        </div>

        <div className="gv1-scry-swap-arrow" aria-hidden="true">
          →
        </div>

        {/* ADD slot */}
        <div className="gv1-scry-swap-side">
          <span className="gv1-scry-swap-label">Add</span>
          <div className={'gv1-scry-swap-slot' + (addCard ? ' is-filled' : '')}>
            {addCard ? (
              <SwapCardDisplay card={addCard} onClear={() => setAddCard(null)} isAdd />
            ) : (
              <div className="gv1-scry-swap-picker">
                <input
                  ref={searchRef}
                  type="text"
                  className="gv1-scry-search"
                  placeholder={`Search cards across all ${allDecks.length} decks…`}
                  aria-label="Search for a card to add"
                  value={searchQ}
                  onChange={(e) => setSearchQ(e.target.value)}
                />
                <span className="gv1-scry-search-hint">
                  2+ characters · live cache · Scryfall metadata where loaded
                </span>
                {searchResults.length > 0 && (
                  <div className="gv1-scry-search-results" role="listbox">
                    {searchResults.map((r) => {
                      const cmcStr = r.cmc != null ? ` · MV ${Math.floor(r.cmc)}` : '';
                      return (
                        <button
                          key={r.name}
                          type="button"
                          className="gv1-scry-search-result"
                          role="option"
                          aria-selected="false"
                          onClick={() => selectAdd(r.name)}
                        >
                          <span>{r.name}</span>
                          <span className="gv1-scry-search-result-type">
                            {r.type_line || '—'}
                            {cmcStr}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                )}
                {searchQ.length >= 2 && searchResults.length === 0 && (
                  <div className="gv1-scry-search-no-results">
                    No cards in the loaded pool match "{searchQ}". Hover any card name elsewhere
                    in the app to fetch it into the cache.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {delta ? <DeltaPanel delta={delta} /> : (
        <div className="gv1-scry-empty">
          Pick a card to cut and a card to add to see the impact on mana value, color balance,
          lands, and synergies.
        </div>
      )}
    </section>
  );
}

interface DeltaPanelProps {
  delta: SwapDelta;
}

function DeltaPanel({ delta }: DeltaPanelProps) {
  const cmcDir =
    delta.cmcChange == null
      ? 'neutral'
      : delta.cmcChange === 0
        ? 'neutral'
        : delta.cmcChange > 0
          ? 'increase'
          : 'decrease';
  const avgDir =
    delta.avgCmcChange == null
      ? 'neutral'
      : Math.abs(delta.avgCmcChange) < 0.005
        ? 'neutral'
        : delta.avgCmcChange > 0
          ? 'increase'
          : 'decrease';

  return (
    <div className="gv1-scry-delta">
      <div className="gv1-scry-delta-head">
        <h4 className="gv1-scry-delta-title">Δ Impact</h4>
        <span className="gv1-mono-xs gv1-dim">computed against current decklist</span>
      </div>

      {delta.cmcChange != null && (
        <div className="gv1-scry-delta-row">
          <span className="gv1-scry-delta-label">Mana value</span>
          <div className="gv1-scry-delta-values">
            <span className="gv1-scry-delta-detail">
              <GlyphText text={`${delta.cutCmc} → ${delta.addCmc}`} words={ARROW_TO} />
            </span>
            <span className="gv1-scry-delta-change" data-dir={cmcDir}>
              {delta.cmcChange > 0 ? '+' : ''}
              {delta.cmcChange}
            </span>
          </div>
        </div>
      )}

      {delta.avgCmcChange != null && (
        <div className="gv1-scry-delta-row">
          <span className="gv1-scry-delta-label">Avg mana value</span>
          <div className="gv1-scry-delta-values">
            <span className="gv1-scry-delta-detail">
              <GlyphText
                text={`${delta.avgCmcBefore.toFixed(2)} → ${delta.avgCmcAfter.toFixed(2)}`}
                words={ARROW_TO}
              />
            </span>
            <span className="gv1-scry-delta-change" data-dir={avgDir}>
              {delta.avgCmcChange > 0 ? '+' : ''}
              {delta.avgCmcChange.toFixed(2)}
            </span>
          </div>
        </div>
      )}

      {delta.landsBefore !== delta.landsAfter && (
        <div className="gv1-scry-delta-row">
          <span className="gv1-scry-delta-label">Lands</span>
          <div className="gv1-scry-delta-values">
            <span className="gv1-scry-delta-detail">
              <GlyphText text={`${delta.landsBefore} → ${delta.landsAfter}`} words={ARROW_TO} />
            </span>
            <span
              className="gv1-scry-delta-change"
              data-dir={delta.landsAfter > delta.landsBefore ? 'info' : 'warning'}
            >
              {delta.landsAfter > delta.landsBefore ? '+' : ''}
              {delta.landsAfter - delta.landsBefore}
            </span>
          </div>
        </div>
      )}

      {Object.keys(delta.colorDelta).length > 0 && (
        <div className="gv1-scry-delta-row">
          <span className="gv1-scry-delta-label">Color pips</span>
          <div className="gv1-scry-delta-values">
            {Object.entries(delta.colorDelta).map(([c, n]) => (
              <span key={c} className="gv1-scry-color-pip" data-c={c}>
                {n > 0 ? '+' : ''}
                {n} {SCRY_COLOR_NAMES[c] || c}
              </span>
            ))}
          </div>
        </div>
      )}

      {delta.typeChanged && (
        <div className="gv1-scry-delta-row">
          <span className="gv1-scry-delta-label">Type</span>
          <div className="gv1-scry-delta-values">
            <span className="gv1-scry-delta-detail">
              <GlyphText text={`${delta.cutType} → ${delta.addType}`} words={ARROW_TO} />
            </span>
          </div>
        </div>
      )}

      {delta.gcKind && (
        <div className="gv1-scry-delta-row">
          <span className="gv1-scry-delta-label">Game Changers</span>
          <div className="gv1-scry-delta-values">
            <span className="gv1-scry-delta-detail">
              {delta.gcDetail && <GlyphText text={delta.gcDetail} words={ARROW_TO} />}
            </span>
            <span
              className="gv1-scry-delta-change"
              data-dir={
                delta.gcKind === 'adding' ? 'warning' : delta.gcKind === 'removing' ? 'info' : 'neutral'
              }
            >
              {/* The row label names the Game Changers; the detail says "GC for GC — count unchanged" (DEC-1190). */}
              {delta.gcKind === 'adding' ? (
                <>
                  <Glyph>★ </Glyph>+1
                </>
              ) : delta.gcKind === 'removing' ? (
                <>
                  <Glyph>★ </Glyph>−1
                </>
              ) : (
                <Glyph>★ ↔</Glyph>
              )}
            </span>
          </div>
        </div>
      )}

      {delta.synergiesBroken.length > 0 && (
        <div className="gv1-scry-delta-row">
          <span className="gv1-scry-delta-label">Synergies broken</span>
          <div className="gv1-scry-delta-values">
            <div className="gv1-scry-synergy-list">
              {delta.synergiesBroken.map((s, i) => (
                <div key={i} className="gv1-scry-synergy-item" data-kind="broken">
                  <span className="gv1-scry-synergy-icon" aria-hidden="true">⚠</span>
                  <div>
                    <span className="gv1-scry-synergy-title">{s.title}</span>
                    <span className="gv1-scry-synergy-cards">{(s.cards || []).join(' · ')}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {delta.synergiesKept.length > 0 && (
        <div className="gv1-scry-delta-row">
          <span className="gv1-scry-delta-label">Synergies enabled</span>
          <div className="gv1-scry-delta-values">
            <div className="gv1-scry-synergy-list">
              {delta.synergiesKept.map((s, i) => (
                <div key={i} className="gv1-scry-synergy-item" data-kind="kept">
                  <span className="gv1-scry-synergy-icon" aria-hidden="true">✓</span>
                  <div>
                    <span className="gv1-scry-synergy-title">{s.title}</span>
                    <span className="gv1-scry-synergy-cards">{(s.cards || []).join(' · ')}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ============================================================
 * § VIII.C  SIMULATION BASELINE
 * ──────────────────────────────────────────────────────────── */

interface ManaCurveChartProps {
  manaByTurn: Record<string, RawSimManaTurn> | undefined;
  numTurns: number;
}

function ManaCurveChart({ manaByTurn, numTurns }: ManaCurveChartProps) {
  if (!manaByTurn) return null;
  const turns: Array<{ t: number } & RawSimManaTurn> = [];
  for (let t = 1; t <= numTurns; t++) {
    const k = String(t);
    if (manaByTurn[k]) turns.push({ t, ...manaByTurn[k] });
  }
  if (!turns.length) return null;

  const W = 480;
  const H = 180;
  const PAD_L = 32;
  const PAD_R = 12;
  const PAD_T = 12;
  const PAD_B = 28;
  const innerW = W - PAD_L - PAD_R;
  const innerH = H - PAD_T - PAD_B;

  const maxY = Math.ceil(Math.max(...turns.map((t) => t.p75)) + 1);
  const minY = 0;
  const x = (t: number): number => PAD_L + (innerW * (t - 1)) / (numTurns - 1);
  const y = (v: number): number => PAD_T + innerH - ((v - minY) / (maxY - minY)) * innerH;

  const upper = turns.map((t) => `${x(t.t)},${y(t.p75)}`).join(' L ');
  const lower = turns
    .slice()
    .reverse()
    .map((t) => `${x(t.t)},${y(t.p25)}`)
    .join(' L ');
  const bandPath = `M ${upper} L ${lower} Z`;
  const linePath = 'M ' + turns.map((t) => `${x(t.t)},${y(t.median)}`).join(' L ');
  const yTicks = [0, Math.floor(maxY / 2), maxY];

  return (
    <svg
      className="gv1-scry-mana-chart"
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label="Median mana available by turn with P25–P75 band"
    >
      {yTicks.map((v, i) => (
        <g key={i}>
          <line
            x1={PAD_L}
            x2={W - PAD_R}
            y1={y(v)}
            y2={y(v)}
            className="gv1-scry-mana-axis"
            strokeDasharray="2 4"
          />
          <text className="gv1-scry-mana-tick" x={PAD_L - 8} y={y(v) + 3} textAnchor="end">
            {v}
          </text>
        </g>
      ))}
      {turns.map((t, i) => (
        <text key={i} className="gv1-scry-mana-tick" x={x(t.t)} y={H - 10} textAnchor="middle">
          T{t.t}
        </text>
      ))}
      <path d={bandPath} className="gv1-scry-mana-band" />
      <path d={linePath} className="gv1-scry-mana-line" />
      {turns.map((t, i) => (
        <circle key={i} cx={x(t.t)} cy={y(t.median)} r="2.5" className="gv1-scry-mana-dot" />
      ))}
    </svg>
  );
}

interface LandDistHistogramProps {
  landDist: Record<string, number> | undefined;
  currentLands: number | null;
}

function LandDistHistogram({ landDist, currentLands }: LandDistHistogramProps) {
  if (!landDist) return null;
  const entries = Object.keys(landDist)
    .map((k) => ({ n: Number(k), pct: landDist[k] }))
    .sort((a, b) => a.n - b.n);
  const max = Math.max(0.01, ...entries.map((e) => e.pct));

  return (
    <div
      className="gv1-scry-hist"
      role="img"
      aria-label="Opening hand land distribution histogram"
    >
      {entries.map((e) => (
        <div
          key={e.n}
          className="gv1-scry-hist-col"
          data-current={currentLands === e.n ? 'true' : 'false'}
          title={`${e.pct.toFixed(1)}% of hands have ${e.n} land${e.n !== 1 ? 's' : ''}`}
        >
          <div className="gv1-scry-hist-bar-wrap">
            <div className="gv1-scry-hist-bar" style={{ height: `${(e.pct / max) * 100}%` }} />
          </div>
          <div className="gv1-scry-hist-label">
            <span className="gv1-scry-hist-label-n">{e.n}</span>
            <span className="gv1-scry-hist-pct">{e.pct.toFixed(1)}%</span>
          </div>
        </div>
      ))}
    </div>
  );
}

interface SimulationBaselineProps {
  sim: RawSimulation | null;
  currentLands: number | null;
}

function SimulationBaseline({ sim, currentLands }: SimulationBaselineProps) {
  if (!sim) {
    return (
      <section className="gv1-section">
        <div className="gv1-section-head">
          <span className="gv1-mono-xs gv1-dim">VIII · C</span>
          <h3 className="gv1-serif-xl">Simulation Baseline</h3>
        </div>
        <div className="gv1-scry-no-sim">No simulation.json for this deck.</div>
      </section>
    );
  }

  const manaT3 = sim.manaByTurn?.['3']?.median;
  const cmdMedian = sim.commanderTiming?.medianTurn;
  const cmdName = sim.commanderTiming?.name;
  const cmdCmc = sim.commanderTiming?.cmc;
  const numTurns = sim.metadata?.numTurns ?? 10;
  const numGames = sim.metadata?.numGames ?? 0;
  const mull = sim.mulliganStats || {};

  const castableByT3 =
    sim.curveEfficiency?.castableByTurn?.['3'] ??
    sim.curveEfficiency?.byTurn?.['3'] ??
    null;

  return (
    <section className="gv1-section">
      <div className="gv1-section-head">
        <span className="gv1-mono-xs gv1-dim">VIII · C</span>
        <h3 className="gv1-serif-xl">Simulation Baseline</h3>
        <span className="gv1-mono-xs gv1-dim">
          · {numGames.toLocaleString()} games × {numTurns} turns
        </span>
      </div>

      <div className="gv1-scry-sim-grid">
        <div className="gv1-scry-sim-panel">
          <div className="gv1-scry-sim-panel-head">
            <h4 className="gv1-scry-sim-panel-title">Key indicators</h4>
            <span className="gv1-scry-sim-panel-meta">
              medians across {numGames.toLocaleString()} sims
            </span>
          </div>
          <div className="gv1-scry-kpis">
            <div className="gv1-scry-kpi">
              <span className="gv1-scry-kpi-label">Mana T3</span>
              <span className="gv1-scry-kpi-value">{manaT3 != null ? manaT3.toFixed(1) : '—'}</span>
              <span className="gv1-scry-kpi-unit">median available</span>
            </div>
            <div className="gv1-scry-kpi">
              <span className="gv1-scry-kpi-label">Castable T3</span>
              <span className="gv1-scry-kpi-value">
                {castableByT3 != null ? Math.round(castableByT3) + '%' : '—'}
              </span>
              <span className="gv1-scry-kpi-unit">spells on curve</span>
            </div>
            <div className="gv1-scry-kpi">
              <span className="gv1-scry-kpi-label">Commander</span>
              <span className="gv1-scry-kpi-value">{cmdMedian != null ? `T${cmdMedian}` : '—'}</span>
              <span className="gv1-scry-kpi-unit">{cmdName ? `${cmdName} · MV ${cmdCmc}` : '—'}</span>
            </div>
          </div>

          {(mull.keptFirst != null || mull.freeMulligan != null || mull.paidMulligan != null) && (
            <div className="gv1-scry-mulligan-stats">
              <div className="gv1-scry-mulligan-stat">
                <span className="gv1-scry-mulligan-stat-value">{(mull.keptFirst ?? 0).toFixed(1)}%</span>
                <span className="gv1-scry-mulligan-stat-label">keep first 7</span>
              </div>
              <div className="gv1-scry-mulligan-stat">
                <span className="gv1-scry-mulligan-stat-value">
                  {(mull.freeMulligan ?? 0).toFixed(1)}%
                </span>
                <span className="gv1-scry-mulligan-stat-label">free mulligan</span>
              </div>
              <div className="gv1-scry-mulligan-stat">
                <span className="gv1-scry-mulligan-stat-value">
                  {(mull.paidMulligan ?? 0).toFixed(1)}%
                </span>
                <span className="gv1-scry-mulligan-stat-label">paid mulligan</span>
              </div>
            </div>
          )}
        </div>

        <div className="gv1-scry-sim-panel">
          <div className="gv1-scry-sim-panel-head">
            <h4 className="gv1-scry-sim-panel-title">Mana available by turn</h4>
            <span className="gv1-scry-sim-panel-meta">P25 — median — P75</span>
          </div>
          <ManaCurveChart manaByTurn={sim.manaByTurn} numTurns={numTurns} />
          <div className="gv1-scry-chart-legend">
            <span>
              <span className="gv1-scry-legend-band" /> P25–P75 range
            </span>
            <span>
              <span className="gv1-scry-legend-line" /> Median
            </span>
          </div>
        </div>

        <div className="gv1-scry-sim-panel" style={{ gridColumn: '1 / -1' }}>
          <div className="gv1-scry-sim-panel-head">
            <h4 className="gv1-scry-sim-panel-title">Opening hand · land distribution</h4>
            <span className="gv1-scry-sim-panel-meta">
              {currentLands != null
                ? `your hand · ${currentLands} land${currentLands !== 1 ? 's' : ''} highlighted`
                : 'across 7-card opening hands'}
            </span>
          </div>
          <LandDistHistogram
            landDist={sim.openingHand?.landDistribution}
            currentLands={currentLands}
          />
        </div>
      </div>
    </section>
  );
}

/* ============================================================
 * SCRYING POOL — orchestrator
 * ──────────────────────────────────────────────────────────── */

export interface ScryingProps {
  deck: DeckFull;
  allDecks: DeckFull[];
}

export function Scrying({ deck, allDecks }: ScryingProps) {
  const [currentLands, setCurrentLands] = useState<number | null>(null);
  const sim = deck.sim;

  return (
    <div data-gv1-screen="scrying">
      <header className="gv1-section">
        <div className="gv1-section-head">
          <span className="gv1-rune" aria-hidden="true">§ VIII</span>
          <h2 className="gv1-section-title">The Scrying Pool</h2>
          <span className="gv1-mono-xs gv1-dim">
            · {deck.deckName} · {deck.commander}
            {deck.partner ? ` + ${deck.partner}` : ''}
            {sim?.metadata?.numGames ? ` · ${sim.metadata.numGames.toLocaleString()} simulations` : ''}
          </span>
          {deck.status === 'brewing' && (
            <span
              className="gv1-mono-xs gv1-brewing-pill"
              title="Brewing — not physically built; excluded from card-usage analysis"
            >
              BREWING
            </span>
          )}
        </div>
        <p className="gv1-scry-lede">
          Two interactive instruments, one passive baseline. The <em>Hand Simulator</em> deals from
          this deck&apos;s {deck.physicalDecklist.length}-card list and grades the result against the
          full simulation. The <em>Swap Analyzer</em> lets you weigh a single cut + add against the
          existing mana value, color balance, and known synergies. Below them, the{' '}
          <em>Simulation Baseline</em> shows the underlying numbers the assessments draw from.
        </p>
        <p className="gv1-scry-mobile-banner" role="note">
          The Scrying Pool reflows to phones, but the swap analyzer sees more at desk
          width.{' '}
          <Link to={`/deck/${deck.slug}`}>
            <Glyph>↗ </Glyph>Open the {deck.deckName} guide
          </Link>{' '}
          if you
          just need the deck overview.
        </p>
      </header>

      <HandSimulator deck={deck} onLandsChange={setCurrentLands} />
      <SwapAnalyzer deck={deck} allDecks={allDecks} />
      <SimulationBaseline sim={sim} currentLands={currentLands} />
    </div>
  );
}

// Re-export the derived type for tests/external consumers.
export type { DerivedType };
