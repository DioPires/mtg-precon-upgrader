// A fake api.scryfall.com for the limiter and card cache cases (DEC-1102).
// Every send is logged with the fake clock's time. Not a test file itself.

export class MemoryStorage implements Storage {
  private store = new Map<string, string>();
  get length(): number { return this.store.size; }
  clear(): void { this.store.clear(); }
  getItem(k: string): string | null { return this.store.get(k) ?? null; }
  setItem(k: string, v: string): void { this.store.set(k, String(v)); }
  removeItem(k: string): void { this.store.delete(k); }
  key(i: number): string | null { return Array.from(this.store.keys())[i] ?? null; }
}

/** What the fake does with one request: a status, or 'reject' for a fetch that rejects. */
export type Outcome = number | 'reject';

export interface Send {
  url: string;
  /** The card name of a lookup, or the query of an autocomplete. */
  name: string;
  at: number;
}

export interface FakeScryfall {
  fetch: typeof fetch;
  sends: Send[];
  /** The fake clock's times of the sends. */
  times(): number[];
  names(): string[];
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

/**
 * `delayMs`: the time each answer takes. `outcome(n, url)`: the answer to the
 * n-th send (from 1); 200 by default.
 */
export function fakeScryfall(
  options: { delayMs?: number; outcome?: (n: number, url: string) => Outcome } = {},
): FakeScryfall {
  const delayMs = options.delayMs ?? 0;
  const sends: Send[] = [];
  const fetchImpl = (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = String(input);
    const parsed = new URL(url);
    const name = parsed.searchParams.get('fuzzy') ?? parsed.searchParams.get('q') ?? '';
    sends.push({ url, name, at: Date.now() });
    const outcome = options.outcome?.(sends.length, url) ?? 200;
    const answer = (): Response => {
      if (outcome === 'reject') throw new TypeError('Failed to fetch');
      if (outcome !== 200) return new Response('{"object":"error"}', { status: outcome });
      const body = parsed.pathname === '/cards/autocomplete'
        ? { object: 'catalog', data: [`${name} One`, `${name} Two`] }
        : cardJson(name);
      return new Response(JSON.stringify(body), { status: 200 });
    };
    const signal = init?.signal;
    if (signal?.aborted) return Promise.reject(abortError());
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
    names: () => sends.map((s) => s.name),
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
