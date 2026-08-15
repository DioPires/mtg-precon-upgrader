// Combo Lab — DEC-487 (DEC-476 Phase 0).
//
// A curated (Tier-A) combo report for a Commander deck. Two modes:
//   • Fleet — pick a Grimoire deck; renders its precomputed spellbook-combos.json.
//   • Paste — paste any decklist; matches client-side against the matcher index.
//
// Everything shown is Tier A — Curated (Commander Spellbook). No runtime call to
// Spellbook: fleet mode reads a committed per-deck file, paste mode matches a
// committed index in memory (NF-9). Tier B/C arrive in later phases.

import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { deckLoader } from '../data/loader';
import { loadMatcherIndex } from '../data/spellbook';
import type { RawDeckIndex, RawDeckBundle } from '../data/types';
import type { SpellbookCombo } from '../data/spellbook';
import { matchDecklist, parseDecklist } from '../lib/spellbookMatch';
import {
  bracketLabel,
  buildBracketDisclosure,
  buildPlainTextExport,
  isTwoCardInfinite,
  isWinCombo,
  type ComboReport,
} from '../lib/spellbookReport';

const NEAR_MISS_COLLAPSE_THRESHOLD = 12;

export function ComboLab() {
  const [params, setParams] = useSearchParams();
  const mode = params.get('mode') === 'paste' ? 'paste' : 'fleet';

  const setMode = (m: 'fleet' | 'paste') => {
    const next = new URLSearchParams(params);
    next.set('mode', m);
    setParams(next, { replace: true });
  };

  return (
    <section className="gv1-cl">
      <header className="gv1-cl-head">
        <div>
          <h1 className="gv1-cl-title gv1-serif-lg">Combo Lab</h1>
          <p className="gv1-mono-xs gv1-dim">
            Curated combo detection · Commander Spellbook · Tier A
          </p>
        </div>
        <div className="gv1-cl-modes" role="group" aria-label="Analysis mode">
          <button
            type="button"
            aria-pressed={mode === 'fleet'}
            className={['gv1-chip', mode === 'fleet' ? 'gv1-chip-active' : ''].join(' ')}
            onClick={() => setMode('fleet')}
          >
            Fleet deck
          </button>
          <button
            type="button"
            aria-pressed={mode === 'paste'}
            className={['gv1-chip', mode === 'paste' ? 'gv1-chip-active' : ''].join(' ')}
            onClick={() => setMode('paste')}
          >
            Paste decklist
          </button>
        </div>
      </header>

      {mode === 'fleet' ? <FleetMode params={params} setParams={setParams} /> : <PasteMode />}
    </section>
  );
}

// ─── Fleet mode ────────────────────────────────────────────────────────────────

function FleetMode({
  params,
  setParams,
}: {
  params: URLSearchParams;
  setParams: ReturnType<typeof useSearchParams>[1];
}) {
  const [index, setIndex] = useState<RawDeckIndex | null>(null);
  const [bundle, setBundle] = useState<RawDeckBundle | null>(null);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [error, setError] = useState<string>();

  const selectedId = params.get('deck') ?? index?.commanders[0]?.id ?? '';

  useEffect(() => {
    let cancelled = false;
    deckLoader
      .loadIndex()
      .then((idx) => {
        if (!cancelled) setIndex(idx);
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e));
          setStatus('error');
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    let cancelled = false;
    setStatus('loading');
    deckLoader
      .loadDeck(selectedId)
      .then((b) => {
        if (cancelled) return;
        setBundle(b);
        setStatus('ready');
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : String(e));
        setStatus('error');
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  const report = useMemo<ComboReport | null>(() => {
    const sc = bundle?.spellbookCombos;
    if (!bundle || !sc) return null;
    const deckSize = bundle.deck.decklist?.length ?? 0;
    return {
      mode: 'fleet',
      deckLabel: bundle.deck.name,
      commander: sc.commander,
      corpusVersion: sc.meta.corpusVersion,
      included: sc.included,
      nearMisses: sc.nearMisses,
      nearMissesTotal: sc.counts.nearMissesTotal,
      cardsAnalyzed: deckSize,
      cardsTotal: deckSize,
      unresolved: [],
    };
  }, [bundle]);

  if (status === 'error') {
    return (
      <div className="gv1-stub" role="alert">
        <h2 className="gv1-stub-title">Could not load combos</h2>
        <p className="gv1-mono-xs gv1-dim">{error}</p>
      </div>
    );
  }

  return (
    <div className="gv1-cl-body">
      <label className="gv1-cl-field">
        <span className="gv1-mono-xs gv1-dim">Deck</span>
        <select
          className="gv1-cl-select"
          value={selectedId}
          onChange={(e) => {
            const next = new URLSearchParams(params);
            next.set('deck', e.target.value);
            setParams(next, { replace: true });
          }}
        >
          {(index?.commanders ?? []).map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} — {c.commander ?? ''}
            </option>
          ))}
        </select>
      </label>

      {status === 'loading' && (
        <p className="gv1-mono-xs gv1-dim" aria-busy="true">
          ◇ consulting the curated corpus …
        </p>
      )}
      {status === 'ready' && !report && (
        <div className="gv1-cl-empty gv1-mono-xs gv1-dim">
          No <code>spellbook-combos.json</code> for this deck yet — re-run{' '}
          <code>scripts/sync_spellbook_combos.py</code>.
        </div>
      )}
      {report && <ComboReportView report={report} />}
    </div>
  );
}

// ─── Paste mode ────────────────────────────────────────────────────────────────

function PasteMode() {
  const [text, setText] = useState('');
  const [commander, setCommander] = useState('');
  const [report, setReport] = useState<ComboReport | null>(null);
  const [phase, setPhase] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [error, setError] = useState<string>();
  const [timingMs, setTimingMs] = useState<number | null>(null);

  const analyze = async () => {
    setPhase('loading');
    setError(undefined);
    try {
      const t0 = performance.now();
      const index = await loadMatcherIndex();
      if (!index) throw new Error('matcher index unavailable');
      const parsed = parseDecklist(text);
      if (commander.trim()) {
        for (const line of parseDecklist(commander).cardNames) parsed.commanderNames.push(line);
      }
      const result = matchDecklist(parsed, index);
      const elapsed = performance.now() - t0;
      setTimingMs(elapsed);
      // NF-3 mobile budget: log if the cold parse+match blows the 1.5 s target.
      if (elapsed > 1500) {
        console.warn(`[Combo Lab] parse+match took ${elapsed.toFixed(0)}ms (> 1500ms NF-3 gate)`);
      }
      const resolved = parsed.cardNames.length + parsed.commanderNames.length;
      setReport({
        mode: 'paste',
        deckLabel: 'Pasted decklist',
        commander: parsed.commanderNames,
        corpusVersion: index.meta.corpusVersion,
        included: result.included,
        nearMisses: result.nearMisses,
        nearMissesTotal: result.nearMissesTotal,
        cardsAnalyzed: resolved,
        cardsTotal: resolved + parsed.unresolved.length,
        unresolved: parsed.unresolved,
      });
      setPhase('ready');
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setPhase('error');
    }
  };

  return (
    <div className="gv1-cl-body">
      <div className="gv1-cl-paste">
        <label className="gv1-cl-field">
          <span className="gv1-mono-xs gv1-dim">Commander(s) — optional, comma or newline</span>
          <input
            className="gv1-cl-input"
            value={commander}
            placeholder="e.g. Meren of Clan Nel Toth"
            onChange={(e) => setCommander(e.target.value)}
          />
        </label>
        <label className="gv1-cl-field">
          <span className="gv1-mono-xs gv1-dim">Decklist — one card per line (quantities OK)</span>
          <textarea
            className="gv1-cl-textarea"
            value={text}
            rows={10}
            placeholder={'1 Sol Ring\n1 Ashnod’s Altar\n1 Nim Deathmantle\n…'}
            onChange={(e) => setText(e.target.value)}
          />
        </label>
        <div className="gv1-cl-paste-actions">
          <button
            type="button"
            className="gv1-chip gv1-chip-active gv1-cl-analyze"
            disabled={phase === 'loading' || !text.trim()}
            onClick={analyze}
          >
            {phase === 'loading' ? 'Matching …' : 'Analyze'}
          </button>
          {timingMs != null && (
            <span className="gv1-mono-xs gv1-dim">
              parse+match {timingMs.toFixed(0)}ms
            </span>
          )}
        </div>
      </div>

      {phase === 'error' && (
        <div className="gv1-stub" role="alert">
          <p className="gv1-mono-xs gv1-dim">Could not analyze: {error}</p>
        </div>
      )}
      {report && <ComboReportView report={report} />}
    </div>
  );
}

// ─── Report ────────────────────────────────────────────────────────────────────

function ComboReportView({ report }: { report: ComboReport }) {
  const disc = useMemo(() => buildBracketDisclosure(report.included), [report.included]);
  const [showAllNear, setShowAllNear] = useState(false);
  const [copied, setCopied] = useState(false);

  const nearShown = showAllNear
    ? report.nearMisses
    : report.nearMisses.slice(0, NEAR_MISS_COLLAPSE_THRESHOLD);

  const doExport = async (download: boolean) => {
    const txt = buildPlainTextExport(report);
    if (download) {
      const blob = new Blob([txt], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `combo-report-${report.deckLabel.replace(/\s+/g, '-').toLowerCase()}.txt`;
      a.click();
      URL.revokeObjectURL(url);
      return;
    }
    try {
      await navigator.clipboard.writeText(txt);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="gv1-cl-report">
      {/* Corpus version (DR-7) + attribution (DR-6) + export (RT-4/BR-4) */}
      <div className="gv1-cl-report-bar">
        <div className="gv1-mono-xs gv1-dim">
          Corpus <span className="gv1-rune">{report.corpusVersion.slice(0, 10)}</span>
          {report.mode === 'paste' && report.cardsAnalyzed > 0 && (
            <> · analyzed {report.cardsAnalyzed} cards</>
          )}
        </div>
        <div className="gv1-cl-export">
          <button type="button" className="gv1-chip" onClick={() => doExport(false)}>
            {copied ? 'Copied ✓' : 'Copy report'}
          </button>
          <button type="button" className="gv1-chip" onClick={() => doExport(true)}>
            Download .txt
          </button>
        </div>
      </div>

      {/* Epistemic framing (EI-1..EI-5) */}
      <p className="gv1-cl-framing gv1-mono-xs">
        <span className="gv1-cl-tier gv1-cl-tier-a">Tier A · Curated</span> Every finding below is
        human-verified by Commander Spellbook. Analysis is a <strong>goldfish</strong> (no
        interaction assumed). Not exhaustive — only combos in the curated corpus are detected.
      </p>

      {/* IN-6 / RT-5 — completeness warning: unresolvable lines, remainder analyzed. */}
      {report.unresolved.length > 0 && (
        <div className="gv1-cl-warn gv1-mono-xs" role="status">
          Analyzed {report.cardsAnalyzed} of {report.cardsTotal} lines.{' '}
          {report.unresolved.length} line{report.unresolved.length > 1 ? 's' : ''} could not be read
          and {report.unresolved.length > 1 ? 'were' : 'was'} skipped:{' '}
          <span className="gv1-dim">{report.unresolved.join(' · ')}</span>
        </div>
      )}

      {/* Tier-A combos present */}
      <section className="gv1-cl-section" aria-label="Combos present">
        <h2 className="gv1-cl-h2 gv1-mono-xs">
          Combos present <span className="gv1-dim">({report.included.length})</span>
        </h2>
        {report.included.length === 0 ? (
          <p className="gv1-cl-empty gv1-mono-xs gv1-dim">
            No curated combos found (at any tier), within corpus coverage.
          </p>
        ) : (
          <ul className="gv1-cl-list">
            {report.included.map((c) => (
              <FindingCard key={c.id} combo={c} kind="included" />
            ))}
          </ul>
        )}
      </section>

      {/* Tier-A near-misses */}
      <section className="gv1-cl-section" aria-label="Near-misses">
        <h2 className="gv1-cl-h2 gv1-mono-xs">
          One–two cards away{' '}
          <span className="gv1-dim">
            ({report.nearMisses.length}
            {report.nearMissesTotal > report.nearMisses.length
              ? ` of ${report.nearMissesTotal}`
              : ''}
            )
          </span>
        </h2>
        {report.nearMisses.length === 0 ? (
          <p className="gv1-cl-empty gv1-mono-xs gv1-dim">No qualifying near-misses.</p>
        ) : (
          <>
            <ul className="gv1-cl-list">
              {nearShown.map((c) => (
                <FindingCard key={c.id} combo={c} kind="near" />
              ))}
            </ul>
            {report.nearMisses.length > NEAR_MISS_COLLAPSE_THRESHOLD && (
              <button
                type="button"
                className="gv1-chip gv1-cl-more"
                onClick={() => setShowAllNear((v) => !v)}
              >
                {showAllNear
                  ? 'Show fewer'
                  : `Show all ${report.nearMisses.length} near-misses`}
              </button>
            )}
          </>
        )}
      </section>

      {/* Bracket / Rule-0 disclosure (BR-1..BR-4) — RT-2 order: after findings. */}
      <section className="gv1-cl-section" aria-label="Bracket disclosure">
        <h2 className="gv1-cl-h2 gv1-mono-xs">Bracket / Rule-0 disclosure</h2>
        <div className="gv1-cl-disclosure">
          <Stat n={disc.totalCombos} label="curated combos" />
          <Stat n={disc.twoCardInfinites} label="two-card infinites" emphasize />
          <Stat n={disc.winCombos} label="win the game" />
        </div>
        {disc.byBracketTag.length > 0 && (
          <p className="gv1-mono-xs gv1-dim gv1-cl-tags">
            Spellbook bracket tags:{' '}
            {disc.byBracketTag.map((b) => `${b.label} ×${b.count}`).join(' · ')}
          </p>
        )}
      </section>

      <footer className="gv1-cl-attrib gv1-mono-xs gv1-dim">
        Combo data © Commander Spellbook (CC-BY-SA). Card data © Scryfall. Not affiliated with or
        endorsed by Wizards of the Coast.
      </footer>
    </div>
  );
}

function Stat({ n, label, emphasize }: { n: number; label: string; emphasize?: boolean }) {
  return (
    <div className={['gv1-cl-stat', emphasize && n > 0 ? 'gv1-cl-stat-hot' : ''].join(' ')}>
      <span className="gv1-cl-stat-n gv1-serif-md">{n}</span>
      <span className="gv1-mono-xs gv1-dim">{label}</span>
    </div>
  );
}

function FindingCard({ combo, kind }: { combo: SpellbookCombo; kind: 'included' | 'near' }) {
  const twoCard = isTwoCardInfinite(combo);
  const win = isWinCombo(combo);
  return (
    <li className="gv1-cl-finding">
      <div className="gv1-cl-finding-head">
        <span className="gv1-cl-tier gv1-cl-tier-a">Tier A</span>
        {win && <span className="gv1-cl-flag gv1-cl-flag-win">Win</span>}
        {twoCard && <span className="gv1-cl-flag">2-card infinite</span>}
        <span className="gv1-mono-xs gv1-dim gv1-cl-bracket">
          {bracketLabel(combo.bracketTag)}
        </span>
        {combo.popularity > 0 && (
          <span className="gv1-mono-xs gv1-dim gv1-cl-pop" title="Decks running this on Spellbook">
            {combo.popularity.toLocaleString()} decks
          </span>
        )}
      </div>

      <div className="gv1-cl-finding-cards">
        {combo.cards.map((c, i) => (
          <span key={`${c.name}-${i}`} className="gv1-cl-cardname" data-card-name={c.name}>
            {c.name}
            {c.mustBeCommander && <span className="gv1-cl-cmdr"> (cmdr)</span>}
          </span>
        ))}
        {combo.templates.map((t, i) => (
          <span key={`t-${i}`} className="gv1-cl-template" title={t.query}>
            {t.name}
          </span>
        ))}
      </div>

      {kind === 'near' && combo.missing && (
        <p className="gv1-cl-needs gv1-mono-xs">
          <span className="gv1-cl-needs-label">Needs</span>{' '}
          {combo.missing.cards.map((n, i) => (
            <span key={`c-${i}-${n}`}>
              {i > 0 && ', '}
              <span className="gv1-cl-cardname gv1-cl-needs-card" data-card-name={n}>
                {n}
              </span>
            </span>
          ))}
          {combo.missing.templates.map((t, i) => (
            <span key={`t-${i}-${t.name}`}>
              {(combo.missing!.cards.length > 0 || i > 0) && ', '}
              <span className="gv1-cl-template" title={t.query}>
                a {t.name}
              </span>
            </span>
          ))}
        </p>
      )}

      {combo.produces.length > 0 && (
        <div className="gv1-cl-produces">
          {combo.produces.map((p, i) => (
            <span key={`${p}-${i}`} className="gv1-cl-result">
              {p}
            </span>
          ))}
        </div>
      )}

      {/* PR-1/PR-2/TX-1 — curated prerequisites + steps, passed through verbatim
          with attribution (fleet mode embeds them; paste mode links out). */}
      {hasCuratedDetail(combo) && (
        <details className="gv1-cl-detail">
          <summary className="gv1-mono-xs gv1-cl-detail-summary">Steps &amp; prerequisites</summary>
          {(combo.prerequisites.easy || combo.prerequisites.notable || combo.manaNeeded) && (
            <div className="gv1-cl-detail-block">
              <span className="gv1-cl-detail-label gv1-mono-xs gv1-dim">Prerequisites</span>
              {combo.manaNeeded && <p>Mana: {combo.manaNeeded}</p>}
              {combo.prerequisites.easy && <p>{combo.prerequisites.easy}</p>}
              {combo.prerequisites.notable && <p>{combo.prerequisites.notable}</p>}
            </div>
          )}
          {combo.steps && (
            <div className="gv1-cl-detail-block">
              <span className="gv1-cl-detail-label gv1-mono-xs gv1-dim">Steps</span>
              {combo.steps.split('\n').map((line, i) => (
                <p key={i}>{line}</p>
              ))}
            </div>
          )}
          <span className="gv1-mono-xs gv1-dim">Curated by Commander Spellbook.</span>
        </details>
      )}

      <a
        className="gv1-mono-xs gv1-cl-why"
        href={combo.permalink}
        target="_blank"
        rel="noreferrer"
      >
        Why? — full combo on Commander Spellbook ↗
      </a>
    </li>
  );
}

/** Fleet-mode combos embed steps/prerequisites; paste-mode combos leave them
 * empty and rely on the permalink. */
function hasCuratedDetail(c: SpellbookCombo): boolean {
  return Boolean(c.steps || c.prerequisites.easy || c.prerequisites.notable || c.manaNeeded);
}
