// Deck JSON loader.
//
// Fetches data/index.json + per-deck {deck,simulation,metrics,candidates}.json,
// caches each response in localStorage with a 24h TTL, and returns the bundle
// shape that normalize.ts expects.
//
// Production deploy (Phase 6) places dist/ next to data/ at the host root, so
// `/data/...` is the same origin. In dev the vite middleware in vite.config.ts
// proxies /data/* to ../data/*.

import type {
  RawCandidates,
  RawCardMetadata,
  RawDeck,
  RawDeckBundle,
  RawDeckIndex,
  RawDeckIndexEntry,
  RawMetrics,
  RawSimulation,
} from './types';

// Bump suffix when the persisted shape or upstream data semantics change so
// returning users don't read stale bundles. v5 (DEC-206): Eternal Agony
// bracket re-tune to B4 — 6-card swap (Kederekt/Maddening Hex/Firebrand/Cursed
// Mirror/Gleeful Arsonist/Fiery Inscription -> Vampiric/Diabolic Intent/Grim
// Tutor/Mana Vault/Animate Dead/Entomb), bracket 5 -> 4, GCs 8 -> 10.
// v5 -> v6: sim-fidelity follow-up (DEC-206) — Hidetsugu+Solphim tagged as
// kind:combo, tutor_mode/extra_cost schema added; simulation.json values shift
// for eternal-agony, dark-dominion, eternal-harvest.
// v6 -> v7 (DEC-226): added Witherbloom Balance deck + index reorder.
// v7 -> v8 (DEC-235): card-metadata.json refreshed to cover all decks (was
// missing ~80 cards including Vampiric Tutor, Demonic Consultation, Thassa's
// Oracle, Witherbloom landbase); some tiles rendered "—" mana cost waiting on
// the live-Scryfall fallback. Bump invalidates the persisted card-metadata
// envelope so returning users pick up the fresh data immediately.
// v8 -> v9 (DEC-271): added zada-hedron-grinder deck (Hedron Storm); index
// reorder placed it before Genesis Protocol. Bump invalidates cached deck
// index so returning users see the new deck without manual cache clear.
// v9 -> v10 (DEC-271): swapped Magmatic Hellkite → Spinerock Tyrant
// (board-approved); bump invalidates cached Zada decklist so returning
// users pick up the new card immediately.
// v10 -> v11 (DEC-275): swapped Sword of the Animist → Selfless Safewright
// in Verdant Tide; bump invalidates cached decklist.
// v11 -> v12 (DEC-271): swapped Swiftfoot Boots → Hexing Squelcher in Zada
// (board-approved); bump invalidates cached decklist.
// v12 -> v13 (DEC-280): four Witherbloom Balance swaps (Hidden Stockpile →
// Yawgmoth; Emeritus → Parallel Lives; Reclamation Sage → Bastion of
// Remembrance; Foulmire Knight → Reassembling Skeleton).
// v13 -> v14 (DEC-281): five Quill of Casualties swaps (Karmic Guide →
// Teysa Karlov; Fellwar Stone → Deadly Dispute; Cruel Celebrant → Dark
// Prophecy; Grim Tutor → Plumb the Forbidden; Generous Gift → Teferi's
// Protection); bracket 3 → 4 (4 GCs now).
// v14 -> v15 (DEC-281 follow-up): swap Teferi's Protection → Clever
// Concealment (instant convoke phase-out); non-GC so bracket reverts 4 → 3.
// v19 -> v20 (DEC-287 Verdant Tide swaps 2026-05-19): force-invalidate after
// Hunter's Talent/Fierce Empath -> Beastmaster Ascension/Unnatural Growth swap.
// v20 -> v21 (DEC-287 follow-up 2026-05-19): reverse Beastmaster Ascension
// (deck not combat-attack-heavy) -> Llanowar Tribe (sustained GGG + 3/3 body).
// v21 -> v22 (DEC-290 2026-05-21): Hidden Legion deck added (slot 12); r7-r10
// swaps incl. Hatchery Sliver + Thrumming Hivepool + Stinging Study + Patriarch's Bidding.
// v22 -> v23 (DEC-293 2026-05-24): Superfriends Esika deck added; Genesis Protocol removed.
// v23 -> v24 (DEC-293 follow-up 2026-05-24): Superfriends Esika swap Vraska Relic Seeker -> Leyline of the Guildpact.
// v24 -> v25 (DEC-293 follow-up 2026-05-24): walker protection swap (Magistrate's Scepter + Innkeeper's Talent -> Sphere of Safety + Heroic Intervention).
// v25 -> v26 (DEC-293 follow-up 2026-05-24): force-invalidate so deployed UI picks up the latest superfriends-esika deck.json + simulation.json immediately.
// v26 -> v27 (DEC-297 2026-05-26): "brewing" deck status added; superfriends-esika flipped to brewing.
// v27 -> v28 (DEC-297 follow-up 2026-05-26): brewing badge added to Codex + Scrying surfaces.
// v28 -> v29 (DEC-299 2026-05-27): Aziza, Mage Tower Captain (Mage Tower Brigade) deck added at slot 13 (right before first brewing entry per catalog convention); ships with simulation.json + metrics.
// v29 -> v30 (DEC-299 follow-up 2026-05-27): Aziza simulation.json regenerated via export_simulation_results.py with proper schema (deckHealthScore, goldfish, reliabilityMetrics) so Compare tab populates.
// v30 -> v31 (DEC-299 follow-up 2026-05-27): Zada (Hedron Storm) simulation.json finally written — new mana_simulation_zada_hedron_grinder.py + export_zada() wired into the pipeline; Compare row populates now.
// v31 -> v32 (DEC-299 v8 2026-05-27): Aziza Roaming Throne -> Wedding Announcement (board feedback: €33 narrow swap to €3-5 saga with anthem+draw+tokens); sim regenerated.
// v32 -> v33 (DEC-303 v9 2026-05-27): Aziza aggression pass — 7 swaps (Reforge→Imperial Recruiter, Idol→Ranger-Captain, Mentor of the Meek→Mother of Runes, Increasing Devotion→Empty the Warrens, Hour of Reckoning→Intangible Virtue, Big Score→Guttersnipe, Wrenn's Resolve→Jeska's Will), winConditions[] block added (unlocks combo lethal in sim — was reporting 0%, now 23.6% by T6 / 28.9% by T7), strategyOverview rewritten to drop 20 stale card refs. GC count 2→3, curve 2.9→2.5.
// v33 -> v34 (DEC-306 v10 2026-05-28): Aziza Magus of the Wheel → Flashback ({R} Instant, SOS). 1-mana yard recursion replaces narrow creature hand-refill; Aziza-copyable, fires Storm-Kiln Magecraft on both cast and copy, replays X-spell go-wide bombs (Empty the Warrens / Secure the Wastes / Forth Eorlingas! / Grand Crescendo) and Jeska's Will. New Aziza+Flashback+Storm-Kiln synergy entry, Card Advantage→Spell-Copy & Spellslinger Payoffs category move, v10 sources entry documenting cut rationale.
// v34 -> v35 (DEC-311 2026-05-29): metrics.json now ships a derived win_turn { best, typical, contested } triple surfaced on the Vitals card; force-invalidate so returning users see the new readout.
// v35 -> v36 (DEC-318 2026-06-01): new brewing deck "Calculated Infinity" (Zimone, Infinite Analyst). Force-invalidate so returning users see the new index entry.
// v36 -> v37 (DEC-318 2026-06-01 post-audit): Calculated Infinity board-approved swap +Hullbreaker Horror / -Paradox Surveyor.
// v37 -> v38 (DEC-327/DEC-329 2026-06-03): Mutant Multiplication board-approved swap +Kutzil, Malamet Exemplar / -Basalt Monolith.
// v38 -> v39 (DEC-331 2026-06-05): Calculated Infinity graduates from brewing — status removed and entry reordered above brewing decks in index.json.
// v39 -> v40 (DEC-332 2026-06-05): Calculated Infinity simulation.json finally written (new mana_simulation_calculated_infinity.py + export_calculated_infinity() wired in); force-invalidate so Compare tab populates for returning users.
// v40 -> v41 (DEC-331 2026-06-05 board-approved mana-base rebalance): Calculated Infinity drops LD (Strip Mine, Wasteland) + 5 fetches, adds Forest, 2× Island, Halimar Depths, Simic Growth Chamber, Path of Ancestry, Llanowar Reborn. Sim + metrics regenerated.
// v41 -> v42 (DEC-331 2026-06-05 board-approved X-density add): Calculated Infinity +Pull from Tomorrow / -Mystic Remora.
// v42 -> v43 (DEC-331 2026-06-05 board-approved ownership swap): Calculated Infinity Llanowar Elves -> Fyndhorn Elves (strict functional reprint).
// v43 -> v44 (DEC-331 2026-06-05 illegal-land fix): Calculated Infinity -Lush Portico (Forest/Plains, illegal in {U}{G} CI) / +Flooded Grove (filter dual). Metrics global 85 -> 86, mana 73 -> 74.
// v44 -> v45 (DEC-334 2026-06-15): tokens[] computed for 8 decks that shipped without it (Witherbloom Balance, Quill of Casualties, Hedron Storm, Pyre & Panic, Hidden Legion, Mage Tower Brigade, Calculated Infinity, Esika's Council); force-invalidate so returning users see the Tokens section.
// v45 -> v46 (DEC-334 2026-06-15 board catch): drop false-positive "Shadows Over Innistrad Checklist 2" marker from Quill of Casualties (checklist printing artifact misread as a marker; compute_tokens.py filter now excludes any "...Checklist..." name, not just trailing "Checklist").
// v46 -> v47 (DEC-334 2026-06-15 board catch): add Hanweir's 3/2 Eldrazi Horror token to Pyre & Panic; compute_tokens.py now harvests meld-result tokens (one hop past the meld pieces) when every meld piece is in the deck.
// v47 -> v48 (DEC-336 2026-06-15): new brewing deck "Hivebound Cascade" (The First Sliver, 5C Sliver tribal cascade) added at the brewing-group tail of index.json; ships with deck.json + tokens[] + metrics. Force-invalidate so returning users see the new entry.
// v48 -> v49 (DEC-337 2026-06-15): Hivebound Cascade bespoke Monte Carlo simulation.json (5C no-fetch manabase); metrics refreshed (confidence margin 15 -> 5, win-turn triple populated). Force-invalidate so returning users see the simulation-backed Compare numbers.
// v49 -> v50 (DEC-347 2026-06-22): catalog changes — Calculated Infinity marked brewing (moved to brewing group); Mutant Multiplication deck removed entirely. Force-invalidate so returning users see the updated catalog.
// v50 -> v51 (DEC-347 2026-06-22): new brewing deck "Stampede Acres" (Baylen, the Haymaker — Naya tokens go-wide) added at the brewing-group tail; ships with deck.json + tokens[] + candidates + metrics (global 83). Force-invalidate so returning users see the new entry.
// v51 -> v52 (DEC-347 2026-06-22): Stampede Acres bespoke Monte Carlo simulation.json (new mana_simulation_stampede_acres.py + export_stampede_acres wired in); metrics refreshed (confidence margin 15 -> 8, win-turn triple populated, Baylen median cast T3). Force-invalidate so Compare populates the simulation-backed numbers.
// v52 -> v53 (DEC-347 2026-06-22): project-wide MDFC policy fix. Display now buckets by the FRONT (non-land) face (classifyTypeLine split on // — Hagra Mauling / Valakut Awakening move from Lands to Instants). Metrics use front-face land detection so transform DFCs (Ojer Taq) count as their cast face, modal spell//land MDFCs stay 0.5 land + 0.5 spell, Pathways/Westvale stay full lands. Data fixes: Hagra role land->removal-spot + type (eternal-harvest/silverquill/witherbloom), Valakut type (zada), removed erroneous is_mdfc_land on Needleverge Pathway (aziza) + Hanweir Battlements (pyre). Metrics regenerated for the 7 affected decks.
// v53 -> v54 (DEC-347 2026-06-22): board renamed the new Naya tokens deck "Stampede Acres" -> "Field of Blades" (subtitle "Every Acre an Army"); id stays stampede-acres. Force-invalidate so the catalog/guide show the new name.
// v54 -> v55 (DEC-347 2026-06-22): Field of Blades graduates from brewing — status removed from deck.json + index.json, entry reordered above the brewing group (board is assembling it). Now appears in Shopping. Force-invalidate so returning users see it as a production deck.
// v55 -> v56 (DEC-347 2026-06-22): Field of Blades board-approved swap -Ivy Lane Denizen / +Mother of Runes (Ivy Lane was a redundant combo piece — Scurry Oak still goes infinite with Rosie Cotton; Mother protects the engine). Combo win-condition/synergy refs updated to Scurry Oak + Rosie Cotton; candidates + metrics + sim regenerated (global 81 -> 83).
// v56 -> v57 (DEC-347 2026-06-22): Field of Blades board-approved swap -Heroic Intervention -Skyclave Apparition / +Scute Swarm +Pest Infestation (two unconditional X/landfall token producers; Pest also doubles as artifact/enchant removal). tokens[] Illusion->Pest; candidates + metrics (global 83->81, traded interaction for producers) + sim regenerated.
// v57 -> v58 (DEC-347 2026-06-22): Field of Blades mana-base rebalance — basics 5F/4P/4M -> 5F/6P/2M to match the white-heavy pip demand (W 52% / G 30% / R 18%; lands were an even 21/21/21). White sources 21->23, red 21->19. Metrics + sim regenerated.
// v58 -> v59 (DEC-347 2026-06-22): Field of Blades basics fine-tune 5F/6P/2M -> 4F/7P/2M (board split-the-difference vs Archidekt's heavier Plains rec). White sources 23->24; green still dork-backed. Metrics + sim regenerated.
// v59 -> v60 (DEC-347 2026-06-22): Field of Blades board-approved swaps -Ojer Taq -Jetmir / +Carrot Cake +Worldly Tutor (cut a redundant 6-mana tripler + a win-more anthem for a cheap token/scry/life smoother and a {G} creature tutor that fetches Seedborn/Craterhoof/combo pieces). GCs 5->6. tokens[] +Rabbit; metrics (81->83, lower curve + consistency) + sim regenerated.
// v60 -> v61 (DEC-347 2026-06-23): Field of Blades nonbasic color fix -Castle Embereth -Rogue's Passage / +Eiganjo (W + removal channel) +Wooded Bastion (G/W filter dual). Shifts the red-skewed nonbasics toward white (nonbasic W17/R17 -> W19/R16; total W24/R19 -> W26/R18) to match the W52/R18/G30 pip demand. Metrics + sim regenerated.
// v61 -> v62 (DEC-347 2026-06-23): Field of Blades board-approved swaps -Mentor of the Meek -Bennie Bracks / +Enduring Innocence +Sylvan Library (Enduring = free power<=2 draw + lifelink + resilient enchantment recursion; Sylvan = premium top-deck selection) AND lands -Den of the Bugbear -1 Mountain / +Windswept Heath +Prismatic Vista (two fetches: landfall double-dips, thinning, Sylvan shuffle synergy). 99/38 lands held; GCs stay 6. Metrics + sim regenerated.
// v62 -> v63 (DEC-347 2026-06-23): Field of Blades board-approved swap -1 Plains / +Turbulent Steppe (RW dual, Mountain Plains types; untapped once opponents control 8+ lands ~T3 in a pod). Adds a red source back (16->17, easing Kiki's RRR) without costing white, and is fetchable by Windswept Heath. Basics 4F/6P/1M; 99/38 held. Metrics + sim regenerated.
// v63 -> v64 (DEC-351 2026-06-24): new brewing deck "Exponential Growth" — Zimone, Infinite Analyst +1/+1 counters / Hydra go-big (2nd Zimone build, distinct from Calculated Infinity). Owned-pool constraint build: 11 strategy-specific buys, rest owned/generic.
// v64 -> v65 (DEC-351 2026-06-24): Exponential Growth protection pass — +Repulsive Mutation +Heroic Intervention / -Kinetic Ooze -Altered Ego (protection 2->4, buys 11->12). deck.json/sim/metrics refreshed.
// v65 -> v66 (DEC-351 2026-06-24): promote Exponential Growth brewing -> non-brewing (status removed, moved into production group). Now appears in Shopping/cardAtlas.
// v66 -> v67 (DEC-351 2026-06-24): Exponential Growth tuning — +Strength of the Tajuru +Wan Shi Tong +Valgavoth's Onslaught +Fabled Passage / -Open the Way -Nature's Rhythm -Biomass Mutation -1 Forest. 15 buys (== original ceiling); X-density held at 22; sim/metrics refreshed.
// v67 -> v68 (DEC-351 2026-06-24): Exponential Growth +The Great Henge / -Wildwood Scourge (board-approved 16th buy — card-advantage engine fills the recurring draw gap). 16 buys; sim 81.0 (A); metrics refreshed.
// v68 -> v69 (DEC-351 2026-06-25): Exponential Growth green-mana fix — basics 9F/6I -> 12F/4I, -Arch of Orazca / +1 Forest (Archidekt flagged 70% green demand vs 47% green production). Green-screw T3 ~15% (was higher); 37 lands held, 0 buys.
// v69 -> v70 (DEC-351 2026-06-25): Exponential Growth -Reliquary Tower / +1 Forest (12F->13F). Colorless->green swap: green-screw 15%->13.5% T3 with blue unchanged (~29%); manaReliability 71->71.5, sim 81.3 (A). Strict mana improvement, 0 buys.
// v70 -> v71 (DEC-351 2026-06-25): Exponential Growth -Rapid Hybridization / +Repeal (flexible X-spell cantrip over redundant creature-removal). Kept Beast Within as catch-all; declined Syncopate (counter-saturation). X-density 21->22; sim 81.3 (A); 17 strategic buys.
// v71 -> v72 (DEC-356 2026-06-25): Exponential Growth +Terrasymbiosis / -Cultivate. Counter->card draw engine (wrath-resilient) over redundant ramp (Kodama's Reach retains the identical tapped-fetch effect); ramp was the only over-target role. global 71; sim + candidate pool refreshed.
// v72 -> v73 (DEC-356 2026-06-25): Exponential Growth +Fierce Guardianship / -An Offer You Can't Refuse. Free noncreature counter with Zimone out (the deck's normal state); drops An Offer's 2-Treasure donation. gameChangers 1->2 (B4-legal). global 71->72; counter count unchanged.
// v73 -> v74 (DEC-358 2026-06-26): Field of Blades -Kiki-Jiki/-Zealous Conscripts/-Dictate of Heliod +Cori-Steel Cutter/+Frontline Rush/+Aligned Heart. Cut the backup combo + lowest-synergy anthem for on-theme token engines. Inevitability intact (Scurry+Rosie, Halo Fountain, Craterhoof). gameChangers unchanged at 6; global 84; strategy-ceiling ok.
// v74 -> v75 (DEC-359 2026-06-29): Exponential Growth +Turbulent Wilderness / -1 Forest (13->12). Fetchable G/U dual (Forest Island types) untapped from ~turn 3 in a pod; manabase polish, land count + colors unchanged.
// v75 -> v76 (DEC-359 2026-06-29): Exponential Growth +Mind into Matter / -Stroke of Genius. GU X-sorcery (draw X + free permanent) — Zimone trigger + copied by Unbound Flourishing; board cut Stroke over Pull after a wash-level economy comparison.
// v76 -> v77 (DEC-359 2026-06-29): Exponential Growth +Overflowing Basin / -Tangled Islet. GU dual that enters untapped (net +1 mana via {1},{T}: GU); trims a tapland per B4 manabase philosophy. Land count + colors unchanged.
// v77 -> v78 (DEC-359 2026-06-29): Exponential Growth +Owlin Spiralmancer / -Pathbreaker Ibex. {3}{U} flyer copies first X-spell each turn (any type) — extends copy engine to X-creature Hydras Unbound Flourishing can't; board cut Ibex (no counter synergy) over Master Biomancer.
// v78 -> v79 (DEC-359 2026-06-29): Exponential Growth +Nev, the Practical Dean +Lattice Library / -Warden of the Grove -Master Biomancer. Nev = team trample for countered creatures; Lattice = wipe-proof Fractal engine (resilience 54->57). Metrics-verified (worktree): global flat 72, interaction held 111.
// v84 -> v85 (DEC-367 2026-07-01): The White Forge ETB/LTB assessment 7-for-7. IN Tezzeret Cruel Captain, Ultron Artificial Malevolence, Haliya Guided by Light, White Auracite, Lembas, Aang Airbending Master, Portal to Phyrexia / OUT Mycosynth Wellspring, Mind Stone, Reprieve, Nexus of Becoming, Airbender Ascension, Ao the Dawn Sky, The Eternal Wanderer. Deepens Gandalf-doubled ETB axis + adds Aang as the blink "leave-without-dying" payoff; trims wipe-glut 5->4, keeps Wurmcoil. GC unchanged (6); deck.json/candidates/metrics/sim refreshed (health B/74.5).
// v85 -> v86 (DEC-367 2026-07-01): The White Forge manabase pass — +3 Plains (33->36 lands) / -Basalt Monolith (net-0 without an untapper, colourless), -Jhoira's Familiar (weakest cost reducer), -Urza's Ruinous Blast (per board wipe eval: most self-damaging in an artifact deck; kept engine-safe Avatar's Wrath). manaReliability 62.1->67.3, health B/74.5->A/76.3, 0-1 land keeps 10.3%->7.1%.
// v86 -> v87 (DEC-389/DEC-390 2026-07-02): metrics.json regenerated for all 18 decks with global_health_normalized (fixed-B3 ruler); Compare gains Vitals + Norm. columns reading it. Force-invalidate so returning users refetch metrics and the Norm. column populates.
// v87 -> v88 (DEC-373 2026-07-03): Hidden Legion consistency retune. OUT Conspicuous Snoop/Kiki-Jiki/Impact Tremors (phantom combo, 1.4% assembly @T7), Irregular Cohort, Universal Automaton / IN Flooded Strand, Fabled Passage (37->39 lands, Karsten U/R closed), Kindred Discovery, Esper Sentinel (draw 6->8, median online T5->T2), Graveshifter (recursion gap closed). GC unchanged (3); global 85->93, manabase 64->85, sim health 65.8->67.5.
const STORAGE_PREFIX = 'gv1-deck-data-v88:';
// TTL relaxed from 24h to 1h (DEC-226): new decks land more frequently than
// once a day; the cache is still useful for fast navigation within a session
// without making returning users wait a full day to see new content.
const TTL_MS = 60 * 60 * 1000;

interface PersistedEnvelope<T> {
  fetchedAt: number;
  payload: T;
}

interface LoaderDeps {
  fetchImpl?: typeof fetch;
  storage?: Storage | null;
  now?: () => number;
}

function defaultStorage(): Storage | null {
  if (typeof window !== 'undefined' && window.localStorage) return window.localStorage;
  return null;
}

export interface DeckLoader {
  loadIndex(): Promise<RawDeckIndex>;
  loadCardMetadata(): Promise<RawCardMetadata>;
  loadDeck(id: string): Promise<RawDeckBundle | null>;
  loadAll(): Promise<RawDeckBundle[]>;
  /** Test-only: drop in-memory state. */
  _reset(): void;
}

export function createDeckLoader(deps: LoaderDeps = {}): DeckLoader {
  const fetchImpl = deps.fetchImpl ?? (typeof fetch !== 'undefined' ? fetch : undefined);
  const explicitStorage = deps.storage;
  const resolveStorage = (): Storage | null =>
    explicitStorage === undefined ? defaultStorage() : explicitStorage;
  const now = deps.now ?? (() => Date.now());

  const indexInflight = new Map<string, Promise<RawDeckIndex>>();
  const metadataInflight = new Map<string, Promise<RawCardMetadata>>();
  const deckInflight = new Map<string, Promise<RawDeckBundle | null>>();
  let memIndex: RawDeckIndex | null = null;
  let memCardMetadata: RawCardMetadata | null = null;
  const memDecks = new Map<string, RawDeckBundle>();

  function readPersisted<T>(key: string): T | null {
    const storage = resolveStorage();
    if (!storage) return null;
    try {
      const raw = storage.getItem(STORAGE_PREFIX + key);
      if (!raw) return null;
      const env = JSON.parse(raw) as PersistedEnvelope<T>;
      if (!env.fetchedAt || now() - env.fetchedAt > TTL_MS) {
        storage.removeItem(STORAGE_PREFIX + key);
        return null;
      }
      return env.payload;
    } catch {
      return null;
    }
  }

  function writePersisted<T>(key: string, payload: T): void {
    const storage = resolveStorage();
    if (!storage) return;
    try {
      const env: PersistedEnvelope<T> = { fetchedAt: now(), payload };
      storage.setItem(STORAGE_PREFIX + key, JSON.stringify(env));
    } catch {
      // Quota exceeded — skip persistence; in-memory cache still works.
    }
  }

  async function fetchJson<T>(url: string): Promise<T | null> {
    if (!fetchImpl) throw new Error('fetch unavailable');
    const r = await fetchImpl(url);
    if (r.status === 404) return null;
    if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
    return (await r.json()) as T;
  }

  async function loadIndex(): Promise<RawDeckIndex> {
    if (memIndex) return memIndex;
    const cached = readPersisted<RawDeckIndex>('index');
    if (cached) {
      memIndex = cached;
      return cached;
    }
    const existing = indexInflight.get('index');
    if (existing) return existing;
    const promise = (async () => {
      const data = await fetchJson<RawDeckIndex>('/data/index.json');
      if (!data) throw new Error('index.json missing');
      memIndex = data;
      writePersisted('index', data);
      return data;
    })().finally(() => indexInflight.delete('index'));
    indexInflight.set('index', promise);
    return promise;
  }

  async function loadCardMetadata(): Promise<RawCardMetadata> {
    if (memCardMetadata) return memCardMetadata;
    const cached = readPersisted<RawCardMetadata>('card-metadata');
    if (cached) {
      memCardMetadata = cached;
      return cached;
    }
    const existing = metadataInflight.get('card-metadata');
    if (existing) return existing;
    const promise = (async () => {
      const data = await fetchJson<RawCardMetadata>('/data/card-metadata.json');
      const metadata = data ?? {};
      memCardMetadata = metadata;
      writePersisted('card-metadata', metadata);
      return metadata;
    })().finally(() => metadataInflight.delete('card-metadata'));
    metadataInflight.set('card-metadata', promise);
    return promise;
  }

  function withoutCardMetadata(bundle: RawDeckBundle): RawDeckBundle {
    const persistable = { ...bundle };
    delete persistable.cardMetadata;
    return persistable;
  }

  async function attachCardMetadata(bundle: RawDeckBundle): Promise<RawDeckBundle> {
    const cardMetadata = await loadCardMetadata();
    return { ...bundle, cardMetadata };
  }

  async function fetchDeckBundle(entry: RawDeckIndexEntry): Promise<RawDeckBundle> {
    const id = entry.id;
    const base = `/data/commanders/${id}`;
    const [deck, sim, metrics, candidates, cardMetadata] = await Promise.all([
      fetchJson<RawDeck>(`${base}/deck.json`),
      fetchJson<RawSimulation>(`${base}/simulation.json`),
      fetchJson<RawMetrics>(`${base}/metrics.json`),
      fetchJson<RawCandidates>(`${base}/candidates.json`),
      loadCardMetadata(),
    ]);
    if (!deck) throw new Error(`deck.json missing for ${id}`);
    return {
      id,
      index: entry,
      deck,
      sim: sim ?? null,
      metrics: metrics ?? null,
      candidates: candidates ?? null,
      cardMetadata,
    };
  }

  async function loadDeck(id: string): Promise<RawDeckBundle | null> {
    const cachedMem = memDecks.get(id);
    if (cachedMem) return cachedMem;
    const persisted = readPersisted<RawDeckBundle>(`deck:${id}`);
    if (persisted) {
      const withMetadata = await attachCardMetadata(persisted);
      memDecks.set(id, withMetadata);
      return withMetadata;
    }
    const existing = deckInflight.get(id);
    if (existing) return existing;

    const promise = (async (): Promise<RawDeckBundle | null> => {
      const index = await loadIndex();
      const entry = index.commanders.find((c) => c.id === id);
      if (!entry) return null;
      const bundle = await fetchDeckBundle(entry);
      memDecks.set(id, bundle);
      writePersisted(`deck:${id}`, withoutCardMetadata(bundle));
      return bundle;
    })().finally(() => deckInflight.delete(id));

    deckInflight.set(id, promise);
    return promise;
  }

  async function loadAll(): Promise<RawDeckBundle[]> {
    const index = await loadIndex();
    const bundles = await Promise.all(index.commanders.map((c) => loadDeck(c.id)));
    return bundles.filter((b): b is RawDeckBundle => !!b);
  }

  function _reset(): void {
    memIndex = null;
    memCardMetadata = null;
    memDecks.clear();
    indexInflight.clear();
    metadataInflight.clear();
    deckInflight.clear();
  }

  return { loadIndex, loadCardMetadata, loadDeck, loadAll, _reset };
}

export const deckLoader: DeckLoader = createDeckLoader();
