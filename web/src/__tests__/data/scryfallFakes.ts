// A fake api.scryfall.com for the limiter and card cache cases (DEC-1102,
// DEC-1131). Every send is logged with the fake clock's times. Not a test file
// itself.

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

/** A LockManager that runs one holder at a time, as two tabs of one origin share navigator.locks. */
export function fakeLocks(): LockManager {
  let tail: Promise<unknown> = Promise.resolve();
  const request = (_name: string, ...rest: unknown[]) => {
    const callback = rest[rest.length - 1] as (lock: Lock | null) => unknown;
    const run = tail.then(() => callback({ name: _name, mode: 'exclusive' } as Lock));
    tail = run.then(() => undefined, () => undefined);
    return run;
  };
  return { request, query: async () => ({ held: [], pending: [] }) } as unknown as LockManager;
}
