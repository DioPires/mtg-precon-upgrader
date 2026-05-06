import { useEffect, useId, useRef, useState } from 'react';
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
  const menuId = useId();
  const [storedDeckId, setStoredDeckId] = useState<string | null>(() => readLastDeck());
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

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

  // Close mobile menu on route change.
  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  // Close mobile menu when clicking outside or pressing Escape.
  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMenuOpen(false);
    };
    const onClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('mousedown', onClick);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('mousedown', onClick);
    };
  }, [menuOpen]);

  const urlMatch = pathname.match(/^\/(?:deck|scrying|m)\/([^/]+)/);
  const fromUrl = urlMatch && urlMatch[1] !== '_' ? urlMatch[1] : null;
  const activeDeckId = fromUrl ?? storedDeckId;

  const resolveTo = (item: NavItem): string =>
    item.kind === 'deck'
      ? activeDeckId
        ? `/${item.surface}/${activeDeckId}`
        : '/codex'
      : item.to;

  const isActive = (item: NavItem): boolean =>
    item.kind === 'deck'
      ? pathname.startsWith(`/${item.surface}/`)
      : pathname === item.to;

  const activeItem = NAV_ITEMS.find(isActive) ?? NAV_ITEMS[0];

  return (
    <header className="gv1-topbar" role="banner">
      <div className="gv1-topbar-left">
        <span className="gv1-sigil-sm" aria-hidden="true">◈</span>
        <span className="gv1-mono-xs gv1-topbar-prompt">grimoire@commander:~$</span>
        <span className="gv1-mono-xs gv1-dim gv1-topbar-prompt">// the grimoire</span>
      </div>
      <nav className="gv1-topbar-nav" role="navigation" aria-label="Surfaces">
        {NAV_ITEMS.map((item) => {
          const active = isActive(item);
          return (
            <NavLink
              key={item.label}
              to={resolveTo(item)}
              className={['gv1-nav-item', active ? 'gv1-active' : ''].filter(Boolean).join(' ')}
              aria-current={active ? 'page' : undefined}
            >
              <span className="gv1-mono-xs gv1-dim gv1-nav-rune" aria-hidden="true">§{item.rune}</span>
              <span className="gv1-mono-xs gv1-nav-label">{item.label}</span>
            </NavLink>
          );
        })}
      </nav>
      <div className="gv1-topbar-mobile" ref={menuRef}>
        <button
          type="button"
          className="gv1-topbar-mobile-btn"
          aria-expanded={menuOpen}
          aria-controls={menuId}
          aria-label={menuOpen ? 'Close navigation menu' : 'Open navigation menu'}
          onClick={() => setMenuOpen((v) => !v)}
        >
          <span className="gv1-sigil-sm" aria-hidden="true">◈</span>
          <span className="gv1-mono-xs gv1-topbar-mobile-label">
            §{activeItem.rune} <span className="gv1-rune">{activeItem.label}</span>
          </span>
          <span className="gv1-mono-xs gv1-dim" aria-hidden="true">{menuOpen ? '▴' : '▾'}</span>
        </button>
        {menuOpen && (
          <div
            id={menuId}
            className="gv1-topbar-mobile-menu"
            role="navigation"
            aria-label="Surfaces"
          >
            {NAV_ITEMS.map((item) => {
              const active = isActive(item);
              return (
                <NavLink
                  key={item.label}
                  to={resolveTo(item)}
                  className={['gv1-nav-item', active ? 'gv1-active' : ''].filter(Boolean).join(' ')}
                  aria-current={active ? 'page' : undefined}
                  onClick={() => setMenuOpen(false)}
                >
                  <span className="gv1-mono-xs gv1-dim gv1-nav-rune" aria-hidden="true">§{item.rune}</span>
                  <span className="gv1-mono-xs gv1-nav-label">{item.label}</span>
                </NavLink>
              );
            })}
          </div>
        )}
      </div>
      <div className="gv1-topbar-right">
        <span className="gv1-mono-xs gv1-dim" aria-hidden="true">⌘K</span>
        <span className="gv1-mono-xs">search</span>
        <span className="gv1-mono-xs gv1-dim gv1-sep" aria-hidden="true">│</span>
        <span className="gv1-mono-xs gv1-rune">scaffold · phase 0</span>
      </div>
    </header>
  );
}
