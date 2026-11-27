import { useEffect, useId, useRef, useState } from 'react';
import { NavLink, useLocation, useMatch } from 'react-router-dom';
import { deckLoader } from '../data/loader';
import { LAST_DECK_KEY } from '../data/lastDeck';
import { Glyph } from './atoms/Glyph';

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
  { kind: 'static', to: '/atlas', rune: 'XI', label: 'Atlas' },
  { kind: 'static', to: '/combos', rune: 'XII', label: 'Combos' },
];

export function Topbar() {
  const { pathname } = useLocation();
  const menuId = useId();
  const [storedDeckId, setStoredDeckId] = useState<string | null>(() => readLastDeck());
  const [deckIds, setDeckIds] = useState<string[] | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  // Pick up writes from DeckGuide / Scrying when navigation occurs.
  useEffect(() => {
    const stored = readLastDeck();
    if (stored && stored !== storedDeckId) setStoredDeckId(stored);
  }, [pathname, storedDeckId]);

  // The index's deck ids. A saved or routed deck id is dropped once the
  // loaded index does not list it (a removed deck's id can stay in
  // localStorage); before the index loads, or if it fails to, it is used as
  // it is. With no usable id the links take the first commander.
  useEffect(() => {
    let cancelled = false;
    deckLoader
      .loadIndex()
      .then((idx) => {
        if (!cancelled) setDeckIds(idx.commanders.map((c) => c.id));
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

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

  // The router's own matches give the URL's deck id decoded
  // (/deck/%65ternal-agony gives eternal-agony).
  const deckMatch = useMatch('/deck/:id');
  const scryingMatch = useMatch('/scrying/:id');
  const mobileMatch = useMatch('/m/:id');
  const urlId = (deckMatch ?? scryingMatch ?? mobileMatch)?.params.id;
  const fromUrl = urlId && urlId !== '_' ? urlId : null;
  const usable = (id: string | null): string | null =>
    id && (deckIds === null || deckIds.includes(id)) ? id : null;
  const activeDeckId = usable(fromUrl) ?? usable(storedDeckId) ?? deckIds?.[0] ?? null;

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
            <Glyph>§{activeItem.rune} </Glyph>
            <span className="gv1-rune">{activeItem.label}</span>
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
