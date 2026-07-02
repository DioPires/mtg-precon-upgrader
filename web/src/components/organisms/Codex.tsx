// Port of design_handoff_grimoire/prototype/gv1-codex.jsx.
// Cross-deck overview: stats strip + sort/filter toolbar + grid of deck cards.
// Click a card → router navigation to that deck's guide.

import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { GV1ManaPips } from '../atoms/GV1ManaPips';
import type { DeckFull } from '../../data/types';

type SortKey = 'idx' | 'health' | 'cmc' | 'wincons' | 'combos';
type FilterKey = 'all' | 'mono' | 'multi' | 'bracket4';

const SORT_OPTIONS: Array<[SortKey, string]> = [
  ['idx', '№'],
  ['health', 'health'],
  ['cmc', 'cmc'],
  ['wincons', 'wins'],
  ['combos', 'combos'],
];

const FILTER_OPTIONS: Array<[FilterKey, string]> = [
  ['all', 'all'],
  ['mono', 'mono'],
  ['multi', 'multicolor'],
  ['bracket4', 'bracket IV'],
];

function applyFilter(decks: DeckFull[], filter: FilterKey): DeckFull[] {
  if (filter === 'mono') return decks.filter((d) => Array.from(d.colors).length <= 1);
  if (filter === 'multi') return decks.filter((d) => Array.from(d.colors).length >= 2);
  if (filter === 'bracket4') return decks.filter((d) => (d.bracket || '').includes('IV'));
  return decks;
}

function applySort(decks: DeckFull[], key: SortKey): DeckFull[] {
  const out = [...decks];
  if (key === 'health') out.sort((a, b) => (b.health?.score ?? 0) - (a.health?.score ?? 0));
  else if (key === 'cmc') out.sort((a, b) => (a.composition?.avgCmc ?? 99) - (b.composition?.avgCmc ?? 99));
  else if (key === 'wincons') out.sort((a, b) => (b.wincons?.length ?? 0) - (a.wincons?.length ?? 0));
  else if (key === 'combos') out.sort((a, b) => (b.combos?.length ?? 0) - (a.combos?.length ?? 0));
  else out.sort((a, b) => a.idx - b.idx);
  return out;
}

export interface CodexProps {
  decks: DeckFull[];
}

export function Codex({ decks }: CodexProps) {
  const [sortKey, setSortKey] = useState<SortKey>('idx');
  const [filter, setFilter] = useState<FilterKey>('all');
  const navigate = useNavigate();

  const rows = useMemo(() => applySort(applyFilter(decks, filter), sortKey), [decks, filter, sortKey]);

  const stats = useMemo(() => {
    const total = decks.length || 1;
    const avgHealth = Math.round(decks.reduce((s, d) => s + (d.health?.score ?? 0), 0) / total);
    const avgCmc = (decks.reduce((s, d) => s + (d.composition?.avgCmc ?? 0), 0) / total).toFixed(2);
    const totalWincons = decks.reduce((s, d) => s + (d.wincons?.length ?? 0), 0);
    const totalCombos = decks.reduce((s, d) => s + (d.combos?.length ?? 0), 0);
    const totalCards = decks.reduce((s, d) => s + (d.composition?.totalCards ?? 0), 0);
    const bracketCounts = decks.reduce<Record<string, number>>((acc, d) => {
      const b = d.bracket || '?';
      acc[b] = (acc[b] ?? 0) + 1;
      return acc;
    }, {});
    return {
      total: decks.length,
      avgHealth,
      avgCmc,
      totalWincons,
      totalCombos,
      totalCards,
      bracketCounts,
    };
  }, [decks]);

  return (
    <section className="gv1-codex" aria-labelledby="codex-title">
      <div className="gv1-codex-head">
        <div className="gv1-codex-eyebrow">
          <span className="gv1-rune" aria-hidden="true">◈</span>
          <span className="gv1-mono-xs">CODEX · OVERVIEW</span>
          <span className="gv1-mono-xs gv1-dim">— the entire grimoire, in one breath</span>
        </div>
        <h1 id="codex-title" className="gv1-codex-title">
          The <em>Codex</em>
        </h1>
        <p className="gv1-codex-sub">
          All {stats.total} scribed tomes side by side. Sort, filter, and scry across the shelf.
        </p>
      </div>

      <div className="gv1-codex-stats">
        <div className="gv1-codex-stat">
          <div className="gv1-mono-xs gv1-dim">SHELVED</div>
          <div className="gv1-serif-xxl">{stats.total}</div>
          <div className="gv1-mono-xs gv1-dim">tomes · {stats.totalCards} cards</div>
        </div>
        <div className="gv1-codex-stat">
          <div className="gv1-mono-xs gv1-dim">AVG HEALTH</div>
          <div className="gv1-serif-xxl">{stats.avgHealth}</div>
          <div className="gv1-mono-xs gv1-rune">across the shelf</div>
        </div>
        <div className="gv1-codex-stat">
          <div className="gv1-mono-xs gv1-dim">AVG CMC</div>
          <div className="gv1-serif-xxl">{stats.avgCmc}</div>
          <div className="gv1-mono-xs gv1-dim">mana value mean</div>
        </div>
        <div className="gv1-codex-stat">
          <div className="gv1-mono-xs gv1-dim">WIN PATHS</div>
          <div className="gv1-serif-xxl">{stats.totalWincons}</div>
          <div className="gv1-mono-xs gv1-dim">{stats.totalCombos} combos charted</div>
        </div>
        <div className="gv1-codex-stat">
          <div className="gv1-mono-xs gv1-dim">BRACKETS</div>
          <div className="gv1-codex-stat-brackets">
            {Object.entries(stats.bracketCounts)
              .sort((a, b) => a[0].localeCompare(b[0]))
              .map(([b, n]) => (
                <div key={b} className="gv1-codex-bracket-row">
                  <span className="gv1-mono-xs gv1-rune">{b}</span>
                  <span className="gv1-serif-md">{n}</span>
                </div>
              ))}
          </div>
        </div>
      </div>

      <div className="gv1-codex-toolbar" role="toolbar" aria-label="Sort and filter decks">
        <div className="gv1-codex-toolbar-l">
          <span className="gv1-mono-xs gv1-dim">sort:</span>
          {SORT_OPTIONS.map(([k, l]) => (
            <button
              key={k}
              type="button"
              className={'gv1-mono-xs gv1-chip' + (sortKey === k ? ' gv1-chip-active' : '')}
              aria-pressed={sortKey === k}
              onClick={() => setSortKey(k)}
            >
              {l}
            </button>
          ))}
        </div>
        <div className="gv1-codex-toolbar-r">
          <span className="gv1-mono-xs gv1-dim">filter:</span>
          {FILTER_OPTIONS.map(([k, l]) => (
            <button
              key={k}
              type="button"
              className={'gv1-mono-xs gv1-chip' + (filter === k ? ' gv1-chip-active' : '')}
              aria-pressed={filter === k}
              onClick={() => setFilter(k)}
            >
              {l}
            </button>
          ))}
        </div>
      </div>

      <div className="gv1-codex-grid">
        {rows.map((d, i) => (
          <CodexCard
            key={d.slug}
            deck={d}
            rank={i + 1}
            onOpen={() => navigate(`/deck/${d.slug}`)}
          />
        ))}
      </div>
    </section>
  );
}

interface CodexCardProps {
  deck: DeckFull;
  rank: number;
  onOpen: () => void;
}

function CodexCard({ deck, rank, onOpen }: CodexCardProps) {
  const score = deck.health?.score ?? 0;
  const grade = deck.health?.grade ?? '—';
  const wincons = deck.wincons?.length ?? 0;
  const combos = deck.combos?.length ?? 0;
  const cmc =
    typeof deck.composition?.avgCmc === 'number' ? deck.composition.avgCmc.toFixed(2) : '—';
  const lands = deck.composition?.lands ?? '—';

  return (
    <button
      type="button"
      className="gv1-codex-card"
      onClick={onOpen}
      aria-label={`Open ${deck.deckName} guide`}
    >
      <div className="gv1-codex-card-head">
        <div className="gv1-codex-card-num">
          <span className="gv1-mono-xs gv1-dim">№ {String(deck.idx).padStart(2, '0')}</span>
          <span className="gv1-mono-xs gv1-dim">RANK {String(rank).padStart(2, '0')}</span>
        </div>
        <GV1ManaPips colors={deck.colors} />
      </div>
      <h3 className="gv1-codex-card-title">
        {deck.deckName}
        {deck.status === 'brewing' && (
          <span
            className="gv1-mono-xs gv1-brewing-pill"
            title="Brewing — not physically built; excluded from card-usage analysis"
          >
            BREWING
          </span>
        )}
      </h3>
      <div className="gv1-codex-card-cmd">
        <span data-card-name={deck.commander}>{deck.commander}</span>
        {deck.partner && (
          <>
            <span className="gv1-codex-card-cmd-amp" aria-hidden="true"> + </span>
            <span data-card-name={deck.partner}>{deck.partner}</span>
          </>
        )}
      </div>
      <div className="gv1-codex-card-type gv1-mono-xs gv1-dim">{deck.type}</div>

      <div className="gv1-codex-card-health">
        <div className="gv1-codex-health-meter" aria-hidden="true">
          <div
            className="gv1-codex-health-bar"
            style={{ width: Math.min(100, score) + '%' }}
          />
          <div className="gv1-codex-health-grid">
            {[20, 40, 60, 80].map((n) => (
              <span key={n} style={{ left: n + '%' }} />
            ))}
          </div>
        </div>
        <div className="gv1-codex-card-health-meta">
          <span className="gv1-mono-xs gv1-dim">HEALTH</span>
          <span className="gv1-serif-md">{Math.round(score)}</span>
          <span className="gv1-mono-xs gv1-rune">· {grade}</span>
        </div>
      </div>

      <div className="gv1-codex-card-stats">
        <div>
          <div className="gv1-mono-xs gv1-dim">BRKT</div>
          <div className="gv1-serif-md">{deck.bracket}</div>
        </div>
        <div>
          <div className="gv1-mono-xs gv1-dim">CMC</div>
          <div className="gv1-serif-md">{cmc}</div>
        </div>
        <div>
          <div className="gv1-mono-xs gv1-dim">LANDS</div>
          <div className="gv1-serif-md">{lands}</div>
        </div>
      </div>

      <div className="gv1-codex-card-bars">
        <CodexBar label="WINS" n={wincons} max={6} />
        <CodexBar label="COMBOS" n={combos} max={8} />
      </div>

      <div className="gv1-codex-card-foot">
        <span className="gv1-mono-xs gv1-dim">tomus № {String(deck.idx).padStart(2, '0')}</span>
        <span className="gv1-mono-xs gv1-rune">
          open<span aria-hidden="true"> ◇</span>
        </span>
      </div>
    </button>
  );
}

interface CodexBarProps {
  label: string;
  n: number;
  max: number;
}

function CodexBar({ label, n, max }: CodexBarProps) {
  const pct = Math.min(100, (n / max) * 100);
  return (
    <div className="gv1-codex-bar-row">
      <span className="gv1-mono-xs gv1-dim gv1-codex-bar-l">{label}</span>
      <div className="gv1-codex-bar-track" aria-hidden="true">
        <div className="gv1-codex-bar-fill" style={{ width: pct + '%' }} />
      </div>
      <span className="gv1-mono-xs gv1-codex-bar-n">{n}</span>
    </div>
  );
}
