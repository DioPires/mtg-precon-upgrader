import { NavLink, useLocation } from 'react-router-dom';

type NavItem = { to: string; rune: string; label: string };

const NAV_ITEMS: NavItem[] = [
  { to: '/codex', rune: 'I', label: 'Codex' },
  { to: '/deck/_', rune: 'II', label: 'Guide' },
  { to: '/scrying/_', rune: 'VIII', label: 'Scrying' },
  { to: '/shopping', rune: 'IX', label: 'Shopping' },
  { to: '/compare', rune: 'X', label: 'Compare' },
];

export function Topbar() {
  const { pathname } = useLocation();
  return (
    <header className="gv1-topbar" role="banner">
      <div className="gv1-topbar-left">
        <span className="gv1-sigil-sm" aria-hidden="true">◈</span>
        <span className="gv1-mono-xs">grimoire@commander:~$</span>
        <span className="gv1-mono-xs gv1-dim">// the grimoire</span>
      </div>
      <nav className="gv1-topbar-nav" role="navigation" aria-label="Surfaces">
        {NAV_ITEMS.map((item) => {
          const prefix = item.to.replace(/\/_$/, '');
          const active = pathname === item.to || pathname.startsWith(`${prefix}/`);
          return (
            <NavLink
              key={item.to}
              to={item.to.replace(/\/_$/, '')}
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
