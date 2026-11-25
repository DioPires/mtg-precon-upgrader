// A fake api.scryfall.com for the limiter and card cache cases (DEC-1102,
// DEC-1131). Every send is logged with the fake clock's times. Not a test file
// itself.

import type { TurnStore } from '../../data/scryfallLimiter';

export class MemoryStorage implements Storage {
  private store = new Map<string, string>();
  get length(): number { return this.store.size; }
  clear(): void { this.store.clear(); }
  getItem(k: string): string | null { return this.store.get(k) ?? null; }
  setItem(k: string, v: string): void { this.store.set(k, String(v)); }
  removeItem(k: string): void { this.store.delete(k); }
  key(i: number): string | null { return Array.from(this.store.keys())[i] ?? null; }
}

/** What the fake does with one request: a status, 'reject' for a fetch that rejects, or 'hang' for no answer. */
export type Outcome = number | 'reject' | 'hang';

export interface Send {
  url: string;
  method: string;
  /** The names of a /cards/collection batch, or the query of an autocomplete. */
  names: string[];
  /** The first of `names`. */
  name: string;
  /** The wall clock (Date.now()) at the send. */
  at: number;
  /** The tab's own clock (performance.now()) at the send. */
  elapsed: number;
}

export interface FakeScryfall {
  fetch: typeof fetch;
  sends: Send[];
  /** The wall clock's times of the sends. */
  times(): number[];
  /** The names of every send, in order: each batch's names, and each autocomplete's query. */
  names(): string[];
  /** The names of each send. */
  batches(): string[][];
}

export function cardJson(name: string) {
  const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '-');
  return {
    object: 'card',
    name,
    mana_cost: '{1}',
    cmc: 1,
    type_line: 'Artifact',
    image_uris: {
      small: `https://cards.scryfall.io/small/looked/${slug}.jpg`,
      normal: `https://cards.scryfall.io/normal/looked/${slug}.jpg`,
      large: `https://cards.scryfall.io/large/looked/${slug}.jpg`,
      art_crop: `https://cards.scryfall.io/art_crop/looked/${slug}.jpg`,
    },
    prices: { usd: '0.42' },
  };
}

function abortError(): DOMException {
  return new DOMException('The operation was aborted.', 'AbortError');
}

/** The names of a /cards/collection body. */
export function identifiersOf(body: unknown): string[] {
  try {
    const parsed = JSON.parse(String(body)) as { identifiers?: Array<{ name?: string }> };
    return (parsed.identifiers ?? []).map((id) => id.name ?? '');
  } catch {
    return [];
  }
}

/** A /cards/collection answer: the card of each name that `card` knows, in the order asked, and the rest in not_found. */
export function collectionJson(names: string[], card: (name: string) => object | null = cardJson) {
  const data: object[] = [];
  const notFound: Array<{ name: string }> = [];
  for (const name of names) {
    const found = card(name);
    if (found) data.push(found);
    else notFound.push({ name });
  }
  return { object: 'list', not_found: notFound, data };
}

/**
 * `delayMs`: the time each answer takes. `outcome(n, url)`: the answer to the
 * n-th send (from 1); 200 by default. `card(name)`: the card of a batch's name,
 * or null for not_found; cardJson(name) by default.
 */
export function fakeScryfall(
  options: {
    delayMs?: number;
    outcome?: (n: number, url: string) => Outcome;
    card?: (name: string) => object | null;
  } = {},
): FakeScryfall {
  const delayMs = options.delayMs ?? 0;
  const sends: Send[] = [];
  const fetchImpl = (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = String(input);
    const parsed = new URL(url);
    const method = init?.method ?? 'GET';
    const names = parsed.pathname === '/cards/collection'
      ? identifiersOf(init?.body)
      : [parsed.searchParams.get('q') ?? ''];
    sends.push({ url, method, names, name: names[0] ?? '', at: Date.now(), elapsed: performance.now() });
    const outcome = options.outcome?.(sends.length, url) ?? 200;
    const answer = (): Response => {
      if (outcome === 'reject') throw new TypeError('Failed to fetch');
      if (outcome !== 200) return new Response('{"object":"error"}', { status: outcome as number });
      const body = parsed.pathname === '/cards/autocomplete'
        ? { object: 'catalog', data: [`${names[0]} One`, `${names[0]} Two`] }
        : collectionJson(names, options.card);
      return new Response(JSON.stringify(body), { status: 200 });
    };
    const signal = init?.signal;
    if (signal?.aborted) return Promise.reject(abortError());
    if (outcome === 'hang') {
      return new Promise<Response>((_resolve, reject) => {
        signal?.addEventListener('abort', () => reject(abortError()));
      });
    }
    if (delayMs === 0) {
      try {
        return Promise.resolve(answer());
      } catch (err) {
        return Promise.reject(err);
      }
    }
    return new Promise<Response>((resolve, reject) => {
      const timer = setTimeout(() => {
        try {
          resolve(answer());
        } catch (err) {
          reject(err);
        }
      }, delayMs);
      signal?.addEventListener('abort', () => {
        clearTimeout(timer);
        reject(abortError());
      });
    });
  };
  return {
    fetch: fetchImpl as typeof fetch,
    sends,
    times: () => sends.map((s) => s.at),
    names: () => sends.flatMap((s) => s.names),
    batches: () => sends.map((s) => s.names),
  };
}

/** The most starts that any closed window of `windowMs` holds (both ends count). */
export function peakInClosedWindow(times: number[], windowMs = 1000): number {
  const sorted = [...times].sort((a, b) => a - b);
  let peak = 0;
  for (let i = 0, j = 0; i < sorted.length; i += 1) {
    while (sorted[i] - sorted[j] > windowMs) j += 1;
    peak = Math.max(peak, i - j + 1);
  }
  return peak;
}

export function gaps(times: number[]): number[] {
  return times.slice(1).map((t, i) => t - times[i]);
}

/** An EventTarget that counts the listeners added and not removed: a case checks that a wait leaves none. */
export class CountingEvents extends EventTarget {
  listening = 0;
  addEventListener(
    type: string,
    listener: EventListenerOrEventListenerObject | null,
    options?: AddEventListenerOptions | boolean,
  ): void {
    if (listener) this.listening += 1;
    super.addEventListener(type, listener, options);
  }
  removeEventListener(
    type: string,
    listener: EventListenerOrEventListenerObject | null,
    options?: EventListenerOptions | boolean,
  ): void {
    if (listener) this.listening -= 1;
    super.removeEventListener(type, listener, options);
  }
}

/** One tab of laggingStorages(): its own copy of localStorage, and where it hears of the other tabs' writes. */
export interface LaggingTab {
  storage: Storage;
  events: CountingEvents;
}

/**
 * localStorage shared by `tabs` tabs, with ordered, late delivery: each tab
 * reads its own copy. A write that changes a value reaches the writer's copy at
 * once and each other tab's copy `lagMs` later, in the order made, with a
 * `storage` event on that tab's own target; the writer hears no event of its
 * own write. A lock that the writer frees in between does not wait for it.
 * The hand-over of src/data/scryfallLimiter.ts rests on this order.
 */
export function laggingStorages(lagMs: number, tabs = 2): LaggingTab[] {
  const copies = Array.from({ length: tabs }, () => ({ own: new MemoryStorage(), events: new CountingEvents() }));
  return copies.map(({ own, events }) => {
    const write = (key: string, newValue: string | null) => {
      if (own.getItem(key) === newValue) return;
      if (newValue === null) own.removeItem(key);
      else own.setItem(key, newValue);
      for (const other of copies) {
        if (other.own === own) continue;
        setTimeout(() => {
          if (newValue === null) other.own.removeItem(key);
          else other.own.setItem(key, newValue);
          other.events.dispatchEvent(new StorageEvent('storage', { key, newValue }));
        }, lagMs);
      }
    };
    const storage: Storage = {
      get length() { return own.length; },
      clear: () => Array.from({ length: own.length }, (_, i) => own.key(i)!).forEach((k) => write(k, null)),
      getItem: (k) => own.getItem(k),
      key: (i) => own.key(i),
      setItem: (k, v) => write(k, String(v)),
      removeItem: (k) => write(k, null),
    };
    return { storage, events };
  });
}

/** What a fake turn store holds: shared by the tabs' stores, as one IndexedDB database is. */
export interface TurnDb {
  token: string | null;
  /** The tokens of the writes that landed, in order. */
  landed: string[];
  reads: number;
  /** The writes asked for, landed or not. */
  writes: number;
  /** Settles when every write asked for so far has landed or stopped. */
  pending: Promise<unknown>;
}

export function turnDb(token: string | null = null): TurnDb {
  return { token, landed: [], reads: 0, writes: 0, pending: Promise.resolve() };
}

/** How long a fake store's read or write takes once it starts (fake timers): ms, 'never' settles, or 'fail' rejects. */
export type TurnTiming = number | 'never' | 'fail';

/** A fake turn store, and whether the limiter closed it (the hand-over went off). */
export interface FakeTurnStore extends TurnStore {
  closed: boolean;
}

/**
 * A turn store over `db`, as IndexedDB's: an operation starts once every write
 * asked for before it has landed or stopped, as a transaction waits for an
 * earlier read-write one, so a read never overtakes an earlier write. A read
 * gives the token of the writes that have landed. An abort stops an operation
 * that has not landed (also one that never settles); one aborted before it
 * starts is never issued. `ready` says whether a connection is open (true by
 * default).
 */
export function fakeTurns(
  db: TurnDb,
  timing: { read?: TurnTiming; write?: TurnTiming; ready?: () => boolean } = {},
): FakeTurnStore {
  const after = <T>(how: TurnTiming, signal: AbortSignal, land: () => T): Promise<T> =>
    db.pending.then(
      () =>
        new Promise<T>((resolve, reject) => {
          if (signal.aborted) return reject(signal.reason);
          if (how === 'fail') return reject(new DOMException('The fake store failed.', 'UnknownError'));
          const timer = how === 'never' ? undefined : setTimeout(() => resolve(land()), how);
          signal.addEventListener('abort', () => {
            clearTimeout(timer);
            reject(signal.reason);
          });
        }),
    );
  const store: FakeTurnStore = {
    closed: false,
    read: (signal) => {
      db.reads += 1;
      return after(timing.read ?? 0, signal, () => db.token);
    },
    write: (token, signal) => {
      db.writes += 1;
      const written = after(timing.write ?? 0, signal, () => {
        db.token = token;
        db.landed.push(token);
      });
      db.pending = written.catch(() => undefined);
      return written;
    },
    ready: () => timing.ready?.() ?? true,
    close: () => {
      store.closed = true;
    },
  };
  return store;
}

/**
 * A LockManager that runs one holder of each lock name at a time, in the order
 * asked, as the tabs of one origin share navigator.locks.
 */
export function fakeLocks(): LockManager {
  const tails = new Map<string, Promise<unknown>>();
  const request = (name: string, ...rest: unknown[]) => {
    const callback = rest[rest.length - 1] as (lock: Lock | null) => unknown;
    const run = (tails.get(name) ?? Promise.resolve()).then(() => callback({ name, mode: 'exclusive' } as Lock));
    tails.set(name, run.then(() => undefined, () => undefined));
    return run;
  };
  return { request, query: async () => ({ held: [], pending: [] }) } as unknown as LockManager;
}

/** One transaction of fakeIndexedDb(), as the test sees it. */
export interface FakeTransaction {
  mode: IDBTransactionMode;
  durability: string | undefined;
  state: 'running' | 'complete' | 'failed' | 'aborted';
  /** The calls of abort(), also those that came after the transaction finished. */
  aborts: number;
}

/**
 * How endTransactions() ends the transactions that wait: a request fails
 * (`error`: the transaction hears `error` while its own error is still null,
 * then aborts with it, its `abort` in a later task), or the browser aborts them.
 */
export type FakeTransactionEnd = 'complete' | 'error' | 'abort';

/**
 * A minimal IndexedDB for indexedDbTurns(): one database with its version,
 * object stores and values. An open succeeds on the next timer, after
 * `upgradeneeded` when the version asked for is newer; an open for an older
 * version than the database's fails with VersionError. With `holdOpens` set,
 * opens wait for releaseOpens(). A transaction completes on the next timer, or
 * waits for releaseTransactions() while `holdTransactions` is set; abort()
 * stops one that has not completed and throws after. A closed connection
 * refuses new transactions. versionChange() is another tab's upgrade to
 * version 2: each open connection hears `versionchange`, then the database is
 * at version 2. forceClose() is site data cleared while connections are open.
 */
export function fakeIndexedDb() {
  interface Connection {
    closed: boolean;
    onversionchange: ((this: Connection) => void) | null;
    onclose: ((this: Connection) => void) | null;
    close(): void;
    createObjectStore(name: string): void;
    transaction(store: string, mode: IDBTransactionMode, options?: { durability?: string }): unknown;
  }
  const state = {
    /** 0 while the database does not exist. */
    version: 0,
    stores: new Set<string>(),
    values: new Map<string, unknown>(),
    opens: 0,
    connections: [] as Connection[],
    transactions: [] as FakeTransaction[],
    holdOpens: false,
    holdTransactions: false,
  };
  const heldOpens: Array<() => void> = [];
  const heldTransactions: Array<(how: FakeTransactionEnd) => void> = [];
  const later = (fn: () => void, held: boolean, queue: Array<() => void>) => (held ? queue.push(fn) : setTimeout(fn, 0));

  function connect(): Connection {
    const connection: Connection = {
      closed: false,
      onversionchange: null,
      onclose: null,
      close: () => {
        connection.closed = true;
      },
      createObjectStore: (name) => {
        state.stores.add(name);
      },
      transaction: (store, mode, options) => {
        if (connection.closed) throw new DOMException('The connection is closed.', 'InvalidStateError');
        if (!state.stores.has(store)) throw new DOMException(`No store ${store}.`, 'NotFoundError');
        const record: FakeTransaction = { mode, durability: options?.durability, state: 'running', aborts: 0 };
        state.transactions.push(record);
        const requests: Array<{ result?: unknown; apply: () => void }> = [];
        const transaction = {
          error: null as DOMException | null,
          oncomplete: null as (() => void) | null,
          onerror: null as (() => void) | null,
          onabort: null as (() => void) | null,
          objectStore: () => ({
            get: (key: string) => {
              const request: { result?: unknown; apply: () => void } = { apply: () => (request.result = state.values.get(key)) };
              requests.push(request);
              return request;
            },
            put: (value: unknown, key: string) => {
              const request: { result?: unknown; apply: () => void } = {
                apply: () => {
                  state.values.set(key, value);
                  request.result = key;
                },
              };
              requests.push(request);
              return request;
            },
          }),
          abort: () => {
            record.aborts += 1;
            if (record.state !== 'running') throw new DOMException('The transaction has finished.', 'InvalidStateError');
            record.state = 'aborted';
            setTimeout(() => transaction.onabort?.(), 0);
          },
        };
        const end = (how: FakeTransactionEnd) => {
          if (record.state !== 'running') return;
          if (how === 'complete') {
            requests.forEach((request) => request.apply());
            record.state = 'complete';
            transaction.oncomplete?.();
          } else if (how === 'error') {
            // As IndexedDB does: the request's error reaches the transaction while the
            // transaction's own error is still null; then the transaction aborts with it,
            // and its abort event comes in a later task.
            record.state = 'failed';
            transaction.onerror?.();
            transaction.error = new DOMException('A request of the transaction failed.', 'DataError');
            setTimeout(() => transaction.onabort?.(), 0);
          } else {
            record.state = 'aborted';
            transaction.error = new DOMException('The browser aborted the transaction.', 'AbortError');
            transaction.onabort?.();
          }
        };
        if (state.holdTransactions) heldTransactions.push(end);
        else setTimeout(() => end('complete'), 0);
        return transaction;
      },
    };
    state.connections.push(connection);
    return connection;
  }

  const factory = {
    open: (_name: string, version = 1) => {
      state.opens += 1;
      const request = {
        result: null as Connection | null,
        error: null as DOMException | null,
        transaction: null as { abort(): void } | null,
        onupgradeneeded: null as (() => void) | null,
        onsuccess: null as (() => void) | null,
        onerror: null as (() => void) | null,
      };
      later(
        () => {
          if (version < state.version) {
            request.error = new DOMException(`The database is at version ${state.version}.`, 'VersionError');
            request.onerror?.();
            return;
          }
          const connection = connect();
          request.result = connection;
          if (version > state.version) {
            let aborted = false;
            request.transaction = { abort: () => (aborted = true) };
            request.onupgradeneeded?.();
            request.transaction = null;
            if (aborted) {
              state.stores.clear();
              connection.closed = true;
              request.result = null;
              request.error = new DOMException('The upgrade was aborted.', 'AbortError');
              request.onerror?.();
              return;
            }
            state.version = version;
          }
          request.onsuccess?.();
        },
        state.holdOpens,
        heldOpens,
      );
      return request;
    },
  };

  return {
    factory: factory as unknown as IDBFactory,
    state,
    releaseOpens: () => heldOpens.splice(0).forEach((open) => open()),
    releaseTransactions: () => heldTransactions.splice(0).forEach((end) => end('complete')),
    /** Ends the transactions that wait: each request fails (`error`), or the browser aborts them (`abort`). */
    endTransactions: (how: FakeTransactionEnd) => heldTransactions.splice(0).forEach((end) => end(how)),
    /** Another tab upgrades the database to version 2: each open connection hears `versionchange` first. */
    versionChange: () => {
      state.connections.filter((c) => !c.closed).forEach((c) => c.onversionchange?.call(c));
      state.version = 2;
    },
    /** Site data cleared: the browser closes each open connection, and each hears `close`. */
    forceClose: () =>
      state.connections
        .filter((c) => !c.closed)
        .forEach((c) => {
          c.closed = true;
          c.onclose?.call(c);
        }),
  };
}
