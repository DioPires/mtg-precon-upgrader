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

const SCRYFALL_DEBOUNCE_MS = 220;
const MAX_SUGGESTIONS = 10;

export interface CardAtlasProps {
  decks: DeckFull[];
}

export function CardAtlas({ decks }: CardAtlasProps) {
  const navigate = useNavigate();
  const index = useMemo(() => buildCardAtlasIndex(decks), [decks]);
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
      const remote = await scryfallSuggest(query, fetch, ctrl.signal);
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
          Type any card. The Atlas charts which of your {decks.length} tomes already use it,
          what role it plays, and whether you own a copy.
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
              const inDecks = index.byName.has(frontFace(s).toLowerCase());
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
                  <span className={'gv1-mono-xs ' + (inDecks ? 'gv1-rune' : 'gv1-dim')}>
                    {inDecks ? 'in tomes' : 'scryfall'}
                  </span>
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
                ◇ No tome currently lists this card. Pull it into a deck via the Apothecary or
                Shopping surfaces.
              </p>
            </div>
          ) : (
            <ul className="gv1-atlas-usage-list">
              {usages.map((u, i) => (
                <li key={`${u.deckSlug}-${i}`} className="gv1-atlas-usage">
                  <button
                    type="button"
                    className="gv1-atlas-usage-btn"
                    onClick={() => navigate(`/deck/${u.deckSlug}`)}
                  >
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
                      {u.qty > 1 && (
                        <span className="gv1-mono-xs gv1-dim">×{u.qty}</span>
                      )}
                      <span className="gv1-mono-xs gv1-dim gv1-atlas-usage-bracket">{u.bracket}</span>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {!selected && (
        <div className="gv1-atlas-hint">
          <p className="gv1-mono-xs gv1-dim">
            ◇ Start typing. Names that already appear in your tomes are highlighted; anything
            else falls through to Scryfall's full card index.
          </p>
        </div>
      )}
    </section>
  );
}
