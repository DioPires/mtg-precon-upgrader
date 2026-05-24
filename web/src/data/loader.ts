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
const STORAGE_PREFIX = 'gv1-deck-data-v25:';
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
