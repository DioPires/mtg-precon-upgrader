// The one module that sends requests to api.scryfall.com (DEC-1102 and DEC-1131,
// design D of DEC-1072).
//
// Scryfall allows 2 requests a second on /cards/named, /cards/search,
// /cards/random and /cards/collection, and 10 a second on its other methods. A
// 429 limits the caller for 30 s, and a caller that ignores 429s can be banned.
// Scryfall's 429 carries no CORS header, so the browser shows it to the app as a
// fetch that rejects.
//
// Bucket 1 ('lookup': /cards/collection). The card cache sends every card
// lookup as one POST of up to 75 names (cardCache.ts). A JSON POST from the
// browser goes after a CORS preflight (OPTIONS), and nobody knows whether
// Scryfall counts the preflight, so each POST counts as two starts. A request
// starts 1,200 ms or more after the last start, and only after the last answer
// has arrived: no 1 s window then holds more than 2 starts. Inside a tab the
// spacing runs on performance.now(), so a step of the wall clock does not
// shorten it. The tabs of one origin share bucket 1: navigator.locks lets one
// tab send at a time, and localStorage holds the last start in wall time.
// A caller that stores the answer (next() with `settle`) keeps the lock until
// it has stored it, so the next tab's turn finds those names in storage
// (DEC-1153; the hand-over below says when). Such a caller gets the answer
// whole: the limiter reads its body inside the request's 20 s. The lock frees
// at the latest 20 s after the request's start plus what the hand-over has
// left of its allowance: 21 s at most. These bounds, and the hand-over's 1 s
// below, are timer deadlines: a browser call that blocks the thread, or a
// suspended tab, stretches them. Without navigator.locks (jsdom) the bucket
// holds in the one tab.
//
// The hand-over. Chrome and WebKit bring one tab's localStorage writes to
// another tab late, in the order they were made (measured 2026-11-24; HTML does
// not promise it), and a lock that the writer frees in between does not wait
// for them. drain() reads the last start and the stop before it asks for the
// lock and again inside it; the checks inside the lock (the last start, the
// stop, the stored names) could read storage as it was before the last turn
// (the two-tab case of web/tests/dec1153-card-data-followups.spec.ts, as it
// stood on 2026-11-24, sent names twice in 11 of 20 runs). So each turn of
// bucket 1 that sent a request ends with a new random token, written in
// localStorage after the turn's other writes there (the last start, the stop,
// and the card writes of a `settle` that finished), then in IndexedDB, whose
// completed writes every tab reads. The next holder reads the token from
// IndexedDB and waits until its own localStorage shows exactly that token
// before its checks.
//
// What it promises: while the hand-over is on in both tabs, the names that one
// holder's batch stored before the turn wrote its mark are found by the next
// holder's batch when the mark arrives within the allowance. A mark that does
// not come costs the turn that wait, and the turn then reads storage as it
// finds it. Three paths of the card cache can still send a stored name again
// (web/README.md, "The hand-over"). In normal use the wait never starts, and a
// turn costs a few milliseconds.
//
// The allowance. HANDOVER_WAIT_MS bounds the hand-over's work in one turn, all
// together: the read and the wait at its start, the write at its end; the
// request is not counted. The allowance runs from before the first call; each
// call's timer is armed before the call, so time that a call spends blocked
// counts, and a call that settles after it counts as late. When the mark came,
// the end write gets what is left. When it did not, nobody waits for the end
// write: the turn issues it only on the connection that the read used, which
// is open, so the write creates its read-write transaction before the lock
// frees. IndexedDB's specification makes a later transaction on the same
// store, on any connection, wait until an earlier read-write transaction has
// finished, so the next holder's read comes after that write. Not established:
// that the write's commit succeeds (its failure turns the hand-over off). If
// that connection has closed (another tab upgraded or deleted the database),
// the turn writes no token and the hand-over goes off.
//
// Failure. A read or open of IndexedDB, or a write that the turn waits for,
// that fails or runs out of the allowance turns the hand-over off for the page:
// no more IndexedDB, no more waits, the bucket as without it. A write that
// nobody waits for turns it off only when it fails. Going off aborts a write
// that nobody waits for, and closes the connection, also one that an open
// still pending brings later. A read already issued runs on its own signal to
// its own deadline, and its turn then ignores its result: a turn whose read
// was waiting when the hand-over went off does not wait for the mark. An abort
// stops a transaction that has not begun to commit; one that has begun can
// still land, and IndexedDB's order keeps it ahead of any transaction begun
// after it. An IndexedDB that the browser denies, or a localStorage whose mark
// cannot be read, gives a turn no hand-over. When localStorage refuses the
// mark (a full quota), whether or not the last turn's mark came in time, the
// turn writes no token and the hand-over goes off: IndexedDB keeps the last
// turn's token, which this tab may never show.
//
// Limits. (1) If the allowance runs out during a call that blocks the thread,
// the turn waits for that call to return, and later blocking work in the same
// turn can delay the lock's release further. (2) A `settle` still storing when the
// 20 s request timeout frees the turn writes its cards after the mark: the next
// holder can send those names again, one duplicate request. (3) A mark that
// arrives in the last milliseconds of the allowance leaves the end write little
// time: whether the page's hand-over goes off depends on how long that write
// takes. After that switch-off IndexedDB can hold the old token, or the new one
// (a write that committed before its late completion was noticed). When the old
// token remains, each later turn of the other tab waits its full allowance,
// until a turn that sends a request publishes a new token (a turn with nothing
// to send publishes nothing); while the new mark still lags there, a turn reads
// storage at once and can resend that turn's names.
//
// Bucket 2 ('autocomplete': /cards/autocomplete). 120 ms between starts.
//
// The stop. A 429, a fetch to api.scryfall.com that rejects, or a request with no
// answer after 20 s (the limiter aborts it) stops both buckets for 30 s; for a
// caller with `settle`, a body that has not ended is no answer (DEC-1188). The
// request that met it stays first in its bucket, and nothing goes. When the stop
// ends, one request goes. If that one fails too, the stop doubles (60 s, 120 s,
// 240 s), up to 300 s. Any other answer to it ends the stop and resets it to
// 30 s. A fetch that its caller aborts is no failure.
//
// The stop record: its end, its length and its number. The record stays after
// the end until a request succeeds, so the next failure doubles the stop; a
// record that ended more than 300 s ago counts as no record. A request notes the
// record's number when it starts, and it can double or end only that stop: a
// request that was out when another one started the stop changes nothing. A
// clock that went back cannot stretch a stop past now plus its length. The
// record lives in localStorage, so a reload and a second tab obey it; without
// storage, or when storage refuses the write, it lives in memory.

export const SCRYFALL_API = 'https://api.scryfall.com';
export const COLLECTION_URL = `${SCRYFALL_API}/cards/collection`;
export const LOOKUP_SPACING_MS = 1_200;
export const AUTOCOMPLETE_SPACING_MS = 120;
export const FIRST_STOP_MS = 30_000;
export const MAX_STOP_MS = 300_000;
export const REQUEST_TIMEOUT_MS = 20_000;
export const STOP_KEY = 'grimoire-scryfall-stop';
export const LAST_START_KEY = 'grimoire-scryfall-last-start';
const LOCK_NAME = 'grimoire-scryfall-bucket-1';
/** The token of the last bucket 1 turn, in localStorage (the hand-over). */
export const TURN_KEY = 'grimoire-scryfall-turn';
/** The most time that the hand-over adds to one turn of bucket 1, its read, wait and write together. */
export const HANDOVER_WAIT_MS = 1_000;
const TURN_DB = 'grimoire-scryfall';
const TURN_STORE = 'turn';
const TURN_ID = 'last';

export type Bucket = 'lookup' | 'autocomplete';

/** One request to api.scryfall.com: a GET by default. */
export interface ApiRequest {
  url: string;
  method?: 'GET' | 'POST';
  headers?: Record<string, string>;
  body?: string;
}

/** The lookup of up to 75 cards by name: one POST to /cards/collection. */
export function collectionRequest(names: string[]): ApiRequest {
  return {
    url: COLLECTION_URL,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ identifiers: names.map((name) => ({ name })) }),
  };
}

export function autocompleteUrl(query: string): string {
  return `${SCRYFALL_API}/cards/autocomplete?q=${encodeURIComponent(query)}`;
}

function isApiUrl(url: string): boolean {
  try {
    return new URL(url).origin === SCRYFALL_API;
  } catch {
    return false;
  }
}

export function bucketOf(url: string): Bucket {
  return new URL(url).pathname === '/cards/autocomplete' ? 'autocomplete' : 'lookup';
}

/** A stop: its end (epoch ms), its length and its number. The record stays after the end until a request succeeds. */
export interface Stop {
  until: number;
  ms: number;
  n: number;
}

export interface SendOptions {
  /** Aborts the request, also while it waits for its turn. An abort is no failure and starts no stop. */
  signal?: AbortSignal;
  /** Puts the request before the others that wait in its bucket. */
  first?: boolean;
  /** fetch() only: the method, the headers and the body of the request. */
  method?: ApiRequest['method'];
  headers?: ApiRequest['headers'];
  body?: ApiRequest['body'];
  /**
   * next() only: runs with the answer, and the call resolves after it. Bucket 1
   * holds its lock while it runs, so the caller stores the answer before another
   * tab takes its turn (DEC-1153). The lock frees when it settles, or
   * REQUEST_TIMEOUT_MS after the request started, whichever comes first, and
   * then the end of the hand-over (within HANDOVER_WAIT_MS for the turn). When
   * it runs, the body of the answer has ended or has failed (DEC-1188).
   */
  settle?: (sent: Sent) => Promise<void> | void;
}

export interface Sent {
  url: string;
  response: Response;
}

export interface ScryfallLimiter {
  /** Sends one request when its bucket allows. Resolves with any answer but a 429. */
  fetch(url: string, options?: SendOptions): Promise<Response>;
  /**
   * For a caller with a queue of its own. `pick` runs once, when the turn comes,
   * and gives the request to send: a URL for a GET, or the URL with the method,
   * the headers and the body. Null gives the turn back, and the call resolves null.
   */
  next(bucket: Bucket, pick: () => string | ApiRequest | null, options?: SendOptions): Promise<Sent | null>;
  /** The end of the stop that holds now (epoch ms), or null. Read it at each render: it holds the cap. */
  stoppedUntil(): number | null;
  /** Calls `fn` with stoppedUntil() when a stop starts or ends, also when another tab starts or ends it. */
  subscribe(fn: (until: number | null) => void): () => void;
  /** Test-only: drop the waiting requests and this tab's last starts and stop. Does not touch localStorage. */
  _reset?(): void;
}

export interface LimiterDeps {
  fetchImpl?: typeof fetch;
  storage?: Storage | null;
  locks?: LockManager | null;
  /** The wall clock (epoch ms): the stop and the last start that other tabs read. */
  now?: () => number;
  /** The tab's own clock, which no step of the wall clock moves: the spacing inside the tab. */
  monotonic?: () => number;
  /** The token of the last bucket 1 turn, in a store whose completed writes every tab reads: IndexedDB by default. */
  turns?: TurnStore | null;
  /** Where this tab hears of another tab's localStorage writes (`storage` events): window by default. */
  events?: EventTarget | null;
}

/** The token of the last bucket 1 turn, in a store whose completed writes every tab reads (the hand-over). */
export interface TurnStore {
  /** The last turn's token; null before the first. */
  read(signal: AbortSignal): Promise<string | null>;
  /**
   * Resolves once the write has completed. An abort stops a write that has not
   * begun to commit; one that has begun to commit can still land. With a
   * connection open (ready()), the write begins its transaction at once.
   */
  write(token: string, signal: AbortSignal): Promise<void>;
  /** True while a connection is open, so that a write begins its transaction at once. */
  ready(): boolean;
  /** The hand-over is off: close the connection, and any that an open still pending brings. */
  close(): void;
}

/** The hand-over of one turn of bucket 1. */
interface HandoverTurn {
  store: TurnStore;
  /** Whether this tab's localStorage showed the last turn's token within the allowance. */
  markCame: boolean;
  /** What is left of HANDOVER_WAIT_MS after the start of the turn. */
  left: number;
}

interface Job {
  pick: () => string | ApiRequest | null;
  request: ApiRequest | null;
  signal?: AbortSignal;
  settle?: SendOptions['settle'];
  done: boolean;
  resolve: (sent: Sent | null) => void;
  reject: (reason: unknown) => void;
}

interface BucketState {
  name: Bucket;
  spacingMs: number;
  jobs: Job[];
  running: boolean;
  /** This tab's last start on the monotonic clock. */
  lastStart: number;
}

function defaultStorage(): Storage | null {
  try {
    if (typeof window !== 'undefined' && window.localStorage) return window.localStorage;
  } catch {
    // A browser that blocks storage throws on access.
  }
  return null;
}

function defaultLocks(): LockManager | null {
  return (typeof navigator !== 'undefined' && navigator.locks) || null;
}

function defaultMonotonic(): number {
  return typeof performance !== 'undefined' ? performance.now() : Date.now();
}

function defaultIndexedDb(): IDBFactory | null {
  try {
    if (typeof indexedDB !== 'undefined' && indexedDB) return indexedDB;
  } catch {
    // A browser that denies storage throws on access.
  }
  return null;
}

function defaultEvents(): EventTarget | null {
  return typeof window !== 'undefined' ? window : null;
}

/**
 * The turn token in IndexedDB; null where the browser has none or denies it.
 * A transaction that a tab begins after another tab's write has completed reads
 * that write, which localStorage does not promise (the hand-over). On an open
 * connection a read or write begins its transaction at once. `factory` is for
 * the tests.
 */
export function indexedDbTurns(factory: IDBFactory | null = defaultIndexedDb()): TurnStore | null {
  if (!factory) return null;
  let connection: IDBDatabase | null = null;
  let opening: Promise<IDBDatabase> | null = null;
  // Set when the hand-over goes off: an open that succeeds later is closed at once.
  let closed = false;
  const forget = (db: IDBDatabase) => {
    if (connection !== db) return;
    connection = null;
    opening = null;
  };
  const open = () =>
    (opening ??= new Promise<IDBDatabase>((resolve, reject) => {
      const request = factory.open(TURN_DB, 1);
      request.onupgradeneeded = () => {
        // An open that outlived the hand-over creates nothing.
        if (closed) request.transaction?.abort();
        else request.result.createObjectStore(TURN_STORE);
      };
      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        const db = request.result;
        if (closed) {
          db.close();
          reject(new DOMException('The hand-over is off.', 'AbortError'));
          return;
        }
        // Another tab upgrades or deletes the database: let it, and open again at the next turn.
        db.onversionchange = () => {
          db.close();
          forget(db);
        };
        // The browser closed it (site data cleared): open again at the next turn.
        db.onclose = () => forget(db);
        connection = db;
        resolve(db);
      };
    }));
  function run<T>(
    mode: IDBTransactionMode,
    signal: AbortSignal,
    use: (store: IDBObjectStore) => IDBRequest<T>,
  ): Promise<T> {
    const begin = (db: IDBDatabase) =>
      new Promise<T>((resolve, reject) => {
        // An operation that waited for the open past its time is never issued. After
        // close(), the open rejects, and a closed connection refuses transactions.
        if (signal.aborted) return reject(abortReason(signal));
        // Other tabs need the token to be visible, not flushed to disk.
        const transaction = db.transaction(TURN_STORE, mode, mode === 'readwrite' ? { durability: 'relaxed' } : undefined);
        const request = use(transaction.objectStore(TURN_STORE));
        const stop = () => {
          try {
            transaction.abort();
          } catch {
            // It has completed or begun to commit: too late to stop it.
          }
        };
        signal.addEventListener('abort', stop, { once: true });
        // A settled transaction lets go of the signal, which can live as long as the page.
        const settled = () => signal.removeEventListener('abort', stop);
        transaction.oncomplete = () => {
          settled();
          resolve(request.result);
        };
        transaction.onerror = () => {
          settled();
          reject(transaction.error);
        };
        transaction.onabort = () => {
          settled();
          reject(transaction.error ?? abortReason(signal));
        };
      });
    return connection ? begin(connection) : open().then(begin);
  }
  return {
    read: async (signal) => {
      const token = await run('readonly', signal, (store) => store.get(TURN_ID));
      return typeof token === 'string' ? token : null;
    },
    write: (token, signal) => run('readwrite', signal, (store) => store.put(token, TURN_ID)).then(() => undefined),
    ready: () => connection !== null && !closed,
    close: () => {
      closed = true;
      connection?.close();
      connection = null;
    },
  };
}

function abortReason(signal: AbortSignal): unknown {
  return signal.reason ?? new DOMException('The request was aborted.', 'AbortError');
}

/** A number that no other stop record or turn token holds. */
function randomId(): number {
  return Math.floor(Math.random() * Number.MAX_SAFE_INTEGER) + 1;
}

export function createScryfallLimiter(deps: LimiterDeps = {}): ScryfallLimiter {
  const resolveStorage = (): Storage | null =>
    deps.storage === undefined ? defaultStorage() : deps.storage;
  const resolveLocks = (): LockManager | null =>
    deps.locks === undefined ? defaultLocks() : deps.locks;
  const resolveEvents = (): EventTarget | null =>
    deps.events === undefined ? defaultEvents() : deps.events;
  // The hand-over is on until IndexedDB fails or times out once, or localStorage
  // refuses a mark; then it stays off for the page.
  let handover = true;
  // Aborted when the hand-over goes off: the signal of the write that nobody waits for.
  const off = new AbortController();
  let pageTurns: TurnStore | null | undefined;
  const resolveTurns = (): TurnStore | null => {
    if (!handover) return null;
    if (deps.turns !== undefined) return deps.turns;
    if (pageTurns === undefined) pageTurns = indexedDbTurns();
    return pageTurns;
  };
  // Resolved on each send so that a test's spy on globalThis.fetch is honoured.
  const resolveFetch = (): typeof fetch | undefined =>
    deps.fetchImpl ?? (typeof fetch !== 'undefined' ? fetch : undefined);
  const now = deps.now ?? (() => Date.now());
  const monotonic = deps.monotonic ?? defaultMonotonic;

  const buckets: Record<Bucket, BucketState> = {
    lookup: { name: 'lookup', spacingMs: LOOKUP_SPACING_MS, jobs: [], running: false, lastStart: -Infinity },
    autocomplete: {
      name: 'autocomplete',
      spacingMs: AUTOCOMPLETE_SPACING_MS,
      jobs: [],
      running: false,
      lastStart: -Infinity,
    },
  };
  let memoryStop: Stop | null = null;
  let stopInMemoryOnly = false;
  let inFlight = 0;
  let idleWaiters: Array<() => void> = [];
  // _reset() ends the loops that run; a loop that wakes after it stops.
  let generation = 0;
  const listeners = new Set<(until: number | null) => void>();
  let listeningToStorage = false;

  // ── The stop ─────────────────────────────────────────────────────────────

  /** A record that ended more than MAX_STOP_MS ago counts as no record. */
  function isOld(stop: Stop): boolean {
    return now() - stop.until > MAX_STOP_MS;
  }

  // A clock that went back must not stretch a stop past its own length. An end
  // past now + the length becomes now + the length, in memory and in storage, so
  // the next read finds it and the stop ends one length after this read. No
  // listener hears of it, so a read inside notifyListeners() cannot start
  // another; a reader that shows the end reads stoppedUntil() again.

  function readMemoryStop(): Stop | null {
    if (!memoryStop || isOld(memoryStop)) return null;
    const cap = now() + memoryStop.ms;
    if (memoryStop.until > cap) memoryStop = { ...memoryStop, until: cap };
    return memoryStop;
  }

  function readStop(): Stop | null {
    const storage = resolveStorage();
    if (!storage || stopInMemoryOnly) return readMemoryStop();
    try {
      const raw = storage.getItem(STOP_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw) as Partial<Stop> | null;
      if (typeof parsed?.until !== 'number' || typeof parsed?.ms !== 'number') return null;
      // A record from before the stop number (PR #38) is one stop, number 0.
      const stop: Stop = { until: parsed.until, ms: parsed.ms, n: typeof parsed.n === 'number' ? parsed.n : 0 };
      if (isOld(stop)) return null;
      const cap = now() + stop.ms;
      if (stop.until <= cap) return stop;
      const capped = { ...stop, until: cap };
      storeStop(capped);
      return capped;
    } catch {
      return readMemoryStop();
    }
  }

  /** Puts the stop in memory and in storage. Tells no listener. */
  function storeStop(stop: Stop | null): void {
    memoryStop = stop;
    stopInMemoryOnly = false;
    const storage = resolveStorage();
    if (storage) {
      try {
        if (stop) storage.setItem(STOP_KEY, JSON.stringify(stop));
        else storage.removeItem(STOP_KEY);
      } catch {
        // Storage full or blocked: the stop lives in memory.
        stopInMemoryOnly = true;
      }
    }
  }

  function writeStop(stop: Stop | null): void {
    storeStop(stop);
    notifyListeners();
  }

  function stoppedUntil(): number | null {
    const stop = readStop();
    return stop && stop.until > now() ? stop.until : null;
  }

  function notifyListeners(): void {
    const until = stoppedUntil();
    listeners.forEach((fn) => {
      try {
        fn(until);
      } catch {
        // A listener's error is its own.
      }
    });
  }

  /** The number of the stop record that a request sees when it starts; null for no record. */
  function stopNumber(): number | null {
    return readStop()?.n ?? null;
  }

  /** A 429, a rejected fetch or a timeout. Only the request that went after the stop it noted can double that stop. */
  function fail(noted: number | null): void {
    const prev = readStop();
    if (prev && prev.n !== noted) return;
    const ms = prev ? Math.min(prev.ms * 2, MAX_STOP_MS) : FIRST_STOP_MS;
    writeStop({ until: now() + ms, ms, n: randomId() });
  }

  /** Any other answer. It ends a stop only when it is the request that went after that stop. */
  function succeed(noted: number | null): void {
    const prev = readStop();
    if (prev && prev.n === noted) writeStop(null);
  }

  function subscribe(fn: (until: number | null) => void): () => void {
    listeners.add(fn);
    const events = resolveEvents();
    if (!listeningToStorage && events) {
      listeningToStorage = true;
      events.addEventListener('storage', (event) => {
        if ('key' in event && event.key === STOP_KEY) notifyListeners();
      });
    }
    return () => {
      listeners.delete(fn);
    };
  }

  // ── Turns ────────────────────────────────────────────────────────────────

  /** The last bucket 1 start that the tabs share (wall time), or -Infinity. */
  function sharedLastStart(): number {
    let last = -Infinity;
    try {
      const raw = resolveStorage()?.getItem(LAST_START_KEY);
      const stored = raw == null ? NaN : Number(raw);
      if (Number.isFinite(stored)) last = stored;
    } catch {
      // This tab keeps its own last start.
    }
    // A last start in the future (a clock that went back) becomes now in
    // storage, so the bucket waits one spacing after this read at most.
    const t = now();
    if (last <= t) return last;
    writeSharedLastStart(t);
    return t;
  }

  function writeSharedLastStart(at: number): void {
    try {
      resolveStorage()?.setItem(LAST_START_KEY, String(at));
    } catch {
      // This tab keeps its own last start.
    }
  }

  function markStart(bucket: BucketState): void {
    bucket.lastStart = monotonic();
    if (bucket.name === 'lookup') writeSharedLastStart(now());
  }

  /** Milliseconds until the bucket may start a request; 'busy' while the request after a stop is out. */
  function waitFor(bucket: BucketState): number | 'busy' {
    const t = now();
    const stop = readStop();
    if (stop && stop.until > t) return stop.until - t;
    if (stop && inFlight > 0) return 'busy';
    const inTab = bucket.lastStart + bucket.spacingMs - monotonic();
    const shared = bucket.name === 'lookup' ? sharedLastStart() + bucket.spacingMs - t : -Infinity;
    return Math.max(0, inTab, shared);
  }

  function sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /** The value of `work` when it settles first; null when it fails or `ms` passes first. */
  function within<T>(work: Promise<T>, ms: number): Promise<T | null> {
    let timer: ReturnType<typeof setTimeout> | undefined;
    return new Promise<T | null>((resolve) => {
      timer = setTimeout(() => resolve(null), ms);
      work.then(resolve, () => resolve(null));
    }).finally(() => clearTimeout(timer));
  }

  function idle(): Promise<void> {
    if (inFlight === 0) return Promise.resolve();
    return new Promise((resolve) => idleWaiters.push(resolve));
  }

  async function waitForTurn(bucket: BucketState): Promise<void> {
    for (;;) {
      const wait = waitFor(bucket);
      if (wait === 0) return;
      if (wait === 'busy') await idle();
      else await sleep(wait);
    }
  }

  // ── The hand-over ────────────────────────────────────────────────────────

  /** The token that this tab's localStorage shows (null for none); undefined when reading it throws. */
  function shownToken(storage: Storage): string | null | undefined {
    try {
      return storage.getItem(TURN_KEY);
    } catch {
      return undefined;
    }
  }

  /**
   * Waits until this tab's localStorage shows `token`: 'came' when it does by
   * `deadline`, 'late' when the deadline passes first, 'unreadable' when
   * reading the mark throws. The timer is armed before the first read.
   */
  function storageShows(
    token: string,
    deadline: number,
    storage: Storage,
    events: EventTarget,
  ): Promise<'came' | 'late' | 'unreadable'> {
    return new Promise((resolve) => {
      const finish = (how: 'came' | 'late' | 'unreadable') => {
        clearTimeout(timer);
        events.removeEventListener('storage', check);
        resolve(how);
      };
      // Another tab's write reaches this tab's localStorage with a `storage` event.
      const check = () => {
        const shown = shownToken(storage);
        if (shown === undefined) finish('unreadable');
        else if (monotonic() > deadline) finish('late');
        else if (shown === token) finish('came');
      };
      // Armed before the first read; finish() runs only after this line.
      const timer = setTimeout(() => finish('late'), Math.max(0, deadline - monotonic()));
      events.addEventListener('storage', check);
      check();
    });
  }

  /**
   * `op` with a signal that aborts at `deadline`: its value, or null when it
   * fails or does not settle by the deadline. The timer is armed before `op`
   * runs, and the deadline is checked again when `op` settles, so time spent
   * inside a call that blocks counts.
   */
  function bounded<T>(op: (signal: AbortSignal) => Promise<T>, deadline: number): Promise<{ value: T } | null> {
    const controller = new AbortController();
    const late = () => controller.abort(new DOMException('The hand-over ran out of time.', 'TimeoutError'));
    return new Promise((resolve) => {
      const timer = setTimeout(() => {
        late();
        resolve(null);
      }, Math.max(0, deadline - monotonic()));
      const settle = (result: { value: T } | null) => {
        clearTimeout(timer);
        if (result && monotonic() > deadline) {
          late();
          resolve(null);
        } else resolve(result);
      };
      try {
        op(controller.signal).then((value) => settle({ value }), () => settle(null));
      } catch {
        settle(null);
      }
    });
  }

  /**
   * IndexedDB failed or did not settle in time, or localStorage refused a mark:
   * no hand-over for the rest of the page's life.
   */
  function handoverOff(store: TurnStore): void {
    if (!handover) return;
    handover = false;
    // A write that nobody waits for stops, if it has not begun to commit. A read already
    // issued runs on its own signal to its own deadline, and its turn ignores its result.
    off.abort(new DOMException('The hand-over is off.', 'AbortError'));
    store.close();
  }

  /**
   * At the start of a turn: waits until this tab's localStorage shows the last
   * turn's token. Gives the store, whether the mark came in time, and what is
   * left of the turn's allowance; null without the hand-over.
   */
  async function beginTurn(): Promise<HandoverTurn | null> {
    // The allowance runs from before the first call of the hand-over (the first access to indexedDB is in resolveTurns).
    const deadline = monotonic() + HANDOVER_WAIT_MS;
    const store = resolveTurns();
    const storage = resolveStorage();
    const events = resolveEvents();
    if (!store || !storage || !events) return null;
    // A localStorage whose mark cannot be read gives the turn no hand-over.
    if (shownToken(storage) === undefined) return null;
    const last = await bounded((signal) => store.read(signal), deadline);
    if (!last) {
      handoverOff(store);
      return null;
    }
    // The hand-over went off while the read waited (an earlier write failed): no wait.
    if (!handover) return null;
    const mark = last.value === null ? 'came' : await storageShows(last.value, deadline, storage, events);
    if (mark === 'unreadable') return null;
    return { store, markCame: mark === 'came', left: Math.max(0, deadline - monotonic()) };
  }

  /**
   * At the end of a turn that sent a request: a new token, last of the turn's
   * localStorage writes, then in the store, within what is left of the turn's
   * allowance (the request is not counted).
   */
  async function endTurn(turn: HandoverTurn | null, sent: boolean): Promise<void> {
    // What is left of the allowance runs from before the first call of the turn's end.
    const deadline = monotonic() + (turn?.left ?? 0);
    const storage = resolveStorage();
    if (!turn || !sent || !handover || !storage) return;
    // When the mark did not come, nobody waits for the write, which must begin on
    // the connection that the read used. If that one has closed, no token.
    if (!turn.markCame && !turn.store.ready()) {
      handoverOff(turn.store);
      return;
    }
    const token = String(randomId());
    try {
      storage.setItem(TURN_KEY, token);
    } catch {
      // No mark, so no token: the store keeps the last turn's, which this tab may never
      // show again (a full quota), so every later turn would wait its whole allowance.
      handoverOff(turn.store);
      return;
    }
    if (turn.markCame) {
      if (!(await bounded((signal) => turn.store.write(token, signal), deadline))) handoverOff(turn.store);
      return;
    }
    // The mark did not come in the allowance. The write creates its read-write
    // transaction now, on the read's open connection, before the lock frees.
    // IndexedDB's specification makes a later transaction on the same store, on any
    // connection, wait until this one has finished, so the next holder's read comes
    // after it. Nobody waits for it; only its failure turns the hand-over off, and
    // the hand-over going off aborts it if it has not begun to commit.
    void (async () => turn.store.write(token, off.signal))().catch(() => handoverOff(turn.store));
  }

  /** One turn of bucket 1: it sees what the turn before wrote, and hands over what it wrote. */
  async function withLock(task: () => Promise<boolean>): Promise<void> {
    const locks = resolveLocks();
    if (!locks) {
      await task();
      return;
    }
    await locks.request(LOCK_NAME, async () => {
      const turn = await beginTurn();
      let sent = false;
      try {
        sent = await task();
      } finally {
        await endTurn(turn, sent);
      }
    });
  }

  // ── Sending ──────────────────────────────────────────────────────────────

  function finish(job: Job, outcome: { sent: Sent | null } | { error: unknown }): void {
    if (job.done) return;
    job.done = true;
    if ('error' in outcome) job.reject(outcome.error);
    else job.resolve(outcome.sent);
  }

  /**
   * One fetch with the timeout. Gives the answer; or `timedOut` when no answer
   * came inside REQUEST_TIMEOUT_MS (the timer aborts the fetch, and a flag, not
   * the order in which the promises settle, says so); or the error of a fetch
   * that rejects. With `wholeBody`, an answer other than a 429 comes when its
   * body has ended: a copy of the body is read inside the same
   * REQUEST_TIMEOUT_MS (DEC-1188). The caller's abort aborts the fetch.
   */
  async function fetchWithTimeout(
    fetchImpl: typeof fetch,
    request: ApiRequest,
    signal: AbortSignal | undefined,
    wholeBody: boolean,
  ): Promise<{ response: Response | null; error: unknown; timedOut: boolean }> {
    const controller = new AbortController();
    const forward = () => controller.abort(signal ? abortReason(signal) : undefined);
    signal?.addEventListener('abort', forward, { once: true });
    let timedOut = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const timeout = new Promise<null>((resolve) => {
      timer = setTimeout(() => {
        timedOut = true;
        controller.abort(new DOMException('No answer from api.scryfall.com in 20 s.', 'TimeoutError'));
        resolve(null);
      }, REQUEST_TIMEOUT_MS);
    });
    const init: RequestInit = { signal: controller.signal };
    if (request.method) init.method = request.method;
    if (request.headers) init.headers = request.headers;
    if (request.body !== undefined) init.body = request.body;
    try {
      const fetching = fetchImpl(request.url, init);
      // After a timeout the aborted fetch rejects, and nobody waits for it.
      fetching.catch(() => undefined);
      const response = await Promise.race([fetching, timeout]);
      // A 429 is a stop at its head: nobody reads its body.
      if (response && wholeBody && response.status !== 429) {
        // A body that fails before the deadline fails the caller's own read in the same way.
        await Promise.race([response.clone().arrayBuffer().catch(() => undefined), timeout]);
      }
      return { response: timedOut ? null : response, error: null, timedOut };
    } catch (error) {
      return { response: null, error, timedOut };
    } finally {
      clearTimeout(timer);
      signal?.removeEventListener('abort', forward);
    }
  }

  /** Sends one job. True when a request started (its tab then has writes to hand over). */
  async function send(bucket: BucketState, job: Job): Promise<boolean> {
    if (job.done) return false;
    if (job.signal?.aborted) {
      finish(job, { error: abortReason(job.signal) });
      return false;
    }
    if (job.request === null) {
      const picked = job.pick();
      if (picked === null) {
        finish(job, { sent: null });
        return false;
      }
      const request = typeof picked === 'string' ? { url: picked } : picked;
      if (!isApiUrl(request.url)) {
        finish(job, { error: new TypeError(`not an api.scryfall.com address: ${request.url}`) });
        return false;
      }
      job.request = request;
    }
    const fetchImpl = resolveFetch();
    if (!fetchImpl) {
      finish(job, { error: new Error('fetch unavailable') });
      return false;
    }

    const request = job.request;
    const run = generation;
    const noted = stopNumber();
    markStart(bucket);
    const deadline = monotonic() + REQUEST_TIMEOUT_MS;
    inFlight += 1;
    // A caller that stores the answer gets it whole, so its own read cannot hang (DEC-1188).
    const { response, error, timedOut } = await fetchWithTimeout(fetchImpl, request, job.signal, job.settle !== undefined);
    if (run !== generation) return true;
    inFlight = Math.max(0, inFlight - 1);
    if (inFlight === 0) {
      const waiters = idleWaiters;
      idleWaiters = [];
      waiters.forEach((wake) => wake());
    }

    // A timeout is a failure; the caller's own abort is not.
    if (!timedOut && job.signal?.aborted) {
      finish(job, { error: error ?? abortReason(job.signal) });
      return true;
    }
    if (timedOut || !response || response.status === 429) {
      // The request that met the stop goes first when the stop ends.
      bucket.jobs.unshift(job);
      fail(noted);
      return true;
    }
    succeed(noted);
    const sent = { url: request.url, response };
    if (!job.settle) {
      finish(job, { sent });
      return true;
    }
    // The caller's work holds the bucket, but no longer than the request's own 20 s.
    const settling = (async () => job.settle!(sent))();
    settling.then(() => finish(job, { sent }), (error) => finish(job, { error }));
    await within(settling, deadline - monotonic());
    return true;
  }

  async function drain(bucket: BucketState): Promise<void> {
    if (bucket.running) return;
    bucket.running = true;
    const run = generation;
    try {
      while (run === generation && bucket.jobs.length > 0) {
        await waitForTurn(bucket);
        if (bucket.name === 'lookup') {
          // Bucket 1 sends one request at a time across tabs, and waits for its answer.
          await withLock(async () => {
            await waitForTurn(bucket);
            const job = bucket.jobs.shift();
            return job ? send(bucket, job) : false;
          });
        } else {
          const job = bucket.jobs.shift();
          if (job) {
            void send(bucket, job).then(() => {
              if (bucket.jobs.length > 0) void drain(bucket);
            });
          }
        }
      }
    } finally {
      if (run === generation) bucket.running = false;
    }
  }

  function next(
    bucketName: Bucket,
    pick: () => string | ApiRequest | null,
    options: SendOptions = {},
  ): Promise<Sent | null> {
    const bucket = buckets[bucketName];
    return new Promise<Sent | null>((resolve, reject) => {
      const job: Job = {
        pick,
        request: null,
        signal: options.signal,
        settle: options.settle,
        done: false,
        resolve,
        reject,
      };
      const { signal } = options;
      if (signal?.aborted) return finish(job, { error: abortReason(signal) });
      signal?.addEventListener(
        'abort',
        () => {
          const at = bucket.jobs.indexOf(job);
          if (at < 0) return; // in flight: the fetch itself rejects
          bucket.jobs.splice(at, 1);
          finish(job, { error: abortReason(signal) });
        },
        { once: true },
      );
      if (options.first) bucket.jobs.unshift(job);
      else bucket.jobs.push(job);
      void drain(bucket);
    });
  }

  async function limitedFetch(url: string, options: SendOptions = {}): Promise<Response> {
    if (!isApiUrl(url)) throw new TypeError(`not an api.scryfall.com address: ${url}`);
    const { method, headers, body } = options;
    const sent = await next(bucketOf(url), () => ({ url, method, headers, body }), options);
    return sent!.response;
  }

  function _reset(): void {
    generation += 1;
    for (const bucket of Object.values(buckets)) {
      bucket.jobs.length = 0;
      bucket.lastStart = -Infinity;
      bucket.running = false;
    }
    inFlight = 0;
    idleWaiters = [];
    memoryStop = null;
    stopInMemoryOnly = false;
  }

  return { fetch: limitedFetch, next, stoppedUntil, subscribe, _reset };
}

export const scryfallLimiter: ScryfallLimiter = createScryfallLimiter();
