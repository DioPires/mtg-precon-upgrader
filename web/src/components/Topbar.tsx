import { useEffect, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { deckLoader } from '../data/loader';
import { LAST_DECK_KEY } from '../data/lastDeck';

function readLastDeck(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    const v = window.localStorage.getItem(LAST_DECK_KEY);
    return v && v !== '_' ? v : null;
  } catch {
    return null;
  }
}

type NavItem = { rune: string; label: string } & (
  | { kind: 'static'; to: string }
  | { kind: 'deck'; surface: 'deck' | 'scrying' }
);

const NAV_ITEMS: NavItem[] = [
  { kind: 'static', to: '/codex', rune: 'I', label: 'Codex' },
  { kind: 'deck', surface: 'deck', rune: 'II', label: 'Guide' },
  { kind: 'deck', surface: 'scrying', rune: 'VIII', label: 'Scrying' },
  { kind: 'static', to: '/shopping', rune: 'IX', label: 'Shopping' },
  { kind: 'static', to: '/compare', rune: 'X', label: 'Compare' },
];

export function Topbar() {
  const { pathname } = useLocation();
  const [storedDeckId, setStoredDeckId] = useState<string | null>(() => readLastDeck());

  // Pick up writes from DeckGuide / Scrying when navigation occurs.
  // Only adopt non-null reads — the first-visit fallback below seeds storedDeckId
  // from the index when LS is empty, and we don't want a no-op LS read to clobber it.
  useEffect(() => {
    const stored = readLastDeck();
    if (stored && stored !== storedDeckId) setStoredDeckId(stored);
  }, [pathname, storedDeckId]);

  // First-visit fallback: resolve to first commander in the index.
  useEffect(() => {
    if (storedDeckId) return;
    let cancelled = false;
    deckLoader
      .loadIndex()
      .then((idx) => {
        if (cancelled) return;
        const first = idx.commanders[0]?.id;
        if (first) setStoredDeckId(first);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [storedDeckId]);

  const urlMatch = pathname.match(/^\/(?:deck|scrying|m)\/([^/]+)/);
  const fromUrl = urlMatch && urlMatch[1] !== '_' ? urlMatch[1] : null;
  const activeDeckId = fromUrl ?? storedDeckId;

  return (
    <header className="gv1-topbar" role="banner">
      <div className="gv1-topbar-left">
        <span className="gv1-sigil-sm" aria-hidden="true">◈</span>
        <span className="gv1-mono-xs">grimoire@commander:~$</span>
        <span className="gv1-mono-xs gv1-dim">// the grimoire</span>
      </div>
      <nav className="gv1-topbar-nav" role="navigation" aria-label="Surfaces">
        {NAV_ITEMS.map((item) => {
          const to =
            item.kind === 'deck'
              ? activeDeckId
                ? `/${item.surface}/${activeDeckId}`
                : '/codex'
              : item.to;
          const active =
            item.kind === 'deck'
              ? pathname.startsWith(`/${item.surface}/`)
              : pathname === item.to;
          return (
            <NavLink
              key={item.label}
              to={to}
              className={['gv1-nav-item', active ? 'gv1-active' : ''].filter(Boolean).join(' ')}
              aria-current={active ? 'page' : undefined}
            >
              <span className="gv1-mono-xs gv1-dim gv1-nav-rune" aria-hidden="true">§{item.rune}</span>
              <span className="gv1-mono-xs gv1-nav-label">{item.label}</span>
            </NavLink>
          );
        })}
      </nav>
      <div className="gv1-topbar-right">
        <span className="gv1-mono-xs gv1-dim" aria-hidden="true">⌘K</span>
        <span className="gv1-mono-xs">search</span>
        <span className="gv1-mono-xs gv1-dim gv1-sep" aria-hidden="true">│</span>
        <span className="gv1-mono-xs gv1-rune">scaffold · phase 0</span>
      </div>
    </header>
  );
}
