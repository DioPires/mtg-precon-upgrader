// Port of design_handoff_grimoire/prototype/gv1-shopping.jsx.
// Cross-deck buy planner: select decks, import owned cards from CSV/TXT,
// split aggregated unique-card list into Need-to-Buy / Already-Own.

import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
} from 'react';
import { GV1ManaPips } from '../atoms/GV1ManaPips';
import { cardCache } from '../../data/cardCache';
import {
  aggregateBuiltClaims,
  computeBuyOwnSplit,
} from '../../data/builtDecks';
import { useBuiltDecks } from '../../hooks/useBuiltDecks';
import type { DeckFull } from '../../data/types';

const SHOP_OWNED_KEY = 'grimoire-owned-cards';

const BASIC_LANDS = new Set([
  'Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes',
  'Snow-Covered Plains', 'Snow-Covered Island', 'Snow-Covered Swamp',
  'Snow-Covered Mountain', 'Snow-Covered Forest',
]);

const TYPE_ORDER = [
  'Commander', 'Creature', 'Planeswalker', 'Artifact',
  'Enchantment', 'Instant', 'Sorcery', 'Battle', 'Land', 'Other',
] as const;

type TypeBucket = (typeof TYPE_ORDER)[number];

function typeBucket(name: string, fallback: string | undefined): TypeBucket {
  const cached = cardCache.get(name);
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

// CSV parser that respects quoted fields.
export function parseCsvRows(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let val = '';
  let inQ = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQ) {
      if (c === '"') {
        if (text[i + 1] === '"') { val += '"'; i++; }
        else inQ = false;
      } else val += c;
      continue;
    }
    if (c === '"') inQ = true;
    else if (c === ',') { row.push(val); val = ''; }
    else if (c === '\n' || c === '\r') {
      if (val !== '' || row.length) {
        row.push(val);
        if (row.some((x) => x !== '')) rows.push(row);
      }
      row = [];
      val = '';
      if (c === '\r' && text[i + 1] === '\n') i++;
    } else val += c;
  }
  if (val !== '' || row.length) {
    row.push(val);
    if (row.some((x) => x !== '')) rows.push(row);
  }
  return rows;
}

export function parseOwnedFile(text: string): Map<string, number> {
  const stripped = (text || '').replace(/^﻿/, '');
  const rows = parseCsvRows(stripped);
  const out = new Map<string, number>();
  if (rows.length) {
    const headers = rows[0].map((c) => c.trim().toLowerCase());
    const ni = headers.indexOf('name');
    const qi = headers.indexOf('quantity');
    if (ni !== -1 && qi !== -1) {
      rows.slice(1).forEach((r) => {
        const name = (r[ni] || '').trim();
        if (!name) return;
        const q = parseInt((r[qi] || '1').trim(), 10) || 1;
        out.set(name, (out.get(name) || 0) + q);
      });
      return out;
    }
  }
  // Text path: `1x Card Name` or bare names
  stripped.split('\n').forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed) return;
    const m = trimmed.match(/^(\d+)x?\s+(.+)$/i);
    if (m) {
      const q = parseInt(m[1], 10) || 1;
      const name = m[2].trim();
      out.set(name, (out.get(name) || 0) + q);
    } else {
      out.set(trimmed, (out.get(trimmed) || 0) + 1);
    }
  });
  return out;
}

function loadOwned(): Map<string, number> {
  try {
    const raw = localStorage.getItem(SHOP_OWNED_KEY);
    if (raw) return new Map(JSON.parse(raw));
  } catch {
    // ignore
  }
  return new Map();
}

function saveOwned(map: Map<string, number>): void {
  try {
    localStorage.setItem(SHOP_OWNED_KEY, JSON.stringify([...map]));
  } catch {
    // ignore
  }
}

interface AggregateInfo {
  qty: number;
  fallbackType: string;
  isCommander: boolean;
  decks: Set<string>;
}

export function aggregateCards(selectedSlugs: Set<string>, allDecks: DeckFull[]): Map<string, AggregateInfo> {
  const map = new Map<string, AggregateInfo>();
  selectedSlugs.forEach((slug) => {
    const d = allDecks.find((x) => x.slug === slug);
    if (!d) return;
    if (d.commander) {
      const cur = map.get(d.commander);
      if (cur) cur.decks.add(slug);
      else map.set(d.commander, {
        qty: 1, fallbackType: 'Creature', isCommander: true, decks: new Set([slug]),
      });
    }
    if (d.partner) {
      const cur = map.get(d.partner);
      if (cur) cur.decks.add(slug);
      else map.set(d.partner, {
        qty: 1, fallbackType: 'Creature', isCommander: true, decks: new Set([slug]),
      });
    }
    (d.list || []).forEach((group) => {
      if (group.name === 'Commander') return;
      (group.cards || []).forEach((c) => {
        if (!c.n || BASIC_LANDS.has(c.n)) return;
        const cur = map.get(c.n);
        if (cur) cur.decks.add(slug);
        else map.set(c.n, {
          qty: 1, fallbackType: c.type || 'Other', isCommander: false, decks: new Set([slug]),
        });
      });
    });
  });
  return map;
}

interface ShopRowCard extends AggregateInfo {
  name: string;
  reservedBy: number;
}

export function splitOwnership(
  cardMap: Map<string, AggregateInfo>,
  ownedMap: Map<string, number>,
  builtClaims: Map<string, number> = new Map(),
): { buy: ShopRowCard[]; own: ShopRowCard[] } {
  // planned shape required by computeBuyOwnSplit
  const planned = new Map<string, AggregateInfo & { quantity: number }>();
  cardMap.forEach((info, name) => planned.set(name, { ...info, quantity: info.qty }));
  const split = computeBuyOwnSplit(planned, ownedMap, builtClaims);
  const toRow = (r: { name: string; info: AggregateInfo; qty: number; reservedBy: number }): ShopRowCard => ({
    name: r.name,
    qty: r.qty,
    fallbackType: r.info.fallbackType,
    isCommander: r.info.isCommander,
    decks: r.info.decks,
    reservedBy: r.reservedBy,
  });
  return { buy: split.buy.map(toRow), own: split.own.map(toRow) };
}

const MANA_LETTER: Record<string, string> = { W: 'W', U: 'U', B: 'B', R: 'R', G: 'G', C: 'C' };

function ManaCostInline({ cost }: { cost: string | undefined }) {
  if (!cost) return null;
  const symbols = cost.match(/\{[^}]+\}/g) || [];
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

function deckDotColor(colorsGlyph: string | undefined): string {
  const map: Record<string, string> = {
    '⚪': '#c4b998', '🔵': '#1a7cc0', '⚫': '#4a3a5c',
    '🔴': '#c23028', '🟢': '#2d8a56', '◇': '#6B7280',
  };
  const chars = Array.from(colorsGlyph || '');
  if (chars.length === 0) return '#6B7280';
  if (chars.length === 1) return map[chars[0]] || '#6B7280';
  const a = map[chars[0]] || '#6B7280';
  const b = map[chars[chars.length - 1]] || '#6B7280';
  return `linear-gradient(135deg, ${a} 50%, ${b} 50%)`;
}

interface ShopRowProps {
  name: string;
  qty: number;
  decks: Set<string>;
  multiDeck: boolean;
  allDecks: DeckFull[];
  fallbackType: string;
  reservedBy: number;
}

function ShopRow({ name, qty, decks, multiDeck, allDecks, fallbackType, reservedBy }: ShopRowProps) {
  // Subscribe to Scryfall arrival for this row.
  const [, bump] = useState(0);
  useEffect(() => {
    if (!name) return;
    const unsub = cardCache.subscribe(name, () => bump((n) => n + 1));
    cardCache.enqueue(name);
    return unsub;
  }, [name]);
  const entry = cardCache.get(name);
  const price = entry?.price || null;
  const mana = entry?.mana_cost || null;
  const isLand = (entry?.type_line || fallbackType || '').toLowerCase().includes('land');

  return (
    <div className="gv1-shop-row" data-card-name={name} role="row">
      <span className="gv1-shop-row-qty gv1-mono-xs gv1-dim">{qty}×</span>
      <span className="gv1-shop-row-name gv1-serif-md">{name}</span>
      {!isLand && mana && <ManaCostInline cost={mana} />}
      {isLand && <span className="gv1-shop-row-mana gv1-mono-xs gv1-dim">LAND</span>}
      {multiDeck && (
        <span className="gv1-shop-row-decks">
          {[...decks].slice(0, 6).map((slug) => {
            const d = allDecks.find((x) => x.slug === slug);
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
      {reservedBy > 0 && (
        <span className="gv1-shop-row-reserved gv1-mono-xs gv1-dim">
          Reserved by {reservedBy} built deck{reservedBy === 1 ? '' : 's'}
        </span>
      )}
    </div>
  );
}

interface RowGroup {
  name: string | null;
  cards: ShopRowCard[];
}

function groupRows(cards: ShopRowCard[], mode: 'type' | 'az'): RowGroup[] {
  if (mode === 'az') {
    return [{ name: null, cards: [...cards].sort((a, b) => a.name.localeCompare(b.name)) }];
  }
  const buckets: Partial<Record<TypeBucket, ShopRowCard[]>> = {};
  cards.forEach((c) => {
    const t = c.isCommander ? 'Commander' : typeBucket(c.name, c.fallbackType);
    (buckets[t] ||= []).push(c);
  });
  return TYPE_ORDER.filter((t) => buckets[t]?.length).map((t) => ({
    name: t,
    cards: (buckets[t] || []).sort((a, b) => a.name.localeCompare(b.name)),
  }));
}

function summarizePrice(cards: ShopRowCard[]): { sum: number; priced: number; total: number } {
  let sum = 0;
  let priced = 0;
  cards.forEach((c) => {
    const e = cardCache.get(c.name);
    if (e?.price) {
      const n = parseFloat(String(e.price).replace(/[^0-9.]/g, ''));
      if (!Number.isNaN(n)) {
        sum += n * c.qty;
        priced++;
      }
    }
  });
  return { sum, priced, total: cards.length };
}

export interface ShoppingProps {
  decks: DeckFull[];
}

export function Shopping({ decks }: ShoppingProps) {
  const [selected, setSelected] = useState<Set<string>>(() =>
    new Set(decks.length ? [decks[0].slug] : []),
  );
  const { built, toggle: toggleBuilt, setAll: setAllBuilt, clear: clearBuilt } = useBuiltDecks();
  const [owned, setOwned] = useState<Map<string, number>>(() => loadOwned());
  const [sortMode, setSortMode] = useState<'type' | 'az'>('type');
  const [ownedCollapsed, setOwnedCollapsed] = useState(true);
  const [importMsg, setImportMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [copyState, setCopyState] = useState<'ok' | 'err' | null>(null);
  const [, bump] = useState(0);
  const fileRef = useRef<HTMLInputElement>(null);

  // Slow re-render so price summary refreshes as Scryfall data arrives.
  useEffect(() => {
    const id = window.setInterval(() => bump((n) => n + 1), 1500);
    return () => window.clearInterval(id);
  }, []);

  // Default-select the first deck on initial arrival only — re-firing on
  // selected.size would undo the user's "None" / clear-all action.
  const didInitSelectionRef = useRef(false);
  useEffect(() => {
    if (didInitSelectionRef.current) return;
    if (!decks.length) return;
    didInitSelectionRef.current = true;
    setSelected(new Set([decks[0].slug]));
  }, [decks]);

  const cardMap = useMemo(() => aggregateCards(selected, decks), [selected, decks]);
  const builtClaims = useMemo(() => aggregateBuiltClaims(built, decks), [built, decks]);
  const { buy, own } = useMemo(
    () => splitOwnership(cardMap, owned, builtClaims),
    [cardMap, owned, builtClaims],
  );
  const buyGroups = useMemo(() => groupRows(buy, sortMode), [buy, sortMode]);
  const ownGroups = useMemo(() => groupRows(own, sortMode), [own, sortMode]);

  const buyTotal = buy.reduce((s, c) => s + c.qty, 0);
  const ownTotal = own.reduce((s, c) => s + c.qty, 0);
  const priceSummary = summarizePrice(buy);

  const toggleDeck = (slug: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(slug)) next.delete(slug);
      else {
        next.add(slug);
        // Mutually exclusive with the Built rail (legacy behavior).
        if (built.has(slug)) toggleBuilt(slug);
      }
      return next;
    });
  };
  const selectAll = () => setSelected(new Set(decks.map((d) => d.slug)));
  const clearSelection = () => setSelected(new Set());

  const toggleBuiltDeckLocal = (slug: string) => {
    if (selected.has(slug)) {
      setSelected((prev) => {
        const next = new Set(prev);
        next.delete(slug);
        return next;
      });
    }
    toggleBuilt(slug);
  };
  const allBuiltSelected = decks.length > 0 && built.size === decks.length;
  const toggleBuiltAll = () => {
    if (allBuiltSelected) {
      clearBuilt();
    } else {
      setAllBuilt(decks.map((d) => d.slug));
      // Drop any selected decks that just became built.
      setSelected(new Set());
    }
  };

  const onFile = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const parsed = parseOwnedFile(text);
      if (!parsed.size) {
        setImportMsg({ ok: false, text: 'No cards detected in that file.' });
        return;
      }
      const merged = new Map(owned);
      parsed.forEach((q, n) => merged.set(n, (merged.get(n) || 0) + q));
      setOwned(merged);
      saveOwned(merged);
      const totalCards = [...parsed.values()].reduce((s, q) => s + q, 0);
      setImportMsg({ ok: true, text: `Imported ${parsed.size} unique cards (${totalCards} total).` });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setImportMsg({ ok: false, text: 'Could not read file: ' + msg });
    }
    e.target.value = '';
  };

  const clearOwned = () => {
    if (!window.confirm('Clear all owned cards? This is local-only and cannot be undone.')) return;
    setOwned(new Map());
    saveOwned(new Map());
    setImportMsg(null);
  };

  const copyBuyList = async () => {
    const lines: string[] = [];
    buyGroups.forEach((g) => g.cards.forEach((c) => lines.push(`${c.qty}x ${c.name}`)));
    if (!lines.length) {
      setCopyState('err');
      window.setTimeout(() => setCopyState(null), 1500);
      return;
    }
    try {
      await navigator.clipboard.writeText(lines.join('\n'));
      setCopyState('ok');
      window.setTimeout(() => setCopyState(null), 1500);
    } catch {
      setCopyState('err');
      window.setTimeout(() => setCopyState(null), 1500);
    }
  };

  if (!decks.length) {
    return (
      <section className="gv1-section">
        <div className="gv1-empty">
          <span className="gv1-rune">◇</span>
          <span className="gv1-mono-xs">No decks loaded.</span>
        </div>
      </section>
    );
  }

  return (
    <>
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

      <section className="gv1-section gv1-shop-section">
        <div className="gv1-shop-rail-head">
          <span className="gv1-mono-xs gv1-dim">BUILT DECKS</span>
          <span className="gv1-mono-xs gv1-dim">· {built.size} reserved</span>
          <span className="gv1-shop-rail-spacer" />
          <button
            id="shopping-built-select-all"
            className="gv1-shop-mini-btn"
            onClick={toggleBuiltAll}
            type="button"
            disabled={decks.length === 0}
          >
            {allBuiltSelected ? 'None' : 'All'}
          </button>
        </div>
        <div className="gv1-shop-built-chips" role="group" aria-label="Built decks (reserves owned cards)">
          {decks.map((d) => {
            const on = built.has(d.slug);
            return (
              <button
                key={d.slug}
                type="button"
                className={'gv1-shop-built-chip' + (on ? ' gv1-active' : '')}
                onClick={() => toggleBuiltDeckLocal(d.slug)}
                aria-pressed={on}
                aria-label={on ? `Unmark ${d.deckName} as built` : `Mark ${d.deckName} as built`}
                title={on ? `Unmark ${d.deckName} as built` : `Mark ${d.deckName} as built`}
              >
                <span className="gv1-shop-chip-pips"><GV1ManaPips colors={d.colors} /></span>
                <span className="gv1-shop-chip-name gv1-serif-sm">{d.deckName}</span>
                <span className="gv1-shop-built-check" aria-hidden="true">✓</span>
              </button>
            );
          })}
        </div>
        <p className="gv1-mono-xs gv1-dim gv1-shop-built-note">
          // Cards in built decks reserve owned copies before the buy list is computed.
        </p>
      </section>

      <section className="gv1-section gv1-shop-section">
        <div className="gv1-shop-rail-head">
          <span className="gv1-mono-xs gv1-dim">SELECT DECKS</span>
          <span className="gv1-mono-xs gv1-dim">· {selected.size} of {decks.length}</span>
          <span className="gv1-shop-rail-spacer" />
          <button className="gv1-shop-mini-btn" onClick={selectAll} type="button">Select all</button>
          <button className="gv1-shop-mini-btn" onClick={clearSelection} type="button" disabled={selected.size === 0}>Clear</button>
        </div>
        <div className="gv1-shop-chips" role="group" aria-label="Deck selection">
          {decks.map((d) => {
            const on = selected.has(d.slug);
            return (
              <button
                key={d.slug}
                type="button"
                className={'gv1-shop-chip' + (on ? ' gv1-active' : '')}
                onClick={() => toggleDeck(d.slug)}
                aria-pressed={on}
                aria-label={on ? `Remove ${d.deckName}` : `Add ${d.deckName}`}
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
          <div
            role={importMsg.ok ? 'status' : 'alert'}
            className={'gv1-shop-import-msg ' + (importMsg.ok ? 'gv1-shop-import-ok' : 'gv1-shop-import-err')}
          >
            <span className="gv1-mono-xs">{importMsg.ok ? '◆' : '⚠'}</span>
            <span className="gv1-mono-xs">{importMsg.text}</span>
          </div>
        )}
      </section>

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
                  aria-pressed={sortMode === 'type'}
                >Type</button>
                <button
                  type="button"
                  className={'gv1-shop-mini-btn' + (sortMode === 'az' ? ' gv1-active' : '')}
                  onClick={() => setSortMode('az')}
                  aria-pressed={sortMode === 'az'}
                >A–Z</button>
              </div>
              <button
                type="button"
                className={
                  'gv1-shop-btn gv1-shop-btn-primary'
                  + (copyState === 'ok' ? ' gv1-shop-btn-success' : copyState === 'err' ? ' gv1-shop-btn-error' : '')
                }
                onClick={copyBuyList}
                disabled={buy.length === 0}
              >
                {copyState === 'ok' ? '✓ Copied' : copyState === 'err' ? '⚠ Failed' : 'Copy buy list'}
              </button>
            </div>
          </div>
        </section>
      )}

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
                  {g.cards.map((c) => (
                    <ShopRow
                      key={c.name}
                      name={c.name}
                      qty={c.qty}
                      decks={c.decks}
                      multiDeck={selected.size > 1}
                      allDecks={decks}
                      fallbackType={c.fallbackType}
                      reservedBy={c.reservedBy}
                    />
                  ))}
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {selected.size > 0 && own.length > 0 && (
        <section className={'gv1-section gv1-shop-section gv1-shop-own-section' + (ownedCollapsed ? ' gv1-shop-collapsed' : '')}>
          <button
            type="button"
            className="gv1-shop-own-head"
            onClick={() => setOwnedCollapsed((c) => !c)}
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
                  {g.cards.map((c) => (
                    <ShopRow
                      key={c.name}
                      name={c.name}
                      qty={c.qty}
                      decks={c.decks}
                      multiDeck={selected.size > 1}
                      allDecks={decks}
                      fallbackType={c.fallbackType}
                      reservedBy={c.reservedBy}
                    />
                  ))}
                </div>
              ))}
            </div>
          )}
        </section>
      )}

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
    </>
  );
}
