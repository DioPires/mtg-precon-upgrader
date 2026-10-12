// Port of gv1-perf.jsx GV1Apothecary (lines 56–355).
// Co-locates the ScoreRing SVG until the Phase 7 atoms refactor lands.

import { useState, type ReactNode } from 'react';
import { ManaCost } from '../atoms/ManaCost';
import type { DeckApothecary, RawCandidate, RawResilienceGap, RawRoleGap } from '../../data/types';

const METRICS_KEYS = [
  'manabase_health',
  'role_coverage_health',
  'curve_health',
  'interaction_density',
  'gameplan_cohesion',
] as const;

const METRICS_LABELS: Record<string, string> = {
  manabase_health: 'Manabase Health',
  role_coverage_health: 'Role Coverage',
  curve_health: 'Curve Health',
  interaction_density: 'Interaction Density',
  gameplan_cohesion: 'Gameplan Cohesion',
};

const METRICS_DESCRIPTIONS: Record<string, string> = {
  manabase_health: 'Karsten color sources, untapped ratio, fetch density, land-count fit vs. avg CMC.',
  role_coverage_health: 'Counts of ramp, draw, removal, protection, tutors, wincons vs. bracket targets.',
  curve_health: 'Average CMC vs. target curve and topcurve penalty; archetype-aware.',
  interaction_density: 'Weighted count of removal, counterspells, protection vs. target.',
  gameplan_cohesion: 'How concentrated the deck is in its primary archetypes (in-set ratio).',
};

const ROLE_LABELS: Record<string, string> = {
  ramp: 'Ramp',
  'card-draw': 'Card Draw',
  'removal-spot': 'Spot Removal',
  'removal-board': 'Board Wipes',
  protection: 'Protection',
  tutor: 'Tutors',
  wincon: 'Wincons',
  counterspell: 'Counters',
};

// DEC-1007 — metrics.json gaps[] entries keyed by `resilience_component` (DEC-308).
const RESILIENCE_LABELS: Record<string, string> = {
  recursion: 'Recursion',
  redundancy: 'Redundancy',
  protection: 'Protection',
  gy_second_hand: 'Graveyard second hand',
};

const REMEDIES_TOP_N = 30;

function gradeForGlobalHealth(s: number | null | undefined): string {
  // DEC-310 — single letter only. The ±margin number is the uncertainty
  // channel; banding ("A+/A/A-") double-counts that signal and adds noise.
  if (s == null) return '—';
  if (s >= 90) return 'A';
  if (s >= 80) return 'B';
  if (s >= 70) return 'C';
  if (s >= 60) return 'D';
  return 'F';
}

function maladyTier(s: number | null | undefined): 'ok' | 'warn' | 'bad' | 'crit' {
  if (s == null) return 'crit';
  if (s >= 75) return 'ok';
  if (s >= 50) return 'warn';
  if (s >= 25) return 'bad';
  return 'crit';
}

// At most one decimal; em-dash when absent. Malady counts and pin scores.
function fmtFigure(v: number | null | undefined): string {
  if (v == null) return '—';
  return Number.isInteger(v) ? String(v) : v.toFixed(1);
}

// DEC-1007 — `actual / target` like a role chip when the gap carries both.
// Redundancy carries win lines and a floor instead: the floor is where the
// score starts, not the count to reach, so it is not written as `lines / floor`.
function resilienceFigure(g: RawResilienceGap): ReactNode {
  if (g.actual != null && g.target != null) {
    return (
      <>
        {fmtFigure(g.actual)}
        <span className="gv1-dim"> / {fmtFigure(g.target)}</span>
      </>
    );
  }
  if (g.lines != null && g.floor != null) {
    return (
      <>
        {fmtFigure(g.lines)} {g.lines === 1 ? 'line' : 'lines'}
        <span className="gv1-dim"> · floor {fmtFigure(g.floor)}</span>
      </>
    );
  }
  return g.score_pct != null ? `${Math.round(g.score_pct)}%` : '—';
}

// DEC-311 — render T-prefixed numbers (`T6`) or em-dash when unreached.
function fmtWinTurn(v: number | null | undefined): string {
  return typeof v === 'number' ? `T${v}` : '—';
}

interface ScoreRingProps {
  score: number | null | undefined;
  max?: number;
  size?: number;
}

function ScoreRing({ score, max = 50, size = 44 }: ScoreRingProps) {
  const r = size / 2 - 4;
  const C = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(1, (score ?? 0) / max));
  const off = C * (1 - pct);
  return (
    <div className="gv1-apo-ring" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle className="gv1-apo-ring-bg" cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth="2.5" />
        <circle
          className="gv1-apo-ring-fill"
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth="2.5"
          strokeDasharray={C}
          strokeDashoffset={off}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          strokeLinecap="round"
        />
      </svg>
      <span className="gv1-apo-ring-num">{Math.round(score ?? 0)}</span>
    </div>
  );
}

interface ApothecaryProps {
  apothecary: DeckApothecary | null;
}

export function Apothecary({ apothecary }: ApothecaryProps) {
  const [filterRole, setFilterRole] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  if (!apothecary) {
    return (
      <section className="gv1-section gv1-apothecary">
        <div className="gv1-section-head">
          <span className="gv1-rune" aria-hidden="true">§ VI</span>
          <h2 className="gv1-section-title">The Apothecary</h2>
        </div>
        <div className="gv1-empty">No diagnosis on file for this commander.</div>
      </section>
    );
  }

  const { diagnosis, maladies, remedies, pins } = apothecary;
  const score = Math.round(diagnosis.score ?? 0);
  const grade = gradeForGlobalHealth(diagnosis.score);
  const margin = diagnosis.confidenceMargin;
  const winTurn = diagnosis.winTurn ?? null;

  let weakKey: string | null = null;
  let weakScore = Infinity;
  for (const k of METRICS_KEYS) {
    const s = diagnosis.components?.[k]?.score;
    if (typeof s === 'number' && s < weakScore) {
      weakScore = s;
      weakKey = k;
    }
  }

  // DEC-1007 — only role gaps can filter: a pool entry's `deck_role` and
  // `mitigates_gap` hold roles, never resilience components.
  const roleGaps = (maladies || []).filter((g): g is RawRoleGap => 'role' in g);
  const activeRoles = new Set(roleGaps.map((g) => g.role));
  const effectiveFilter = filterRole && activeRoles.has(filterRole) ? filterRole : null;

  // DEC-1015 — filter the whole pool, then cut to the top N. The cards that
  // fill a gap mostly rank below N, so cutting first left the grid empty.
  let pool: RawCandidate[] = remedies || [];
  if (effectiveFilter) {
    pool = pool.filter((c) => c.deck_role === effectiveFilter || c.mitigates_gap === effectiveFilter);
  }
  pool = pool.slice(0, REMEDIES_TOP_N).sort((a, b) => {
    const ga = a.mitigates_gap ? 0 : 1;
    const gb = b.mitigates_gap ? 0 : 1;
    if (ga !== gb) return ga - gb;
    return (b.score ?? 0) - (a.score ?? 0);
  });

  const maxRemedyScore = Math.max(50, ...pool.map((c) => c.score ?? 0));

  return (
    <section className="gv1-section gv1-apothecary">
      <div className="gv1-section-head">
        <span className="gv1-rune" aria-hidden="true">§ VI</span>
        <h2 className="gv1-section-title">The Apothecary</h2>
        <span className="gv1-mono-xs gv1-dim">diagnosis · maladies · remedies</span>
      </div>

      {/* DIAGNOSIS */}
      <div className="gv1-apo-subhead">
        <span className="gv1-mono-xs gv1-rune">DIAGNOSIS</span>
        <span className="gv1-apo-rule" aria-hidden="true" />
        <span className="gv1-mono-xs gv1-dim">methodology · {diagnosis.methodology}</span>
      </div>

      <div className="gv1-apo-vitals">
        <div className="gv1-apo-grade-block">
          <div className={'gv1-apo-grade gv1-apo-grade-' + grade.charAt(0).toLowerCase()}>{grade}</div>
          <div className="gv1-apo-grade-meta">
            <div className="gv1-serif-xxl">
              {score}
              {typeof margin === 'number' && (
                <span className="gv1-mono-xs gv1-dim gv1-apo-margin"> ± {margin}</span>
              )}
              <span className="gv1-mono-xs gv1-dim"> / 100</span>
            </div>
            <div className="gv1-mono-xs gv1-dim">DECK HEALTH</div>
          </div>
        </div>
        <div className="gv1-apo-vitals-divider" aria-hidden="true" />
        <div className="gv1-apo-weakest">
          <div className="gv1-mono-xs gv1-dim">WEAKEST COMPONENT</div>
          {weakKey ? (
            <>
              <div className="gv1-serif-md gv1-apo-weak-name">{METRICS_LABELS[weakKey]}</div>
              <div className="gv1-mono-xs gv1-apo-weak-score">{Math.round(weakScore)} / 100</div>
            </>
          ) : (
            <div className="gv1-mono-xs gv1-dim">No clear weakness.</div>
          )}
        </div>
        {winTurn && (
          <>
            <div className="gv1-apo-vitals-divider" aria-hidden="true" />
            <div className="gv1-apo-winturn" aria-label="Win-turn estimate">
              <div className="gv1-mono-xs gv1-dim">WIN TURN</div>
              <div className="gv1-apo-winturn-row">
                <div className="gv1-apo-winturn-cell">
                  <div className="gv1-mono-xs gv1-dim">BEST</div>
                  <div className="gv1-serif-md">{fmtWinTurn(winTurn.best)}</div>
                </div>
                <div className="gv1-apo-winturn-cell">
                  <div className="gv1-mono-xs gv1-dim">TYPICAL</div>
                  <div className="gv1-serif-md">{fmtWinTurn(winTurn.typical)}</div>
                </div>
                <div className="gv1-apo-winturn-cell">
                  <div className="gv1-mono-xs gv1-dim">CONTESTED</div>
                  <div className="gv1-serif-md">{fmtWinTurn(winTurn.contested)}</div>
                </div>
              </div>
            </div>
          </>
        )}
        <button
          type="button"
          className="gv1-apo-details-btn"
          onClick={() => setShowDetails((v) => !v)}
          aria-expanded={showDetails}
        >
          {showDetails ? 'Hide breakdown' : 'Show breakdown'}
        </button>
      </div>

      {showDetails && (
        <div className="gv1-apo-breakdown">
          {METRICS_KEYS.map((k) => {
            const s = diagnosis.components?.[k]?.score;
            if (typeof s !== 'number') return null;
            const pct = Math.min(Math.max(s, 0), 100);
            const isWeak = k === weakKey;
            const tier = pct >= 75 ? 'ok' : pct >= 50 ? 'warn' : 'bad';
            return (
              <div key={k} className={'gv1-apo-bk-row gv1-apo-tier-' + tier + (isWeak ? ' is-weakest' : '')}>
                <div className="gv1-apo-bk-head">
                  <span className="gv1-serif-sm">
                    {METRICS_LABELS[k]}
                    {isWeak && <em className="gv1-apo-weak-badge">weakest</em>}
                  </span>
                  <span className="gv1-mono-xs">{Math.round(s)}</span>
                </div>
                <div className="gv1-apo-bk-track">
                  <div className="gv1-apo-bk-fill" style={{ width: pct + '%' }} />
                </div>
                <div className="gv1-mono-xs gv1-dim gv1-apo-bk-desc">{METRICS_DESCRIPTIONS[k]}</div>
              </div>
            );
          })}
        </div>
      )}

      {/* MALADIES */}
      {(maladies || []).length > 0 && (
        <>
          <div className="gv1-apo-subhead">
            <span className="gv1-mono-xs gv1-rune">MALADIES</span>
            <span className="gv1-apo-rule" aria-hidden="true" />
            {roleGaps.length > 0 && <span className="gv1-mono-xs gv1-dim">click to filter remedies</span>}
          </div>
          <div className="gv1-apo-maladies">
            {maladies.map((g) => {
              if (!('role' in g)) {
                return (
                  <div
                    key={'resilience:' + g.resilience_component}
                    className={'gv1-apo-malady gv1-apo-malady-static gv1-apo-tier-' + maladyTier(g.score_pct)}
                  >
                    <span className="gv1-mono-xs gv1-dim gv1-apo-malady-kind">resilience</span>
                    <span className="gv1-apo-malady-label">
                      {RESILIENCE_LABELS[g.resilience_component] || g.resilience_component}
                    </span>
                    <span className="gv1-mono-xs gv1-apo-malady-fig">{resilienceFigure(g)}</span>
                  </div>
                );
              }
              const tier = maladyTier(g.score);
              const isActive = effectiveFilter === g.role;
              return (
                <button
                  key={'role:' + g.role}
                  type="button"
                  className={'gv1-apo-malady gv1-apo-tier-' + tier + (isActive ? ' is-active' : '')}
                  onClick={() => setFilterRole(isActive ? null : g.role)}
                  aria-pressed={isActive}
                >
                  <span className="gv1-apo-malady-label">{ROLE_LABELS[g.role] || g.role}</span>
                  <span className="gv1-mono-xs gv1-apo-malady-fig">
                    {fmtFigure(g.actual)}
                    <span className="gv1-dim"> / {fmtFigure(g.target)}</span>
                  </span>
                </button>
              );
            })}
            {effectiveFilter && (
              <button type="button" className="gv1-apo-malady-clear" onClick={() => setFilterRole(null)}>
                Clear filter ×
              </button>
            )}
          </div>
        </>
      )}

      {/* REMEDIES */}
      <div className="gv1-apo-subhead">
        <span className="gv1-mono-xs gv1-rune">REMEDIES</span>
        <span className="gv1-apo-rule" aria-hidden="true" />
        <span className="gv1-mono-xs gv1-dim">
          top {REMEDIES_TOP_N} by archetype fit, cards we own and EDHREC play rate · not a quality order
          {effectiveFilter
            ? ` · filtered: ${ROLE_LABELS[effectiveFilter] || effectiveFilter}`
            : ' · gap-addressers floated'}
        </span>
      </div>

      {/* DEC-1000 — board picks (deck.json candidate_pins). Outside the malady
          filter and the top-N cut: a pick stays visible wherever it ranks. */}
      {(pins || []).length > 0 && (
        <section className="gv1-apo-pins" aria-label="Board picks">
          {pins.map((p) => {
            const c = p.card;
            const fit = (c.matched_archetypes || []).join(' · ');
            return (
              <article key={p.name} className="gv1-apo-pin" data-card-name={c.name}>
                <span className="gv1-apo-tag gv1-apo-pin-label">board pick</span>
                <div className="gv1-apo-remedy-body">
                  <div className="gv1-apo-remedy-head">
                    <span className="gv1-apo-remedy-name">{c.name}</span>
                    <ManaCost mv={c.mana_cost || (c.cmc != null ? `{${c.cmc}}` : '—')} />
                  </div>
                  <div className="gv1-mono-xs gv1-dim gv1-apo-remedy-type">{c.type_line || ''}</div>
                  <div className="gv1-mono-xs gv1-apo-pin-meta">
                    {fit && <span className="gv1-apo-pin-fit">{fit}</span>}
                    <span className="gv1-dim">{`rank ${p.rank} of ${p.poolSize}`}</span>
                    <span className="gv1-dim">score {fmtFigure(c.score)}</span>
                  </div>
                  {p.reason && <div className="gv1-apo-remedy-rationale">{p.reason}</div>}
                </div>
                <div className="gv1-apo-remedy-score">
                  <ScoreRing score={c.score} max={maxRemedyScore} />
                </div>
              </article>
            );
          })}
        </section>
      )}

      {pool.length === 0 ? (
        <div className="gv1-empty">
          {effectiveFilter ? (
            <>
              No remedies match <em>{ROLE_LABELS[effectiveFilter] || effectiveFilter}</em>.
            </>
          ) : (
            'No remedies available.'
          )}
        </div>
      ) : (
        <div className="gv1-apo-remedies">
          {pool.map((c, i) => {
            const isGapAddr = !!c.mitigates_gap;
            const cls = ['gv1-apo-remedy'];
            if (isGapAddr) cls.push('is-gap-addresser');
            if (c.owned) cls.push('is-owned');
            if (c.pinned === true) cls.push('is-pinned');
            return (
              <article key={c.name + i} className={cls.join(' ')} data-card-name={c.name}>
                <div className="gv1-apo-remedy-num gv1-mono-xs gv1-dim">{String(i + 1).padStart(2, '0')}</div>
                <div className="gv1-apo-remedy-body">
                  <div className="gv1-apo-remedy-head">
                    <span className="gv1-apo-remedy-name">{c.name}</span>
                    <ManaCost mv={c.mana_cost || (c.cmc != null ? `{${c.cmc}}` : '—')} />
                  </div>
                  <div className="gv1-mono-xs gv1-dim gv1-apo-remedy-type">{c.type_line || ''}</div>
                  {c.strategy_line && <div className="gv1-apo-remedy-rationale">{c.strategy_line}</div>}
                  <div className="gv1-apo-remedy-tags">
                    {isGapAddr && (
                      <span className="gv1-apo-tag gv1-apo-tag-addresses">
                        addresses · {ROLE_LABELS[c.mitigates_gap as string] || c.mitigates_gap}
                      </span>
                    )}
                    {c.owned && <span className="gv1-apo-tag gv1-apo-tag-owned">owned</span>}
                    {c.game_changer && <span className="gv1-apo-tag gv1-apo-tag-gc">game changer</span>}
                    {c.pinned === true && <span className="gv1-apo-tag gv1-apo-tag-pinned">board pick</span>}
                    {c.deck_role && c.deck_role !== c.mitigates_gap && (
                      <span className="gv1-apo-tag gv1-apo-tag-role">
                        {ROLE_LABELS[c.deck_role] || c.deck_role}
                      </span>
                    )}
                  </div>
                </div>
                <div className="gv1-apo-remedy-score">
                  <ScoreRing score={c.score} max={maxRemedyScore} />
                </div>
              </article>
            );
          })}
        </div>
      )}

      {(diagnosis.generatedAt || diagnosis.mirrorUpdatedAt) && (
        <div className="gv1-apo-footer gv1-mono-xs gv1-dim">
          {diagnosis.generatedAt && (
            <span>metrics · {new Date(diagnosis.generatedAt).toISOString().slice(0, 10)}</span>
          )}
          {diagnosis.generatedAt && diagnosis.mirrorUpdatedAt && <span aria-hidden="true">·</span>}
          {diagnosis.mirrorUpdatedAt && (
            <span>scryfall mirror · {new Date(diagnosis.mirrorUpdatedAt).toISOString().slice(0, 10)}</span>
          )}
        </div>
      )}
    </section>
  );
}
