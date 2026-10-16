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
// it has stored it, so the next tab's turn finds those names in storage; the
// lock frees 20 s after the start at the latest (DEC-1153). Such a caller gets
// the answer whole: the limiter reads its body inside the request's 20 s.
// Without navigator.locks (jsdom) the bucket holds in the one tab.
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
   * REQUEST_TIMEOUT_MS after the request started, whichever comes first. The
   * body of the answer has ended when it runs (DEC-1188).
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

function abortReason(signal: AbortSignal): unknown {
  return signal.reason ?? new DOMException('The request was aborted.', 'AbortError');
}

/** A number that no other stop record holds. */
function newStopNumber(): number {
  return Math.floor(Math.random() * Number.MAX_SAFE_INTEGER) + 1;
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
    writeStop({ until: now() + ms, ms, n: newStopNumber() });
  }

  /** Any other answer. It ends a stop only when it is the request that went after that stop. */
  function succeed(noted: number | null): void {
    const prev = readStop();
    if (prev && prev.n === noted) writeStop(null);
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

  /** Resolves when `work` settles or after `ms`, whichever comes first. */
  function settledOrAfter(work: Promise<unknown>, ms: number): Promise<void> {
    let timer: ReturnType<typeof setTimeout> | undefined;
    return new Promise<void>((resolve) => {
      timer = setTimeout(resolve, ms);
      work.then(() => resolve(), () => resolve());
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

  /**
   * One fetch with the timeout. Gives the answer; or `timedOut` when no answer
   * came inside REQUEST_TIMEOUT_MS (the timer aborts the fetch, and a flag, not
   * the order in which the promises settle, says so); or the error of a fetch
   * that rejects. With `wholeBody`, the answer comes when its body has ended: a
   * copy of the body is read inside the same REQUEST_TIMEOUT_MS (DEC-1188). The
   * caller's abort aborts the fetch.
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
      if (response && wholeBody) {
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

  async function send(bucket: BucketState, job: Job): Promise<void> {
    if (job.done) return;
    if (job.signal?.aborted) return finish(job, { error: abortReason(job.signal) });
    if (job.request === null) {
      const picked = job.pick();
      if (picked === null) return finish(job, { sent: null });
      const request = typeof picked === 'string' ? { url: picked } : picked;
      if (!isApiUrl(request.url)) {
        return finish(job, { error: new TypeError(`not an api.scryfall.com address: ${request.url}`) });
      }
      job.request = request;
    }
    const fetchImpl = resolveFetch();
    if (!fetchImpl) return finish(job, { error: new Error('fetch unavailable') });

    const request = job.request;
    const run = generation;
    const noted = stopNumber();
    markStart(bucket);
    const deadline = monotonic() + REQUEST_TIMEOUT_MS;
    inFlight += 1;
    // A caller that stores the answer gets it whole, so its own read cannot hang (DEC-1188).
    const { response, error, timedOut } = await fetchWithTimeout(fetchImpl, request, job.signal, job.settle !== undefined);
    if (run !== generation) return;
    inFlight = Math.max(0, inFlight - 1);
    if (inFlight === 0) {
      const waiters = idleWaiters;
      idleWaiters = [];
      waiters.forEach((wake) => wake());
    }

    // A timeout is a failure; the caller's own abort is not.
    if (!timedOut && job.signal?.aborted) return finish(job, { error: error ?? abortReason(job.signal) });
    if (timedOut || !response || response.status === 429) {
      // The request that met the stop goes first when the stop ends.
      bucket.jobs.unshift(job);
      fail(noted);
      return;
    }
    succeed(noted);
    const sent = { url: request.url, response };
    if (!job.settle) return finish(job, { sent });
    // The caller's work holds the bucket, but no longer than the request's own 20 s.
    const settling = (async () => job.settle!(sent))();
    settling.then(() => finish(job, { sent }), (error) => finish(job, { error }));
    await settledOrAfter(settling, deadline - monotonic());
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
