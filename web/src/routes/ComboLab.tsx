// Combo Lab — DEC-534 redesign (render layer only; pipeline unchanged).
//
// Lab-bench surface: sticky control rail (mode · deck · contents · tier legend ·
// export) beside a report column that opens with the bracket/Rule-0 Disclosure,
// then § XII·a Combos Present (Tier A) → § XII·b Verified Loops (Tier B) →
// § XII·c near-miss ledger → § XII·d Synergy Candidates (Tier C) → § XII·e
// Complete a Near-Miss → attribution.
//
// Two modes: Fleet (precomputed spellbook-combos.json per deck) and Paste (the
// full client-side pipeline: matcher index, Tier-B verifier, Tier-C synergy
// engine, completions). Everything data-side is the existing DEC-476 pipeline —
// this file is presentation only.

import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { deckLoader } from '../data/loader';
import { colorsToGlyphs } from '../data/normalize';
import { GV1ManaPips } from '../components/atoms/GV1ManaPips';
import { useCard } from '../hooks/useCard';
import { loadMatcherIndex } from '../data/spellbook';
import type { SpellbookCombo, SpellbookComboTemplate } from '../data/spellbook';
import { loadFeatureIndex, loadSynergyConfig } from '../data/synergy';
import type { FeatureIndex, SynergyCandidate, SynergyConfig } from '../data/synergy';
import type { RawDeckIndex, RawDeckBundle, RawDeckIndexEntry } from '../data/types';
import { analyze as analyzeSynergy, nameKeys } from '../lib/synergyMatch';
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
  type CompletionReport,
  type TierBCompletion,
  type TierCCompletion,
} from '../lib/nearMissComplete';
import { resolveDeckUrl, DeckUrlError } from '../lib/deckUrl';
import { loadTierBIndex } from '../data/tierBIndex';
import { verifyDeck } from '../lib/comboVerify';

// Collapse thresholds (design spec).
const NEAR_COLLAPSE = 8;
const SYN_COLLAPSE = 6;
const COMPLETION_MAX = 10;

// Same store § IX Shopping writes (SHOP_OWNED_KEY there) — ownership flags here
// read it, never write it.
const SHOP_OWNED_KEY = 'grimoire-owned-cards';

const EXAMPLE_LIST = [
  '1 Gravecrawler',
  '1 Phyrexian Altar',
  '1 Blood Artist',
  '1 Warren Soultrader',
  '1 Basalt Monolith',
  '1 Forsaken Monument',
  '1 Rings of Brighthearth',
  "1 Ashnod's Altar",
  '1 Nim Deathmantle',
  '1 Sol Ring',
  '1 Command Tower',
].join('\n');
const EXAMPLE_COMMANDER = 'Meren of Clan Nel Toth';

// ─── Rail combo counts (per-deck, module-cached) ──────────────────────────────
// The rail shows each deck's curated combo count. Only spellbook-combos.json is
// fetched (plain fetch, no localStorage envelope — same bypass rationale as the
// matcher index); null = the deck definitively has no combo data ("unscribed",
// 404). Transient failures are NOT cached — the entry stays absent so the next
// mount refetches instead of branding the deck unscribed for the session.

const railCountsCache = new Map<string, number | null>();

async function fetchRailCounts(ids: string[]): Promise<Map<string, number | null>> {
  await Promise.all(
    ids
      .filter((id) => !railCountsCache.has(id))
      .map(async (id) => {
        try {
          const r = await fetch(`/data/commanders/${id}/spellbook-combos.json`);
          if (r.status === 404) {
            railCountsCache.set(id, null);
            return;
          }
          if (!r.ok) return; // transient — leave absent, retry next mount
          const j = (await r.json()) as { counts?: { included?: number } };
          railCountsCache.set(
            id,
            typeof j?.counts?.included === 'number' ? j.counts.included : null,
          );
        } catch {
          // network/parse failure — leave absent so a later mount retries
        }
      }),
  );
  return new Map(railCountsCache);
}

// ─── Owned collection (read-only view of the Shopping store) ─────────────────

function loadOwnedCollection(): { keys: Set<string>; count: number } {
  try {
    const raw = localStorage.getItem(SHOP_OWNED_KEY);
    if (raw) {
      const entries = JSON.parse(raw) as Array<[string, number]>;
      const keys = new Set<string>();
      for (const [n] of entries) for (const k of nameKeys(String(n))) keys.add(k);
      return { keys, count: entries.length };
    }
  } catch {
    // ignore — treated as "no collection on file"
  }
  return { keys: new Set(), count: 0 };
}

// ─── Root ─────────────────────────────────────────────────────────────────────

export function ComboLab() {
  const [params, setParams] = useSearchParams();
  const mode: 'fleet' | 'paste' = params.get('mode') === 'paste' ? 'paste' : 'fleet';

  const setMode = (m: 'fleet' | 'paste') => {
    const next = new URLSearchParams(params);
    next.set('mode', m);
    setParams(next, { replace: true });
  };

  // Deck index + per-deck combo counts for the rail.
  const [index, setIndex] = useState<RawDeckIndex | null>(null);
  const [indexError, setIndexError] = useState<string>();
  const [deckCounts, setDeckCounts] = useState<Map<string, number | null> | null>(null);

  const selectedId = params.get('deck') ?? index?.commanders[0]?.id ?? '';
  const selectDeck = (id: string) => {
    const next = new URLSearchParams(params);
    next.set('deck', id);
    setParams(next, { replace: true });
  };

  useEffect(() => {
    let cancelled = false;
    deckLoader
      .loadIndex()
      .then((idx) => {
        if (cancelled) return;
        setIndex(idx);
        fetchRailCounts(idx.commanders.map((c) => c.id)).then((m) => {
          if (!cancelled) setDeckCounts(m);
        });
      })
      .catch((e) => {
        if (!cancelled) setIndexError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Fleet bundle for the selected deck.
  const [bundle, setBundle] = useState<RawDeckBundle | null>(null);
  const [fleetStatus, setFleetStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [fleetError, setFleetError] = useState<string>();

  useEffect(() => {
    if (!selectedId) return;
    let cancelled = false;
    setFleetStatus('loading');
    deckLoader
      .loadDeck(selectedId)
      .then((b) => {
        if (cancelled) return;
        setBundle(b);
        setFleetStatus('ready');
      })
      .catch((e) => {
        if (cancelled) return;
        setFleetError(e instanceof Error ? e.message : String(e));
        setFleetStatus('error');
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  const fleetReport = useMemo<ComboReport | null>(() => {
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

  // Completion inputs (Phase 4): deck names + engine deficits + color identity.
  const fleetCompletionInputs = useMemo(() => {
    if (!bundle) return null;
    const names = [
      ...(bundle.deck.decklist ?? []).map((c) => c.name),
      ...(bundle.spellbookCombos?.commander ?? []),
    ];
    const colors = index?.commanders.find((c) => c.id === selectedId)?.colors ?? [];
    const ci = colors.filter((c) => c !== 'C').join('') || 'C';
    return { names, engines: bundle.tierBLoops?.engines ?? [], colorIdentity: ci };
  }, [bundle, index, selectedId]);

  // ── Paste-mode state (full pipeline, hoisted so the single rail drives it) ──
  const [text, setText] = useState('');
  const [commander, setCommander] = useState('');
  const [deckUrl, setDeckUrl] = useState('');
  const [urlBusy, setUrlBusy] = useState(false);
  const [urlMsg, setUrlMsg] = useState<string>();
  const [pasteReport, setPasteReport] = useState<ComboReport | null>(null);
  const [pasteNames, setPasteNames] = useState<string[]>([]);
  // Computed Tier-B engine deficits from the last Analyze; feed the near-miss
  // completion engine. null ⇒ verifier index unavailable (completion falls back).
  const [pasteEngines, setPasteEngines] = useState<TierBFinding[] | null>(null);
  const [pastePhase, setPastePhase] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [pasteError, setPasteError] = useState<string>();
  const [timingMs, setTimingMs] = useState<number | null>(null);
  const [corpusSize, setCorpusSize] = useState<number | null>(null);
  const [deepScanning, setDeepScanning] = useState(false);
  // Inputs cached from the last Analyze so the deep scan can re-run the engine
  // without re-parsing or refetching the 3.3 MB feature index.
  const synergyInput = useRef<{ names: string[]; fi: FeatureIndex; cfg: SynergyConfig } | null>(
    null,
  );

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

  const analyze = async (textArg?: string, commanderArg?: string) => {
    const listText = textArg ?? text;
    const cmdrText = commanderArg ?? commander;
    setPastePhase('loading');
    setPasteError(undefined);
    synergyInput.current = null;
    try {
      const t0 = performance.now();
      const matcher = await loadMatcherIndex();
      if (!matcher) throw new Error('matcher index unavailable');
      const parsed = parseDecklist(listText);
      if (cmdrText.trim()) {
        for (const line of parseDecklist(cmdrText).cardNames) parsed.commanderNames.push(line);
      }
      const result = matchDecklist(parsed, matcher);

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
        // paste mode gets Tier-B completions too.
        setPasteEngines(vres.engines);
      } else {
        setPasteEngines(null);
      }

      setPasteNames([...parsed.cardNames, ...parsed.commanderNames]);
      const elapsed = performance.now() - t0;
      setTimingMs(elapsed);
      setCorpusSize(matcher.meta.variantCount);
      // NF-3 mobile budget: log if the cold parse+match blows the 1.5 s target.
      if (elapsed > 1500) {
        console.warn(`[Combo Lab] parse+match took ${elapsed.toFixed(0)}ms (> 1500ms NF-3 gate)`);
      }
      const resolved = parsed.cardNames.length + parsed.commanderNames.length;
      setPasteReport({
        mode: 'paste',
        deckLabel: 'Pasted decklist',
        commander: parsed.commanderNames,
        corpusVersion: matcher.meta.corpusVersion,
        included: result.included,
        nearMisses: result.nearMisses,
        nearMissesTotal: result.nearMissesTotal,
        cardsAnalyzed: resolved,
        cardsTotal: resolved + parsed.unresolved.length,
        unresolved: parsed.unresolved,
        synergy,
        tierB,
      });
      setPastePhase('ready');
    } catch (e) {
      setPasteError(e instanceof Error ? e.message : String(e));
      setPastePhase('error');
    }
  };

  const loadExample = () => {
    setText(EXAMPLE_LIST);
    setCommander(EXAMPLE_COMMANDER);
    void analyze(EXAMPLE_LIST, EXAMPLE_COMMANDER);
  };

  // OQ-3 — deep scan: re-run the engine with deep:true to enumerate triples &
  // 4-cycles, then fold them into the existing report.
  const runDeepScan = async () => {
    const inp = synergyInput.current;
    if (!inp || deepScanning) return;
    setDeepScanning(true);
    // Yield a frame so the busy label paints before the synchronous enumeration.
    await new Promise((r) => setTimeout(r, 0));
    try {
      const syn = analyzeSynergy(inp.names, inp.fi, inp.cfg, { deep: true });
      setPasteReport((prev) =>
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

  // ── Shared report + export state ────────────────────────────────────────────
  const report = mode === 'fleet' ? (fleetStatus === 'ready' ? fleetReport : null) : pasteReport;
  // Memoized (stable identity per analyze) so the § XII·e recompute effect can
  // depend on it without looping.
  const pasteCompletionInputs = useMemo<CompletionInputs | null>(
    () => (pasteNames.length > 0 ? { names: pasteNames, engines: pasteEngines } : null),
    [pasteNames, pasteEngines],
  );
  const completionInputs: CompletionInputs | null =
    mode === 'fleet' ? fleetCompletionInputs : pasteCompletionInputs;

  const [completions, setCompletions] = useState<CompletionReport | null>(null);
  // Drop stale completions when the underlying report changes (deck switch or a
  // fresh paste analysis) so exports never carry another deck's suggestions.
  useEffect(() => setCompletions(null), [report]);

  const owned = useMemo(loadOwnedCollection, []);

  const [copied, setCopied] = useState<string | null>(null);
  // Track the 1.6s feedback timer so rapid sequential copies restart it instead
  // of the first timer cutting the second "Copied ◆" short; cleared on unmount.
  const copyTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(
    () => () => {
      if (copyTimer.current) clearTimeout(copyTimer.current);
    },
    [],
  );
  const doExport = async (kind: 'txt' | 'md' | 'dl-txt' | 'dl-md') => {
    if (!report) return;
    const md = kind.endsWith('md');
    const txt = md
      ? buildMarkdownExport(report, completions)
      : buildPlainTextExport(report, completions);
    if (kind.startsWith('dl')) {
      const blob = new Blob([txt], { type: md ? 'text/markdown' : 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `combo-report-${report.deckLabel.replace(/\s+/g, '-').toLowerCase()}.${md ? 'md' : 'txt'}`;
      a.click();
      URL.revokeObjectURL(url);
      return;
    }
    try {
      await navigator.clipboard.writeText(txt);
      if (copyTimer.current) clearTimeout(copyTimer.current);
      setCopied(kind);
      copyTimer.current = setTimeout(() => setCopied(null), 1600);
    } catch {
      setCopied(null);
    }
  };

  const tierBCount = report?.tierB
    ? report.tierB.corroborated.length + report.tierB.novel.length + report.tierB.engines.length
    : 0;

  const toc: TocRow[] = [
    { key: 'disc', folio: '◈', label: 'The Disclosure', n: '' },
    { key: 'a', folio: 'XII·a', label: 'Combos Present', n: report ? report.included.length : '—' },
    { key: 'b', folio: 'XII·b', label: 'Verified Loops', n: report?.tierB ? tierBCount : '—' },
    {
      key: 'c',
      folio: 'XII·c',
      label: 'One–Two Cards Away',
      n: report ? report.nearMisses.length : '—',
    },
    {
      key: 'd',
      folio: 'XII·d',
      label: 'Synergy Candidates',
      n: report?.synergy ? report.synergy.counts.pairs : '—',
    },
    {
      key: 'e',
      folio: 'XII·e',
      label: 'Complete a Near-Miss',
      n: completions ? completions.tierB.length + completions.tierC.length : '—',
    },
  ];

  // Smooth-scroll the page scroll container to the section (the rail is sticky,
  // so window scrolling is the page scroll — scrollIntoView drives it).
  const onToc = (key: string) => {
    document
      .getElementById(`gv1-lab-sec-${key}`)
      ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const deckEntry = index?.commanders.find((c) => c.id === selectedId) ?? null;

  return (
    <div data-gv1-screen="combolab">
      <header className="gv1-lab-hero">
        <div>
          <div className="gv1-lab-hero-eyebrow">
            <span className="gv1-rune" aria-hidden="true">
              § XII
            </span>
            <span className="gv1-mono-xs gv1-dim">
              · curated combo detection · commander spellbook · three tiers of certainty
            </span>
          </div>
          <h1 className="gv1-lab-title">
            The <em>Combo Lab</em>
          </h1>
        </div>
        <p className="gv1-lab-lede">
          Every chain the corpus knows about — what’s <strong>present</strong>, what’s{' '}
          <strong>one card away</strong>, and what would close it. Curated findings are cited;
          computed findings say which model verified them; heuristics never wear a verified badge.
        </p>
      </header>

      <div className="gv1-lab-layout">
        <Rail
          mode={mode}
          setMode={setMode}
          decks={index?.commanders ?? []}
          deckCounts={deckCounts}
          selectedId={selectedId}
          onSelectDeck={selectDeck}
          toc={toc}
          onToc={onToc}
          corpusVersion={report?.corpusVersion ?? null}
          canExport={!!report}
          copied={copied}
          onExport={doExport}
          paste={{
            text,
            setText,
            commander,
            setCommander,
            deckUrl,
            setDeckUrl,
            urlBusy,
            urlMsg,
            resolveUrl,
            analyze: () => void analyze(),
            loadExample,
            phase: pastePhase,
            error: pasteError,
            timingMs,
            corpusSize,
          }}
        />

        {report ? (
          <ReportColumn
            report={report}
            deckEntry={mode === 'fleet' ? deckEntry : null}
            tierBCount={tierBCount}
            onDeepScan={mode === 'paste' ? runDeepScan : undefined}
            deepScanning={deepScanning}
            completionInputs={completionInputs}
            owned={owned}
            onCompletions={setCompletions}
          />
        ) : (
          <div className="gv1-lab-report">
            {mode === 'fleet' ? (
              indexError || fleetStatus === 'error' ? (
                <div className="gv1-empty gv1-lab-unscribed" role="alert">
                  <span className="gv1-empty-title">Could not load combos</span>
                  <span>{indexError ?? fleetError}</span>
                </div>
              ) : fleetStatus === 'loading' || !index ? (
                <div className="gv1-empty gv1-lab-unscribed" aria-busy="true">
                  <span>◇ consulting the curated corpus …</span>
                </div>
              ) : (
                <div className="gv1-empty gv1-lab-unscribed">
                  <span className="gv1-empty-title">Nothing scribed for this tome yet</span>
                  <span>
                    No <code>spellbook-combos.json</code> has been committed for{' '}
                    {deckEntry ? deckEntry.name : 'this deck'}.
                  </span>
                  <span className="gv1-empty-hint">re-run scripts/sync_spellbook_combos.py</span>
                </div>
              )
            ) : pastePhase === 'loading' ? (
              <div className="gv1-empty gv1-lab-unscribed" aria-busy="true">
                <span>◇ consulting the corpus …</span>
              </div>
            ) : (
              <div className="gv1-empty gv1-lab-unscribed">
                <span className="gv1-empty-title">Paste a decklist to consult the corpus</span>
                <span>
                  One card per line, quantities welcome. The match runs entirely in your browser.
                </span>
                <span className="gv1-empty-hint">or press “load example” for a classic combo pile</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Control rail ─────────────────────────────────────────────────────────────

interface TocRow {
  key: string;
  folio: string;
  label: string;
  n: number | string;
}

interface PasteBag {
  text: string;
  setText: (v: string) => void;
  commander: string;
  setCommander: (v: string) => void;
  deckUrl: string;
  setDeckUrl: (v: string) => void;
  urlBusy: boolean;
  urlMsg?: string;
  resolveUrl: () => void;
  analyze: () => void;
  loadExample: () => void;
  phase: 'idle' | 'loading' | 'ready' | 'error';
  error?: string;
  timingMs: number | null;
  corpusSize: number | null;
}

function Rail({
  mode,
  setMode,
  decks,
  deckCounts,
  selectedId,
  onSelectDeck,
  toc,
  onToc,
  corpusVersion,
  canExport,
  copied,
  onExport,
  paste,
}: {
  mode: 'fleet' | 'paste';
  setMode: (m: 'fleet' | 'paste') => void;
  decks: RawDeckIndexEntry[];
  deckCounts: Map<string, number | null> | null;
  selectedId: string;
  onSelectDeck: (id: string) => void;
  toc: TocRow[];
  onToc: (key: string) => void;
  corpusVersion: string | null;
  canExport: boolean;
  copied: string | null;
  onExport: (kind: 'txt' | 'md' | 'dl-txt' | 'dl-md') => void;
  paste: PasteBag;
}) {
  return (
    <aside className="gv1-lab-rail" aria-label="Combo Lab controls">
      <div className="gv1-lab-block gv1-lab-modes" role="group" aria-label="Analysis mode">
        <button
          type="button"
          className="gv1-lab-mode"
          aria-pressed={mode === 'fleet'}
          onClick={() => setMode('fleet')}
        >
          <span className="gv1-mono-xs gv1-dim gv1-lab-mode-tag">◈ mode i</span>
          <span className="gv1-lab-mode-name">Fleet deck</span>
        </button>
        <button
          type="button"
          className="gv1-lab-mode"
          aria-pressed={mode === 'paste'}
          onClick={() => setMode('paste')}
        >
          <span className="gv1-mono-xs gv1-dim gv1-lab-mode-tag">◈ mode ii</span>
          <span className="gv1-lab-mode-name">Paste decklist</span>
        </button>
      </div>

      {mode === 'fleet' ? (
        <div className="gv1-lab-block">
          <div className="gv1-lab-block-head">
            <span className="gv1-mono-xs gv1-dim">Select a tome</span>
            <span className="gv1-mono-xs gv1-dim">combos</span>
          </div>
          <div className="gv1-lab-decks" role="listbox" aria-label="Fleet decks">
            {decks.map((d, i) => {
              const count = deckCounts?.get(d.id);
              // Unscribed = a cached, definitive "no combo data" (404). An absent
              // entry (still loading / transient fetch failure) shows a plain dash.
              const unscribed = deckCounts != null && deckCounts.has(d.id) && count === null;
              return (
                <button
                  key={d.id}
                  type="button"
                  role="option"
                  data-deck-id={d.id}
                  aria-selected={d.id === selectedId}
                  className={[
                    'gv1-lab-deck',
                    d.id === selectedId ? 'gv1-active' : '',
                    unscribed ? 'gv1-lab-deck-unscribed' : '',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                  onClick={() => onSelectDeck(d.id)}
                  title={
                    unscribed
                      ? `${d.name} — combos not scribed yet`
                      : `${d.name} — ${d.commander ?? ''}`
                  }
                >
                  <span className="gv1-lab-deck-idx">№{String(i + 1).padStart(2, '0')}</span>
                  <span className="gv1-lab-deck-name">{d.name}</span>
                  <span className="gv1-lab-deck-meta">
                    <span className="gv1-lab-deck-n">{count ?? '—'}</span>
                    <GV1ManaPips colors={colorsToGlyphs(d.colors)} />
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="gv1-lab-block">
          <div className="gv1-lab-block-head">
            <span className="gv1-mono-xs gv1-dim">Any decklist · stays in your browser</span>
          </div>
          <div className="gv1-lab-form">
            {/* IN-2 deck-URL resolver — production keeps it (prototype omitted it). */}
            <label className="gv1-lab-field">
              <span className="gv1-mono-xs gv1-dim">Deck URL — Moxfield or Archidekt (optional)</span>
              <div className="gv1-lab-url-row">
                <input
                  className="gv1-lab-input"
                  value={paste.deckUrl}
                  placeholder="https://moxfield.com/decks/… or https://archidekt.com/decks/…"
                  onChange={(e) => paste.setDeckUrl(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      paste.resolveUrl();
                    }
                  }}
                />
                <button
                  type="button"
                  className="gv1-lab-more"
                  disabled={paste.urlBusy || !paste.deckUrl.trim()}
                  onClick={paste.resolveUrl}
                >
                  {paste.urlBusy ? 'Loading …' : 'Load'}
                </button>
              </div>
              {paste.urlMsg && (
                <span className="gv1-lab-note gv1-lab-url-msg">{paste.urlMsg}</span>
              )}
            </label>
            <label className="gv1-lab-field">
              <span className="gv1-mono-xs gv1-dim">Commander(s) — optional</span>
              <input
                className="gv1-lab-input"
                value={paste.commander}
                placeholder="e.g. Meren of Clan Nel Toth"
                onChange={(e) => paste.setCommander(e.target.value)}
              />
            </label>
            <label className="gv1-lab-field">
              <span className="gv1-mono-xs gv1-dim">Decklist — one card per line, quantities ok</span>
              <textarea
                className="gv1-lab-textarea"
                rows={11}
                value={paste.text}
                placeholder={'1 Gravecrawler\n1 Phyrexian Altar\n1 Blood Artist\n…'}
                onChange={(e) => paste.setText(e.target.value)}
              />
            </label>
            <div className="gv1-lab-form-foot">
              <button
                type="button"
                className="gv1-lab-analyze"
                disabled={paste.phase === 'loading' || !paste.text.trim()}
                aria-busy={paste.phase === 'loading'}
                onClick={paste.analyze}
              >
                Analyze ⟶
              </button>
              <button type="button" className="gv1-lab-more" onClick={paste.loadExample}>
                Load example
              </button>
            </div>
            {paste.phase === 'error' && (
              <p className="gv1-lab-warn" role="alert">
                Could not analyze: {paste.error}
              </p>
            )}
            {paste.timingMs != null && (
              <span className="gv1-lab-note">
                parse+match {paste.timingMs.toFixed(0)}ms
                {paste.corpusSize != null && (
                  <> · {paste.corpusSize.toLocaleString()} combo variants in the corpus</>
                )}
              </span>
            )}
          </div>
        </div>
      )}

      <div className="gv1-lab-block">
        <div className="gv1-lab-block-head">
          <span className="gv1-mono-xs gv1-dim">Contents</span>
          <span className="gv1-mono-xs gv1-dim">§ XII</span>
        </div>
        <nav className="gv1-lab-toc" aria-label="Report contents">
          {toc.map((t) => (
            <button key={t.key} type="button" className="gv1-lab-toc-row" onClick={() => onToc(t.key)}>
              <span className="gv1-lab-toc-folio">{t.folio}</span>
              <span className="gv1-lab-toc-label">{t.label}</span>
              <span className="gv1-lab-toc-n">{t.n}</span>
            </button>
          ))}
        </nav>
      </div>

      <div className="gv1-lab-block">
        <div className="gv1-lab-block-head">
          <span className="gv1-mono-xs gv1-dim">The three tiers</span>
        </div>
        <dl className="gv1-lab-kv">
          <dt>
            <TierChip t="a" label="A" />
          </dt>
          <dd>curated · human-verified (Spellbook)</dd>
          <dt>
            <TierChip t="b" label="B" />
          </dt>
          <dd>computed · verified under the model</dd>
          <dt>
            <TierChip t="c" label="C" />
          </dt>
          <dd>heuristic · speculative couplings</dd>
        </dl>
      </div>

      <div className="gv1-lab-block">
        <div className="gv1-lab-block-head">
          <span className="gv1-mono-xs gv1-dim">Scribe the findings</span>
          <span className="gv1-mono-xs gv1-dim">
            {corpusVersion ? corpusVersion.slice(0, 10) : '—'}
          </span>
        </div>
        <div className="gv1-lab-export">
          <button
            type="button"
            className="gv1-lab-export-btn"
            disabled={!canExport}
            onClick={() => onExport('txt')}
          >
            {copied === 'txt' ? 'Copied ◆' : 'Copy text'}
          </button>
          <button
            type="button"
            className="gv1-lab-export-btn"
            disabled={!canExport}
            onClick={() => onExport('md')}
          >
            {copied === 'md' ? 'Copied ◆' : 'Copy markdown'}
          </button>
          <button
            type="button"
            className="gv1-lab-export-btn"
            disabled={!canExport}
            onClick={() => onExport('dl-txt')}
          >
            ⇣ .txt
          </button>
          <button
            type="button"
            className="gv1-lab-export-btn"
            disabled={!canExport}
            onClick={() => onExport('dl-md')}
          >
            ⇣ .md
          </button>
        </div>
      </div>

      <p className="gv1-lab-smallprint">
        Combo data © Commander Spellbook (CC-BY-SA) · card data © Scryfall · not affiliated with or
        endorsed by Wizards of the Coast. Ownership flags read the collection imported in § IX
        Shopping — nothing leaves the page.
      </p>
    </aside>
  );
}

// ─── Report column ────────────────────────────────────────────────────────────

interface CompletionInputs {
  names: string[];
  engines: TierBFinding[] | null;
  colorIdentity?: string;
}

interface OwnedCollection {
  keys: Set<string>;
  count: number;
}

function ReportColumn({
  report,
  deckEntry,
  tierBCount,
  onDeepScan,
  deepScanning,
  completionInputs,
  owned,
  onCompletions,
}: {
  report: ComboReport;
  deckEntry: RawDeckIndexEntry | null;
  tierBCount: number;
  onDeepScan?: () => void;
  deepScanning?: boolean;
  completionInputs: CompletionInputs | null;
  owned: OwnedCollection;
  onCompletions: (r: CompletionReport | null) => void;
}) {
  const disc = useMemo(() => buildBracketDisclosure(report.included), [report.included]);
  const [showAllNear, setShowAllNear] = useState(false);

  const nearShown = showAllNear ? report.nearMisses : report.nearMisses.slice(0, NEAR_COLLAPSE);
  const twoCard = disc.twoCardInfinites;

  return (
    <div className="gv1-lab-report">
      {/* ── The Disclosure (BR-1..BR-4) — first, not buried ── */}
      <section
        className="gv1-lab-summary"
        id="gv1-lab-sec-disc"
        aria-label="Bracket and Rule-0 disclosure"
      >
        <div className="gv1-lab-summary-head">
          <h2 className="gv1-lab-summary-deck">{report.deckLabel}</h2>
          {deckEntry && <GV1ManaPips colors={colorsToGlyphs(deckEntry.colors)} />}
          <span className="gv1-lab-note">
            {report.commander.join(' · ') || 'no commander declared'}
          </span>
          <span className="gv1-lab-summary-spacer" />
          <span className="gv1-mono-xs gv1-dim">bracket / rule-0 disclosure</span>
        </div>
        <div className="gv1-lab-stats">
          <div className="gv1-lab-stat">
            <span className="gv1-lab-stat-n">{disc.totalCombos}</span>
            <span className="gv1-lab-stat-sub">curated combos</span>
          </div>
          <div className={'gv1-lab-stat' + (twoCard > 0 ? ' gv1-lab-stat-hot' : '')}>
            <span className="gv1-lab-stat-n">{twoCard}</span>
            <span className="gv1-lab-stat-sub">two-card infinites</span>
          </div>
          <div className="gv1-lab-stat">
            <span className="gv1-lab-stat-n">{disc.winCombos}</span>
            <span className="gv1-lab-stat-sub">win the game</span>
          </div>
          {report.mode === 'fleet' ? (
            <div className="gv1-lab-stat">
              <span className="gv1-lab-stat-n">{tierBCount}</span>
              <span className="gv1-lab-stat-sub">verified loops</span>
            </div>
          ) : (
            <div className="gv1-lab-stat">
              <span className="gv1-lab-stat-n">{report.cardsAnalyzed}</span>
              <span className="gv1-lab-stat-sub">cards analyzed</span>
            </div>
          )}
          <div className="gv1-lab-stat">
            <span className="gv1-lab-stat-n">{report.nearMissesTotal.toLocaleString()}</span>
            <span className="gv1-lab-stat-sub">near-misses in corpus</span>
          </div>
        </div>
        <div className="gv1-lab-summary-foot">
          <span className="gv1-lab-note">
            A <span className="gv1-rune">goldfish</span> is assumed — no opposing interaction.
            Absence is not proof: only corpus combos are detected.
          </span>
          <span className="gv1-lab-summary-spacer" />
          {disc.byBracketTag.length > 0 && (
            <span className="gv1-lab-note">
              spellbook tags: {disc.byBracketTag.map((b) => `${b.label} ×${b.count}`).join(' · ')}
            </span>
          )}
          <span className="gv1-lab-note" title={report.corpusVersion}>
            corpus {report.corpusVersion.slice(0, 10)}
          </span>
        </div>
      </section>

      {/* IN-6 / RT-5 — completeness warning: unresolvable lines, remainder analyzed. */}
      {report.unresolved.length > 0 && (
        <p className="gv1-lab-warn" role="status">
          Analyzed {report.cardsAnalyzed} of {report.cardsTotal} lines.{' '}
          {report.unresolved.length} line{report.unresolved.length > 1 ? 's' : ''} could not be read
          and {report.unresolved.length > 1 ? 'were' : 'was'} skipped:{' '}
          <span className="gv1-dim">{report.unresolved.join(' · ')}</span>
        </p>
      )}

      {/* ── § XII·a — Tier A combos present ── */}
      <section className="gv1-lab-sec" aria-label="Combos present">
        <SecHead
          folio="a"
          title="Combos Present"
          note={`${report.included.length} chains scribed`}
        />
        <Framing tier="a">
          Every finding below is <strong>human-verified</strong> by Commander Spellbook and cited
          back to it. Not exhaustive — only combos in the curated corpus are detected.
        </Framing>
        {report.included.length === 0 ? (
          <div className="gv1-empty">
            <span className="gv1-empty-title">No curated combos found</span>
            <span>at any tier, within corpus coverage — the corpus is not exhaustive.</span>
          </div>
        ) : (
          <div className="gv1-lab-grid2">
            {report.included.map((c) => (
              <ComboCard key={c.id} combo={c} />
            ))}
          </div>
        )}
      </section>

      {/* ── § XII·b — Tier B verified loops (DEC-501) ── */}
      <TierBSec tierB={report.tierB} tierBCount={tierBCount} />

      {/* ── § XII·c — near-miss ledger ── */}
      <section className="gv1-lab-sec" aria-label="Near-misses">
        <SecHead
          folio="c"
          title="One–Two Cards Away"
          note={
            report.mode === 'fleet'
              ? `top ${report.nearMisses.length} stored · ${report.nearMissesTotal.toLocaleString()} qualifying`
              : `${report.nearMisses.length} shown of ${report.nearMissesTotal.toLocaleString()}`
          }
        />
        <p className="gv1-lab-note">
          Still Tier A — curated combos the list is short a piece for. The{' '}
          <span style={{ color: 'var(--gv1-gold-300)' }}>gold name</span> is the piece that’s
          missing.
        </p>
        {report.nearMisses.length === 0 ? (
          <div className="gv1-empty">
            <span>No qualifying near-misses.</span>
          </div>
        ) : (
          <>
            <div className="gv1-lab-near">
              {nearShown.map((c) => (
                <NearRow key={c.id} combo={c} />
              ))}
            </div>
            {report.nearMisses.length > NEAR_COLLAPSE && (
              <button
                type="button"
                className="gv1-lab-more"
                onClick={() => setShowAllNear((v) => !v)}
              >
                {showAllNear ? 'Show fewer' : `Show all ${report.nearMisses.length}`}
              </button>
            )}
          </>
        )}
      </section>

      {/* ── § XII·d — Tier C synergy candidates (DEC-491) ── */}
      <SynergySec
        synergy={report.synergy}
        onDeepScan={onDeepScan}
        deepScanning={deepScanning}
      />

      {/* ── § XII·e — complete a near-miss (DEC-516, Phase 4) ── */}
      {completionInputs && completionInputs.names.length > 0 ? (
        // Full (untruncated) key: any change to the analyzed list remounts the
        // section (resetting filters); the recompute effect inside also depends
        // on `inputs`, so engines-only changes recompute too.
        <CompletionSec
          key={completionInputs.names.join('|')}
          inputs={completionInputs}
          owned={owned}
          onResult={onCompletions}
        />
      ) : (
        <section className="gv1-lab-sec" aria-label="Complete a near-miss">
          {/* id lives on the SecHead div only — the TOC scroll target. */}
          <SecHead folio="e" title="Complete a Near-Miss" note="one card · most combos unlocked" />
          <div className="gv1-empty">
            <span>No deck names available for the completion search.</span>
          </div>
        </section>
      )}

      <footer className="gv1-lab-attrib">
        Combo data ©{' '}
        <a href="https://commanderspellbook.com" target="_blank" rel="noreferrer">
          Commander Spellbook
        </a>{' '}
        (CC-BY-SA) · card data &amp; imagery © Scryfall (Cardmarket EUR / TCGplayer USD prices) ·
        The Grimoire is not affiliated with or endorsed by Wizards of the Coast.
      </footer>
    </div>
  );
}

// ─── Section scaffolding ──────────────────────────────────────────────────────

function SecHead({ folio, title, note }: { folio: string; title: string; note?: string }) {
  return (
    <div className="gv1-lab-sec-head" id={`gv1-lab-sec-${folio}`}>
      <span className="gv1-lab-sec-folio" aria-hidden="true">
        § XII·{folio}
      </span>
      <h3 className="gv1-lab-sec-title">{title}</h3>
      {note && <span className="gv1-lab-sec-note">{note}</span>}
    </div>
  );
}

function TierChip({ t, label }: { t: 'a' | 'b' | 'c'; label?: string }) {
  return (
    <span className={`gv1-lab-tier gv1-lab-tier-${t}`}>
      {label ?? (t === 'a' ? 'Tier A · Curated' : t === 'b' ? 'Tier B · Computed' : 'Tier C · Heuristic')}
    </span>
  );
}

function Framing({ tier, children }: { tier: 'a' | 'b' | 'c'; children: ReactNode }) {
  return (
    <div
      className={
        'gv1-lab-framing' +
        (tier === 'b' ? ' gv1-lab-framing-b' : tier === 'c' ? ' gv1-lab-framing-c' : '')
      }
    >
      <TierChip t={tier} />
      <p>{children}</p>
    </div>
  );
}

function Chain({
  cards,
  templates,
}: {
  cards: { name: string; cmdr?: boolean }[];
  templates?: SpellbookComboTemplate[];
}) {
  const n = cards.length + (templates?.length ?? 0);
  return (
    <p className="gv1-lab-chain">
      {cards.map((c, i) => (
        <span key={`${c.name}-${i}`}>
          <span data-card-name={c.name}>{c.name}</span>
          {c.cmdr && <span className="gv1-lab-cmdr"> cmdr</span>}
          {i < n - 1 && <span className="gv1-lab-chain-sep">+</span>}
        </span>
      ))}
      {(templates ?? []).map((t, i) => (
        <span key={`t-${i}`}>
          <span className="gv1-lab-tpl" title={t.query}>
            {t.name}
          </span>
          {cards.length + i < n - 1 && <span className="gv1-lab-chain-sep">+</span>}
        </span>
      ))}
    </p>
  );
}

/** Produce chips — ∞ prefix + rune tint for infinite results (design copy). */
function Results({ produces }: { produces: string[] }) {
  if (!produces.length) return null;
  return (
    <div className="gv1-lab-results">
      {produces.map((p, i) => (
        <span
          key={`${p}-${i}`}
          className={'gv1-lab-result' + (/infinite/i.test(p) ? ' gv1-lab-result-inf' : '')}
        >
          {/infinite/i.test(p) ? '∞ ' : ''}
          {p.replace(/^Infinite /i, '').replace(/^Near-infinite /i, 'near-∞ ')}
        </span>
      ))}
    </div>
  );
}

function Steps({ lines, label }: { lines: string[]; label: string }) {
  return (
    <div>
      <span className="gv1-lab-steps-label">{label}</span>
      {lines.map((line, i) => (
        <div key={i} className="gv1-lab-step">
          <span className="gv1-lab-step-n">{String(i + 1).padStart(2, '0')}</span>
          <p>{line}</p>
        </div>
      ))}
    </div>
  );
}

// ─── Tier A finding card ──────────────────────────────────────────────────────

function ComboCard({ combo }: { combo: SpellbookCombo }) {
  const win = isWinCombo(combo);
  const two = isTwoCardInfinite(combo);
  const pr = combo.prerequisites;
  const hasDetail = Boolean(combo.steps || pr.easy || pr.notable || combo.manaNeeded);
  return (
    <article className="gv1-lab-combo">
      <div className="gv1-lab-combo-head">
        <TierChip t="a" label="Tier A" />
        {win && <span className="gv1-lab-flag gv1-lab-flag-win">Win</span>}
        {two && <span className="gv1-lab-flag">2-card infinite</span>}
        <span className="gv1-lab-flag" style={{ border: 'none', padding: 0 }}>
          {bracketLabel(combo.bracketTag)}
        </span>
        {combo.popularity > 0 && (
          <span className="gv1-lab-pop" title="Decks running this on Commander Spellbook">
            {combo.popularity.toLocaleString()} decks
          </span>
        )}
      </div>
      <Chain
        cards={combo.cards.map((x) => ({ name: x.name, cmdr: x.mustBeCommander }))}
        templates={combo.templates}
      />
      <Results produces={combo.produces} />
      {hasDetail && (
        <details className="gv1-lab-steps">
          <summary>Steps &amp; prerequisites</summary>
          <div className="gv1-lab-steps-body">
            {(combo.manaNeeded || pr.easy || pr.notable) && (
              <div>
                <span className="gv1-lab-steps-label">Prerequisites</span>
                {combo.manaNeeded && <p className="gv1-lab-prose">Mana: {combo.manaNeeded}</p>}
                {pr.easy && <p className="gv1-lab-prose">{pr.easy}</p>}
                {pr.notable && <p className="gv1-lab-prose">{pr.notable}</p>}
              </div>
            )}
            {combo.steps && (
              <Steps lines={combo.steps.split('\n')} label="Steps · curated by Commander Spellbook" />
            )}
          </div>
        </details>
      )}
      <div className="gv1-lab-combo-foot">
        <a className="gv1-lab-link" href={combo.permalink} target="_blank" rel="noreferrer">
          Why? — Commander Spellbook ↗
        </a>
      </div>
    </article>
  );
}

// ─── Tier B section + loop card ───────────────────────────────────────────────

const TIER_B_KIND_FLAG: Record<'corroborated' | 'novel' | 'engine', string> = {
  corroborated: 'Also curated · Tier A',
  novel: 'Novel — verified by the model',
  engine: 'Value engine / near-miss',
};

/** Machine-verified loop layer. Findings are Tier B — computed, "verified under
 * Laço's model" (EI-2), never a comprehensive-rules proof. Corroborated loops are
 * also curated (Tier A) and labelled as such (DB-7). Loops the provenance gate
 * held back are disclosed, not shown as verified (plan 6b). */
function TierBSec({ tierB, tierBCount }: { tierB?: TierBReport; tierBCount: number }) {
  return (
    <section className="gv1-lab-sec" aria-label="Verified loops">
      <SecHead
        folio="b"
        title="Verified Loops"
        note={tierB ? `${tierBCount} under the model` : 'no verifier data'}
      />
      <Framing tier="b">
        Machine-verified against Laço’s loop-closure model — <strong>verified under the model</strong>,
        never a comprehensive-rules ruling. Deterministic; consumes only human-reviewed or
        deterministic knowledge (provenance gate).
      </Framing>
      {!tierB ||
      (!tierB.corroborated.length && !tierB.novel.length && !tierB.engines.length) ? (
        <div className="gv1-empty">
          <span>
            No loops verified under the model — not an exhaustiveness claim; only the modelled loop
            shapes over covered cards are checked.
          </span>
        </div>
      ) : (
        <div className="gv1-lab-grid2">
          {tierB.corroborated.map((f, i) => (
            <LoopCard key={`c-${i}-${f.cards.join('|')}`} f={f} kind="corroborated" />
          ))}
          {tierB.novel.map((f, i) => (
            <LoopCard key={`n-${i}-${f.cards.join('|')}`} f={f} kind="novel" />
          ))}
          {tierB.engines.map((f, i) => (
            <LoopCard key={`e-${i}-${f.cards.join('|')}`} f={f} kind="engine" />
          ))}
        </div>
      )}
      {tierB && tierB.capped.length > 0 && (
        <p className="gv1-lab-warn" role="status">
          {tierB.capped.length} candidate loop{tierB.capped.length > 1 ? 's' : ''} held at Tier C —
          a loop-relevant knowledge-base entry is not yet human-reviewed (provenance gate).
        </p>
      )}
    </section>
  );
}

function LoopCard({ f, kind }: { f: TierBFinding; kind: 'corroborated' | 'novel' | 'engine' }) {
  const leaks = f.deficit.filter((d) => d.shortfall != null);
  return (
    <article className="gv1-lab-combo">
      <div className="gv1-lab-combo-head">
        <TierChip t={kind === 'corroborated' ? 'a' : 'b'} label={kind === 'corroborated' ? 'Tier A' : 'Tier B'} />
        <span className="gv1-lab-flag">{TIER_B_KIND_FLAG[kind]}</span>
        <span className="gv1-lab-pop">{loopClassLabel(f)}</span>
      </div>
      <Chain cards={f.cards.map((n) => ({ name: n }))} />
      <Results produces={f.resultTypes.map((r) => r.replace(/_/g, ' ').replace(/:/g, ' · '))} />
      {leaks.length > 0 && (
        <div>
          <span className="gv1-lab-leak">
            Leaks {leaks.map((d) => `${d.shortfall} ${d.resource}/iteration`).join(', ')}
          </span>
          {leaks[0].note && <p className="gv1-lab-leak-note">{leaks[0].note}</p>}
        </div>
      )}
      <details className="gv1-lab-steps">
        <summary>Loop trace &amp; provenance</summary>
        <div className="gv1-lab-steps-body">
          {f.trace.length > 0 && <Steps lines={f.trace} label="Trace · one iteration" />}
          <div>
            <span className="gv1-lab-steps-label">Prerequisites</span>
            <p className="gv1-lab-prose">
              Minimum starting mana: {f.prerequisites.minInitialMana}
              {f.prerequisites.guards.length > 0
                ? ` · guards: ${f.prerequisites.guards.map((g) => g.replace(/_/g, ' ')).join(', ')}`
                : ''}
            </p>
            {f.prerequisites.note && (
              <p className="gv1-lab-prose" style={{ fontStyle: 'italic', color: 'var(--gv1-ink-dim)' }}>
                {f.prerequisites.note}
              </p>
            )}
          </div>
          <p className="gv1-lab-note">
            ontology {String(f.provenance.ontologyVersion)} · extractor{' '}
            {String(f.provenance.extractorVersion)} · {f.provenance.gate}
          </p>
        </div>
      </details>
    </article>
  );
}

// ─── Near-miss ledger row ─────────────────────────────────────────────────────

function NearRow({ combo }: { combo: SpellbookCombo }) {
  const missing = combo.missing ?? { cards: [], templates: [] };
  const missSet = new Set(missing.cards);
  const present = combo.cards.filter((x) => !missSet.has(x.name));
  return (
    <div className="gv1-lab-near-row">
      <span
        className={'gv1-lab-dist' + (combo.distance > 1 ? ' gv1-lab-dist-2' : '')}
        title={`${combo.distance} piece${combo.distance > 1 ? 's' : ''} short`}
      >
        −{combo.distance}
      </span>
      <span className="gv1-lab-needs">
        {missing.cards.map((n, i) => (
          <span key={`${n}-${i}`}>
            {i > 0 && ', '}
            <span data-card-name={n}>{n}</span>
          </span>
        ))}
        {missing.templates.map((t, i) => (
          <span key={`t-${i}`}>
            {(missing.cards.length > 0 || i > 0) && ', '}
            <span className="gv1-lab-tpl" title={t.query}>
              a {t.name}
            </span>
          </span>
        ))}
      </span>
      <span className="gv1-lab-near-with">
        completes{' '}
        {present.map((x, i) => (
          <span key={`${x.name}-${i}`}>
            {i > 0 && ' + '}
            <span data-card-name={x.name}>{x.name}</span>
          </span>
        ))}
        <span className="gv1-lab-near-produce">
          → {combo.produces.slice(0, 2).join(' · ')}
          {combo.produces.length > 2 ? ` · +${combo.produces.length - 2}` : ''}
        </span>
      </span>
      <span className="gv1-lab-near-end">
        {combo.popularity > 0 && (
          <span className="gv1-lab-pop">{combo.popularity.toLocaleString()} decks</span>
        )}
        <a className="gv1-lab-link" href={combo.permalink} target="_blank" rel="noreferrer">
          spellbook ↗
        </a>
      </span>
    </div>
  );
}

// ─── Tier C synergy section ───────────────────────────────────────────────────

const SYN_SHAPE_LABEL: Record<'pair' | 'triple' | 'cycle', string> = {
  pair: '2-card',
  triple: '3-card',
  cycle: '4-cycle',
};

function SynRow({ cand, shape }: { cand: SynergyCandidate; shape: 'pair' | 'triple' | 'cycle' }) {
  return (
    <div className="gv1-lab-syn">
      <div className="gv1-lab-syn-head">
        <TierChip t="c" label="Tier C" />
        <span className={'gv1-lab-flag' + (cand.band === 'strong' ? ' gv1-lab-band-strong' : '')}>
          {cand.band}
        </span>
        <span className="gv1-lab-syn-cards">
          {cand.cards.map((n, i) => (
            <span key={`${n}-${i}`}>
              {i > 0 && <span className="gv1-lab-chain-sep">+</span>}
              <span data-card-name={n}>{n}</span>
            </span>
          ))}
        </span>
        <span className="gv1-lab-econ">
          <span className="gv1-lab-flag" style={{ border: 'none', padding: 0 }}>
            {SYN_SHAPE_LABEL[shape]}
          </span>
        </span>
      </div>
      <ul className="gv1-lab-edges">
        {cand.edges.map((e, i) => (
          <li key={`${e.from}-${e.to}-${e.fromFeature}-${e.toFeature}-${i}`} className="gv1-lab-edge">
            {e.from}
            <span className="gv1-arrow">⟶</span>
            {e.to} <span className="gv1-lab-edge-label">· {e.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Heuristic synergy layer — Tier C, speculative signals, NOT verified combos
 * (EI-1/EI-4). Coarse bands only, never a numeric score (RK-5). Pairs by default;
 * triples & 4-cycles behind the deep-couplings action (OQ-3). */
function SynergySec({
  synergy,
  onDeepScan,
  deepScanning,
}: {
  synergy?: SynergyReport;
  onDeepScan?: () => void;
  deepScanning?: boolean;
}) {
  const [showAllSyn, setShowAllSyn] = useState(false);
  const [showDeep, setShowDeep] = useState(false);
  // Auto-reveal deep results the moment they arrive from a paste-mode deep scan
  // (fleet mode ships them pre-loaded, so we must NOT auto-reveal there).
  const prevDeep = useRef(synergy?.deepAvailable ?? false);
  useEffect(() => {
    const avail = synergy?.deepAvailable ?? false;
    if (!prevDeep.current && avail) setShowDeep(true);
    prevDeep.current = avail;
  }, [synergy?.deepAvailable]);

  const deepCount = synergy ? synergy.counts.triples + synergy.counts.cycles : 0;
  const deepReveal = () => {
    if (synergy?.deepAvailable) setShowDeep((v) => !v);
    else if (onDeepScan) onDeepScan();
  };
  const deepLabel = deepScanning
    ? '◇ scanning couplings …'
    : synergy?.deepAvailable
      ? showDeep
        ? 'Hide triples & 4-cycles'
        : `Deep couplings — triples & 4-cycles (${deepCount})`
      : 'Deep couplings — scan triples & 4-cycles';

  const pairsShown = synergy
    ? showAllSyn
      ? synergy.pairs
      : synergy.pairs.slice(0, SYN_COLLAPSE)
    : [];

  return (
    <section className="gv1-lab-sec" aria-label="Tier-C synergies">
      <SecHead
        folio="d"
        title="Synergy Candidates"
        note={
          synergy
            ? `${synergy.counts.pairs} pairs ranked · crowd prior ${synergy.crowdPriorApplied ? 'applied' : 'off'}`
            : 'no synergy data'
        }
      />
      <Framing tier="c">
        Speculative signals from a provides / wants coupling graph — <strong>not verified combos</strong>.
        Every candidate is justified by its matched couplings below; bands stay coarse by design,
        never a numeric score.
      </Framing>
      {!synergy ? (
        <div className="gv1-empty">
          <span>No synergy knowledge-base data available for this list.</span>
        </div>
      ) : (
        <>
          {/* KB-gap caveat (DC-6) — distinct wording from the IN-6 unresolved warning. */}
          {synergy.uncovered.length > 0 && (
            <p className="gv1-lab-warn" role="status">
              {synergy.uncovered.length} card{synergy.uncovered.length > 1 ? 's have' : ' has'} no
              knowledge-base entry yet and {synergy.uncovered.length > 1 ? 'were' : 'was'} skipped
              for synergy analysis: <span className="gv1-dim">{synergy.uncovered.join(' · ')}</span>
            </p>
          )}
          {synergy.pairs.length === 0 ? (
            <div className="gv1-empty">
              <span>No heuristic synergy pairs surfaced.</span>
            </div>
          ) : (
            <div className="gv1-lab-syn-list">
              {pairsShown.map((c, i) => (
                <SynRow key={`p-${i}-${c.cards.join('|')}`} cand={c} shape="pair" />
              ))}
            </div>
          )}
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            {synergy.pairs.length > SYN_COLLAPSE && (
              <button type="button" className="gv1-lab-more" onClick={() => setShowAllSyn((v) => !v)}>
                {showAllSyn ? 'Show fewer' : `Show all ${synergy.pairs.length} pairs`}
              </button>
            )}
            <button
              type="button"
              className="gv1-lab-more"
              onClick={deepReveal}
              disabled={deepScanning}
              aria-busy={deepScanning}
            >
              {deepLabel}
            </button>
            {synergy.deepFocused && (showDeep || synergy.deepAvailable) && (
              <span className="gv1-lab-note">Deep scan focused on the strongest couplings.</span>
            )}
          </div>
          {showDeep && synergy.deepAvailable && (
            <div className="gv1-lab-syn-groups">
              <div>
                <h4 className="gv1-lab-h3">
                  Triples{' '}
                  <span className="gv1-dim">
                    ({synergy.triples.length} of {synergy.counts.triplesTotal})
                  </span>
                </h4>
                {synergy.triples.length === 0 ? (
                  <p className="gv1-lab-note">No triples surfaced.</p>
                ) : (
                  <div className="gv1-lab-syn-list">
                    {synergy.triples.map((c, i) => (
                      <SynRow key={`t-${i}-${c.cards.join('|')}`} cand={c} shape="triple" />
                    ))}
                  </div>
                )}
              </div>
              <div>
                <h4 className="gv1-lab-h3">
                  4-cycles{' '}
                  <span className="gv1-dim">
                    ({synergy.cycles.length} of {synergy.counts.cyclesTotal})
                  </span>
                </h4>
                {synergy.cycles.length === 0 ? (
                  <p className="gv1-lab-note">No 4-cycles surfaced.</p>
                ) : (
                  <div className="gv1-lab-syn-list">
                    {synergy.cycles.map((c, i) => (
                      <SynRow key={`c-${i}-${c.cards.join('|')}`} cand={c} shape="cycle" />
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}

// ─── § XII·e — Complete a Near-Miss (DEC-516, Phase 4) ────────────────────────

/** The mechanistic recommendation engine (NM-7). Loads the full-coverage KB
 * feature index + price index and searches the pool for cards that CLOSE the
 * deck's near-misses: Tier-B deficit cover + Tier-C half-edge cover. Filterable
 * by price / owned (owned flags read the § IX Shopping collection). Nothing here
 * edits a deck (NG5); it is a report. */
function CompletionSec({
  inputs,
  owned,
  onResult,
}: {
  inputs: CompletionInputs;
  owned: OwnedCollection;
  onResult: (r: CompletionReport | null) => void;
}) {
  const [currency, setCurrency] = useState<Currency>('eur');
  const [maxPriceStr, setMaxPriceStr] = useState('');
  const [ownedOnly, setOwnedOnly] = useState(false);
  const [result, setResult] = useState<CompletionReport | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [error, setError] = useState<string>();
  const assets = useRef<{ fi: FeatureIndex; cfg: SynergyConfig; px: PriceIndex | null } | null>(
    null,
  );

  const compute = (a: { fi: FeatureIndex; cfg: SynergyConfig; px: PriceIndex | null }) => {
    const parsedMax = maxPriceStr.trim() ? Number(maxPriceStr) : NaN;
    const maxPrice = Number.isFinite(parsedMax) && parsedMax > 0 ? parsedMax : null;
    const ownedKeys = owned.keys.size > 0 ? owned.keys : null;
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

  // Auto-run on mount (the design renders the section populated; assets are
  // module-cached, so only the first visit pays the KB + price fetch).
  useEffect(() => {
    let cancelled = false;
    (async () => {
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
        if (cancelled) return;
        setLoaded(true);
        setStatus('ready');
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : String(e));
        setStatus('error');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Recompute (no refetch — indices are cached) whenever a filter changes or the
  // analyzed inputs change (`inputs` is memoized by the caller, so its identity
  // only moves on a genuine re-analyze — e.g. fresh engine deficits).
  useEffect(() => {
    if (!loaded || !assets.current) return;
    compute(assets.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currency, maxPriceStr, ownedOnly, loaded, inputs]);

  // Aggregate Tier-B completions per card so a card closing several loops reads
  // as one row with "+N loops closed" (design's aggregation semantics).
  const tierBRows = useMemo(() => {
    if (!result) return [];
    const byCard = new Map<string, { card: TierBCompletion['card']; closes: TierBCompletion[] }>();
    for (const b of result.tierB) {
      const e = byCard.get(b.card.name);
      if (e) e.closes.push(b);
      else byCard.set(b.card.name, { card: b.card, closes: [b] });
    }
    return [...byCard.values()].slice(0, COMPLETION_MAX);
  }, [result]);

  const tierCRows = useMemo(
    () => (result ? result.tierC.slice(0, COMPLETION_MAX) : []),
    [result],
  );

  const sym = currency === 'eur' ? '€' : '$';
  const priceText = (p: number | null) => (p != null ? `${sym}${p.toFixed(2)}` : '· no price yet');

  return (
    <section className="gv1-lab-sec" aria-label="Complete a near-miss">
      <SecHead folio="e" title="Complete a Near-Miss" note="one card · most combos unlocked" />
      <Framing tier="b">
        The mechanistic recommendation engine — pool cards that would <strong>close</strong> the
        near-misses above. A report only: it never edits your deck. Confirm each interaction
        yourself.
      </Framing>

      <div className="gv1-lab-filters">
        <label className="gv1-lab-field" style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <span className="gv1-mono-xs gv1-dim">Max price</span>
          <input
            className="gv1-lab-input"
            type="number"
            min="0"
            step="0.5"
            inputMode="decimal"
            placeholder="any"
            value={maxPriceStr}
            onChange={(e) => setMaxPriceStr(e.target.value)}
          />
        </label>
        <label className="gv1-lab-field" style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <span className="gv1-mono-xs gv1-dim">Currency</span>
          <select
            className="gv1-lab-input"
            value={currency}
            onChange={(e) => setCurrency(e.target.value as Currency)}
          >
            <option value="eur">EUR (Cardmarket)</option>
            <option value="usd">USD (TCGplayer)</option>
          </select>
        </label>
        <button
          type="button"
          className={'gv1-lab-filter-chip' + (ownedOnly ? ' gv1-active' : '')}
          aria-pressed={ownedOnly}
          disabled={owned.count === 0}
          title={
            owned.count === 0
              ? 'Import your collection in § IX Shopping first'
              : `${owned.count} owned cards on file`
          }
          onClick={() => setOwnedOnly((v) => !v)}
        >
          Owned only
        </button>
        <span className="gv1-lab-note">
          {owned.count > 0 ? (
            `${owned.count} owned cards on file — imported in § IX Shopping`
          ) : (
            <>
              no collection on file — <Link to="/shopping">import in § IX Shopping</Link>
            </>
          )}
        </span>
      </div>

      {status === 'loading' && (
        <p className="gv1-lab-note" aria-busy="true">
          ◇ loading the knowledge base &amp; prices …
        </p>
      )}
      {status === 'error' && (
        <p className="gv1-lab-warn" role="alert">
          Could not run completion search: {error}
        </p>
      )}

      {status === 'ready' && result && (
        <>
          <p className="gv1-lab-note">
            Color identity <span className="gv1-rune">{result.deckColorIdentity}</span> · legal in
            Commander · searched {result.poolSize.toLocaleString()} pool cards in{' '}
            {result.elapsedMs.toFixed(0)}ms · {result.counts.droppedByColor.toLocaleString()}{' '}
            off-color
            {result.counts.droppedByPrice > 0 && <> · {result.counts.droppedByPrice} over budget</>}
            {ownedOnly && result.counts.droppedByOwned > 0 && (
              <> · {result.counts.droppedByOwned} unowned</>
            )}{' '}
            filtered out.
          </p>

          {/* Tier B — computed deficit completions */}
          <div>
            <h4 className="gv1-lab-h3">
              <TierChip t="b" label="Tier B" /> Computed completions{' '}
              <span className="gv1-dim">
                ({tierBRows.length}
                {result.counts.tierBTotal > tierBRows.length ? ` of ${result.counts.tierBTotal}` : ''})
              </span>
            </h4>
            {!result.tierBAvailable ? (
              <p className="gv1-lab-note">
                Computed completions run on this deck’s verified loop deficits — the Tier-B verifier
                index is currently unavailable.
              </p>
            ) : tierBRows.length === 0 ? (
              <p className="gv1-lab-note">
                No computed loop deficits to complete under the current filters.
              </p>
            ) : (
              <div className="gv1-lab-comp-list">
                {tierBRows.map((row) => (
                  <CompRow
                    key={`tb-${row.card.name}`}
                    name={row.card.name}
                    owned={row.card.owned === true}
                    big={`+${row.closes.length}`}
                    bigSub={row.closes.length > 1 ? 'loops closed' : 'loop closed'}
                    price={priceText(row.card.price)}
                    sample={
                      <>
                        closes the {row.closes[0].resource} leak on{' '}
                        {row.closes[0].loopCards.join(' + ')} via {row.closes[0].closerLabel}
                        {row.closes.length > 1 ? ` — and ${row.closes.length - 1} more` : ''}
                      </>
                    }
                  />
                ))}
              </div>
            )}
            {result.tierBAvailable && tierBRows.length > 0 && (
              <p className="gv1-lab-note">
                “Verified under the model”, not a comprehensive-rules proof — confirm the
                interaction.
              </p>
            )}
          </div>

          {/* Tier C — speculative half-edge completions */}
          <div>
            <h4 className="gv1-lab-h3">
              <TierChip t="c" label="Tier C" /> Speculative completions{' '}
              <span className="gv1-dim">
                ({tierCRows.length}
                {result.counts.tierCTotal > tierCRows.length ? ` of ${result.counts.tierCTotal}` : ''})
              </span>
            </h4>
            {tierCRows.length === 0 ? (
              <p className="gv1-lab-note">No half-edge completions under the current filters.</p>
            ) : (
              <div className="gv1-lab-comp-list">
                {tierCRows.map((t) => (
                  <CompRow
                    key={`tc-${t.card.name}`}
                    name={t.card.name}
                    owned={t.card.owned === true}
                    band={t.band}
                    big={`+${t.couplings.length}`}
                    bigSub={t.couplings.length > 1 ? 'couplings matched' : 'coupling matched'}
                    price={priceText(t.card.price)}
                    sample={<CompSample t={t} />}
                  />
                ))}
              </div>
            )}
            {tierCRows.length > 0 && (
              <p className="gv1-lab-note">
                Tier C is a speculative compatibility signal, NOT a verified combo.
              </p>
            )}
          </div>
        </>
      )}
    </section>
  );
}

function CompSample({ t }: { t: TierCCompletion }) {
  const shown = t.couplings.slice(0, 2);
  return (
    <>
      {shown.map((e) => e.label).join(' · ')}
      {t.couplings.length > shown.length ? ` — and ${t.couplings.length - shown.length} more` : ''}
    </>
  );
}

/** Completion row — the one place inline card art stays (58px thumb). */
function CompRow({
  name,
  owned,
  band,
  big,
  bigSub,
  price,
  sample,
}: {
  name: string;
  owned: boolean;
  band?: 'strong' | 'speculative';
  big: string;
  bigSub: string;
  price: string;
  sample: ReactNode;
}) {
  const front = name.split(' // ')[0];
  return (
    <div className="gv1-lab-comp">
      <Art name={front} />
      <div>
        <div className="gv1-lab-comp-name">
          <span data-card-name={front}>{name}</span>
          {band && (
            <span
              className={'gv1-lab-flag' + (band === 'strong' ? ' gv1-lab-band-strong' : '')}
              style={{ marginLeft: 10 }}
            >
              {band}
            </span>
          )}
          {owned && (
            <span className="gv1-lab-pop gv1-lab-owned-tag" style={{ marginLeft: 10 }}>
              · owned
            </span>
          )}
        </div>
        <div className="gv1-lab-comp-sample">{sample}</div>
      </div>
      <div className="gv1-lab-comp-end">
        <span className="gv1-lab-comp-unlocks">{big}</span>
        <span className="gv1-lab-stat-sub">{bigSub}</span>
        <span className="gv1-lab-pop">{price}</span>
      </div>
    </div>
  );
}

function Art({ name }: { name: string }) {
  const e = useCard(name);
  return (
    <span className="gv1-lab-art" data-card-name={name} title={name}>
      {e && e.status === 'loaded' && e.image_small ? (
        <img src={e.image_small} alt={name} loading="lazy" />
      ) : e && e.status === 'error' ? (
        <span className="gv1-lab-art-fallback" aria-hidden="true">
          ◇
        </span>
      ) : (
        <span className="gv1-lab-skeleton" aria-hidden="true" />
      )}
    </span>
  );
}
