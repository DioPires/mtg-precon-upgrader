// Grimoire v1 — Scrying Pool (real)
// ─────────────────────────────────────────────────────────────
// Real implementation of the analytics surface:
//   § VIII.A  Hand Simulator (draw / mulligan / London bottom / keep)
//   § VIII.B  Swap Analyzer (cut + add + Δ delta panel)
//   § VIII.C  Simulation Baseline (KPIs, mana curve, land histogram, mulligan stats)
//
// Data sources (per deck):
//   deck.rawDecklist  — array of { name, type, role } (no CMC here; we lazy-fetch via GV1Cards)
//   deck.sim          — full simulation.json (manaByTurn, openingHand, mulliganStats, commanderTiming, ...)
//   deck.engine.combos / deck.combos / deck.synergies — for swap impact (synergy aware)
//
// Card metadata (CMC, mana_cost, type_line, image, price) is loaded lazily via
// window.GV1Cards.fetch / .subscribe / .enqueue. Until cached, we render '—'.
//
// Mobile (≤720px): hand goes 3-up, swap stacks, sim grid stacks. The original
// app dropped tooltips on mobile; we keep parity (no hover-card on touch).
// ─────────────────────────────────────────────────────────────

const { useState: useStateScry, useMemo: useMemoScry, useEffect: useEffectScry, useRef: useRefScry } = React;

/* ── Color names + simple Set helpers ─────────────────────── */
const SCRY_COLOR_NAMES = { W: 'White', U: 'Blue', B: 'Black', R: 'Red', G: 'Green', C: 'Colorless' };

// Extract colors from a Scryfall mana_cost string.
// '{2}{U}{B}' → ['U', 'B']; '{X}{R}{R}' → ['R']; '' → [].
function colorsFromManaCost(manaCost) {
  if (!manaCost) return [];
  const out = new Set();
  manaCost.replace(/\{([^}]+)\}/g, (_, sym) => {
    sym.split('/').forEach(s => {
      const u = s.toUpperCase();
      if (['W', 'U', 'B', 'R', 'G'].includes(u)) out.add(u);
    });
  });
  return [...out];
}

// Friendly mana cost render: '{2}{U}{B}' → '2·U·B'
function fmtManaCost(manaCost) {
  if (!manaCost) return '';
  const parts = [];
  manaCost.replace(/\{([^}]+)\}/g, (_, sym) => { parts.push(sym.replace('/', '/').toUpperCase()); });
  return parts.join(' · ');
}

function deriveType(typeLine, fallback) {
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

/* ── Live Scryfall hook (subscribe + enqueue) ──────────────── */
function useScryEntry(name) {
  const [, bump] = useStateScry(0);
  useEffectScry(() => {
    if (!name || !window.GV1Cards) return;
    const unsub = window.GV1Cards.subscribe(name, () => bump(n => n + 1));
    window.GV1Cards.enqueue(name);
    return unsub;
  }, [name]);
  return name ? (window.GV1Cards?.get(name) || null) : null;
}

/* ============================================================
 * § VIII.A  HAND SIMULATOR
 * ──────────────────────────────────────────────────────────── */

// Commander mulligan (London variant matched to original app):
// First mulligan is free; subsequent mulligans require putting (mulliganCount - 1) cards on bottom.
function bottomCountFor(mulligans) { return Math.max(0, mulligans - 1); }
function keptHandSize(mulligans)  { return Math.max(0, 7 - bottomCountFor(mulligans)); }

function shuffleArr(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function HandSimCard({ card, selectable, onSelect, idx }) {
  const meta = useScryEntry(card.name);
  const cmc = meta?.cmc != null ? Math.floor(meta.cmc) : null;
  const typeShort = deriveType(meta?.type_line, card.type);
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
    <li className="gv1-scry-card" data-card-name={card.name}>{inner}</li>
  );
}

function HandSimulator({ deck }) {
  const decklist = deck.rawDecklist || [];
  const sim = deck.sim || null;

  const [phase, setPhase] = useStateScry('empty'); // empty | drawn | bottoming | kept
  const [hand, setHand] = useStateScry([]);
  const [mulligans, setMulligans] = useStateScry(0);
  const [bottomed, setBottomed] = useStateScry([]);

  // Reset on deck switch.
  useEffectScry(() => {
    setPhase('empty');
    setHand([]);
    setMulligans(0);
    setBottomed([]);
  }, [deck.slug]);

  function draw() {
    if (!decklist.length) return;
    const shuf = shuffleArr(decklist);
    setHand(shuf.slice(0, 7));
    setMulligans(0);
    setBottomed([]);
    setPhase('drawn');
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
      // mulled to 0
      setHand([]);
      setPhase('kept');
    } else if (numToBottom > 0) {
      setHand(newHand);
      setPhase('bottoming');
    } else {
      setHand(newHand);
      setPhase('drawn');
    }
  }

  function bottomCard(idx) {
    if (phase !== 'bottoming') return;
    const card = hand[idx];
    const newHand = hand.filter((_, i) => i !== idx);
    const newBottom = bottomed.concat([card]);
    const need = bottomCountFor(mulligans);
    setHand(newHand);
    setBottomed(newBottom);
    if (newBottom.length >= need) setPhase('kept');
  }

  function keep() { setPhase('kept'); }

  const phaseLabel =
    phase === 'empty'     ? 'awaiting draw'
    : phase === 'drawn'    ? 'opening hand drawn — keep or mulligan'
    : phase === 'bottoming'? `bottom ${bottomCountFor(mulligans) - bottomed.length} more`
    : phase === 'kept'     ? `kept · ${mulligans} mulligan${mulligans !== 1 ? 's' : ''}`
    : '';

  // Hand assessment (only when drawn/kept). Uses Scryfall meta where available.
  const assessment = useMemoScry(() => {
    if (!hand.length) return null;
    if (phase !== 'drawn' && phase !== 'kept') return null;

    let lands = 0, ramp = 0, castableT3 = 0, totalNonLand = 0;
    hand.forEach(card => {
      const meta = window.GV1Cards?.get(card.name);
      if (!meta) return;
      const tl = (meta.type_line || card.type || '').toLowerCase();
      if (tl.includes('land')) {
        lands++;
        return;
      }
      totalNonLand++;
      if (meta.cmc != null && meta.cmc <= 3) castableT3++;
      // ramp: low-cost mana producers (rough heuristic — no oracle text from GV1Cards yet)
      if (meta.cmc <= 2 && (tl.includes('artifact') || tl.includes('creature'))) {
        // best-effort ramp detection: low MV artifact/creature
        ramp++;
      }
    });

    const out = [];
    out.push({
      label: 'Lands',
      value: `${lands} of 7`,
      rating: (lands >= 2 && lands <= 4) ? 'good' : (lands === 1 || lands === 5) ? 'fair' : 'poor',
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

    // Commander timing from sim
    if (sim?.commanderTiming?.byTurn && sim.commanderTiming.cmc) {
      const cmdCmc = sim.commanderTiming.cmc;
      const cmdTurn = Math.max(1, cmdCmc - ramp);
      const pct = sim.commanderTiming.byTurn[String(cmdTurn)] ?? null;
      out.push({
        label: 'Commander on curve',
        value: `~T${cmdTurn}`,
        detail: pct != null ? `${pct.toFixed(0)}% of sims by T${cmdTurn}` : null,
        rating: cmdTurn <= cmdCmc ? 'good' : cmdTurn <= cmdCmc + 1 ? 'fair' : 'poor',
      });
    }

    // Land odds from opening-hand distribution
    if (sim?.openingHand?.landDistribution) {
      const pct = sim.openingHand.landDistribution[String(lands)];
      if (pct != null) {
        out.push({
          label: 'Land odds',
          value: `${pct.toFixed(1)}%`,
          detail: `of ${(sim.metadata?.numGames || 0).toLocaleString()} hands have ${lands} land${lands !== 1 ? 's' : ''}`,
          rating: 'info',
        });
      }
    }
    return out;
  }, [hand, phase, sim, deck.slug]);

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
            <button className="gv1-scry-btn gv1-scry-btn-primary" onClick={draw}>Draw 7</button>
          )}
          {phase === 'drawn' && (
            <>
              <button className="gv1-scry-btn gv1-scry-btn-primary" onClick={keep}>Keep</button>
              <button className="gv1-scry-btn" onClick={mulligan}>Mulligan</button>
            </>
          )}
          {phase === 'bottoming' && (
            <span className="gv1-scry-instruction">
              Click {bottomCountFor(mulligans) - bottomed.length} card{bottomCountFor(mulligans) - bottomed.length !== 1 ? 's' : ''} to put on bottom
            </span>
          )}
          {phase === 'kept' && (
            <>
              <button className="gv1-scry-btn gv1-scry-btn-primary" onClick={draw}>New hand</button>
              {mulligans > 0 && (
                <span className="gv1-mono-xs gv1-dim">
                  Kept {keptHandSize(mulligans)} · {mulligans === 1 ? 'free mulligan' : `${mulligans} mulligans`}
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
            Draw an opening hand to evaluate it against {(sim?.metadata?.numGames || 0).toLocaleString()} simulated games.
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
              <span key={i} className="gv1-scry-bottomed-name" data-card-name={c.name}>{c.name}</span>
            ))}
          </div>
        )}

        {phase === 'kept' && hand.length === 0 && (
          <div className="gv1-scry-empty">
            Mulliganed to zero. Try a new hand.
          </div>
        )}

        {assessment && assessment.length > 0 && (
          <div className="gv1-scry-assess" role="list">
            {assessment.map((cell, i) => (
              <div key={i} className="gv1-scry-assess-cell" data-rating={cell.rating} role="listitem">
                <div className="gv1-scry-assess-label">{cell.label}</div>
                <div className="gv1-scry-assess-value">{cell.value}</div>
                {cell.detail ? <div className="gv1-scry-assess-detail">{cell.detail}</div> : null}
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

function SwapCardDisplay({ card, onClear, isAdd }) {
  const meta = useScryEntry(card.name);
  const img = meta?.image_normal || meta?.image_small || '';
  const tl = meta?.type_line || card.type_line || card.type || '';
  const mc = meta?.mana_cost || '';
  return (
    <div className="gv1-scry-swap-card" data-card-name={card.name}>
      <div className="gv1-scry-swap-card-img">
        {img ? <img src={img} alt={card.name} loading="eager" /> : null}
      </div>
      <div className="gv1-scry-swap-card-info">
        <span className="gv1-scry-swap-card-name">{card.name}</span>
        <span className="gv1-scry-swap-card-type">{tl}</span>
        {mc ? <span className="gv1-scry-swap-card-mana">{fmtManaCost(mc)}</span> : null}
      </div>
      <button
        type="button"
        className="gv1-scry-swap-clear"
        onClick={onClear}
        aria-label={(isAdd ? 'Clear add' : 'Clear cut') + ': ' + card.name}
      >×</button>
    </div>
  );
}

function SwapAnalyzer({ deck }) {
  const decklist = deck.rawDecklist || [];
  const synergies = deck.synergies || []; // raw synergies array on transformed deck (if exposed)
  const gameChangers = deck.gameChangers || 0;

  const [cutCard, setCutCard] = useStateScry(null);
  const [addCard, setAddCard] = useStateScry(null);
  const [searchQ, setSearchQ] = useStateScry('');
  const searchRef = useRefScry(null);

  // Reset on deck switch.
  useEffectScry(() => {
    setCutCard(null);
    setAddCard(null);
    setSearchQ('');
  }, [deck.slug]);

  // Group decklist by type for the cut <select>.
  const cutOptions = useMemoScry(() => {
    const groups = {};
    decklist.forEach(c => {
      const t = c.type || 'Other';
      (groups[t] ||= []).push(c.name);
    });
    Object.keys(groups).forEach(k => groups[k].sort());
    return groups;
  }, [deck.slug]);

  // Search results: scan loaded GV1Cards cache, plus the deck's own decklist (so we can swap into another role).
  // Bias: in-deck candidates first (they typically have richer cached metadata).
  const [, bumpSearch] = useStateScry(0);
  useEffectScry(() => {
    if (!searchQ || searchQ.length < 2) return;
    // Subscribe to all known cache entries so their fetches re-render us.
    // (GV1Cards has no global change event; we just bump on a slow tick.)
    const t = setInterval(() => bumpSearch(n => n + 1), 700);
    return () => clearInterval(t);
  }, [searchQ]);

  const searchResults = useMemoScry(() => {
    const q = searchQ.trim().toLowerCase();
    if (q.length < 2) return [];
    const inDeck = new Set(decklist.map(c => c.name.toLowerCase()));
    const results = [];
    // 1) try GV1Cards cache (cards we've already loaded somewhere)
    if (window.GV1Cards) {
      const seen = new Set();
      // We don't have a direct iterator on GV1Cards, but we can probe known names from
      // the deck (highlights / decklist). Still, the user is searching; best we can do
      // is search the union of decklist names + cached names we *know about* via the
      // deck object. We expand to all loaded decks' decklists for a richer pool.
      const allDecks = (window.GV1_DATA && window.GV1_DATA.DECK_FULL) || [];
      const pool = new Set();
      allDecks.forEach(d => (d.rawDecklist || []).forEach(c => pool.add(c.name)));
      pool.forEach(name => {
        if (results.length >= 30) return;
        if (seen.has(name.toLowerCase())) return;
        if (inDeck.has(name.toLowerCase())) return;
        if (!name.toLowerCase().includes(q)) return;
        seen.add(name.toLowerCase());
        const meta = window.GV1Cards.get(name);
        results.push({
          name,
          type_line: meta?.type_line || '',
          cmc: meta?.cmc,
          mana_cost: meta?.mana_cost || '',
        });
      });
    }
    return results.slice(0, 30);
  }, [searchQ, deck.slug]);

  function selectCut(name) {
    const card = decklist.find(c => c.name === name);
    if (card) setCutCard(card);
  }
  function selectAdd(name) {
    const meta = window.GV1Cards?.get(name) || {};
    setAddCard({ name, ...meta });
    setSearchQ('');
  }

  // Compute deck-wide deltas using available metadata.
  const delta = useMemoScry(() => {
    if (!cutCard || !addCard) return null;
    const cutMeta = window.GV1Cards?.get(cutCard.name) || {};
    const addMeta = window.GV1Cards?.get(addCard.name) || addCard;

    const cutCmc = cutMeta.cmc ?? null;
    const addCmc = addMeta.cmc ?? null;
    const cmcChange = (cutCmc != null && addCmc != null) ? (addCmc - cutCmc) : null;

    const cutColors = colorsFromManaCost(cutMeta.mana_cost);
    const addColors = colorsFromManaCost(addMeta.mana_cost);
    const colorDelta = {};
    cutColors.forEach(c => colorDelta[c] = (colorDelta[c] || 0) - 1);
    addColors.forEach(c => colorDelta[c] = (colorDelta[c] || 0) + 1);
    Object.keys(colorDelta).forEach(k => { if (colorDelta[k] === 0) delete colorDelta[k]; });

    const cutType = deriveType(cutMeta.type_line, cutCard.type);
    const addType = deriveType(addMeta.type_line, addCard.type);

    // Aggregate deck stats (using whatever is in GV1Cards cache)
    let totalCmc = 0, nonLandCount = 0, landCount = 0;
    decklist.forEach(c => {
      const m = window.GV1Cards?.get(c.name);
      const tl = (m?.type_line || c.type || '').toLowerCase();
      const cmc = m?.cmc ?? null;
      if (tl.includes('land')) landCount++;
      else if (cmc != null) { totalCmc += cmc; nonLandCount++; }
    });
    const oldAvg = nonLandCount > 0 ? totalCmc / nonLandCount : 0;
    const cutIsLand = cutType === 'Land';
    const addIsLand = addType === 'Land';
    let newTotal = totalCmc, newCount = nonLandCount;
    if (!cutIsLand && cutCmc != null) { newTotal -= cutCmc; newCount -= 1; }
    if (!addIsLand && addCmc != null) { newTotal += addCmc; newCount += 1; }
    const newAvg = newCount > 0 ? newTotal / newCount : 0;
    const avgCmcChange = (nonLandCount > 0 || newCount > 0) ? (newAvg - oldAvg) : null;

    const landsBefore = landCount;
    const landsAfter = landCount + (addIsLand ? 1 : 0) - (cutIsLand ? 1 : 0);

    // Synergy impact
    const synergiesBroken = synergies.filter(s =>
      (s.cards || []).some(c => c.toLowerCase() === cutCard.name.toLowerCase())
    );
    const synergiesKept = synergies.filter(s =>
      (s.cards || []).some(c => c.toLowerCase() === addCard.name.toLowerCase())
    );

    // Game changer impact (uses window.GV1_GAME_CHANGERS_SET, loaded from data/game-changers.json)
    const gcSet = window.GV1_GAME_CHANGERS_SET || new Set();
    const cutIsGC = gcSet.has(cutCard.name.toLowerCase());
    const addIsGC = gcSet.has(addCard.name.toLowerCase());
    let gcKind = null;
    let gcDetail = null;
    if (cutIsGC && addIsGC) {
      gcKind = 'swap';
      gcDetail = 'GC for GC — count unchanged';
    } else if (addIsGC) {
      gcKind = 'adding';
      gcDetail = `+1 GC · ${gameChangers} → ${gameChangers + 1}`;
    } else if (cutIsGC) {
      gcKind = 'removing';
      gcDetail = `−1 GC · ${gameChangers} → ${gameChangers - 1}`;
    }

    return {
      cutCmc, addCmc, cmcChange,
      colorDelta,
      cutType, addType,
      typeChanged: cutType !== addType,
      avgCmcBefore: oldAvg, avgCmcAfter: newAvg, avgCmcChange,
      landsBefore, landsAfter,
      synergiesBroken, synergiesKept,
      gcKind, gcDetail, gameChangers,
      cutManaCost: cutMeta.mana_cost, addManaCost: addMeta.mana_cost,
    };
  }, [cutCard, addCard, deck.slug]);

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
                  onChange={(e) => { selectCut(e.target.value); e.target.value = ''; }}
                >
                  <option value="" disabled>Select a card to cut…</option>
                  {Object.keys(cutOptions).sort().map(type => (
                    <optgroup key={type} label={type}>
                      {cutOptions[type].map(name => (
                        <option key={name} value={name}>{name}</option>
                      ))}
                    </optgroup>
                  ))}
                </select>
                <span className="gv1-scry-search-hint">Choose any card from the {decklist.length}-card list</span>
              </div>
            )}
          </div>
        </div>

        <div className="gv1-scry-swap-arrow" aria-hidden="true">→</div>

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
                  placeholder="Search cards across all 12 decks…"
                  value={searchQ}
                  onChange={(e) => setSearchQ(e.target.value)}
                />
                <span className="gv1-scry-search-hint">2+ characters · live cache · Scryfall metadata where loaded</span>
                {searchResults.length > 0 && (
                  <div className="gv1-scry-search-results" role="listbox">
                    {searchResults.map(r => {
                      const cmcStr = r.cmc != null ? ` · MV ${Math.floor(r.cmc)}` : '';
                      return (
                        <button
                          key={r.name}
                          type="button"
                          className="gv1-scry-search-result"
                          onClick={() => selectAdd(r.name)}
                        >
                          <span>{r.name}</span>
                          <span className="gv1-scry-search-result-type">{r.type_line || '—'}{cmcStr}</span>
                        </button>
                      );
                    })}
                  </div>
                )}
                {searchQ.length >= 2 && searchResults.length === 0 && (
                  <div className="gv1-scry-search-no-results">
                    No cards in the loaded pool match "{searchQ}". Hover any card name elsewhere in the app to fetch it into the cache.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Δ DELTA */}
      {delta ? (
        <div className="gv1-scry-delta">
          <div className="gv1-scry-delta-head">
            <h4 className="gv1-scry-delta-title">Δ Impact</h4>
            <span className="gv1-mono-xs gv1-dim">computed against current decklist</span>
          </div>

          {/* CMC change */}
          {delta.cmcChange != null && (
            <div className="gv1-scry-delta-row">
              <span className="gv1-scry-delta-label">Mana value</span>
              <div className="gv1-scry-delta-values">
                <span className="gv1-scry-delta-detail">{delta.cutCmc} → {delta.addCmc}</span>
                <span
                  className="gv1-scry-delta-change"
                  data-dir={delta.cmcChange === 0 ? 'neutral' : delta.cmcChange > 0 ? 'increase' : 'decrease'}
                >
                  {delta.cmcChange > 0 ? '+' : ''}{delta.cmcChange}
                </span>
              </div>
            </div>
          )}

          {/* Avg CMC */}
          {delta.avgCmcChange != null && (
            <div className="gv1-scry-delta-row">
              <span className="gv1-scry-delta-label">Avg mana value</span>
              <div className="gv1-scry-delta-values">
                <span className="gv1-scry-delta-detail">{delta.avgCmcBefore.toFixed(2)} → {delta.avgCmcAfter.toFixed(2)}</span>
                <span
                  className="gv1-scry-delta-change"
                  data-dir={Math.abs(delta.avgCmcChange) < 0.005 ? 'neutral' : delta.avgCmcChange > 0 ? 'increase' : 'decrease'}
                >
                  {delta.avgCmcChange > 0 ? '+' : ''}{delta.avgCmcChange.toFixed(2)}
                </span>
              </div>
            </div>
          )}

          {/* Land count */}
          {delta.landsBefore !== delta.landsAfter && (
            <div className="gv1-scry-delta-row">
              <span className="gv1-scry-delta-label">Lands</span>
              <div className="gv1-scry-delta-values">
                <span className="gv1-scry-delta-detail">{delta.landsBefore} → {delta.landsAfter}</span>
                <span
                  className="gv1-scry-delta-change"
                  data-dir={delta.landsAfter > delta.landsBefore ? 'info' : 'warning'}
                >
                  {delta.landsAfter > delta.landsBefore ? '+' : ''}{delta.landsAfter - delta.landsBefore}
                </span>
              </div>
            </div>
          )}

          {/* Color balance */}
          {Object.keys(delta.colorDelta).length > 0 && (
            <div className="gv1-scry-delta-row">
              <span className="gv1-scry-delta-label">Color pips</span>
              <div className="gv1-scry-delta-values">
                {Object.entries(delta.colorDelta).map(([c, n]) => (
                  <span key={c} className="gv1-scry-color-pip" data-c={c}>
                    {n > 0 ? '+' : ''}{n} {SCRY_COLOR_NAMES[c] || c}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Type change */}
          {delta.typeChanged && (
            <div className="gv1-scry-delta-row">
              <span className="gv1-scry-delta-label">Type</span>
              <div className="gv1-scry-delta-values">
                <span className="gv1-scry-delta-detail">{delta.cutType} → {delta.addType}</span>
              </div>
            </div>
          )}

          {/* Game Changers */}
          {delta.gcKind && (
            <div className="gv1-scry-delta-row">
              <span className="gv1-scry-delta-label">Game Changers</span>
              <div className="gv1-scry-delta-values">
                <span className="gv1-scry-delta-detail">{delta.gcDetail}</span>
                <span
                  className="gv1-scry-delta-change"
                  data-dir={delta.gcKind === 'adding' ? 'warning' : delta.gcKind === 'removing' ? 'info' : 'neutral'}
                >
                  {delta.gcKind === 'adding' ? '★ +1' : delta.gcKind === 'removing' ? '★ −1' : '★ ↔'}
                </span>
              </div>
            </div>
          )}

          {/* Synergies broken */}
          {delta.synergiesBroken.length > 0 && (
            <div className="gv1-scry-delta-row">
              <span className="gv1-scry-delta-label">Synergies broken</span>
              <div className="gv1-scry-delta-values">
                <div className="gv1-scry-synergy-list">
                  {delta.synergiesBroken.map((s, i) => (
                    <div key={i} className="gv1-scry-synergy-item" data-kind="broken">
                      <span className="gv1-scry-synergy-icon">⚠</span>
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

          {/* Synergies kept */}
          {delta.synergiesKept.length > 0 && (
            <div className="gv1-scry-delta-row">
              <span className="gv1-scry-delta-label">Synergies enabled</span>
              <div className="gv1-scry-delta-values">
                <div className="gv1-scry-synergy-list">
                  {delta.synergiesKept.map((s, i) => (
                    <div key={i} className="gv1-scry-synergy-item" data-kind="kept">
                      <span className="gv1-scry-synergy-icon">✓</span>
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
      ) : (
        <div className="gv1-scry-empty">
          Pick a card to cut and a card to add to see the impact on mana value, color balance, lands, and synergies.
        </div>
      )}
    </section>
  );
}

/* ============================================================
 * § VIII.C  SIMULATION BASELINE  (KPIs / mana curve / land histogram)
 * ──────────────────────────────────────────────────────────── */

function ManaCurveChart({ manaByTurn, numTurns }) {
  if (!manaByTurn) return null;
  const turns = [];
  for (let t = 1; t <= numTurns; t++) {
    const k = String(t);
    if (manaByTurn[k]) turns.push({ t, ...manaByTurn[k] });
  }
  if (!turns.length) return null;

  const W = 480, H = 180, PAD_L = 32, PAD_R = 12, PAD_T = 12, PAD_B = 28;
  const innerW = W - PAD_L - PAD_R;
  const innerH = H - PAD_T - PAD_B;

  const maxY = Math.ceil(Math.max(...turns.map(t => t.p75)) + 1);
  const minY = 0;

  const x = t => PAD_L + (innerW * (t - 1)) / (numTurns - 1);
  const y = v => PAD_T + innerH - ((v - minY) / (maxY - minY)) * innerH;

  const upper = turns.map(t => `${x(t.t)},${y(t.p75)}`).join(' L ');
  const lower = turns.slice().reverse().map(t => `${x(t.t)},${y(t.p25)}`).join(' L ');
  const bandPath = `M ${upper} L ${lower} Z`;
  const linePath = 'M ' + turns.map(t => `${x(t.t)},${y(t.median)}`).join(' L ');

  const yTicks = [0, Math.floor(maxY / 2), maxY];

  return (
    <svg className="gv1-scry-mana-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Median mana available by turn with P25–P75 band">
      {/* Y axis ticks */}
      {yTicks.map((v, i) => (
        <g key={i}>
          <line x1={PAD_L} x2={W - PAD_R} y1={y(v)} y2={y(v)} className="gv1-scry-mana-axis" strokeDasharray="2 4" />
          <text className="gv1-scry-mana-tick" x={PAD_L - 8} y={y(v) + 3} textAnchor="end">{v}</text>
        </g>
      ))}
      {/* X axis ticks */}
      {turns.map((t, i) => (
        <text key={i} className="gv1-scry-mana-tick" x={x(t.t)} y={H - 10} textAnchor="middle">T{t.t}</text>
      ))}
      {/* Band */}
      <path d={bandPath} className="gv1-scry-mana-band" />
      {/* Median line */}
      <path d={linePath} className="gv1-scry-mana-line" />
      {/* Median dots */}
      {turns.map((t, i) => (
        <circle key={i} cx={x(t.t)} cy={y(t.median)} r="2.5" className="gv1-scry-mana-dot" />
      ))}
    </svg>
  );
}

function LandDistHistogram({ landDist, currentLands }) {
  if (!landDist) return null;
  const entries = Object.keys(landDist).map(k => ({ n: Number(k), pct: landDist[k] }))
    .sort((a, b) => a.n - b.n);
  const max = Math.max(0.01, ...entries.map(e => e.pct));

  return (
    <div className="gv1-scry-hist" role="img" aria-label="Opening hand land distribution histogram">
      {entries.map(e => (
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

function SimulationBaseline({ deck, currentLands }) {
  const sim = deck.sim;
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
  const numTurns = sim.metadata?.numTurns || 10;
  const numGames = sim.metadata?.numGames || 0;
  const mull = sim.mulliganStats || {};

  // Castable by T3 — try sim.curveEfficiency, else estimate from manaByTurn
  const castableByT3 = sim.curveEfficiency?.castableByTurn?.['3']
    ?? sim.curveEfficiency?.byTurn?.['3']
    ?? null;

  return (
    <section className="gv1-section">
      <div className="gv1-section-head">
        <span className="gv1-mono-xs gv1-dim">VIII · C</span>
        <h3 className="gv1-serif-xl">Simulation Baseline</h3>
        <span className="gv1-mono-xs gv1-dim">· {numGames.toLocaleString()} games × {numTurns} turns</span>
      </div>

      <div className="gv1-scry-sim-grid">
        {/* KPIs */}
        <div className="gv1-scry-sim-panel">
          <div className="gv1-scry-sim-panel-head">
            <h4 className="gv1-scry-sim-panel-title">Key indicators</h4>
            <span className="gv1-scry-sim-panel-meta">medians across {numGames.toLocaleString()} sims</span>
          </div>
          <div className="gv1-scry-kpis">
            <div className="gv1-scry-kpi">
              <span className="gv1-scry-kpi-label">Mana T3</span>
              <span className="gv1-scry-kpi-value">{manaT3 != null ? manaT3.toFixed(1) : '—'}</span>
              <span className="gv1-scry-kpi-unit">median available</span>
            </div>
            <div className="gv1-scry-kpi">
              <span className="gv1-scry-kpi-label">Castable T3</span>
              <span className="gv1-scry-kpi-value">{castableByT3 != null ? Math.round(castableByT3) + '%' : '—'}</span>
              <span className="gv1-scry-kpi-unit">spells on curve</span>
            </div>
            <div className="gv1-scry-kpi">
              <span className="gv1-scry-kpi-label">Commander</span>
              <span className="gv1-scry-kpi-value">{cmdMedian != null ? `T${cmdMedian}` : '—'}</span>
              <span className="gv1-scry-kpi-unit">{cmdName ? `${cmdName} · MV ${cmdCmc}` : '—'}</span>
            </div>
          </div>

          {/* Mulligan stats */}
          {(mull.keptFirst != null || mull.freeMulligan != null || mull.paidMulligan != null) && (
            <div className="gv1-scry-mulligan-stats">
              <div className="gv1-scry-mulligan-stat">
                <span className="gv1-scry-mulligan-stat-value">{(mull.keptFirst ?? 0).toFixed(1)}%</span>
                <span className="gv1-scry-mulligan-stat-label">keep first 7</span>
              </div>
              <div className="gv1-scry-mulligan-stat">
                <span className="gv1-scry-mulligan-stat-value">{(mull.freeMulligan ?? 0).toFixed(1)}%</span>
                <span className="gv1-scry-mulligan-stat-label">free mulligan</span>
              </div>
              <div className="gv1-scry-mulligan-stat">
                <span className="gv1-scry-mulligan-stat-value">{(mull.paidMulligan ?? 0).toFixed(1)}%</span>
                <span className="gv1-scry-mulligan-stat-label">paid mulligan</span>
              </div>
            </div>
          )}
        </div>

        {/* Mana curve */}
        <div className="gv1-scry-sim-panel">
          <div className="gv1-scry-sim-panel-head">
            <h4 className="gv1-scry-sim-panel-title">Mana available by turn</h4>
            <span className="gv1-scry-sim-panel-meta">P25 — median — P75</span>
          </div>
          <ManaCurveChart manaByTurn={sim.manaByTurn} numTurns={numTurns} />
          <div className="gv1-scry-chart-legend">
            <span><span className="gv1-scry-legend-band" /> P25–P75 range</span>
            <span><span className="gv1-scry-legend-line" /> Median</span>
          </div>
        </div>

        {/* Land histogram (full width below) */}
        <div className="gv1-scry-sim-panel" style={{ gridColumn: '1 / -1' }}>
          <div className="gv1-scry-sim-panel-head">
            <h4 className="gv1-scry-sim-panel-title">Opening hand · land distribution</h4>
            <span className="gv1-scry-sim-panel-meta">
              {currentLands != null ? `your hand · ${currentLands} land${currentLands !== 1 ? 's' : ''} highlighted` : 'across 7-card opening hands'}
            </span>
          </div>
          <LandDistHistogram landDist={sim.openingHand?.landDistribution} currentLands={currentLands} />
        </div>
      </div>
    </section>
  );
}

/* ============================================================
 * SCRYING POOL — orchestrator
 * ──────────────────────────────────────────────────────────── */

function GV1Scrying({ deck }) {
  if (!deck) {
    return (
      <div className="gv1-root" data-screen-label="04 Scrying Pool" data-gv1-screen="scrying">
        <GV1Topbar screen="scrying" />
        <section className="gv1-section">
          <div className="gv1-empty">
            <span className="gv1-rune">◇</span>
            <span className="gv1-mono-xs">No deck selected.</span>
          </div>
        </section>
      </div>
    );
  }

  // Track current hand (if any) so the histogram can mark it.
  // The handsim is internal state to HandSimulator — we surface it via a global handle.
  const [currentLands, setCurrentLands] = useStateScry(null);
  // Subscribe to changes via a small bus on window. (Cheaper than lifting state up.)
  useEffectScry(() => {
    const handler = (e) => setCurrentLands(e.detail);
    window.addEventListener('gv1-scry-hand-lands', handler);
    return () => window.removeEventListener('gv1-scry-hand-lands', handler);
  }, []);

  const sim = deck.sim;

  return (
    <div className="gv1-root" data-screen-label="04 Scrying Pool" data-gv1-screen="scrying">
      <GV1Topbar screen="scrying" />

      {/* Hero */}
      <header className="gv1-section">
        <div className="gv1-section-head">
          <span className="gv1-rune" aria-hidden="true">§ VIII</span>
          <h2 className="gv1-section-title">The Scrying Pool</h2>
          <span className="gv1-mono-xs gv1-dim">
            · {deck.deckName} · {deck.commander}
            {sim?.metadata?.numGames ? ` · ${sim.metadata.numGames.toLocaleString()} simulations` : ''}
          </span>
        </div>
        <p className="gv1-scry-lede">
          Two interactive instruments, one passive baseline. The <em>Hand Simulator</em> deals from
          this deck's {(deck.rawDecklist || []).length}-card list and grades the result against the
          full simulation. The <em>Swap Analyzer</em> lets you weigh a single cut + add against the
          existing mana value, color balance, and known synergies. Below them, the <em>Simulation
          Baseline</em> shows the underlying numbers the assessments draw from.
        </p>
      </header>

      <HandSimulator deck={deck} />
      <SwapAnalyzer deck={deck} />
      <SimulationBaseline deck={deck} currentLands={currentLands} />
    </div>
  );
}

Object.assign(window, { GV1Scrying });
