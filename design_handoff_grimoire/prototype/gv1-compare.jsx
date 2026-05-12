// Grimoire v1 — Compare: side-by-side health table for all 12 decks
// ─────────────────────────────────────────────────────────────────
// Real surface (not a stub). Renders every deck as a row with the 5
// health components broken out, sortable by column. Click a row's deck
// name to jump to that deck's Guide.
//
// Data shape (from gv1-data.js → DECK_FULL[]):
//   d.idx, d.deckName, d.commander, d.colors (glyph string), d.bracket
//   d.health = { score, grade, components: { manaReliability,
//     threatDeployment, interactionDensity, comboConsistency,
//     commanderIndependence }, weakestComponent }
//   d.composition = { avgCmc, lands, ... }
//   d.engine[] (engine sections — used to count Game Changers)
//   d.combos[] (synergies)
//   d.price (string range)
// ─────────────────────────────────────────────────────────────────

const { useState: useStateCompare, useMemo: useMemoCompare } = React;

// Score → color band. Mirrors the rest of the app: green = good (≥75),
// gold = ok (50–74), red = poor (<50). Returns a CSS variable name, so
// the cell uses tokens instead of hardcoded hex.
function scoreBand(n) {
  if (n == null || isNaN(n)) return null;
  if (n >= 75) return 'good';
  if (n >= 50) return 'mid';
  return 'poor';
}

function gradeBand(g) {
  if (!g) return null;
  const c = g.charAt(0);
  if (c === 'A' || c === 'B') return 'good';
  if (c === 'C') return 'mid';
  return 'poor';
}

// Columns. `key` is what goes into sortKey; `get` reads the value out
// of a deck row; `fmt` is a renderer for the cell. `numeric` controls
// alignment + sort comparator.
const COLUMNS = [
  { key: 'idx',       label: '#',       short: '#',     numeric: true,  get: d => d.idx },
  { key: 'deckName',  label: 'Deck',    short: 'DECK',  numeric: false, get: d => d.deckName },
  { key: 'commander', label: 'Cmdr',    short: 'CMDR',  numeric: false, get: d => d.commander },
  { key: 'colors',    label: 'Colors',  short: 'COLS',  numeric: false, get: d => (d.colors || '').length },
  { key: 'bracket',   label: 'Bracket', short: 'BR',    numeric: false, get: d => d.bracket },
  { key: 'score',     label: 'Health',  short: 'HP',    numeric: true,  get: d => d.health?.score ?? null, band: true },
  { key: 'mana',      label: 'Mana',    short: 'MAN',   numeric: true,  get: d => d.health?.components?.manaReliability ?? null, band: true },
  { key: 'threats',   label: 'Threats', short: 'THR',   numeric: true,  get: d => d.health?.components?.threatDeployment ?? null, band: true },
  { key: 'interact',  label: 'Inter.',  short: 'INT',   numeric: true,  get: d => d.health?.components?.interactionDensity ?? null, band: true },
  { key: 'combo',     label: 'Combo',   short: 'CMB',   numeric: true,  get: d => d.health?.components?.comboConsistency ?? null, band: true },
  { key: 'indep',     label: 'Indep.',  short: 'IND',   numeric: true,  get: d => d.health?.components?.commanderIndependence ?? null, band: true },
  { key: 'avgCmc',    label: 'Avg MV',  short: 'MV',    numeric: true,  get: d => d.composition?.avgCmc ?? null },
  { key: 'lands',     label: 'Lands',   short: 'LND',   numeric: true,  get: d => d.composition?.lands ?? null },
  { key: 'gc',        label: 'GC',      short: 'GC',    numeric: true,  get: d => (d.engine || []).reduce((n, e) => n + (e.isGameChangers ? e.count : 0), 0) },
  { key: 'combos',    label: 'Combos',  short: 'CBN',   numeric: true,  get: d => (d.combos || []).length },
  { key: 'price',     label: 'Cost',    short: 'COST',  numeric: false, get: d => d.price || '—' },
];

function sortBy(decks, key, asc) {
  const col = COLUMNS.find(c => c.key === key);
  if (!col) return decks;
  const sign = asc ? 1 : -1;
  const out = [...decks];
  out.sort((a, b) => {
    const va = col.get(a);
    const vb = col.get(b);
    // Nulls always sort to bottom regardless of direction
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;
    if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * sign;
    return String(va).localeCompare(String(vb)) * sign;
  });
  return out;
}

// Cell for a numeric component score. Renders the integer value
// inside a chip whose tint comes from the band. Adds a thin meter
// underneath so the value is also legible visually at small scale.
function ScoreCell({ value, band }) {
  if (value == null) return <span className="gv1-mono-xs gv1-dim">—</span>;
  const cls = ['gv1-cmp-score', band ? `gv1-cmp-score--${band}` : ''].filter(Boolean).join(' ');
  return (
    <span className={cls}>
      <span className="gv1-cmp-score-value gv1-mono-xs">{Math.round(value)}</span>
      <span className="gv1-cmp-meter" aria-hidden="true">
        <span className="gv1-cmp-meter-fill" style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
      </span>
    </span>
  );
}

function GradeBadge({ grade }) {
  if (!grade) return <span className="gv1-mono-xs gv1-dim">—</span>;
  const band = gradeBand(grade);
  const cls = ['gv1-cmp-grade', band ? `gv1-cmp-grade--${band}` : ''].filter(Boolean).join(' ');
  return <span className={cls}>{grade}</span>;
}

// Header cell — clickable, shows sort direction. Active column highlighted.
function HeaderCell({ col, sortKey, asc, onClick }) {
  const active = col.key === sortKey;
  const dir = active ? (asc ? '▲' : '▼') : '⇅';
  const cls = [
    'gv1-cmp-th',
    col.numeric ? 'gv1-cmp-th--num' : '',
    active ? 'gv1-cmp-th--active' : '',
  ].filter(Boolean).join(' ');
  return (
    <th
      scope="col"
      className={cls}
      onClick={() => onClick(col.key)}
      title={`Sort by ${col.label}`}
    >
      <span className="gv1-mono-xs gv1-cmp-th-label">{col.label}</span>
      <span className={`gv1-mono-xs gv1-cmp-th-dir ${active ? 'gv1-cmp-th-dir--on' : ''}`} aria-hidden="true">{dir}</span>
    </th>
  );
}

function GV1Compare({ allDecks, onSelectDeck }) {
  const decks = useMemoCompare(() => allDecks || [], [allDecks]);
  const [sortKey, setSortKey] = useStateCompare('idx');
  const [asc, setAsc] = useStateCompare(true);

  const sorted = useMemoCompare(() => sortBy(decks, sortKey, asc), [decks, sortKey, asc]);

  const handleSort = (key) => {
    if (key === sortKey) {
      setAsc(a => !a);
    } else {
      setSortKey(key);
      // Numeric columns default to descending (highest first), text to ascending.
      const col = COLUMNS.find(c => c.key === key);
      setAsc(col && col.numeric ? false : true);
    }
  };

  const handleRowClick = (deck) => {
    if (onSelectDeck) onSelectDeck(deck.idx);
    if (typeof window.gv1NavTo === 'function') window.gv1NavTo('guide');
  };

  // Empty state — would happen if data fails to load
  if (!decks.length) {
    return (
      <div className="gv1-root" data-screen-label="06 Compare" data-gv1-screen="compare">
        <GV1Topbar screen="compare" />
        <section className="gv1-section">
          <div className="gv1-empty">
            <span className="gv1-rune">◇</span>
            <span className="gv1-mono-xs">No decks loaded.</span>
          </div>
        </section>
      </div>
    );
  }

  // Aggregate stats for the section header
  const avgScore = (decks.reduce((s, d) => s + (d.health?.score || 0), 0) / decks.length).toFixed(1);
  const minScore = Math.min(...decks.map(d => d.health?.score ?? Infinity).filter(n => isFinite(n)));
  const maxScore = Math.max(...decks.map(d => d.health?.score ?? -Infinity).filter(n => isFinite(n)));

  return (
    <div className="gv1-root" data-screen-label="06 Compare" data-gv1-screen="compare">
      <GV1Topbar screen="compare" />

      <header className="gv1-section gv1-cmp-hero">
        <div className="gv1-section-head">
          <span className="gv1-rune" aria-hidden="true">§ X</span>
          <h2 className="gv1-section-title">Comparative Codex</h2>
          <span className="gv1-mono-xs gv1-dim">· {decks.length} decks · sortable · click a deck name to open</span>
        </div>
        <p className="gv1-cmp-lede">
          The full slate, one screen. Five health components — mana reliability,
          threat deployment, interaction density, combo consistency, commander
          independence — broken out per deck so you can see at a glance where each
          tome is strong and where it bends. Click any column header to sort.
        </p>
        <div className="gv1-cmp-summary">
          <div className="gv1-cmp-summary-stat">
            <div className="gv1-mono-xs gv1-dim">AVG HEALTH</div>
            <div className="gv1-serif-lg">{avgScore}</div>
          </div>
          <div className="gv1-cmp-summary-stat">
            <div className="gv1-mono-xs gv1-dim">RANGE</div>
            <div className="gv1-serif-lg">{minScore.toFixed(1)} <span className="gv1-dim">–</span> {maxScore.toFixed(1)}</div>
          </div>
          <div className="gv1-cmp-summary-stat">
            <div className="gv1-mono-xs gv1-dim">SORTED BY</div>
            <div className="gv1-serif-lg">{COLUMNS.find(c => c.key === sortKey)?.label} <span className="gv1-dim gv1-mono-xs">{asc ? '▲' : '▼'}</span></div>
          </div>
          <div className="gv1-cmp-summary-stat">
            <div className="gv1-mono-xs gv1-dim">SCALE</div>
            <div className="gv1-cmp-legend">
              <span className="gv1-cmp-legend-pill gv1-cmp-score--good">≥75</span>
              <span className="gv1-cmp-legend-pill gv1-cmp-score--mid">50–74</span>
              <span className="gv1-cmp-legend-pill gv1-cmp-score--poor">&lt;50</span>
            </div>
          </div>
        </div>
      </header>

      <section className="gv1-section gv1-cmp-section">
        <div className="gv1-cmp-table-wrap">
          <table className="gv1-cmp-table">
            <thead>
              <tr>
                {COLUMNS.map(col => (
                  <HeaderCell
                    key={col.key}
                    col={col}
                    sortKey={sortKey}
                    asc={asc}
                    onClick={handleSort}
                  />
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.map(d => {
                const gc = (d.engine || []).reduce((n, e) => n + (e.isGameChangers ? e.count : 0), 0);
                return (
                  <tr key={d.slug} className="gv1-cmp-row">
                    <td className="gv1-cmp-td gv1-cmp-td--num">
                      <span className="gv1-mono-xs gv1-dim">№{String(d.idx).padStart(2, '0')}</span>
                    </td>
                    <td className="gv1-cmp-td gv1-cmp-td--deck">
                      <button
                        type="button"
                        className="gv1-cmp-deck-btn"
                        onClick={() => handleRowClick(d)}
                        title={`Open ${d.deckName} guide`}
                      >
                        <span className="gv1-serif-md">{d.deckName}</span>
                        <span className="gv1-mono-xs gv1-dim gv1-cmp-open" aria-hidden="true">↗</span>
                      </button>
                    </td>
                    <td className="gv1-cmp-td">
                      <span className="gv1-mono-xs" data-card-name={d.commander}>{d.commander}</span>
                    </td>
                    <td className="gv1-cmp-td">
                      <span className="gv1-cmp-pips"><GV1ManaPips colors={d.colors} /></span>
                    </td>
                    <td className="gv1-cmp-td">
                      <span className="gv1-mono-xs">{d.bracket}</span>
                    </td>
                    <td className="gv1-cmp-td gv1-cmp-td--num">
                      <span className="gv1-cmp-health">
                        <ScoreCell value={d.health?.score} band={scoreBand(d.health?.score)} />
                        <GradeBadge grade={d.health?.grade} />
                      </span>
                    </td>
                    <td className="gv1-cmp-td gv1-cmp-td--num">
                      <ScoreCell value={d.health?.components?.manaReliability} band={scoreBand(d.health?.components?.manaReliability)} />
                    </td>
                    <td className="gv1-cmp-td gv1-cmp-td--num">
                      <ScoreCell value={d.health?.components?.threatDeployment} band={scoreBand(d.health?.components?.threatDeployment)} />
                    </td>
                    <td className="gv1-cmp-td gv1-cmp-td--num">
                      <ScoreCell value={d.health?.components?.interactionDensity} band={scoreBand(d.health?.components?.interactionDensity)} />
                    </td>
                    <td className="gv1-cmp-td gv1-cmp-td--num">
                      <ScoreCell value={d.health?.components?.comboConsistency} band={scoreBand(d.health?.components?.comboConsistency)} />
                    </td>
                    <td className="gv1-cmp-td gv1-cmp-td--num">
                      <ScoreCell value={d.health?.components?.commanderIndependence} band={scoreBand(d.health?.components?.commanderIndependence)} />
                    </td>
                    <td className="gv1-cmp-td gv1-cmp-td--num">
                      <span className="gv1-mono-xs">{d.composition?.avgCmc != null ? d.composition.avgCmc.toFixed(2) : '—'}</span>
                    </td>
                    <td className="gv1-cmp-td gv1-cmp-td--num">
                      <span className="gv1-mono-xs">{d.composition?.lands ?? '—'}</span>
                    </td>
                    <td className="gv1-cmp-td gv1-cmp-td--num">
                      <span className="gv1-mono-xs gv1-rune">{gc || <span className="gv1-dim">—</span>}</span>
                    </td>
                    <td className="gv1-cmp-td gv1-cmp-td--num">
                      <span className="gv1-mono-xs">{(d.combos || []).length || <span className="gv1-dim">—</span>}</span>
                    </td>
                    <td className="gv1-cmp-td">
                      <span className="gv1-mono-xs">{d.price || '—'}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <p className="gv1-mono-xs gv1-dim gv1-cmp-foot">
          Health = weighted composite (mana 30%, threats 20%, interaction 20%, combo 15%, commander independence 15%).
          Combo Consistency stays low for non-combo decks by design — that doesn't mean weak, it means the deck doesn't rely on a 2-card line.
        </p>
      </section>
    </div>
  );
}

Object.assign(window, { GV1Compare });
