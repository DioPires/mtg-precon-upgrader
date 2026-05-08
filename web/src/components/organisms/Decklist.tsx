// Manifest section. Two grouping modes (by role / by type) + copy-full-list.
// Role grouping is the redesign default; type grouping mirrors Shopping's bucket
// order. Mode persists in `?manifest=type|role` URL state.

import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ManaCost } from '../atoms/ManaCost';
import { TYPE_ORDER, typeBucket, type TypeBucket } from '../../lib/cardType';
import { cardCache } from '../../data/cardCache';
import type { DeckCardTile, DeckListGroup } from '../../data/types';

interface DecklistProps {
  list: DeckListGroup[];
  commander: string;
  partner?: string;
}

/** Synthetic group name used to pin commander(s) at the top of the manifest. */
const COMMANDER_GROUPS = new Set(['Commander', 'Commanders']);

export type ManifestMode = 'role' | 'type';

export function cardCount(cards: DeckCardTile[]): number {
  return cards.reduce((n, c) => n + (c.qty ?? 1), 0);
}

/**
 * Subsection comparator: mana value ascending, alphabetical tiebreak.
 * Tiles without a known cmc collapse to 0 — desirable for lands (cmc=0)
 * and acceptable for not-yet-hydrated entries (the view re-sorts as
 * `cardCache` fills in).
 */
export const byCmcThenName = (a: DeckCardTile, b: DeckCardTile): number => {
  const ca = a.cmc ?? 0;
  const cb = b.cmc ?? 0;
  if (ca !== cb) return ca - cb;
  return a.n.localeCompare(b.n);
};

/**
 * Group cards by type bucket, pinning the commander at the top.
 * Iterates the role-grouped list, skipping the synthetic Commander group, and
 * re-buckets cards via the shared `typeBucket` helper. Output groups follow
 * `TYPE_ORDER`; cards within each group sort by `byCmcThenName` (mana value
 * ascending, alphabetical tiebreak).
 */
export function groupByType(
  list: DeckListGroup[],
  commander: string,
  partner?: string,
): DeckListGroup[] {
  const buckets: Partial<Record<TypeBucket, DeckCardTile[]>> = {};
  list.forEach((g) => {
    if (COMMANDER_GROUPS.has(g.name)) return;
    g.cards.forEach((c) => {
      const t = typeBucket(c.n, c.type);
      (buckets[t] ||= []).push(c);
    });
  });
  const out: DeckListGroup[] = [];
  const commanderCards: DeckCardTile[] = [
    { n: commander, mv: '—', type: 'Commander', price: '—', gc: false },
  ];
  if (partner) {
    commanderCards.push({ n: partner, mv: '—', type: 'Commander', price: '—', gc: false });
  }
  out.push({
    name: partner ? 'Commanders' : 'Commander',
    cards: commanderCards,
  });
  TYPE_ORDER.forEach((t) => {
    if (t === 'Commander') return;
    const cards = buckets[t];
    if (!cards?.length) return;
    out.push({
      name: `${t} (${cardCount(cards)})`,
      cards: [...cards].sort(byCmcThenName),
    });
  });
  return out;
}

/**
 * Serialize the full deck list to Moxfield/Archidekt-pasteable text:
 *   1x {commander}
 *   {qty}x {card name}            (cmc ascending, alphabetical tiebreak)
 * Pure + deterministic — input list+commander → identical output every time.
 */
export function serializeFullList(
  list: DeckListGroup[],
  commander: string,
  partner?: string,
): string {
  const totals = new Map<string, number>();
  const cmcByName = new Map<string, number | undefined>();
  list.forEach((g) => {
    if (COMMANDER_GROUPS.has(g.name)) return;
    g.cards.forEach((c) => {
      totals.set(c.n, (totals.get(c.n) || 0) + (c.qty ?? 1));
      if (!cmcByName.has(c.n)) cmcByName.set(c.n, c.cmc);
    });
  });
  const lines = [`1x ${commander}`];
  if (partner) lines.push(`1x ${partner}`);
  [...totals.entries()]
    .sort((a, b) => {
      const ca = cmcByName.get(a[0]) ?? 0;
      const cb = cmcByName.get(b[0]) ?? 0;
      if (ca !== cb) return ca - cb;
      return a[0].localeCompare(b[0]);
    })
    .forEach(([name, qty]) => lines.push(`${qty}x ${name}`));
  return lines.join('\n');
}

/**
 * Subscribe to `cardCache` for every card name in the manifest so cmc values
 * (Scryfall) flow into tiles for the cmc-ascending sort. Re-renders whenever a
 * card hydrates. The cache itself dedupes + throttles the underlying fetches.
 */
function useNameSet(list: DeckListGroup[]): string[] {
  return useMemo(() => {
    const seen = new Set<string>();
    list.forEach((g) => g.cards.forEach((c) => { if (c.n) seen.add(c.n); }));
    return [...seen];
  }, [list]);
}

interface CardMeta {
  cmc?: number;
  mana_cost?: string;
}

function useCardMetaMap(names: string[]): Map<string, CardMeta> {
  // Bump a version counter whenever any subscribed card hydrates; the resulting
  // re-render rebuilds the map from cardCache (cheap — sync get(), ≤ 99 entries).
  const [version, setVersion] = useState(0);
  useEffect(() => {
    const unsubs = names.map((n) => {
      cardCache.enqueue(n);
      return cardCache.subscribe(n, () => setVersion((v) => v + 1));
    });
    return () => unsubs.forEach((u) => u());
  }, [names]);
  return useMemo(() => {
    const map = new Map<string, CardMeta>();
    names.forEach((n) => {
      const e = cardCache.get(n);
      if (e?.status !== 'loaded') return;
      const meta: CardMeta = {};
      if (typeof e.cmc === 'number') meta.cmc = e.cmc;
      if (typeof e.mana_cost === 'string') meta.mana_cost = e.mana_cost;
      if (meta.cmc != null || meta.mana_cost != null) {
        map.set(n.toLowerCase(), meta);
      }
    });
    return map;
  }, [names, version]);
}

function enrichWithMeta(list: DeckListGroup[], metaMap: Map<string, CardMeta>): DeckListGroup[] {
  return list.map((g) => ({
    ...g,
    cards: g.cards.map((c) => {
      const meta = metaMap.get(c.n.toLowerCase());
      if (!meta) return c;
      const next = { ...c };
      if (meta.cmc != null) next.cmc = meta.cmc;
      // Replace placeholder '—' with real Scryfall mana_cost. Lands keep 'LAND'
      // sentinel; empty mana_cost (some lands/MDFCs) leaves the placeholder.
      if (c.mv !== 'LAND' && meta.mana_cost) next.mv = meta.mana_cost;
      return next;
    }),
  }));
}

export function Decklist({ list, commander, partner }: DecklistProps) {
  const [params, setParams] = useSearchParams();
  const rawMode = params.get('manifest');
  const mode: ManifestMode = rawMode === 'type' ? 'type' : 'role';
  const [copyState, setCopyState] = useState<'ok' | 'err' | null>(null);

  const setMode = (next: ManifestMode) => {
    const sp = new URLSearchParams(params);
    if (next === 'role') sp.delete('manifest');
    else sp.set('manifest', next);
    setParams(sp, { replace: true });
  };

  const names = useNameSet(list);
  const metaMap = useCardMetaMap(names);
  const enriched = useMemo(() => enrichWithMeta(list, metaMap), [list, metaMap]);

  const view = useMemo(() => {
    if (mode === 'type') return groupByType(enriched, commander, partner);
    // Role grouping: preserve normalize.ts group order, sort cards within each
    // subsection by cmc-then-name. Skip the synthetic Commander(s) group.
    return enriched.map((g) =>
      COMMANDER_GROUPS.has(g.name) ? g : { ...g, cards: [...g.cards].sort(byCmcThenName) },
    );
  }, [mode, enriched, commander, partner]);
  const total = view.reduce((n, g) => n + cardCount(g.cards), 0);
  const sortedBy = mode === 'type' ? 'sorted by type' : 'sorted by function';

  const copyAll = async () => {
    const text = serializeFullList(enriched, commander, partner);
    try {
      await navigator.clipboard.writeText(text);
      setCopyState('ok');
    } catch {
      setCopyState('err');
    }
    window.setTimeout(() => setCopyState(null), 1500);
  };

  return (
    <section className="gv1-section gv1-decklist">
      <div className="gv1-section-head">
        <span className="gv1-rune" aria-hidden="true">§ VIII</span>
        <h2 className="gv1-section-title">The Manifest</h2>
        <span className="gv1-mono-xs gv1-dim">
          · {total} cards · {view.length} {mode === 'type' ? 'types' : 'roles'} · {sortedBy}
        </span>
      </div>
      <div className="gv1-dl-toolbar">
        <div className="gv1-dl-toolbar-group">
          <span className="gv1-mono-xs gv1-dim">GROUP</span>
          <button
            type="button"
            role="switch"
            aria-checked={mode === 'role'}
            aria-label="Group by role"
            className={'gv1-shop-mini-btn' + (mode === 'role' ? ' gv1-active' : '')}
            onClick={() => setMode('role')}
          >Role</button>
          <button
            type="button"
            role="switch"
            aria-checked={mode === 'type'}
            aria-label="Group by type"
            className={'gv1-shop-mini-btn' + (mode === 'type' ? ' gv1-active' : '')}
            onClick={() => setMode('type')}
          >Type</button>
        </div>
        <button
          type="button"
          className={
            'gv1-shop-btn'
            + (copyState === 'ok' ? ' gv1-shop-btn-success' : copyState === 'err' ? ' gv1-shop-btn-error' : '')
          }
          onClick={copyAll}
        >
          {copyState === 'ok' ? '✓ Copied' : copyState === 'err' ? '⚠ Failed' : 'Copy decklist'}
        </button>
      </div>
      <div className="gv1-sr-only" aria-live="polite" role="status">
        {copyState === 'ok' ? 'Decklist copied to clipboard' : copyState === 'err' ? 'Could not copy decklist' : ''}
      </div>
      <div className="gv1-decklist-cols">
        {view.map((grp, i) => (
          <div key={i} className="gv1-dl-group">
            <div className="gv1-dl-group-head">
              <span className="gv1-serif-sm">{grp.name}</span>
              <span className="gv1-mono-xs gv1-dim">{cardCount(grp.cards)}</span>
            </div>
            <ul className="gv1-dl-list">
              {grp.cards.map((c, j) => (
                <li
                  key={j}
                  className={'gv1-dl-row' + (c.gc ? ' gv1-dl-gc' : '')}
                  data-card-name={c.n}
                >
                  <span className="gv1-dl-name">
                    {c.gc && <span className="gv1-dl-star">★</span>}
                    {c.n}
                    {c.qty && c.qty > 1 ? (
                      <span className="gv1-dl-qty gv1-mono-xs gv1-dim"> ×{c.qty}</span>
                    ) : null}
                  </span>
                  <span className="gv1-dl-mv">
                    <ManaCost mv={c.mv} />
                  </span>
                  <span className="gv1-dl-price gv1-mono-xs gv1-rune">{c.price}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}
