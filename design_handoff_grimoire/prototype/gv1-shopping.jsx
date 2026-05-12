// Grimoire v1 — Shopping List: cross-deck buy planner
// ─────────────────────────────────────────────────────────────────
// Real surface (replaces the stub). Lets the player:
//   1. Pick one or more decks via a chip rail.
//   2. Import a CSV/TXT of cards they already own (persisted to
//      localStorage under 'grimoire-owned-cards', so reload survives).
//   3. See the union of cards across decks, deduped, split into
//      Need-to-Buy vs Already-Own. Basic lands are skipped (they
//      get reprinted free in any precon-style purchase).
//   4. Group rows by type or A–Z; copy the buy list to clipboard.
//
// Data shape (from gv1-data.js → DECK_FULL[]):
//   d.list = [{ name: 'Commander'|'Ramp (n)'|…, cards: [{n, type, …}] }]
//   d.commander, d.colors (glyph string), d.deckName, d.idx, d.slug, d.price
//
// Scryfall metadata (mana cost, price) is pulled lazily via
// window.GV1Cards.fetch(name); rows render '—' until loaded, then
// re-render via subscribe(). We only enqueue cards that are visible
// in Need-to-Buy — Already-Own stays cheap.
// ─────────────────────────────────────────────────────────────────

const { useState: useStateShop, useEffect: useEffectShop, useMemo: useMemoShop, useRef: useRefShop } = React;

// Storage key — same as the original app.js so existing users don't
// re-upload. Format: JSON-stringified [[name, qty], …] (Map → array).
const SHOP_OWNED_KEY = 'grimoire-owned-cards';

const BASIC_LANDS = new Set([
  'Plains','Island','Swamp','Mountain','Forest','Wastes',
  'Snow-Covered Plains','Snow-Covered Island','Snow-Covered Swamp',
  'Snow-Covered Mountain','Snow-Covered Forest',
]);

// Type bucket the row belongs to. Uses Scryfall type_line if cached,
// otherwise falls back to whatever was in the deck list (e.g. 'Creature').
function typeBucket(name, fallback) {
  const cached = window.GV1Cards?.get(name);
  const tl = (cached?.type_line || fallback || '').toLowerCase();
  if (tl.includes('creature')) return 'Creature';
  if (tl.includes('planeswalker')) return 'Planeswalker';
  if (tl.includes('land')) return 'Land';
  if (tl.includes('artifact')) return 'Artifact';
  if (tl.includes('enchantment')) return 'Enchantment';
  if (tl.includes('instant')) return 'Instant';
  if (tl.includes('sorcery')) return 'Sorcery';
  if (tl.includes('battle')) return 'Battle';
  return 'Other';
}

const TYPE_ORDER = [
  'Commander','Creature','Planeswalker','Artifact',
  'Enchantment','Instant','Sorcery','Battle','Land','Other',
];

// ── Owned-cards parser (CSV with Name,Quantity headers OR a `1x Name` text list)
function parseCsvRows(text) {
  const rows = [];
  let row = [], val = '', inQ = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQ) {
      if (c === '"') {
        if (text[i+1] === '"') { val += '"'; i++; } else inQ = false;
      } else val += c;
      continue;
    }
    if (c === '"') inQ = true;
    else if (c === ',') { row.push(val); val = ''; }
    else if (c === '\n' || c === '\r') {
      if (val !== '' || row.length) { row.push(val); if (row.some(x => x !== '')) rows.push(row); }
      row = []; val = '';
      if (c === '\r' && text[i+1] === '\n') i++;
    } else val += c;
  }
  if (val !== '' || row.length) { row.push(val); if (row.some(x => x !== '')) rows.push(row); }
  return rows;
}

function parseOwnedFile(text) {
  text = (text || '').replace(/^\ufeff/, '');
  const rows = parseCsvRows(text);
  const out = new Map();
  if (rows.length) {
    const headers = rows[0].map(c => c.trim().toLowerCase());
    const ni = headers.indexOf('name');
    const qi = headers.indexOf('quantity');
    if (ni !== -1 && qi !== -1) {
      // CSV path
      rows.slice(1).forEach(r => {
        const name = (r[ni] || '').trim();
        if (!name) return;
        const q = parseInt((r[qi] || '1').trim(), 10) || 1;
        out.set(name, (out.get(name) || 0) + q);
      });
      return out;
    }
  }
  // Text path: `1x Card Name` or bare names
  text.split('\n').forEach(line => {
    line = line.trim();
    if (!line) return;
    const m = line.match(/^(\d+)x?\s+(.+)$/i);
    if (m) {
      const q = parseInt(m[1], 10) || 1;
      out.set(m[2].trim(), (out.get(m[2].trim()) || 0) + q);
    } else {
      out.set(line, (out.get(line) || 0) + 1);
    }
  });
  return out;
}

// ── localStorage helpers
function loadOwned() {
  try {
    const raw = localStorage.getItem(SHOP_OWNED_KEY);
    if (raw) return new Map(JSON.parse(raw));
  } catch {}
  return new Map();
}
function saveOwned(map) {
  try { localStorage.setItem(SHOP_OWNED_KEY, JSON.stringify([...map])); } catch {}
}

// ── Aggregate cards across selected decks
function aggregateCards(selectedSlugs, allDecks) {
  // name → { qty: 1, fallbackType, isCommander, decks: Set<slug> }
  const map = new Map();
  selectedSlugs.forEach(slug => {
    const d = allDecks.find(x => x.slug === slug);
    if (!d) return;
    // Commander
    if (d.commander) {
      const cur = map.get(d.commander);
      if (cur) { cur.decks.add(slug); }
      else map.set(d.commander, {
        qty: 1, fallbackType: 'Creature', isCommander: true, decks: new Set([slug]),
      });
    }
    // Cards from list (skip the synthetic "Commander" group; iterate the rest)
    (d.list || []).forEach(group => {
      if (group.name === 'Commander') return;
      (group.cards || []).forEach(c => {
        if (!c.n || BASIC_LANDS.has(c.n)) return;
        const cur = map.get(c.n);
        if (cur) { cur.decks.add(slug); }
        else map.set(c.n, {
          qty: 1, fallbackType: c.type || 'Other', isCommander: false, decks: new Set([slug]),
        });
      });
    });
  });
  return map;
}

// ── Split into buy / own based on the owned map
function splitOwnership(cardMap, ownedMap) {
  const buy = [], own = [];
  cardMap.forEach((info, name) => {
    const ownedQty = ownedMap.get(name) || 0;
    const need = Math.max(0, info.qty - ownedQty);
    const have = Math.min(info.qty, ownedQty);
    if (need > 0) buy.push({ name, qty: need, ...info });
    if (have > 0) own.push({ name, qty: have, ...info });
  });
  return { buy, own };
}

// ── Mana-cost glyph rendering (compact, monospace text — no SVG dependency).
// Scryfall returns mana_cost like "{2}{U}{U}". We render each as a tight pip.
const MANA_LETTER = { W: 'W', U: 'U', B: 'B', R: 'R', G: 'G', C: 'C' };
function ManaCost({ cost }) {
  if (!cost) return null;
  const symbols = (cost.match(/\{[^}]+\}/g) || []);
  if (!symbols.length) return null;
  return (
    <span className="gv1-shop-mana" aria-label={`mana cost ${cost}`}>
      {symbols.map((s, i) => {
        const inner = s.slice(1, -1);
        const isColor = MANA_LETTER[inner];
        const cls = 'gv1-shop-mana-pip ' + (isColor ? `gv1-shop-mana-${inner}` : 'gv1-shop-mana-num');
        return <span key={i} className={cls} aria-hidden="true">{inner}</span>;
      })}
    </span>
  );
}

// Subscribe a row to its Scryfall entry so price/mana_cost arrive without
// the parent re-rendering the whole list. Returns [entry, _bumper].
function useCardEntry(name) {
  const [, bump] = useStateShop(0);
  useEffectShop(() => {
    if (!name || !window.GV1Cards) return;
    const unsub = window.GV1Cards.subscribe(name, () => bump(n => n + 1));
    window.GV1Cards.enqueue(name);
    return unsub;
  }, [name]);
  return window.GV1Cards?.get(name) || null;
}

// Convert a color glyph string to a single dot color (for deck attribution dots).
function deckDotColor(colorsGlyph) {
  const map = { '⚪': '#c4b998', '🔵': '#1a7cc0', '⚫': '#4a3a5c', '🔴': '#c23028', '🟢': '#2d8a56', '◇': '#6B7280' };
  const chars = Array.from(colorsGlyph || '');
  if (chars.length === 0) return '#6B7280';
  if (chars.length === 1) return map[chars[0]] || '#6B7280';
  const a = map[chars[0]] || '#6B7280';
  const b = map[chars[chars.length - 1]] || '#6B7280';
  return `linear-gradient(135deg, ${a} 50%, ${b} 50%)`;
}

// ── Single card row
function ShopRow({ name, qty, decks, multiDeck, allDecks, isCommander, fallbackType }) {
  const entry = useCardEntry(name);
  const price = entry?.price || null;
  const mana = entry?.mana_cost || null;
  const isLand = (entry?.type_line || fallbackType || '').toLowerCase().includes('land');

  return (
    <div className="gv1-shop-row" data-card-name={name} role="row">
      <span className="gv1-shop-row-qty gv1-mono-xs gv1-dim">{qty}×</span>
      <span className="gv1-shop-row-name gv1-serif-md">{name}</span>
      {!isLand && mana && <ManaCost cost={mana} />}
      {isLand && <span className="gv1-shop-row-mana gv1-mono-xs gv1-dim">LAND</span>}
      {multiDeck && (
        <span className="gv1-shop-row-decks">
          {[...decks].slice(0, 6).map(slug => {
            const d = allDecks.find(x => x.slug === slug);
            if (!d) return null;
            return (
              <span
                key={slug}
                className="gv1-shop-deck-dot"
                style={{ background: deckDotColor(d.colors) }}
                title={d.deckName}
                aria-label={d.deckName}
              />
            );
          })}
          {decks.size > 6 && <span className="gv1-mono-xs gv1-dim">+{decks.size - 6}</span>}
        </span>
      )}
      <span className="gv1-shop-row-price gv1-mono-xs">
        {price ? <span className="gv1-rune">{price}</span> : <span className="gv1-dim">—</span>}
      </span>
    </div>
  );
}

// ── Group rows by type (default) or A–Z
function groupRows(cards, mode) {
  if (mode === 'az') {
    return [{ name: null, cards: [...cards].sort((a, b) => a.name.localeCompare(b.name)) }];
  }
  const buckets = {};
  cards.forEach(c => {
    const t = c.isCommander ? 'Commander' : typeBucket(c.name, c.fallbackType);
    (buckets[t] ||= []).push(c);
  });
  return TYPE_ORDER.filter(t => buckets[t]?.length).map(t => ({
    name: t,
    cards: buckets[t].sort((a, b) => a.name.localeCompare(b.name)),
  }));
}

// ── Aggregate price across all visible buy-list rows. Returns { count, sum }.
function summarizePrice(cards) {
  let sum = 0, priced = 0;
  cards.forEach(c => {
    const e = window.GV1Cards?.get(c.name);
    if (e?.price) {
      const n = parseFloat(e.price.replace(/[^0-9.]/g, ''));
      if (!isNaN(n)) { sum += n * c.qty; priced++; }
    }
  });
  return { sum, priced, total: cards.length };
}

function GV1Shopping({ allDecks }) {
  const decks = allDecks || [];
  const [selected, setSelected] = useStateShop(() => {
    // Pre-select the first deck so the page isn't blank on open.
    return new Set(decks.length ? [decks[0].slug] : []);
  });
  const [owned, setOwned] = useStateShop(() => loadOwned());
  const [sortMode, setSortMode] = useStateShop('type'); // 'type' | 'az'
  const [ownedCollapsed, setOwnedCollapsed] = useStateShop(true);
  const [importMsg, setImportMsg] = useStateShop(null); // { ok, text }
  const [copyState, setCopyState] = useStateShop(null); // 'ok' | 'err' | null
  const [, bump] = useStateShop(0); // re-render on Scryfall arrivals (for price totals)
  const fileRef = useRefShop();

  // Re-render when ANY visible card's Scryfall data lands. Cheap because
  // GV1Cards.subscribe is per-name; ShopRow re-renders itself, but the
  // summary needs a global poke. We just do it on a slow timer.
  useEffectShop(() => {
    const id = setInterval(() => bump(n => n + 1), 1500);
    return () => clearInterval(id);
  }, []);

  const cardMap = useMemoShop(() => aggregateCards(selected, decks), [selected, decks]);
  const { buy, own } = useMemoShop(() => splitOwnership(cardMap, owned), [cardMap, owned]);

  const buyGroups = useMemoShop(() => groupRows(buy, sortMode), [buy, sortMode]);
  const ownGroups = useMemoShop(() => groupRows(own, sortMode), [own, sortMode]);

  const buyTotal = buy.reduce((s, c) => s + c.qty, 0);
  const ownTotal = own.reduce((s, c) => s + c.qty, 0);
  const priceSummary = summarizePrice(buy);

  // ── Selection toggle
  const toggleDeck = (slug) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(slug)) next.delete(slug);
      else next.add(slug);
      return next;
    });
  };
  const selectAll = () => setSelected(new Set(decks.map(d => d.slug)));
  const clearSelection = () => setSelected(new Set());

  // ── Owned import
  const onFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const parsed = parseOwnedFile(text);
      if (!parsed.size) {
        setImportMsg({ ok: false, text: 'No cards detected in that file.' });
        return;
      }
      // Merge with existing rather than replace, so re-imports add up
      const merged = new Map(owned);
      parsed.forEach((q, n) => merged.set(n, (merged.get(n) || 0) + q));
      setOwned(merged);
      saveOwned(merged);
      const totalCards = [...parsed.values()].reduce((s, q) => s + q, 0);
      setImportMsg({ ok: true, text: `Imported ${parsed.size} unique cards (${totalCards} total).` });
    } catch (err) {
      setImportMsg({ ok: false, text: 'Could not read file: ' + err.message });
    }
    // Allow re-uploading the same filename
    e.target.value = '';
  };
  const clearOwned = () => {
    if (!confirm('Clear all owned cards? This is local-only and cannot be undone.')) return;
    setOwned(new Map());
    saveOwned(new Map());
    setImportMsg(null);
  };

  // ── Copy buy list
  const copyBuyList = async () => {
    const lines = [];
    buyGroups.forEach(g => {
      g.cards.forEach(c => lines.push(`${c.qty}x ${c.name}`));
    });
    if (!lines.length) {
      setCopyState('err');
      setTimeout(() => setCopyState(null), 1500);
      return;
    }
    try {
      await navigator.clipboard.writeText(lines.join('\n'));
      setCopyState('ok');
      setTimeout(() => setCopyState(null), 1500);
    } catch {
      setCopyState('err');
      setTimeout(() => setCopyState(null), 1500);
    }
  };

  // ── Empty render guard
  if (!decks.length) {
    return (
      <div className="gv1-root" data-screen-label="05 Shopping" data-gv1-screen="shopping">
        <GV1Topbar screen="shopping" />
        <section className="gv1-section"><div className="gv1-empty"><span className="gv1-rune">◇</span><span className="gv1-mono-xs">No decks loaded.</span></div></section>
      </div>
    );
  }

  return (
    <div className="gv1-root" data-screen-label="05 Shopping" data-gv1-screen="shopping">
      <GV1Topbar screen="shopping" />

      {/* ── Hero / lede ─────────────────────────────────────────── */}
      <header className="gv1-section gv1-shop-hero">
        <div className="gv1-section-head">
          <span className="gv1-rune" aria-hidden="true">§ IX</span>
          <h2 className="gv1-section-title">Shopping List</h2>
          <span className="gv1-mono-xs gv1-dim">· cross-deck buy planner · {decks.length} decks indexed</span>
        </div>
        <p className="gv1-shop-lede">
          Pick the tomes you want to assemble. Import what you already own. The
          ledger collapses duplicates across decks, skips basic lands, and splits
          the result into <em>need to buy</em> versus <em>already own</em>. All
          ownership data stays in your browser — nothing leaves the page.
        </p>
      </header>

      {/* ── Deck selector rail ──────────────────────────────────── */}
      <section className="gv1-section gv1-shop-section">
        <div className="gv1-shop-rail-head">
          <span className="gv1-mono-xs gv1-dim">SELECT DECKS</span>
          <span className="gv1-mono-xs gv1-dim">· {selected.size} of {decks.length}</span>
          <span className="gv1-shop-rail-spacer" />
          <button className="gv1-shop-mini-btn" onClick={selectAll} type="button">Select all</button>
          <button className="gv1-shop-mini-btn" onClick={clearSelection} type="button" disabled={selected.size === 0}>Clear</button>
        </div>
        <div className="gv1-shop-chips" role="group" aria-label="Deck selection">
          {decks.map(d => {
            const on = selected.has(d.slug);
            return (
              <button
                key={d.slug}
                type="button"
                className={'gv1-shop-chip' + (on ? ' gv1-active' : '')}
                onClick={() => toggleDeck(d.slug)}
                aria-pressed={on}
                title={on ? `Remove ${d.deckName}` : `Add ${d.deckName}`}
              >
                <span className="gv1-shop-chip-idx gv1-mono-xs">№{String(d.idx).padStart(2, '0')}</span>
                <span className="gv1-shop-chip-name gv1-serif-sm">{d.deckName}</span>
                <span className="gv1-shop-chip-pips"><GV1ManaPips colors={d.colors} /></span>
              </button>
            );
          })}
        </div>
      </section>

      {/* ── Owned cards bar ─────────────────────────────────────── */}
      <section className="gv1-section gv1-shop-section">
        <div className="gv1-shop-owned-bar">
          <input
            ref={fileRef}
            type="file"
            id="gv1-shop-owned-file"
            accept=".csv,.txt"
            onChange={onFile}
            hidden
          />
          <label htmlFor="gv1-shop-owned-file" className="gv1-shop-btn">
            <span aria-hidden="true">⬆</span>
            <span>Import owned cards</span>
          </label>
          <span className="gv1-mono-xs gv1-dim">
            {owned.size > 0
              ? `${[...owned.values()].reduce((s, q) => s + q, 0)} cards loaded — saved locally`
              : '// .csv (Name,Quantity) or .txt (one card per line)'}
          </span>
          {owned.size > 0 && (
            <button className="gv1-shop-mini-btn" onClick={clearOwned} type="button">Clear owned</button>
          )}
        </div>
        {importMsg && (
          <div className={'gv1-shop-import-msg ' + (importMsg.ok ? 'gv1-shop-import-ok' : 'gv1-shop-import-err')}>
            <span className="gv1-mono-xs">{importMsg.ok ? '◆' : '⚠'}</span>
            <span className="gv1-mono-xs">{importMsg.text}</span>
          </div>
        )}
      </section>

      {/* ── Summary + sort + copy ───────────────────────────────── */}
      {selected.size > 0 && (
        <section className="gv1-section gv1-shop-section">
          <div className="gv1-shop-summary">
            <div className="gv1-shop-stat">
              <span className="gv1-mono-xs gv1-dim">NEED TO BUY</span>
              <span className="gv1-serif-xl gv1-rune">{buyTotal}</span>
            </div>
            <div className="gv1-shop-stat">
              <span className="gv1-mono-xs gv1-dim">ALREADY OWN</span>
              <span className="gv1-serif-xl">{ownTotal}</span>
            </div>
            <div className="gv1-shop-stat">
              <span className="gv1-mono-xs gv1-dim">TOTAL UNIQUE</span>
              <span className="gv1-serif-xl">{cardMap.size}</span>
            </div>
            <div className="gv1-shop-stat">
              <span className="gv1-mono-xs gv1-dim">EST. COST</span>
              <span className="gv1-serif-xl gv1-rune">
                {priceSummary.priced > 0 ? `$${priceSummary.sum.toFixed(0)}` : '—'}
              </span>
              <span className="gv1-mono-xs gv1-dim">
                {priceSummary.priced < buy.length
                  ? `${priceSummary.priced}/${buy.length} priced`
                  : 'all priced'}
              </span>
            </div>
            <div className="gv1-shop-summary-actions">
              <div className="gv1-shop-sort">
                <span className="gv1-mono-xs gv1-dim">SORT</span>
                <button
                  type="button"
                  className={'gv1-shop-mini-btn' + (sortMode === 'type' ? ' gv1-active' : '')}
                  onClick={() => setSortMode('type')}
                >Type</button>
                <button
                  type="button"
                  className={'gv1-shop-mini-btn' + (sortMode === 'az' ? ' gv1-active' : '')}
                  onClick={() => setSortMode('az')}
                >A–Z</button>
              </div>
              <button
                type="button"
                className={'gv1-shop-btn gv1-shop-btn-primary' + (copyState === 'ok' ? ' gv1-shop-btn-success' : copyState === 'err' ? ' gv1-shop-btn-error' : '')}
                onClick={copyBuyList}
                disabled={buy.length === 0}
              >
                {copyState === 'ok' ? '✓ Copied' : copyState === 'err' ? '⚠ Failed' : 'Copy buy list'}
              </button>
            </div>
          </div>
        </section>
      )}

      {/* ── Need-to-Buy list ────────────────────────────────────── */}
      {selected.size > 0 && (
        <section className="gv1-section gv1-shop-section">
          <div className="gv1-section-head">
            <span className="gv1-mono-xs gv1-rune" aria-hidden="true">▾</span>
            <h3 className="gv1-serif-xl">Need to buy</h3>
            <span className="gv1-mono-xs gv1-dim">· {buy.length} unique · {buyTotal} cards</span>
          </div>
          {buy.length === 0 ? (
            <div className="gv1-empty">
              <span className="gv1-rune">◆</span>
              <span className="gv1-mono-xs">All cards owned. The grimoire is complete.</span>
            </div>
          ) : (
            <div className="gv1-shop-list">
              {buyGroups.map((g, gi) => (
                <div key={gi} className="gv1-shop-group">
                  {g.name && (
                    <div className="gv1-shop-group-head">
                      <span className="gv1-mono-xs gv1-rune">{g.name}</span>
                      <span className="gv1-mono-xs gv1-dim">· {g.cards.length}</span>
                    </div>
                  )}
                  {g.cards.map(c => (
                    <ShopRow
                      key={c.name}
                      name={c.name}
                      qty={c.qty}
                      decks={c.decks}
                      multiDeck={selected.size > 1}
                      allDecks={decks}
                      isCommander={c.isCommander}
                      fallbackType={c.fallbackType}
                    />
                  ))}
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* ── Already-Own list (collapsed by default) ─────────────── */}
      {selected.size > 0 && own.length > 0 && (
        <section className={'gv1-section gv1-shop-section gv1-shop-own-section' + (ownedCollapsed ? ' gv1-shop-collapsed' : '')}>
          <button
            type="button"
            className="gv1-shop-own-head"
            onClick={() => setOwnedCollapsed(c => !c)}
            aria-expanded={!ownedCollapsed}
          >
            <span className="gv1-mono-xs gv1-dim" aria-hidden="true">{ownedCollapsed ? '▸' : '▾'}</span>
            <span className="gv1-serif-xl">Already own</span>
            <span className="gv1-mono-xs gv1-dim">· {own.length} unique · {ownTotal} cards</span>
          </button>
          {!ownedCollapsed && (
            <div className="gv1-shop-list">
              {ownGroups.map((g, gi) => (
                <div key={gi} className="gv1-shop-group">
                  {g.name && (
                    <div className="gv1-shop-group-head">
                      <span className="gv1-mono-xs gv1-dim">{g.name}</span>
                      <span className="gv1-mono-xs gv1-dim">· {g.cards.length}</span>
                    </div>
                  )}
                  {g.cards.map(c => (
                    <ShopRow
                      key={c.name}
                      name={c.name}
                      qty={c.qty}
                      decks={c.decks}
                      multiDeck={selected.size > 1}
                      allDecks={decks}
                      isCommander={c.isCommander}
                      fallbackType={c.fallbackType}
                    />
                  ))}
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* ── Empty state ─────────────────────────────────────────── */}
      {selected.size === 0 && (
        <section className="gv1-section">
          <div className="gv1-empty">
            <span className="gv1-rune">◇</span>
            <span className="gv1-mono-xs">No decks selected. Pick at least one above to build a list.</span>
          </div>
        </section>
      )}

      <p className="gv1-mono-xs gv1-dim gv1-shop-foot">
        Basic lands (Plains, Island, Swamp, Mountain, Forest, Wastes, snow-covered) are excluded.
        Cards shared across decks are deduped — a $40 staple bought once covers every deck that uses it.
        Prices are USD from Scryfall and load lazily; the est. cost updates as more arrive.
      </p>
    </div>
  );
}

Object.assign(window, { GV1Shopping });
