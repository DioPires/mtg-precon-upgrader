// Port of gv1-perf.jsx GV1Performance (lines 357–453).

import type {
  DeckCurveEntry,
  DeckFuncEntry,
  RawAssessment,
  RawDeckComposition,
  RawDeckHealthScore,
  RawManaAdequacyShare,
} from '../../data/types';
import { Glyph } from '../atoms/Glyph';

interface PerformanceProps {
  curve: DeckCurveEntry[];
  func: DeckFuncEntry[];
  sources: Array<readonly [string, string]>;
  health: RawDeckHealthScore | null;
  composition: RawDeckComposition | null;
  assessment: RawAssessment | null;
  /** simulation.json `goldfish.numGames`. */
  goldfishGames?: number;
  /** simulation.json `metadata.numGames`: the mana simulation's games. */
  manaSimGames?: number;
}

// The values below come from simulation.json as written, so each is checked
// before it is shown, as isOwnedQuantity (data/ownedCards.ts) checks a stored
// quantity: a value of another shape is not shown.

/** A game count: a whole number of 1 or more. */
function isGameCount(n: unknown): n is number {
  return typeof n === 'number' && Number.isInteger(n) && n >= 1;
}

/** The deciding share as the exporter writes it: turn 4 or 5, a target of 0 or more whole mana, a share from 0 to 100. */
function isManaShare(s: unknown): s is RawManaAdequacyShare {
  return (
    typeof s === 'object' &&
    s !== null &&
    'turn' in s &&
    (s.turn === 4 || s.turn === 5) &&
    'manaTarget' in s &&
    typeof s.manaTarget === 'number' &&
    Number.isInteger(s.manaTarget) &&
    s.manaTarget >= 0 &&
    'share' in s &&
    typeof s.share === 'number' &&
    Number.isFinite(s.share) &&
    s.share >= 0 &&
    s.share <= 100
  );
}

// The approved text, in its own number format whatever the browser's locale.
const games = (n: number) => n.toLocaleString('en-US');

export function Performance({ curve, func, sources, health, composition, assessment, goldfishGames, manaSimGames }: PerformanceProps) {
  const maxCurve = Math.max(1, ...curve.map((c) => c.n));
  const rawShare = assessment?.manaAdequacyShare;
  const share = isManaShare(rawShare) ? rawShare : null;
  const goldfish = isGameCount(goldfishGames) ? goldfishGames : null;
  const manaSim = isGameCount(manaSimGames) ? manaSimGames : null;
  return (
    <section className="gv1-section gv1-perf">
      <div className="gv1-section-head">
        <span className="gv1-rune" aria-hidden="true">§ VII</span>
        <h2 className="gv1-section-title">Performance · Scrying Pool</h2>
        {/* The section reads both simulations: the mana simulation feeds the
            MANA and COMMANDER tiles and part of the health score, the goldfish
            its combo term. One count a line; a no-break space holds each "·"
            to its number, and "mana-sim" does not break at its hyphen. */}
        {(goldfish !== null || manaSim !== null) && (
          <span className="gv1-mono-xs gv1-dim">
            {goldfish !== null && <span className="gv1-perf-count">{`·\u00a0${games(goldfish)} goldfish games`}</span>}
            {goldfish !== null && manaSim !== null && ' '}
            {manaSim !== null && (
              <span className="gv1-perf-count">
                {`·\u00a0${games(manaSim)} `}
                <span className="gv1-perf-count-word">mana-sim</span>
                {' games'}
              </span>
            )}
          </span>
        )}
      </div>
      <div className="gv1-perf-grid">
        <div className="gv1-perf-block gv1-perf-kpis">
          {health && (
            <div className="gv1-kpi">
              <div className="gv1-mono-xs gv1-dim">HEALTH SCORE</div>
              <div className="gv1-serif-xxl">{Math.round(health.score)}</div>
              <div className="gv1-mono-xs gv1-rune">grade {health.grade}</div>
            </div>
          )}
          {composition && (
            <div className="gv1-kpi">
              <div className="gv1-mono-xs gv1-dim">AVG CMC</div>
              <div className="gv1-serif-xxl">{composition.avgCmc}</div>
              <div className="gv1-mono-xs gv1-dim">{composition.totalCards} cards · {composition.lands} lands</div>
            </div>
          )}
          {assessment && (
            <div className="gv1-kpi">
              <div className="gv1-mono-xs gv1-dim">MANA</div>
              <div className="gv1-serif-xxl">{assessment.manaAdequacy}</div>
              {share && (
                <div className="gv1-mono-xs gv1-dim">
                  {share.share.toFixed(1)}% of games have {share.manaTarget} or more mana on turn {share.turn}
                </div>
              )}
              <div className="gv1-mono-xs gv1-dim">mulligan · {assessment.mulliganVerdict}</div>
            </div>
          )}
          {assessment && (
            <div className="gv1-kpi">
              <div className="gv1-mono-xs gv1-dim">COMMANDER</div>
              <div className="gv1-serif-xxl">{assessment.commanderTiming}</div>
              <div className="gv1-mono-xs gv1-dim">deploy timing</div>
            </div>
          )}
        </div>

        <div className="gv1-perf-block gv1-perf-curve">
          <div className="gv1-perf-block-head">
            <h3 className="gv1-serif-md">Role distribution</h3>
            <span className="gv1-mono-xs gv1-dim">cards per function · from the manifest</span>
          </div>
          <div className="gv1-curve">
            {curve.map((c, i) => (
              <div key={i} className={'gv1-curve-col' + (c.peak ? ' gv1-peak' : '')}>
                <div className="gv1-curve-bar-wrap">
                  <div className="gv1-curve-bar" style={{ height: (c.n / maxCurve) * 100 + '%' }}>
                    <div className="gv1-curve-n gv1-mono-xs">{c.n}</div>
                  </div>
                </div>
                <div className="gv1-curve-l gv1-mono-xs gv1-dim">{c.cmc}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="gv1-perf-block gv1-perf-func">
          <div className="gv1-perf-block-head">
            <h3 className="gv1-serif-md">Function mix</h3>
            <span className="gv1-mono-xs gv1-dim">cards per role · normalized</span>
          </div>
          <div className="gv1-func-rows">
            {func.map((f, i) => (
              <div key={i} className="gv1-func-row">
                <span className="gv1-mono-xs gv1-func-label">{f.l}</span>
                <div className="gv1-func-bar-wrap">
                  <div className="gv1-func-bar" style={{ width: f.pct + '%' }} />
                  <span className="gv1-func-bar-n gv1-mono-xs">{f.n}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="gv1-perf-block gv1-perf-sources">
          <div className="gv1-perf-block-head">
            <h3 className="gv1-serif-md">Scried from</h3>
            <span className="gv1-mono-xs gv1-dim">source attributions</span>
          </div>
          <div className="gv1-src-list">
            {sources.map((s, i) => (
              <div key={i} className="gv1-src-row">
                <span className="gv1-mono-xs gv1-dim">{String(i + 1).padStart(2, '0')}</span>
                <span className="gv1-mono-xs gv1-rune">{s[0]}</span>
                <span className="gv1-serif-sm">{s[1]}</span>
                <span className="gv1-mono-xs gv1-dim gv1-src-link">
                  open<Glyph> →</Glyph>
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
