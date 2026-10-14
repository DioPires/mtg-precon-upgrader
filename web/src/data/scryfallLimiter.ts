// The one module that sends requests to api.scryfall.com (DEC-1102, design D of DEC-1072).
//
// Scryfall allows 2 requests a second on /cards/named and /cards/collection and
// 10 a second on its other methods. A 429 limits the caller for 30 s, and a
// caller that ignores 429s can be banned. Scryfall's 429 carries no CORS header,
// so the browser shows it to the app as a fetch that rejects.
//
// Bucket 1 ('lookup': /cards/named, /cards/collection). A request starts 600 ms
// or more after the last start, and only after the last answer has arrived.
// Three starts 500 ms apart can arrive inside one second at Scryfall; 600 ms
// apart they cannot. The tabs of one origin share bucket 1: navigator.locks lets
// one tab send at a time, and localStorage holds the last start. Without
// navigator.locks (jsdom) the bucket holds in the one tab.
// Bucket 2 ('autocomplete': /cards/autocomplete). 120 ms between starts.
//
// The stop. A 429, or a fetch to api.scryfall.com that rejects, stops both
// buckets for 30 s. The request that met it stays first in its bucket, and
// nothing goes. When the stop ends, one request goes. If that one fails too, the
// stop doubles (60 s, 120 s, 240 s), up to 300 s. Any other answer to it ends the
// stop and resets it to 30 s. A fetch that its caller aborts is no failure. The
// stop's end lives in localStorage, so a reload and a second tab obey it; without
// storage it lives in memory.

export const SCRYFALL_API = 'https://api.scryfall.com';
export const LOOKUP_SPACING_MS = 600;
export const AUTOCOMPLETE_SPACING_MS = 120;
export const FIRST_STOP_MS = 30_000;
export const MAX_STOP_MS = 300_000;
export const STOP_KEY = 'grimoire-scryfall-stop';
export const LAST_START_KEY = 'grimoire-scryfall-last-start';
const LOCK_NAME = 'grimoire-scryfall-bucket-1';

export type Bucket = 'lookup' | 'autocomplete';

/** The JSON lookup of one card by name. */
export function lookupUrl(name: string): string {
  return `${SCRYFALL_API}/cards/named?fuzzy=${encodeURIComponent(name)}`;
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

/** A stop: its end (epoch ms) and its length. The record stays after the end until a request succeeds. */
export interface Stop {
  until: number;
  ms: number;
}

export interface SendOptions {
  /** Aborts the request, also while it waits for its turn. An abort is no failure and starts no stop. */
  signal?: AbortSignal;
  /** Puts the request before the others that wait in its bucket. */
  first?: boolean;
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
   * and gives the URL to send. Null gives the turn back, and the call resolves null.
   */
  next(bucket: Bucket, pick: () => string | null, options?: SendOptions): Promise<Sent | null>;
  /** The end of the stop that holds now (epoch ms), or null. */
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
  now?: () => number;
}

interface Job {
  pick: () => string | null;
  url: string | null;
  signal?: AbortSignal;
  done: boolean;
  resolve: (sent: Sent | null) => void;
  reject: (reason: unknown) => void;
}

interface BucketState {
  name: Bucket;
  spacingMs: number;
  jobs: Job[];
  running: boolean;
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

function abortReason(signal: AbortSignal): unknown {
  return signal.reason ?? new DOMException('The request was aborted.', 'AbortError');
}

export function createScryfallLimiter(deps: LimiterDeps = {}): ScryfallLimiter {
  const resolveStorage = (): Storage | null =>
    deps.storage === undefined ? defaultStorage() : deps.storage;
  const resolveLocks = (): LockManager | null =>
    deps.locks === undefined ? defaultLocks() : deps.locks;
  // Resolved on each send so that a test's spy on globalThis.fetch is honoured.
  const resolveFetch = (): typeof fetch | undefined =>
    deps.fetchImpl ?? (typeof fetch !== 'undefined' ? fetch : undefined);
  const now = deps.now ?? (() => Date.now());

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

  function readStop(): Stop | null {
    const storage = resolveStorage();
    if (!storage || stopInMemoryOnly) return memoryStop;
    try {
      const raw = storage.getItem(STOP_KEY);
      if (!raw) return null;
      const stop = JSON.parse(raw) as Stop;
      if (typeof stop?.until !== 'number' || typeof stop?.ms !== 'number') return null;
      // A clock that went back must not stretch a stop past its own length.
      return { until: Math.min(stop.until, now() + stop.ms), ms: stop.ms };
    } catch {
      return memoryStop;
    }
  }

  function writeStop(stop: Stop | null): void {
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

  /** A 429 or a rejected fetch. Only a request that started after the last stop ended can start or double one. */
  function fail(startedAt: number): void {
    const prev = readStop();
    if (prev && startedAt < prev.until) return;
    const ms = prev ? Math.min(prev.ms * 2, MAX_STOP_MS) : FIRST_STOP_MS;
    writeStop({ until: now() + ms, ms });
  }

  /** Any other answer. It ends a stop only when it is the request that went after the stop. */
  function succeed(startedAt: number): void {
    const prev = readStop();
    if (prev && startedAt >= prev.until) writeStop(null);
  }

  function subscribe(fn: (until: number | null) => void): () => void {
    listeners.add(fn);
    if (!listeningToStorage && typeof window !== 'undefined') {
      listeningToStorage = true;
      window.addEventListener('storage', (event) => {
        if (event.key === STOP_KEY) notifyListeners();
      });
    }
    return () => {
      listeners.delete(fn);
    };
  }

  // ── Turns ────────────────────────────────────────────────────────────────

  function lastStartOf(bucket: BucketState): number {
    let last = bucket.lastStart;
    if (bucket.name === 'lookup') {
      const storage = resolveStorage();
      try {
        const stored = Number(storage?.getItem(LAST_START_KEY));
        if (Number.isFinite(stored) && stored > last) last = stored;
      } catch {
        // Fall back to this tab's own last start.
      }
    }
    // A last start in the future (a clock that went back) waits one spacing at most.
    return Math.min(last, now());
  }

  function markStart(bucket: BucketState, at: number): void {
    bucket.lastStart = at;
    if (bucket.name !== 'lookup') return;
    try {
      resolveStorage()?.setItem(LAST_START_KEY, String(at));
    } catch {
      // This tab keeps its own last start.
    }
  }

  /** Milliseconds until the bucket may start a request; 'busy' while the request after a stop is out. */
  function waitFor(bucket: BucketState): number | 'busy' {
    const t = now();
    const stop = readStop();
    if (stop && stop.until > t) return stop.until - t;
    if (stop && inFlight > 0) return 'busy';
    return Math.max(0, lastStartOf(bucket) + bucket.spacingMs - t);
  }

  function sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
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

  async function withLock(task: () => Promise<void>): Promise<void> {
    const locks = resolveLocks();
    if (!locks) return task();
    await locks.request(LOCK_NAME, task);
  }

  // ── Sending ──────────────────────────────────────────────────────────────

  function finish(job: Job, outcome: { sent: Sent | null } | { error: unknown }): void {
    if (job.done) return;
    job.done = true;
    if ('error' in outcome) job.reject(outcome.error);
    else job.resolve(outcome.sent);
  }

  async function send(bucket: BucketState, job: Job): Promise<void> {
    if (job.done) return;
    if (job.signal?.aborted) return finish(job, { error: abortReason(job.signal) });
    if (job.url === null) {
      const url = job.pick();
      if (url === null) return finish(job, { sent: null });
      if (!isApiUrl(url)) return finish(job, { error: new TypeError(`not an api.scryfall.com address: ${url}`) });
      job.url = url;
    }
    const fetchImpl = resolveFetch();
    if (!fetchImpl) return finish(job, { error: new Error('fetch unavailable') });

    const url = job.url;
    const run = generation;
    const startedAt = now();
    markStart(bucket, startedAt);
    inFlight += 1;
    let response: Response | null = null;
    let error: unknown = null;
    try {
      response = job.signal ? await fetchImpl(url, { signal: job.signal }) : await fetchImpl(url);
    } catch (err) {
      error = err;
    }
    if (run !== generation) return;
    inFlight = Math.max(0, inFlight - 1);
    if (inFlight === 0) {
      const waiters = idleWaiters;
      idleWaiters = [];
      waiters.forEach((wake) => wake());
    }

    if (job.signal?.aborted) return finish(job, { error: error ?? abortReason(job.signal) });
    if (!response || response.status === 429) {
      // The request that met the stop goes first when the stop ends.
      bucket.jobs.unshift(job);
      fail(startedAt);
      return;
    }
    succeed(startedAt);
    finish(job, { sent: { url, response } });
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
            if (job) await send(bucket, job);
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
    pick: () => string | null,
    options: SendOptions = {},
  ): Promise<Sent | null> {
    const bucket = buckets[bucketName];
    return new Promise<Sent | null>((resolve, reject) => {
      const job: Job = { pick, url: null, signal: options.signal, done: false, resolve, reject };
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
    const sent = await next(bucketOf(url), () => url, options);
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
