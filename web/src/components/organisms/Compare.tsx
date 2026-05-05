// Port of design_handoff_grimoire/prototype/gv1-compare.jsx.
// Sortable side-by-side health table for all decks. Click a deck name → Guide.

import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { GV1ManaPips } from '../atoms/GV1ManaPips';
import type { DeckFull } from '../../data/types';

type Band = 'good' | 'mid' | 'poor' | null;

function scoreBand(n: number | null | undefined): Band {
  if (n == null || Number.isNaN(n)) return null;
  if (n >= 75) return 'good';
  if (n >= 50) return 'mid';
  return 'poor';
}

function gradeBand(g: string | null | undefined): Band {
  if (!g) return null;
  const c = g.charAt(0);
  if (c === 'A' || c === 'B') return 'good';
  if (c === 'C') return 'mid';
  return 'poor';
}

interface ColumnDef {
  key: string;
  label: string;
  short: string;
  numeric: boolean;
  band?: boolean;
  get: (d: DeckFull) => number | string | null;
}

const COLUMNS: ColumnDef[] = [
  { key: 'idx',       label: '#',       short: '#',     numeric: true,  get: (d) => d.idx },
  { key: 'deckName',  label: 'Deck',    short: 'DECK',  numeric: false, get: (d) => d.deckName },
  { key: 'commander', label: 'Cmdr',    short: 'CMDR',  numeric: false, get: (d) => d.commander },
  { key: 'colors',    label: 'Colors',  short: 'COLS',  numeric: false, get: (d) => Array.from(d.colors || '').length },
  { key: 'bracket',   label: 'Bracket', short: 'BR',    numeric: false, get: (d) => d.bracket },
  { key: 'score',     label: 'Health',  short: 'HP',    numeric: true,  band: true, get: (d) => d.health?.score ?? null },
  { key: 'mana',      label: 'Mana',    short: 'MAN',   numeric: true,  band: true, get: (d) => d.health?.components?.manaReliability ?? null },
  { key: 'threats',   label: 'Threats', short: 'THR',   numeric: true,  band: true, get: (d) => d.health?.components?.threatDeployment ?? null },
  { key: 'interact',  label: 'Inter.',  short: 'INT',   numeric: true,  band: true, get: (d) => d.health?.components?.interactionDensity ?? null },
  { key: 'combo',     label: 'Combo',   short: 'CMB',   numeric: true,  band: true, get: (d) => d.health?.components?.comboConsistency ?? null },
  { key: 'indep',     label: 'Indep.',  short: 'IND',   numeric: true,  band: true, get: (d) => d.health?.components?.commanderIndependence ?? null },
  { key: 'avgCmc',    label: 'Avg MV',  short: 'MV',    numeric: true,  get: (d) => d.composition?.avgCmc ?? null },
  { key: 'lands',     label: 'Lands',   short: 'LND',   numeric: true,  get: (d) => d.composition?.lands ?? null },
  { key: 'gc',        label: 'GC',      short: 'GC',    numeric: true,  get: (d) => d.gameChangers || (d.engine || []).reduce((n, e) => n + (e.isGameChangers ? e.count : 0), 0) },
  { key: 'combos',    label: 'Combos',  short: 'CBN',   numeric: true,  get: (d) => (d.combos || []).length },
  { key: 'price',     label: 'Cost',    short: 'COST',  numeric: false, get: (d) => d.price || '—' },
];

function sortBy(decks: DeckFull[], key: string, asc: boolean): DeckFull[] {
  const col = COLUMNS.find((c) => c.key === key);
  if (!col) return decks;
  const sign = asc ? 1 : -1;
  const out = [...decks];
  out.sort((a, b) => {
    const va = col.get(a);
    const vb = col.get(b);
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;
    if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * sign;
    return String(va).localeCompare(String(vb)) * sign;
  });
  return out;
}

interface ScoreCellProps {
  value: number | null | undefined;
  band: Band;
}

function ScoreCell({ value, band }: ScoreCellProps) {
  if (value == null) return <span className="gv1-mono-xs gv1-dim">—</span>;
  const cls = ['gv1-cmp-score', band ? `gv1-cmp-score--${band}` : ''].filter(Boolean).join(' ');
  return (
    <span className={cls}>
      <span className="gv1-cmp-score-value gv1-mono-xs">{Math.round(value)}</span>
      <span className="gv1-cmp-meter" aria-hidden="true">
        <span
          className="gv1-cmp-meter-fill"
          style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
        />
      </span>
    </span>
  );
}

function GradeBadge({ grade }: { grade: string | null | undefined }) {
  if (!grade) return <span className="gv1-mono-xs gv1-dim">—</span>;
  const band = gradeBand(grade);
  const cls = ['gv1-cmp-grade', band ? `gv1-cmp-grade--${band}` : ''].filter(Boolean).join(' ');
  return <span className={cls}>{grade}</span>;
}

interface HeaderCellProps {
  col: ColumnDef;
  sortKey: string;
  asc: boolean;
  onClick: (key: string) => void;
}

function HeaderCell({ col, sortKey, asc, onClick }: HeaderCellProps) {
  const active = col.key === sortKey;
  const dir = active ? (asc ? '▲' : '▼') : '⇅';
  const cls = [
    'gv1-cmp-th',
    col.numeric ? 'gv1-cmp-th--num' : '',
    active ? 'gv1-cmp-th--active' : '',
  ]
    .filter(Boolean)
    .join(' ');
  const ariaSort: 'ascending' | 'descending' | 'none' = active ? (asc ? 'ascending' : 'descending') : 'none';
  // W3C APG sortable-table pattern: <th> keeps role + aria-sort; native <button> drives interaction.
  return (
    <th scope="col" className={cls} aria-sort={ariaSort}>
      <button
        type="button"
        className="gv1-cmp-th-btn"
        onClick={() => onClick(col.key)}
        title={`Sort by ${col.label}`}
        aria-label={`Sort by ${col.label}${active ? `, currently ${asc ? 'ascending' : 'descending'}` : ''}`}
      >
        <span className="gv1-mono-xs gv1-cmp-th-label">{col.label}</span>
        <span
          className={`gv1-mono-xs gv1-cmp-th-dir ${active ? 'gv1-cmp-th-dir--on' : ''}`}
          aria-hidden="true"
        >
          {dir}
        </span>
      </button>
    </th>
  );
}

export interface CompareProps {
  decks: DeckFull[];
}

export function Compare({ decks }: CompareProps) {
  const [sortKey, setSortKey] = useState('idx');
  const [asc, setAsc] = useState(true);
  const navigate = useNavigate();

  const sorted = useMemo(() => sortBy(decks, sortKey, asc), [decks, sortKey, asc]);

  const handleSort = (key: string) => {
    if (key === sortKey) {
      setAsc((a) => !a);
    } else {
      setSortKey(key);
      const col = COLUMNS.find((c) => c.key === key);
      setAsc(col && col.numeric ? false : true);
    }
  };

  const handleRowClick = (deck: DeckFull) => {
    navigate(`/deck/${deck.slug}`);
  };

  if (!decks.length) {
    return (
      <section className="gv1-section" aria-labelledby="compare-empty">
        <div className="gv1-empty">
          <span className="gv1-rune">◇</span>
          <span id="compare-empty" className="gv1-mono-xs">No decks loaded.</span>
        </div>
      </section>
    );
  }

  const scores = decks.map((d) => d.health?.score).filter((s): s is number => typeof s === 'number');
  const avgScore = scores.length
    ? (scores.reduce((s, n) => s + n, 0) / scores.length).toFixed(1)
    : '—';
  const minScore = scores.length ? Math.min(...scores) : null;
  const maxScore = scores.length ? Math.max(...scores) : null;
  const sortLabel = COLUMNS.find((c) => c.key === sortKey)?.label ?? '';

  return (
    <>
      <header className="gv1-section gv1-cmp-hero">
        <div className="gv1-section-head">
          <span className="gv1-rune" aria-hidden="true">§ X</span>
          <h2 id="compare-title" className="gv1-section-title">Comparative Codex</h2>
          <span className="gv1-mono-xs gv1-dim">
            · {decks.length} decks · sortable · click a deck name to open
          </span>
        </div>
        <p className="gv1-cmp-lede">
          The full slate, one screen. Five health components — mana reliability, threat
          deployment, interaction density, combo consistency, commander independence —
          broken out per deck so you can see at a glance where each tome is strong and
          where it bends. Click any column header to sort.
        </p>
        <div className="gv1-cmp-summary">
          <div className="gv1-cmp-summary-stat">
            <div className="gv1-mono-xs gv1-dim">AVG HEALTH</div>
            <div className="gv1-serif-lg">{avgScore}</div>
          </div>
          <div className="gv1-cmp-summary-stat">
            <div className="gv1-mono-xs gv1-dim">RANGE</div>
            <div className="gv1-serif-lg">
              {minScore != null ? minScore.toFixed(1) : '—'}{' '}
              <span className="gv1-dim">–</span>{' '}
              {maxScore != null ? maxScore.toFixed(1) : '—'}
            </div>
          </div>
          <div className="gv1-cmp-summary-stat">
            <div className="gv1-mono-xs gv1-dim">SORTED BY</div>
            <div className="gv1-serif-lg">
              {sortLabel} <span className="gv1-dim gv1-mono-xs">{asc ? '▲' : '▼'}</span>
            </div>
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

      <section className="gv1-section gv1-cmp-section" aria-labelledby="compare-title">
        <div className="gv1-cmp-table-wrap">
          <table className="gv1-cmp-table">
            <thead>
              <tr>
                {COLUMNS.map((col) => (
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
              {sorted.map((d) => {
                const gc =
                  d.gameChangers ||
                  (d.engine || []).reduce((n, e) => n + (e.isGameChangers ? e.count : 0), 0);
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
                        aria-label={`Open ${d.deckName} guide`}
                      >
                        <span className="gv1-serif-md">{d.deckName}</span>
                        <span className="gv1-mono-xs gv1-dim gv1-cmp-open" aria-hidden="true">
                          ↗
                        </span>
                      </button>
                    </td>
                    <td className="gv1-cmp-td">
                      <span className="gv1-mono-xs" data-card-name={d.commander}>
                        {d.commander}
                      </span>
                    </td>
                    <td className="gv1-cmp-td">
                      <span className="gv1-cmp-pips">
                        <GV1ManaPips colors={d.colors} />
                      </span>
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
                      <ScoreCell
                        value={d.health?.components?.manaReliability}
                        band={scoreBand(d.health?.components?.manaReliability)}
                      />
                    </td>
                    <td className="gv1-cmp-td gv1-cmp-td--num">
                      <ScoreCell
                        value={d.health?.components?.threatDeployment}
                        band={scoreBand(d.health?.components?.threatDeployment)}
                      />
                    </td>
                    <td className="gv1-cmp-td gv1-cmp-td--num">
                      <ScoreCell
                        value={d.health?.components?.interactionDensity}
                        band={scoreBand(d.health?.components?.interactionDensity)}
                      />
                    </td>
                    <td className="gv1-cmp-td gv1-cmp-td--num">
                      <ScoreCell
                        value={d.health?.components?.comboConsistency}
                        band={scoreBand(d.health?.components?.comboConsistency)}
                      />
                    </td>
                    <td className="gv1-cmp-td gv1-cmp-td--num">
                      <ScoreCell
                        value={d.health?.components?.commanderIndependence}
                        band={scoreBand(d.health?.components?.commanderIndependence)}
                      />
                    </td>
                    <td className="gv1-cmp-td gv1-cmp-td--num">
                      <span className="gv1-mono-xs">
                        {d.composition?.avgCmc != null ? d.composition.avgCmc.toFixed(2) : '—'}
                      </span>
                    </td>
                    <td className="gv1-cmp-td gv1-cmp-td--num">
                      <span className="gv1-mono-xs">{d.composition?.lands ?? '—'}</span>
                    </td>
                    <td className="gv1-cmp-td gv1-cmp-td--num">
                      {gc ? (
                        <span className="gv1-mono-xs gv1-rune">{gc}</span>
                      ) : (
                        <span className="gv1-mono-xs gv1-dim">—</span>
                      )}
                    </td>
                    <td className="gv1-cmp-td gv1-cmp-td--num">
                      {(d.combos || []).length ? (
                        <span className="gv1-mono-xs">{(d.combos || []).length}</span>
                      ) : (
                        <span className="gv1-mono-xs gv1-dim">—</span>
                      )}
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
          Health = weighted composite (mana 30%, threats 20%, interaction 20%, combo 15%,
          commander independence 15%). Combo Consistency stays low for non-combo decks by
          design — that doesn't mean weak, it means the deck doesn't rely on a 2-card line.
        </p>
      </section>
    </>
  );
}
