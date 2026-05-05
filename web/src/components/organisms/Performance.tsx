// Port of gv1-perf.jsx GV1Performance (lines 357–453).

import type {
  DeckCurveEntry,
  DeckFuncEntry,
  RawAssessment,
  RawDeckComposition,
  RawDeckHealthScore,
} from '../../data/types';

interface PerformanceProps {
  curve: DeckCurveEntry[];
  func: DeckFuncEntry[];
  sources: Array<readonly [string, string]>;
  health: RawDeckHealthScore | null;
  composition: RawDeckComposition | null;
  assessment: RawAssessment | null;
}

export function Performance({ curve, func, sources, health, composition, assessment }: PerformanceProps) {
  const maxCurve = Math.max(1, ...curve.map((c) => c.n));
  return (
    <section className="gv1-section gv1-perf">
      <div className="gv1-section-head">
        <span className="gv1-rune" aria-hidden="true">§ VI</span>
        <h2 className="gv1-section-title">Performance · Scrying Pool</h2>
        <span className="gv1-mono-xs gv1-dim">· 10,000 simulated games</span>
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
                <div className="gv1-curve-n gv1-mono-xs">{c.n}</div>
                <div className="gv1-curve-bar-wrap">
                  <div className="gv1-curve-bar" style={{ height: (c.n / maxCurve) * 100 + '%' }} />
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
                <span className="gv1-mono-xs gv1-dim gv1-src-link">open →</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
