// Combo Lab — DEC-487 (DEC-476 Phase 0).
//
// A curated (Tier-A) combo report for a Commander deck. Two modes:
//   • Fleet — pick a Grimoire deck; renders its precomputed spellbook-combos.json.
//   • Paste — paste any decklist; matches client-side against the matcher index.
//
// Everything shown is Tier A — Curated (Commander Spellbook). No runtime call to
// Spellbook: fleet mode reads a committed per-deck file, paste mode matches a
// committed index in memory (NF-9). Tier B/C arrive in later phases.

import { useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { deckLoader } from '../data/loader';
import { loadMatcherIndex } from '../data/spellbook';
import { loadFeatureIndex, loadSynergyConfig } from '../data/synergy';
import type { FeatureIndex, SynergyCandidate, SynergyConfig } from '../data/synergy';
import type { RawDeckIndex, RawDeckBundle } from '../data/types';
import type { SpellbookCombo } from '../data/spellbook';
import { analyze as analyzeSynergy } from '../lib/synergyMatch';
import { matchDecklist, parseDecklist } from '../lib/spellbookMatch';
import {
  bracketLabel,
  buildBracketDisclosure,
  buildMarkdownExport,
  buildPlainTextExport,
  isTwoCardInfinite,
  isWinCombo,
  loopClassLabel,
  type ComboReport,
  type SynergyReport,
  type TierBReport,
} from '../lib/spellbookReport';
import type { TierBFinding } from '../data/tierB';
import { loadPriceIndex, type Currency, type PriceIndex } from '../data/prices';
import {
  analyzeCompletions,
  deriveColorIdentity,
  parseOwnedCollection,
  type CompletionReport,
} from '../lib/nearMissComplete';
import { resolveDeckUrl, DeckUrlError } from '../lib/deckUrl';
import { loadTierBIndex } from '../data/tierBIndex';
import { verifyDeck } from '../lib/comboVerify';

const NEAR_MISS_COLLAPSE_THRESHOLD = 12;
const SYNERGY_COLLAPSE_THRESHOLD = 10;

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
    const tbl = bundle.tierBLoops;
    const tierB: TierBReport | undefined = tbl
      ? {
          counts: tbl.counts,
          corroborated: tbl.verifiedCorroborated,
          novel: tbl.verifiedNovel,
          engines: tbl.engines,
          capped: tbl.capped,
          crowdPriorApplied: tbl.meta.crowdPriorApplied,
        }
      : undefined;
    const syn = bundle.synergyCandidates;
    const synergy: SynergyReport | undefined = syn
      ? {
          crowdPriorApplied: syn.meta.crowdPriorApplied,
          deepFocused: syn.meta.deepFocused,
          counts: syn.counts,
          uncovered: syn.uncovered,
          pairs: syn.pairs,
          triples: syn.triples,
          cycles: syn.cycles,
          // Fleet precompute always ships triples/cycles — no deep scan needed.
          deepAvailable: true,
        }
      : undefined;
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
      synergy,
      tierB,
    };
  }, [bundle]);

  // Completion inputs (Phase 4). Deck names + precomputed engine deficits + the
  // declared color identity feed the client-side near-miss completion engine.
  const completionInputs = useMemo(() => {
    if (!bundle) return null;
    const names = [
      ...(bundle.deck.decklist ?? []).map((c) => c.name),
      ...(bundle.spellbookCombos?.commander ?? []),
    ];
    const colors = index?.commanders.find((c) => c.id === selectedId)?.colors ?? [];
    const ci = colors.filter((c) => c !== 'C').join('') || 'C';
    return { names, engines: bundle.tierBLoops?.engines ?? [], colorIdentity: ci };
  }, [bundle, index, selectedId]);

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
      {report && (
        <ComboReportView
          report={report}
          completionInputs={
            completionInputs
              ? {
                  names: completionInputs.names,
                  engines: completionInputs.engines,
                  colorIdentity: completionInputs.colorIdentity,
                }
              : undefined
          }
        />
      )}
    </div>
  );
}

// ─── Paste mode ────────────────────────────────────────────────────────────────

function PasteMode() {
  const [text, setText] = useState('');
  const [commander, setCommander] = useState('');
  const [deckUrl, setDeckUrl] = useState('');
  const [urlBusy, setUrlBusy] = useState(false);
  const [urlMsg, setUrlMsg] = useState<string>();
  const [report, setReport] = useState<ComboReport | null>(null);
  const [pasteNames, setPasteNames] = useState<string[]>([]);
  // Computed Tier-B engine deficits from the last Analyze; feed the near-miss
  // completion engine. null ⇒ verifier index unavailable (completion falls back).
  const [pasteEngines, setPasteEngines] = useState<TierBFinding[] | null>(null);
  const [phase, setPhase] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [error, setError] = useState<string>();
  const [timingMs, setTimingMs] = useState<number | null>(null);
  const [deepScanning, setDeepScanning] = useState(false);

  // IN-2 — resolve a Moxfield/Archidekt deck URL into the paste fields. A static
  // app cannot proxy, so a host that blocks browser access degrades to a message.
  const resolveUrl = async () => {
    if (!deckUrl.trim() || urlBusy) return;
    setUrlBusy(true);
    setUrlMsg(undefined);
    try {
      const deck = await resolveDeckUrl(deckUrl.trim());
      setText(deck.cardNames.join('\n'));
      setCommander(deck.commanderNames.join('\n'));
      setUrlMsg(
        `Loaded ${deck.cardNames.length} cards from ${deck.site}${
          deck.name ? ` — “${deck.name}”` : ''
        }. Review, then Analyze.`,
      );
    } catch (e) {
      setUrlMsg(
        e instanceof DeckUrlError
          ? e.message
          : e instanceof Error
            ? e.message
            : 'Could not resolve that URL.',
      );
    } finally {
      setUrlBusy(false);
    }
  };
  // Inputs cached from the last Analyze so the deep scan can re-run the engine
  // without re-parsing or refetching the 3.3 MB feature index.
  const synergyInput = useRef<{ names: string[]; fi: FeatureIndex; cfg: SynergyConfig } | null>(
    null,
  );

  const analyze = async () => {
    setPhase('loading');
    setError(undefined);
    synergyInput.current = null;
    try {
      const t0 = performance.now();
      const index = await loadMatcherIndex();
      if (!index) throw new Error('matcher index unavailable');
      const parsed = parseDecklist(text);
      if (commander.trim()) {
        for (const line of parseDecklist(commander).cardNames) parsed.commanderNames.push(line);
      }
      const result = matchDecklist(parsed, index);

      // Tier-C synergy engine (paste mode = no crowd prior). Default deep:false —
      // pairs only, instant; triples/cycles arrive behind the deep-scan action.
      const [featureIndex, synergyConfig] = await Promise.all([
        loadFeatureIndex(),
        loadSynergyConfig(),
      ]);
      let synergy: SynergyReport | undefined;
      if (featureIndex && synergyConfig) {
        const names = [...parsed.cardNames, ...parsed.commanderNames];
        synergyInput.current = { names, fi: featureIndex, cfg: synergyConfig };
        const syn = analyzeSynergy(names, featureIndex, synergyConfig, { deep: false });
        synergy = {
          crowdPriorApplied: syn.crowdPriorApplied,
          deepFocused: syn.truncated.deepFocused,
          counts: syn.counts,
          uncovered: syn.uncovered,
          pairs: syn.pairs,
          triples: syn.triples,
          cycles: syn.cycles,
          deepAvailable: false,
        };
      }

      // Tier-B verified loops (DEC-516): run the Phase-3 deterministic verifier
      // client-side over the pasted deck. The matched Tier-A `included` combos are
      // the curated corpus for corroboration (DB-7). No crowd prior (decision 4).
      const tierBIndex = await loadTierBIndex();
      let tierB: TierBReport | undefined;
      if (tierBIndex) {
        const curatedCardSets = result.included.map((c) => c.cards.map((x) => x.name));
        const vres = verifyDeck([...parsed.cardNames, ...parsed.commanderNames], tierBIndex, {
          curatedCardSets,
          commanderNames: parsed.commanderNames,
        });
        tierB = {
          counts: vres.counts,
          corroborated: vres.corroborated,
          novel: vres.novel,
          engines: vres.engines,
          capped: vres.capped,
          crowdPriorApplied: false,
        };
        // Feed the computed engine deficits to the near-miss completion engine so
        // paste mode gets Tier-B completions too (no longer deferred).
        setPasteEngines(vres.engines);
      } else {
        setPasteEngines(null);
      }

      setPasteNames([...parsed.cardNames, ...parsed.commanderNames]);
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
        synergy,
        tierB,
      });
      setPhase('ready');
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setPhase('error');
    }
  };

  // OQ-3 — deep scan: re-run the engine with deep:true to enumerate triples &
  // 4-cycles, then fold them into the existing report.
  const runDeepScan = async () => {
    const inp = synergyInput.current;
    if (!inp || deepScanning) return;
    setDeepScanning(true);
    // Yield a frame so the spinner paints before the synchronous enumeration.
    await new Promise((r) => setTimeout(r, 0));
    try {
      const syn = analyzeSynergy(inp.names, inp.fi, inp.cfg, { deep: true });
      setReport((prev) =>
        prev && prev.synergy
          ? {
              ...prev,
              synergy: {
                ...prev.synergy,
                deepFocused: syn.truncated.deepFocused,
                counts: syn.counts,
                triples: syn.triples,
                cycles: syn.cycles,
                deepAvailable: true,
              },
            }
          : prev,
      );
    } finally {
      setDeepScanning(false);
    }
  };

  return (
    <div className="gv1-cl-body">
      <div className="gv1-cl-paste">
        <label className="gv1-cl-field">
          <span className="gv1-mono-xs gv1-dim">Deck URL — Moxfield or Archidekt (optional)</span>
          <div className="gv1-cl-url-row">
            <input
              className="gv1-cl-input"
              value={deckUrl}
              placeholder="https://moxfield.com/decks/… or https://archidekt.com/decks/…"
              onChange={(e) => setDeckUrl(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  resolveUrl();
                }
              }}
            />
            <button
              type="button"
              className="gv1-chip"
              disabled={urlBusy || !deckUrl.trim()}
              onClick={resolveUrl}
            >
              {urlBusy ? 'Loading …' : 'Load'}
            </button>
          </div>
          {urlMsg && <span className="gv1-mono-xs gv1-dim gv1-cl-url-msg">{urlMsg}</span>}
        </label>
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
      {report && (
        <ComboReportView
          report={report}
          onDeepScan={runDeepScan}
          deepScanning={deepScanning}
          completionInputs={{ names: pasteNames, engines: pasteEngines }}
        />
      )}
    </div>
  );
}

// ─── Report ────────────────────────────────────────────────────────────────────

interface CompletionInputs {
  names: string[];
  engines: TierBFinding[] | null;
  colorIdentity?: string;
}

function ComboReportView({
  report,
  onDeepScan,
  deepScanning,
  completionInputs,
}: {
  report: ComboReport;
  onDeepScan?: () => void;
  deepScanning?: boolean;
  completionInputs?: CompletionInputs;
}) {
  const disc = useMemo(() => buildBracketDisclosure(report.included), [report.included]);
  const [showAllNear, setShowAllNear] = useState(false);
  const [copied, setCopied] = useState<'txt' | 'md' | null>(null);
  const [completions, setCompletions] = useState<CompletionReport | null>(null);

  // Drop stale completions when the underlying report changes (deck switch or a
  // fresh paste analysis) so exports never carry another deck's suggestions.
  useEffect(() => setCompletions(null), [report]);

  const nearShown = showAllNear
    ? report.nearMisses
    : report.nearMisses.slice(0, NEAR_MISS_COLLAPSE_THRESHOLD);

  const slug = report.deckLabel.replace(/\s+/g, '-').toLowerCase();
  const doExport = async (kind: 'copy-txt' | 'download-txt' | 'copy-md' | 'download-md') => {
    const md = kind.endsWith('md');
    const txt = md
      ? buildMarkdownExport(report, completions)
      : buildPlainTextExport(report, completions);
    if (kind.startsWith('download')) {
      const blob = new Blob([txt], { type: md ? 'text/markdown' : 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `combo-report-${slug}.${md ? 'md' : 'txt'}`;
      a.click();
      URL.revokeObjectURL(url);
      return;
    }
    try {
      await navigator.clipboard.writeText(txt);
      setCopied(md ? 'md' : 'txt');
      setTimeout(() => setCopied(null), 1600);
    } catch {
      setCopied(null);
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
          <button type="button" className="gv1-chip" onClick={() => doExport('copy-txt')}>
            {copied === 'txt' ? 'Copied ✓' : 'Copy text'}
          </button>
          <button type="button" className="gv1-chip" onClick={() => doExport('copy-md')}>
            {copied === 'md' ? 'Copied ✓' : 'Copy Markdown'}
          </button>
          <button type="button" className="gv1-chip" onClick={() => doExport('download-txt')}>
            .txt
          </button>
          <button type="button" className="gv1-chip" onClick={() => doExport('download-md')}>
            .md
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

      {/* Tier-B verified loops (RT-2 order: after Tier-A combos, before the rest). */}
      {report.tierB && <TierBSection tierB={report.tierB} />}

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

      {/* Tier-C synergies (RT-2 order: after Tier A, before bracket). */}
      {report.synergy && (
        <SynergySection
          report={report}
          synergy={report.synergy}
          onDeepScan={onDeepScan}
          deepScanning={deepScanning}
        />
      )}

      {/* Computed near-miss completions (Phase 4 / NM-1) — the mechanistic
          recommendation engine, run on demand over the full-coverage KB. */}
      {completionInputs && completionInputs.names.length > 0 && (
        <CompletionPanel
          key={completionInputs.names.join('|').slice(0, 80)}
          inputs={completionInputs}
          onResult={setCompletions}
        />
      )}

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

// ─── Tier-B verified loops (DEC-501) ─────────────────────────────────────────────

/** Machine-verified loop layer. Findings here are Tier B — computed, "verified
 * under Laço's game model" (EI-2), never a comprehensive-rules proof. Corroborated
 * loops are also curated (Tier A) and labelled as such (DB-7). Loops the provenance
 * gate held back are disclosed, not shown as verified (plan 6b). */
function TierBSection({ tierB }: { tierB: TierBReport }) {
  const { corroborated, novel, engines, capped } = tierB;
  const nothing =
    !corroborated.length && !novel.length && !engines.length && !capped.length;
  return (
    <section className="gv1-cl-section" aria-label="Tier-B verified loops">
      <h2 className="gv1-cl-h2 gv1-mono-xs">
        Verified loops{' '}
        <span className="gv1-dim">({corroborated.length + novel.length})</span>
      </h2>

      {/* Epistemic framing (EI-1/EI-2) — model-conditional, one detail away. */}
      <p className="gv1-cl-framing gv1-cl-framing-b gv1-mono-xs">
        <span className="gv1-cl-tier gv1-cl-tier-b">Tier B · Computed</span> Machine-verified
        against Laço's loop-closure model — <strong>verified under the model</strong>, not a
        comprehensive-rules ruling. Deterministic (no AI at query time); a goldfish is assumed.
        Findings consume only human-reviewed / deterministic knowledge (provenance gate).
      </p>

      {nothing ? (
        <p className="gv1-cl-empty gv1-mono-xs gv1-dim">
          No loops verified under the model — not an exhaustiveness claim (only the modelled loop
          shapes over covered cards are checked).
        </p>
      ) : (
        <ul className="gv1-cl-list">
          {corroborated.map((f, i) => (
            <TierBFindingCard key={`corr-${i}-${f.cards.join('|')}`} f={f} kind="corroborated" />
          ))}
          {novel.map((f, i) => (
            <TierBFindingCard key={`nov-${i}-${f.cards.join('|')}`} f={f} kind="novel" />
          ))}
          {engines.map((f, i) => (
            <TierBFindingCard key={`eng-${i}-${f.cards.join('|')}`} f={f} kind="engine" />
          ))}
        </ul>
      )}

      {/* Provenance-gate disclosure (plan 6b) — held at Tier C, not shown as verified. */}
      {capped.length > 0 && (
        <div className="gv1-cl-warn gv1-mono-xs" role="status">
          {capped.length} candidate loop{capped.length > 1 ? 's' : ''} held at Tier C: a
          loop-relevant card's knowledge-base entry is not yet human-reviewed, so the verifier will
          not label {capped.length > 1 ? 'them' : 'it'} verified (provenance gate).
        </div>
      )}
    </section>
  );
}

const TIER_B_KIND_FLAG: Record<'corroborated' | 'novel' | 'engine', string> = {
  corroborated: 'Also curated (Tier A)',
  novel: 'Novel — verified by the model',
  engine: 'Value engine / near-miss',
};

function TierBFindingCard({
  f,
  kind,
}: {
  f: TierBFinding;
  kind: 'corroborated' | 'novel' | 'engine';
}) {
  // A corroborated loop is presented at Tier A (it is curated ground truth), with
  // the computed verification as corroboration. Novel/engine are Tier B.
  const tierClass = kind === 'corroborated' ? 'gv1-cl-tier-a' : 'gv1-cl-tier-b';
  const tierLabel = kind === 'corroborated' ? 'Tier A' : 'Tier B';
  return (
    <li className="gv1-cl-finding">
      <div className="gv1-cl-finding-head">
        <span className={['gv1-cl-tier', tierClass].join(' ')}>{tierLabel}</span>
        <span className="gv1-cl-flag">{TIER_B_KIND_FLAG[kind]}</span>
        <span className="gv1-mono-xs gv1-dim gv1-cl-shape">{loopClassLabel(f)}</span>
      </div>

      <div className="gv1-cl-finding-cards">
        {f.cards.map((n, i) => (
          <span key={`${n}-${i}`} className="gv1-cl-cardname" data-card-name={n}>
            {n}
          </span>
        ))}
      </div>

      {f.resultTypes.length > 0 && (
        <div className="gv1-cl-produces">
          {f.resultTypes.map((r) => (
            <span key={r} className="gv1-cl-result">
              {r.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      )}

      {/* TX-1 — the loop trace / why-is-this-here. For a near-miss, the deficit
          vector states the leak in user terms (TX-3). */}
      {f.deficit.length > 0 && f.deficit.some((d) => d.shortfall != null) ? (
        <p className="gv1-cl-needs gv1-mono-xs">
          <span className="gv1-cl-needs-label">Leaks</span>{' '}
          {f.deficit
            .filter((d) => d.shortfall != null)
            .map((d) => `${d.shortfall} ${d.resource}/iteration`)
            .join(', ')}
        </p>
      ) : null}

      <details className="gv1-cl-detail">
        <summary className="gv1-mono-xs gv1-cl-detail-summary">Loop trace &amp; prerequisites</summary>
        {f.trace.length > 0 && (
          <div className="gv1-cl-detail-block">
            <span className="gv1-cl-detail-label gv1-mono-xs gv1-dim">Trace</span>
            {f.trace.map((line, i) => (
              <p key={i}>{line}</p>
            ))}
          </div>
        )}
        <div className="gv1-cl-detail-block">
          <span className="gv1-cl-detail-label gv1-mono-xs gv1-dim">Prerequisites</span>
          <p>Minimum starting mana: {f.prerequisites.minInitialMana}</p>
          {f.prerequisites.guards.length > 0 && (
            <p>Guards: {f.prerequisites.guards.map((g) => g.replace(/_/g, ' ')).join(', ')}</p>
          )}
          <p className="gv1-dim">{f.prerequisites.note}</p>
        </div>
        <div className="gv1-cl-detail-block">
          <span className="gv1-cl-detail-label gv1-mono-xs gv1-dim">Provenance</span>
          <p className="gv1-dim">
            Ontology {String(f.provenance.ontologyVersion)} · extractor{' '}
            {String(f.provenance.extractorVersion)} · {f.provenance.gate}
          </p>
        </div>
      </details>
    </li>
  );
}

// ─── Tier-C synergies (DEC-491) ──────────────────────────────────────────────────

/** Heuristic synergy layer. Everything here is Tier C — speculative signals, NOT
 * verified combos (EI-1/EI-4). Coarse bands only, never a numeric score (RK-5).
 * Default view: pairs only; a deep scan reveals triples & 4-cycles (OQ-3). */
function SynergySection({
  report,
  synergy,
  onDeepScan,
  deepScanning,
}: {
  report: ComboReport;
  synergy: SynergyReport;
  onDeepScan?: () => void;
  deepScanning?: boolean;
}) {
  const [showAllPairs, setShowAllPairs] = useState(false);
  const [showDeep, setShowDeep] = useState(false);
  // Auto-reveal deep results the moment they arrive from a paste-mode deep scan
  // (fleet mode ships them pre-loaded, so we must NOT auto-reveal there).
  const prevDeep = useRef(synergy.deepAvailable);
  useEffect(() => {
    if (!prevDeep.current && synergy.deepAvailable) setShowDeep(true);
    prevDeep.current = synergy.deepAvailable;
  }, [synergy.deepAvailable]);

  const pairsShown = showAllPairs
    ? synergy.pairs
    : synergy.pairs.slice(0, SYNERGY_COLLAPSE_THRESHOLD);

  const deepReveal = () => {
    if (synergy.deepAvailable) setShowDeep((v) => !v);
    else if (onDeepScan) onDeepScan();
  };

  const deepCount = synergy.counts.triples + synergy.counts.cycles;
  const deepButtonLabel = deepScanning
    ? '◇ scanning couplings …'
    : synergy.deepAvailable
      ? showDeep
        ? 'Hide triples & 4-cycles'
        : `Show triples & 4-cycles (${deepCount})`
      : 'Deep scan (triples & 4-cycles)';

  return (
    <section className="gv1-cl-section" aria-label="Tier-C synergies">
      <h2 className="gv1-cl-h2 gv1-mono-xs">
        Synergies <span className="gv1-dim">({synergy.counts.pairs})</span>
      </h2>

      {/* Epistemic framing (EI-1/EI-4) — Tier C is heuristic, never verified. */}
      <p className="gv1-cl-framing gv1-cl-framing-c gv1-mono-xs">
        <span className="gv1-cl-tier gv1-cl-tier-c">Tier C · Heuristic</span> Speculative synergy
        signals from a provides/wants graph — <strong>not verified combos</strong>. Each finding is
        justified by its matched couplings below; bands are coarse and unvalidated.
      </p>

      {/* Crowd-prior note (plan decision 4). */}
      <p className="gv1-mono-xs gv1-dim gv1-cl-synergy-note">
        {report.mode === 'paste'
          ? 'Crowd-prior ranking (EDHREC) is applied in fleet mode only; this pasted-deck ranking omits it.'
          : synergy.crowdPriorApplied
            ? 'Ranking includes an EDHREC crowd prior.'
            : 'Ranking uses magnitude + deck-fit signals only.'}
      </p>

      {/* KB-gap caveat (DC-6) — distinct wording from the IN-6 unresolved warning. */}
      {synergy.uncovered.length > 0 && (
        <div className="gv1-cl-warn gv1-mono-xs" role="status">
          {synergy.uncovered.length} card{synergy.uncovered.length > 1 ? 's have' : ' has'} no
          knowledge-base entry yet and {synergy.uncovered.length > 1 ? 'were' : 'was'} skipped for
          synergy analysis: <span className="gv1-dim">{synergy.uncovered.join(' · ')}</span>
        </div>
      )}

      {synergy.pairs.length === 0 ? (
        <p className="gv1-cl-empty gv1-mono-xs gv1-dim">No heuristic synergy pairs surfaced.</p>
      ) : (
        <>
          <ul className="gv1-cl-list">
            {pairsShown.map((c, i) => (
              <SynergyFinding key={`p-${i}-${c.cards.join('|')}`} cand={c} shape="pair" />
            ))}
          </ul>
          {synergy.pairs.length > SYNERGY_COLLAPSE_THRESHOLD && (
            <button
              type="button"
              className="gv1-chip gv1-cl-more"
              onClick={() => setShowAllPairs((v) => !v)}
            >
              {showAllPairs ? 'Show fewer' : `Show all ${synergy.pairs.length} pairs`}
            </button>
          )}
        </>
      )}

      {/* Deep scan (OQ-3) — triples & 4-cycles behind an explicit action. */}
      <div className="gv1-cl-synergy-deep">
        <button
          type="button"
          className="gv1-chip gv1-cl-more"
          onClick={deepReveal}
          disabled={deepScanning}
          aria-busy={deepScanning}
        >
          {deepButtonLabel}
        </button>
        {synergy.deepFocused && (showDeep || synergy.deepAvailable) && (
          <span className="gv1-mono-xs gv1-dim">
            Deep scan focused on the strongest couplings.
          </span>
        )}
      </div>

      {showDeep && synergy.deepAvailable && (
        <>
          <div className="gv1-cl-synergy-group">
            <h3 className="gv1-cl-h3 gv1-mono-xs">
              Triples <span className="gv1-dim">({synergy.counts.triples})</span>
            </h3>
            {synergy.triples.length === 0 ? (
              <p className="gv1-cl-empty gv1-mono-xs gv1-dim">No triples surfaced.</p>
            ) : (
              <ul className="gv1-cl-list">
                {synergy.triples.map((c, i) => (
                  <SynergyFinding key={`t-${i}-${c.cards.join('|')}`} cand={c} shape="triple" />
                ))}
              </ul>
            )}
          </div>
          <div className="gv1-cl-synergy-group">
            <h3 className="gv1-cl-h3 gv1-mono-xs">
              4-cycles <span className="gv1-dim">({synergy.counts.cycles})</span>
            </h3>
            {synergy.cycles.length === 0 ? (
              <p className="gv1-cl-empty gv1-mono-xs gv1-dim">No 4-cycles surfaced.</p>
            ) : (
              <ul className="gv1-cl-list">
                {synergy.cycles.map((c, i) => (
                  <SynergyFinding key={`c-${i}-${c.cards.join('|')}`} cand={c} shape="cycle" />
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </section>
  );
}

const SYNERGY_SHAPE_LABEL: Record<'pair' | 'triple' | 'cycle', string> = {
  pair: '2-card',
  triple: '3-card',
  cycle: '4-cycle',
};

function SynergyFinding({
  cand,
  shape,
}: {
  cand: SynergyCandidate;
  shape: 'pair' | 'triple' | 'cycle';
}) {
  return (
    <li className="gv1-cl-finding">
      <div className="gv1-cl-finding-head">
        <span className="gv1-cl-tier gv1-cl-tier-c">Tier C</span>
        <span
          className={[
            'gv1-cl-band',
            cand.band === 'strong' ? 'gv1-cl-band-strong' : 'gv1-cl-band-spec',
          ].join(' ')}
        >
          {cand.band}
        </span>
        <span className="gv1-mono-xs gv1-dim gv1-cl-shape">{SYNERGY_SHAPE_LABEL[shape]}</span>
      </div>

      <div className="gv1-cl-finding-cards">
        {cand.cards.map((n, i) => (
          <span key={`${n}-${i}`} className="gv1-cl-cardname" data-card-name={n}>
            {n}
          </span>
        ))}
      </div>

      {/* DC-3 / TX-1 — every synergy is explained by its matched couplings. */}
      <ul className="gv1-cl-edges">
        {cand.edges.map((e, i) => (
          <li key={`${e.from}-${e.to}-${e.fromFeature}-${e.toFeature}-${i}`} className="gv1-cl-edge">
            <span className="gv1-cl-edge-pair">
              {e.from} → {e.to}
            </span>
            <span className="gv1-cl-edge-label">{e.label}</span>
          </li>
        ))}
      </ul>

      {cand.economies.length > 0 && (
        <div className="gv1-cl-produces">
          {cand.economies.map((eco) => (
            <span key={eco} className="gv1-cl-result">
              {eco}
            </span>
          ))}
        </div>
      )}
    </li>
  );
}

// ─── Computed near-miss completions (DEC-516, Phase 4) ────────────────────────────

/** The mechanistic recommendation engine (NM-7). On demand, loads the full-coverage
 * KB feature index + price index and searches the pool for cards that CLOSE the
 * deck's near-misses: Tier-B deficit cover (fleet — precomputed loop deficits) and
 * Tier-C half-edge cover (both modes). Filterable by color / legality / price /
 * owned (NM-5 / OQ-1). Nothing here edits a deck (NG5); it is a report. */
function CompletionPanel({
  inputs,
  onResult,
}: {
  inputs: CompletionInputs;
  onResult: (r: CompletionReport | null) => void;
}) {
  const [currency, setCurrency] = useState<Currency>('eur');
  const [maxPriceStr, setMaxPriceStr] = useState('');
  const [ownedText, setOwnedText] = useState('');
  const [ownedOnly, setOwnedOnly] = useState(false);
  const [showOwned, setShowOwned] = useState(false);
  const [result, setResult] = useState<CompletionReport | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [status, setStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [error, setError] = useState<string>();
  const assets = useRef<{ fi: FeatureIndex; cfg: SynergyConfig; px: PriceIndex | null } | null>(
    null,
  );

  const compute = (a: { fi: FeatureIndex; cfg: SynergyConfig; px: PriceIndex | null }) => {
    const parsedMax = maxPriceStr.trim() ? Number(maxPriceStr) : NaN;
    const maxPrice = Number.isFinite(parsedMax) && parsedMax > 0 ? parsedMax : null;
    const ownedKeys = ownedText.trim() ? parseOwnedCollection(ownedText) : null;
    const ci = inputs.colorIdentity ?? deriveColorIdentity(inputs.names, a.fi);
    const rep = analyzeCompletions(inputs.names, a.fi, a.cfg, {
      filters: {
        deckColorIdentity: ci,
        currency,
        maxPrice,
        ownedOnly: ownedOnly && !!ownedKeys,
        ownedKeys,
      },
      prices: a.px,
      engines: inputs.engines,
    });
    setResult(rep);
    onResult(rep);
  };

  const run = async () => {
    setStatus('loading');
    setError(undefined);
    try {
      if (!assets.current) {
        const [fi, cfg, px] = await Promise.all([
          loadFeatureIndex(),
          loadSynergyConfig(),
          loadPriceIndex(),
        ]);
        if (!fi || !cfg) throw new Error('knowledge base unavailable');
        assets.current = { fi, cfg, px };
      }
      setLoaded(true);
      setStatus('ready');
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setStatus('error');
    }
  };

  // Recompute (no refetch — indices are cached) whenever a filter changes.
  useEffect(() => {
    if (!loaded || !assets.current) return;
    compute(assets.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currency, maxPriceStr, ownedOnly, ownedText, loaded]);

  return (
    <section className="gv1-cl-section" aria-label="Computed near-miss completions">
      <h2 className="gv1-cl-h2 gv1-mono-xs">
        Complete a near-miss{' '}
        {result && (
          <span className="gv1-dim">({result.tierB.length + result.tierC.length})</span>
        )}
      </h2>

      <p className="gv1-cl-framing gv1-cl-framing-b gv1-mono-xs">
        The mechanistic recommendation engine — pool cards that would <strong>close</strong> this
        deck's near-misses, computed over the full-coverage knowledge base (no AI at query time,
        per-hole linear in the pool). A report only: it never edits your deck.
      </p>

      {status === 'idle' && (
        <button type="button" className="gv1-chip gv1-chip-active gv1-cl-analyze" onClick={run}>
          Find completions
        </button>
      )}
      {status === 'loading' && (
        <p className="gv1-mono-xs gv1-dim" aria-busy="true">
          ◇ loading the knowledge base &amp; prices …
        </p>
      )}
      {status === 'error' && (
        <div className="gv1-stub" role="alert">
          <p className="gv1-mono-xs gv1-dim">Could not run completion search: {error}</p>
        </div>
      )}

      {status === 'ready' && result && (
        <>
          {/* Filters (NM-5) */}
          <div className="gv1-cl-filters" role="group" aria-label="Completion filters">
            <span className="gv1-mono-xs gv1-dim">
              Color identity <span className="gv1-rune">{result.deckColorIdentity}</span> · legal in
              Commander
            </span>
            <label className="gv1-cl-filter">
              <span className="gv1-mono-xs gv1-dim">Currency</span>
              <select
                className="gv1-cl-select gv1-cl-select-sm"
                value={currency}
                onChange={(e) => setCurrency(e.target.value as Currency)}
              >
                <option value="eur">EUR (Cardmarket)</option>
                <option value="usd">USD (TCGplayer)</option>
              </select>
            </label>
            <label className="gv1-cl-filter">
              <span className="gv1-mono-xs gv1-dim">Max price</span>
              <input
                className="gv1-cl-input gv1-cl-input-sm"
                type="number"
                min="0"
                step="0.5"
                inputMode="decimal"
                placeholder="any"
                value={maxPriceStr}
                onChange={(e) => setMaxPriceStr(e.target.value)}
              />
            </label>
            <button
              type="button"
              className={['gv1-chip', showOwned ? 'gv1-chip-active' : ''].join(' ')}
              aria-pressed={showOwned}
              onClick={() => setShowOwned((v) => !v)}
            >
              Owned filter (optional)
            </button>
          </div>

          {showOwned && (
            <div className="gv1-cl-owned">
              <label className="gv1-cl-field">
                <span className="gv1-mono-xs gv1-dim">
                  Paste your collection (ManaBox/decklist/CSV) — stays in your browser
                </span>
                <textarea
                  className="gv1-cl-textarea gv1-cl-textarea-sm"
                  rows={4}
                  placeholder={'1 Sol Ring\nBlood Artist\n…'}
                  value={ownedText}
                  onChange={(e) => setOwnedText(e.target.value)}
                />
              </label>
              <label className="gv1-cl-owned-toggle gv1-mono-xs">
                <input
                  type="checkbox"
                  checked={ownedOnly}
                  disabled={!ownedText.trim()}
                  onChange={(e) => setOwnedOnly(e.target.checked)}
                />
                Only show cards I own
              </label>
            </div>
          )}

          <p className="gv1-mono-xs gv1-dim gv1-cl-latency">
            Searched {result.poolSize.toLocaleString()} pool cards in {result.elapsedMs.toFixed(0)}ms
            · {result.counts.droppedByColor.toLocaleString()} off-color
            {result.counts.droppedByPrice > 0 && <> · {result.counts.droppedByPrice} over budget</>}
            {ownedOnly && result.counts.droppedByOwned > 0 && (
              <> · {result.counts.droppedByOwned} unowned</>
            )}{' '}
            filtered out.
          </p>

          {/* Tier B — computed deficit completions */}
          <div className="gv1-cl-synergy-group">
            <h3 className="gv1-cl-h3 gv1-mono-xs">
              <span className="gv1-cl-tier gv1-cl-tier-b">Tier B</span> Computed completions{' '}
              <span className="gv1-dim">
                ({result.tierB.length}
                {result.counts.tierBTotal > result.tierB.length
                  ? ` of ${result.counts.tierBTotal}`
                  : ''}
                )
              </span>
            </h3>
            {!result.tierBAvailable ? (
              <p className="gv1-cl-empty gv1-mono-xs gv1-dim">
                Computed completions run on this deck's verified loop deficits — the Tier-B verifier
                index is currently unavailable.
              </p>
            ) : result.tierB.length === 0 ? (
              <p className="gv1-cl-empty gv1-mono-xs gv1-dim">
                No computed loop deficits to complete under the current filters.
              </p>
            ) : (
              <ul className="gv1-cl-list">
                {result.tierB.map((b, i) => (
                  <li key={`tb-${i}-${b.card.name}`} className="gv1-cl-finding">
                    <div className="gv1-cl-finding-head">
                      <span className="gv1-cl-tier gv1-cl-tier-b">Tier B</span>
                      <PriceChip card={b.card} currency={currency} />
                    </div>
                    <div className="gv1-cl-finding-cards">
                      <span className="gv1-cl-cardname" data-card-name={b.card.name}>
                        {b.card.name}
                      </span>
                    </div>
                    <p className="gv1-cl-needs gv1-mono-xs">
                      <span className="gv1-cl-needs-label">Closes</span> the {b.resource} leak on{' '}
                      {b.loopCards.join(' + ')} via {b.closerLabel}.
                    </p>
                  </li>
                ))}
              </ul>
            )}
            {result.tierBAvailable && result.tierB.length > 0 && (
              <p className="gv1-mono-xs gv1-dim">
                “Verified under the model”, not a comprehensive-rules proof — confirm the interaction.
              </p>
            )}
          </div>

          {/* Tier C — speculative half-edge completions */}
          <div className="gv1-cl-synergy-group">
            <h3 className="gv1-cl-h3 gv1-mono-xs">
              <span className="gv1-cl-tier gv1-cl-tier-c">Tier C</span> Speculative completions{' '}
              <span className="gv1-dim">
                ({result.tierC.length}
                {result.counts.tierCTotal > result.tierC.length
                  ? ` of ${result.counts.tierCTotal}`
                  : ''}
                )
              </span>
            </h3>
            {result.tierC.length === 0 ? (
              <p className="gv1-cl-empty gv1-mono-xs gv1-dim">
                No half-edge completions under the current filters.
              </p>
            ) : (
              <ul className="gv1-cl-list">
                {result.tierC.map((t, i) => (
                  <li key={`tc-${i}-${t.card.name}`} className="gv1-cl-finding">
                    <div className="gv1-cl-finding-head">
                      <span className="gv1-cl-tier gv1-cl-tier-c">Tier C</span>
                      <span
                        className={[
                          'gv1-cl-band',
                          t.band === 'strong' ? 'gv1-cl-band-strong' : 'gv1-cl-band-spec',
                        ].join(' ')}
                      >
                        {t.band}
                      </span>
                      <PriceChip card={t.card} currency={currency} />
                    </div>
                    <div className="gv1-cl-finding-cards">
                      <span className="gv1-cl-cardname" data-card-name={t.card.name}>
                        {t.card.name}
                      </span>
                    </div>
                    <ul className="gv1-cl-edges">
                      {t.couplings.map((e, j) => (
                        <li key={`${e.deckFeature}-${e.completerFeature}-${j}`} className="gv1-cl-edge">
                          <span className="gv1-cl-edge-label">{e.label}</span>
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </section>
  );
}

function PriceChip({
  card,
  currency,
}: {
  card: { price: number | null; owned: boolean | null };
  currency: Currency;
}) {
  const sym = currency === 'eur' ? '€' : '$';
  return (
    <span className="gv1-mono-xs gv1-dim gv1-cl-price">
      {card.price != null ? `${sym}${card.price.toFixed(2)}` : 'no price'}
      {card.owned === true && <span className="gv1-cl-owned-tag"> · owned</span>}
    </span>
  );
}
