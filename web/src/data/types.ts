// Type contracts for the DEC-149 data layer.
//
// Two layers:
//   1. RAW   — exact shape of files under data/commanders/{id}/{deck,simulation,metrics,candidates}.json.
//   2. DECK_FULL — UI-friendly shape produced by normalize.ts; the only shape components consume.
//
// Missing / sparse fields in raw deck JSON are filled with sentinels at normalization time
// (e.g. mv: "—") so components never branch on absence.

// ─── 1. RAW JSON ────────────────────────────────────────────────────

export type SourceType =
  | 'edhrec'
  | 'youtube'
  | 'draftsim'
  | 'article'
  | 'scryfall'
  | 'commanderspellbook'
  | 'ai-inferred'
  | 'reddit'
  | 'other';

export interface DeckSource {
  type: SourceType;
  name: string;
  url?: string;
  detail?: string;
}

export interface RawDecklistCard {
  name: string;
  type: string;
  primary_role?: string;
  secondary_role?: string;
  wincon_style?: string;
  is_mdfc_land?: boolean;
  quantity?: number;
}

export interface RawHighlight {
  name: string;
  reason?: string;
  price?: string;
  isGameChanger?: boolean;
  sources?: DeckSource[];
}

export interface RawSynergy {
  title: string;
  description: string;
  cards: string[];
  sources?: DeckSource[];
}

export interface RawWinCondition {
  title: string;
  description: string;
  cards: string[];
  sources?: DeckSource[];
}

export interface RawCategory {
  name: string;
  description?: string;
  isHighlighted?: boolean;
  cards: string[];
}

export type DeckStatus = 'physical' | 'brewing';

export interface RawDeckIndexEntry {
  id: string;
  name: string;
  commander: string;
  partner?: string;
  colors: string[];
  theme: string;
  bracket: string;
  lastUpdatedSet?: string;
  /** Build status. Omitted = "physical" for backwards compat. */
  status?: DeckStatus;
}

export interface RawDeckIndex {
  commanders: RawDeckIndexEntry[];
}

/**
 * Token populated by `scripts/compute_tokens.py` from Scryfall `all_parts`.
 * Producers (`produced_by`) are real card names from the decklist; the rest
 * mirrors the Scryfall token-card shape.
 */
export interface DeckToken {
  name: string;
  type_line?: string;
  oracle_text?: string;
  power?: string;
  toughness?: string;
  colors?: string[];
  scryfall_id?: string;
  image_uri?: string;
  produced_by: string[];
}

export interface RawDeck {
  id: string;
  type: string;
  name: string;
  subtitle?: string;
  commander: string;
  partner?: string;
  bracket: string;
  /** Build status. Omitted = "physical" for backwards compat. */
  status?: DeckStatus;
  gameChangers?: number;
  lastUpdatedSet?: string;
  archetypes?: string[];
  commanderRoles?: string[];
  wincon_style?: string;
  asymmetric_only?: boolean;
  guideContent?: { strategyOverview?: string; deckCategories?: RawCategory[] };
  sources?: DeckSource[];
  categories?: RawCategory[];
  highlights?: RawHighlight[];
  synergies?: RawSynergy[];
  winConditions?: RawWinCondition[];
  decklist: RawDecklistCard[];
  tokens?: DeckToken[];
}

export interface RawDeckHealthScore {
  score: number;
  grade: string;
  components?: Record<string, number>;
  methodology?: string;
}

export interface RawDeckComposition {
  totalCards: number;
  lands: number;
  rocks?: number;
  spells?: number;
  avgCmc: number;
}

export interface RawAssessment {
  manaAdequacy?: string;
  mulliganVerdict?: string;
  commanderTiming?: string;
}

export interface RawSimMetadata {
  numGames?: number;
  numTurns?: number;
  generatedAt?: string;
}

export interface RawSimManaTurn {
  median: number;
  p25: number;
  p75: number;
  mean?: number;
}

export interface RawSimMulliganStats {
  keptFirst?: number;
  freeMulligan?: number;
  paidMulligan?: number;
}

export interface RawSimOpeningHand {
  landDistribution?: Record<string, number>;
}

export interface RawSimCommanderTiming {
  name?: string;
  cmc?: number;
  byTurn?: Record<string, number>;
  medianTurn?: number;
}

export interface RawSimCurveEfficiency {
  castableByTurn?: Record<string, number>;
  byTurn?: Record<string, number>;
  curveOutRate?: number;
}

export interface RawSimulation {
  deckHealthScore?: RawDeckHealthScore;
  deckComposition?: RawDeckComposition;
  assessment?: RawAssessment;
  goldfish?: unknown;
  manaByTurn?: Record<string, RawSimManaTurn>;
  metadata?: RawSimMetadata;
  mulliganStats?: RawSimMulliganStats;
  openingHand?: RawSimOpeningHand;
  reliabilityMetrics?: unknown;
  specialMetrics?: unknown;
  colorBalance?: unknown;
  commanderTiming?: RawSimCommanderTiming;
  curveEfficiency?: RawSimCurveEfficiency;
}

export interface RawMetricsGap {
  role: string;
  actual: number;
  target: number;
  score: number;
}

export interface RawMetricsComponent {
  score: number;
  [key: string]: unknown;
}

/**
 * DEC-311 — Best/Typical/Contested win-turn triple derived from goldfish
 * `byTurn` lethality curves. Any number field may be null when the threshold
 * is not reached inside the simulated window; the whole object is null/absent
 * when `simulation.json` is missing or the chosen payoff curve is flat at zero.
 */
export interface RawMetricsWinTurn {
  best: number | null;
  typical: number | null;
  contested: number | null;
  source: 'comboLethal' | 'lethalProxy' | 'max';
  bracket_drag: number;
  thresholds: { best: number; typical: number };
  window_last_turn: number;
}

export interface RawMetrics {
  deck_id: string;
  commander: string;
  bracket: string;
  color_identity?: string[];
  global_health: number;
  /**
   * DEC-389 — same formula as `global_health` but scored against fixed Bracket-3
   * reference targets instead of the deck's declared bracket bar. Cross-deck
   * apples-to-apples. Absent until compute_deck_metrics.py emits it.
   */
  global_health_normalized?: number | null;
  /** DEC-310 — ±N data-completeness band around `global_health`. Clamped [2, 15]. */
  confidence_margin?: number;
  /** DEC-311 — derived win-turn triple. Null when sim missing or curve flat. */
  win_turn?: RawMetricsWinTurn | null;
  metrics: Record<string, RawMetricsComponent>;
  gaps: RawMetricsGap[];
  methodology?: string;
  generated_at?: string;
  scryfall_mirror_updated_at?: string;
  version?: string;
}

export interface RawCandidate {
  name: string;
  cmc: number;
  mana_cost: string;
  type_line: string;
  oracle_text?: string;
  score: number;
  matched_archetypes?: string[];
  owned?: boolean;
  game_changer?: boolean;
  deck_role?: string;
  strategy_line?: string;
  mitigates_gap?: string | null;
  score_breakdown?: Record<string, unknown>;
}

export interface RawCandidates {
  deck_id: string;
  candidates: RawCandidate[];
  scryfall_mirror_updated_at?: string;
  generated_at?: string;
  version?: string;
}

export interface RawCardMetadataEntry {
  type_line?: string;
  cmc?: number;
  mana_cost?: string;
  colors?: string[];
  oracle_text?: string;
  layout?: string;
}

export type RawCardMetadata = Record<string, RawCardMetadataEntry>;

/** Raw record passed into normalize() — one per deck. */
export interface RawDeckBundle {
  id: string;
  index: RawDeckIndexEntry;
  deck: RawDeck;
  sim?: RawSimulation | null;
  metrics?: RawMetrics | null;
  candidates?: RawCandidates | null;
  cardMetadata?: RawCardMetadata;
}

// ─── 2. DECK_FULL (UI shape) ────────────────────────────────────────

/** Card tile payload consumed by `<CardTile>` (web/src/components/molecules/CardTile.tsx). */
export interface DeckCardTile {
  /** Card name. */
  n: string;
  /** Mana value display string ("{2}{R}", "—", "LAND"). */
  mv: string;
  /** Type line; '—' if unknown. */
  type: string;
  /** Live price string (formatted), or '—'. */
  price: string;
  /** Game-changer flag; renders gold star + border. */
  gc: boolean;
  /** Editor's note shown below type line. */
  note?: string;
  /** Number of physical copies (basics with quantity > 1). Defaults to 1 when omitted. */
  qty?: number;
  /** Front-face mana value (Scryfall `cmc`). Populated lazily from `cardCache` at render time. */
  cmc?: number;
}

/** Two-half title: [head, emphasized tail] used by wincon/combo headings. */
export type SplitTitle = readonly [string, string];

export interface DeckWincon {
  title: SplitTitle;
  prob: string;
  desc: string;
  cards: DeckCardTile[];
}

export interface DeckEngineSection {
  title: string;
  count: number;
  cards: DeckCardTile[];
  isGameChangers: boolean;
}

export interface DeckCombo {
  title: SplitTitle;
  desc: string;
  cards: DeckCardTile[];
  src: string;
  tag: string;
}

export interface DeckApothecary {
  diagnosis: {
    score: number;
    /** DEC-389 — bracket-normalized global health (vs fixed B3 targets). Null until emitted. */
    scoreNormalized?: number | null;
    confidenceMargin?: number;
    methodology: string;
    generatedAt?: string;
    mirrorUpdatedAt?: string;
    components: Record<string, RawMetricsComponent>;
    /** DEC-311 — Best/Typical/Contested triple, null when suppressed. */
    winTurn?: RawMetricsWinTurn | null;
  };
  maladies: RawMetricsGap[];
  remedies: RawCandidate[];
}

export interface DeckCurveEntry {
  cmc: string;
  n: number;
  peak: boolean;
}

export interface DeckFuncEntry {
  l: string;
  n: number;
  pct: number;
}

export interface DeckListGroup {
  name: string;
  cards: DeckCardTile[];
}

export interface DeckFull {
  /** 1-based display index. */
  idx: number;
  slug: string;
  deckName: string;
  commander: string;
  /** Optional partner commander (e.g. partner mechanic, background). */
  partner?: string;
  commanderMv: string;
  /** "Commander · {theme}" caption. */
  type: string;
  /** Color identity glyph string (e.g. "🔴⚫"). */
  colors: string;
  /** Roman bracket (e.g. "IV"). */
  bracket: string;
  /** Build status. Always present after normalization (defaults "physical"). */
  status: DeckStatus;
  pt: string;
  winTurn: string;
  winRate: number | null;
  flavor: string;
  oracle: string[];
  strategy: string;

  wincons: DeckWincon[];
  engine: DeckEngineSection[];
  combos: DeckCombo[];
  apothecary: DeckApothecary | null;
  curve: DeckCurveEntry[];
  func: DeckFuncEntry[];
  sources: Array<readonly [string, string]>;
  list: DeckListGroup[];

  health: RawDeckHealthScore | null;
  assessment: RawAssessment | null;
  composition: RawDeckComposition | null;

  /** Raw payloads kept for downstream surfaces (Scrying / Compare). */
  sim: RawSimulation | null;
  /** Decklist as authored — one entry per unique card; basics carry `quantity`. */
  rawDecklist: RawDecklistCard[];
  /** Decklist flattened to physical copies (one entry per card). 99 entries for production decks. */
  physicalDecklist: RawDecklistCard[];
  synergies: Array<{ title: string; cards: string[]; description: string }>;
  gameChangers: number;
  tokens: DeckToken[];
}

/** Lightweight selector entry used by DeckSelector / nav menus. */
export interface DeckStub {
  idx: number;
  slug: string;
  name: string;
  cmd: string;
  /** Optional partner commander; rendered alongside `cmd` when present. */
  partner?: string;
  colors: string;
  bracket: string;
  hasDetail: boolean;
  /** Build status (defaults "physical" when omitted in source). */
  status: DeckStatus;
}
