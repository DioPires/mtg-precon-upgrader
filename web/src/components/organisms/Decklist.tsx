// Manifest section. Two grouping modes (by role / by type) + copy-full-list.
// Role grouping is the redesign default; type grouping mirrors Shopping's bucket
// order. Mode persists in `?manifest=type|role` URL state.

import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ManaCost } from '../atoms/ManaCost';
import { TYPE_ORDER, typeBucket, type TypeBucket } from '../../lib/cardType';
import type { DeckCardTile, DeckListGroup } from '../../data/types';

interface DecklistProps {
  list: DeckListGroup[];
  commander: string;
}

export type ManifestMode = 'role' | 'type';

export function cardCount(cards: DeckCardTile[]): number {
  return cards.reduce((n, c) => n + (c.qty ?? 1), 0);
}

/**
 * Group cards by type bucket, pinning the commander at the top.
 * Iterates the role-grouped list, skipping the synthetic Commander group, and
 * re-buckets cards via the shared `typeBucket` helper. Output groups follow
 * `TYPE_ORDER`; cards within each group sort alphabetically.
 */
export function groupByType(list: DeckListGroup[], commander: string): DeckListGroup[] {
  const buckets: Partial<Record<TypeBucket, DeckCardTile[]>> = {};
  list.forEach((g) => {
    if (g.name === 'Commander') return;
    g.cards.forEach((c) => {
      const t = typeBucket(c.n, c.type);
      (buckets[t] ||= []).push(c);
    });
  });
  const out: DeckListGroup[] = [];
  out.push({
    name: 'Commander',
    cards: [{ n: commander, mv: '—', type: 'Commander', price: '—', gc: false }],
  });
  TYPE_ORDER.forEach((t) => {
    if (t === 'Commander') return;
    const cards = buckets[t];
    if (!cards?.length) return;
    out.push({
      name: `${t} (${cardCount(cards)})`,
      cards: [...cards].sort((a, b) => a.n.localeCompare(b.n)),
    });
  });
  return out;
}

/**
 * Serialize the full deck list to Moxfield/Archidekt-pasteable text:
 *   1x {commander}
 *   {qty}x {card name}            (alphabetical by name; basics keep their qty)
 * Pure + deterministic — input list+commander → identical output every time.
 */
export function serializeFullList(list: DeckListGroup[], commander: string): string {
  const totals = new Map<string, number>();
  list.forEach((g) => {
    if (g.name === 'Commander') return;
    g.cards.forEach((c) => {
      totals.set(c.n, (totals.get(c.n) || 0) + (c.qty ?? 1));
    });
  });
  const lines = [`1x ${commander}`];
  [...totals.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .forEach(([name, qty]) => lines.push(`${qty}x ${name}`));
  return lines.join('\n');
}

export function Decklist({ list, commander }: DecklistProps) {
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

  const view = useMemo(
    () => (mode === 'type' ? groupByType(list, commander) : list),
    [mode, list, commander],
  );
  const total = view.reduce((n, g) => n + cardCount(g.cards), 0);
  const sortedBy = mode === 'type' ? 'sorted by type' : 'sorted by function';

  const copyAll = async () => {
    const text = serializeFullList(list, commander);
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
        <span className="gv1-rune" aria-hidden="true">§ VII</span>
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
