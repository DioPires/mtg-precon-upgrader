// DEC-197 — Card Atlas surface.
//
// Card-name reverse lookup: type a card name, see every built deck it appears
// in plus the role it plays inside that deck. Hybrid autocomplete (built-deck
// names matched locally first; Scryfall fallback for unknown names) and an
// "owned" badge sourced from the same localStorage map Shopping uses.

import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { DeckFull } from '../../data/types';
import {
  buildCardAtlasIndex,
  loadOwnedMap,
  localSuggest,
  scryfallSuggest,
  type CardUsage,
} from '../../data/cardAtlas';
import { frontFace } from '../../data/cardName';
import { Glyph } from '../atoms/Glyph';

const SCRYFALL_DEBOUNCE_MS = 220;
const MAX_SUGGESTIONS = 10;

export interface CardAtlasProps {
  decks: DeckFull[];
}

/** One deck row inside a usage list. Shared by the built and brewing lists. */
function UsageRow({ usage: u, onOpen }: { usage: CardUsage; onOpen: () => void }) {
  return (
    <li className="gv1-atlas-usage">
      <button type="button" className="gv1-atlas-usage-btn" onClick={onOpen}>
        <div className="gv1-atlas-usage-l">
          <span className="gv1-atlas-usage-colors" aria-hidden="true">{u.colors || '◯'}</span>
          <div>
            <div className="gv1-serif-md">{u.deckName}</div>
            <div className="gv1-mono-xs gv1-dim">
              {u.commander}{u.partner ? ` & ${u.partner}` : ''}
            </div>
          </div>
        </div>
        <div className="gv1-atlas-usage-r">
          <span className="gv1-mono-xs gv1-rune gv1-atlas-usage-role">{u.role}</span>
          {u.qty > 1 && <span className="gv1-mono-xs gv1-dim">×{u.qty}</span>}
          <span className="gv1-mono-xs gv1-dim gv1-atlas-usage-bracket">{u.bracket}</span>
        </div>
      </button>
    </li>
  );
}

export function CardAtlas({ decks }: CardAtlasProps) {
  const navigate = useNavigate();
  const index = useMemo(() => buildCardAtlasIndex(decks), [decks]);
  const brewingCount = decks.filter((d) => d.status === 'brewing').length;
  const builtCount = decks.length - brewingCount;
  // Owned map refreshes on cross-tab storage events and tab focus so a CSV
  // imported on /shopping in another tab (or before /atlas was opened) shows
  // up without a manual reload (DEC-325).
  const [owned, setOwned] = useState<Map<string, number>>(() => loadOwnedMap());
  useEffect(() => {
    const refresh = () => setOwned(loadOwnedMap());
    window.addEventListener('storage', refresh);
    window.addEventListener('focus', refresh);
    return () => {
      window.removeEventListener('storage', refresh);
      window.removeEventListener('focus', refresh);
    };
  }, []);

  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<string>('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [highlight, setHighlight] = useState<number>(-1);
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const listboxId = 'gv1-atlas-suggestions';

  // Local suggestions are instant; Scryfall fills in via debounced async fetch.
  useEffect(() => {
    const local = localSuggest(query, index.names, MAX_SUGGESTIONS);
    setSuggestions(local);
    setHighlight(local.length ? 0 : -1);

    if (query.trim().length < 2) return;
    const ctrl = new AbortController();
    const t = window.setTimeout(async () => {
      const remote = await scryfallSuggest(query, ctrl.signal);
      if (ctrl.signal.aborted) return;
      const localSet = new Set(local.map((n) => n.toLowerCase()));
      const merged = [...local];
      for (const r of remote) {
        if (merged.length >= MAX_SUGGESTIONS) break;
        if (!localSet.has(r.toLowerCase())) merged.push(r);
      }
      setSuggestions(merged);
    }, SCRYFALL_DEBOUNCE_MS);
    return () => {
      window.clearTimeout(t);
      ctrl.abort();
    };
  }, [query, index.names]);

  const usages: CardUsage[] = useMemo(() => {
    if (!selected) return [];
    return index.byName.get(frontFace(selected).toLowerCase()) || [];
  }, [selected, index.byName]);

  // Brewing usages are reported separately (DEC-568) — they never count toward
  // USED IN, and never merge into the built-deck list.
  const brewingUsages: CardUsage[] = useMemo(() => {
    if (!selected) return [];
    return index.brewingByName.get(frontFace(selected).toLowerCase()) || [];
  }, [selected, index.brewingByName]);

  const ownedQty = useMemo(() => {
    if (!selected) return 0;
    return owned.get(frontFace(selected).toLowerCase()) || 0;
  }, [selected, owned]);

  const choose = (name: string) => {
    setSelected(name);
    setQuery(name);
    setOpen(false);
    setHighlight(-1);
    inputRef.current?.blur();
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setOpen(true);
      setHighlight((i) => Math.min(suggestions.length - 1, i + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlight((i) => Math.max(0, i - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (highlight >= 0 && suggestions[highlight]) choose(suggestions[highlight]);
      else if (suggestions[0]) choose(suggestions[0]);
      else if (query.trim()) choose(query.trim());
    } else if (e.key === 'Escape') {
      setOpen(false);
      setHighlight(-1);
    }
  };

  return (
    <section className="gv1-atlas" aria-labelledby="atlas-title">
      <div className="gv1-atlas-head">
        <div className="gv1-atlas-eyebrow">
          <span className="gv1-rune" aria-hidden="true">◈</span>
          <span className="gv1-mono-xs">CARD ATLAS · REVERSE LOOKUP</span>
          <span className="gv1-mono-xs gv1-dim">— where does this card live?</span>
        </div>
        <h1 id="atlas-title" className="gv1-atlas-title">
          The <em>Atlas</em>
        </h1>
        <p className="gv1-atlas-sub">
          Type any card. The Atlas charts which of your {builtCount} built tomes already use it,
          what role it plays, and whether you own a copy
          {brewingCount > 0 && ` — with your ${brewingCount} brews listed separately`}.
        </p>
      </div>

      <div className="gv1-atlas-search" role="combobox" aria-expanded={open && suggestions.length > 0} aria-haspopup="listbox" aria-owns={listboxId}>
        <label className="gv1-mono-xs gv1-dim" htmlFor="gv1-atlas-input">card name</label>
        <input
          ref={inputRef}
          id="gv1-atlas-input"
          type="text"
          autoComplete="off"
          spellCheck={false}
          className="gv1-atlas-input"
          placeholder="e.g. Sol Ring, Cyclonic Rift, Dockside …"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
            if (selected && e.target.value !== selected) setSelected('');
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => window.setTimeout(() => setOpen(false), 120)}
          onKeyDown={onKeyDown}
          aria-autocomplete="list"
          aria-controls={listboxId}
          aria-activedescendant={highlight >= 0 ? `${listboxId}-${highlight}` : undefined}
        />
        {open && suggestions.length > 0 && (
          <ul id={listboxId} role="listbox" className="gv1-atlas-listbox">
            {suggestions.map((s, i) => {
              const key = frontFace(s).toLowerCase();
              const inDecks = index.byName.has(key);
              const inBrewingOnly = !inDecks && index.brewingByName.has(key);
              return (
                <li
                  key={s}
                  id={`${listboxId}-${i}`}
                  role="option"
                  aria-selected={i === highlight}
                  className={'gv1-atlas-option' + (i === highlight ? ' gv1-atlas-option-active' : '')}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    choose(s);
                  }}
                  onMouseEnter={() => setHighlight(i)}
                >
                  <span className="gv1-atlas-option-name">{s}</span>
                  {inBrewingOnly ? (
                    <span className="gv1-mono-xs gv1-brewing-pill">brewing</span>
                  ) : (
                    <span className={'gv1-mono-xs ' + (inDecks ? 'gv1-rune' : 'gv1-dim')}>
                      {inDecks ? 'in tomes' : 'scryfall'}
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {selected && (
        <div className="gv1-atlas-result" aria-live="polite">
          <div className="gv1-atlas-result-head">
            <div>
              <div className="gv1-mono-xs gv1-dim">searching for</div>
              <div className="gv1-serif-xxl">{selected}</div>
            </div>
            <div className="gv1-atlas-result-stats">
              <div className="gv1-atlas-result-stat">
                <div className="gv1-mono-xs gv1-dim">USED IN</div>
                <div className="gv1-serif-xl">{usages.length}</div>
                <div className="gv1-mono-xs gv1-dim">tome{usages.length === 1 ? '' : 's'}</div>
              </div>
              <div className="gv1-atlas-result-stat">
                <div className="gv1-mono-xs gv1-dim">BREWING</div>
                <div
                  className={
                    'gv1-serif-xl ' + (brewingUsages.length > 0 ? 'gv1-atlas-brewing-num' : 'gv1-dim')
                  }
                >
                  {brewingUsages.length > 0 ? brewingUsages.length : '—'}
                </div>
                <div className="gv1-mono-xs gv1-dim">
                  {brewingUsages.length > 0
                    ? `brew${brewingUsages.length === 1 ? '' : 's'}`
                    : 'no brews'}
                </div>
              </div>
              <div className="gv1-atlas-result-stat">
                <div className="gv1-mono-xs gv1-dim">OWNED</div>
                <div className={'gv1-serif-xl ' + (ownedQty > 0 ? 'gv1-rune' : 'gv1-dim')}>
                  {ownedQty > 0 ? `×${ownedQty}` : '—'}
                </div>
                <div className="gv1-mono-xs gv1-dim">{ownedQty > 0 ? 'in inventory' : 'not imported'}</div>
              </div>
            </div>
          </div>

          {usages.length === 0 ? (
            <div className="gv1-atlas-empty">
              <p className="gv1-mono-xs gv1-dim">
                {brewingUsages.length > 0 ? (
                  <>
                    <Glyph>◇ </Glyph>No built tome lists this card — it only appears in the brewing decks below.
                  </>
                ) : (
                  <>
                    <Glyph>◇ </Glyph>No tome currently lists this card. Pull it into a deck via the Apothecary or
                    Shopping surfaces.
                  </>
                )}
              </p>
            </div>
          ) : (
            <ul className="gv1-atlas-usage-list">
              {usages.map((u, i) => (
                <UsageRow
                  key={`${u.deckSlug}-${i}`}
                  usage={u}
                  onOpen={() => navigate(`/deck/${u.deckSlug}`)}
                />
              ))}
            </ul>
          )}

          {brewingUsages.length > 0 && (
            <section className="gv1-atlas-brewing" aria-labelledby="atlas-brewing-title">
              <div className="gv1-atlas-brewing-head">
                <h2 id="atlas-brewing-title" className="gv1-mono-xs gv1-atlas-brewing-title">
                  IN BREWING DECKS
                </h2>
                <span className="gv1-mono-xs gv1-dim">
                  — virtual builds, not physically assembled
                </span>
              </div>
              <ul className="gv1-atlas-usage-list gv1-atlas-usage-list-brewing">
                {brewingUsages.map((u, i) => (
                  <UsageRow
                    key={`brewing-${u.deckSlug}-${i}`}
                    usage={u}
                    onOpen={() => navigate(`/deck/${u.deckSlug}`)}
                  />
                ))}
              </ul>
            </section>
          )}
        </div>
      )}

      {!selected && (
        <div className="gv1-atlas-hint">
          <p className="gv1-mono-xs gv1-dim">
            <Glyph>◇ </Glyph>Start typing. Names that already appear in your tomes are highlighted; anything
            else falls through to Scryfall's full card index.
          </p>
        </div>
      )}
    </section>
  );
}
