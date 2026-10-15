import '@testing-library/jest-dom/vitest';

// Node 22+ ships an experimental localStorage that lacks setItem and shadows jsdom's
// real Storage on globalThis. Install an in-memory polyfill so the cardCache 24h
// persistence layer behaves the same as in a browser. (Each suite resets entries
// via beforeEach.)
class MemoryStorage implements Storage {
  private store = new Map<string, string>();
  get length(): number { return this.store.size; }
  clear(): void { this.store.clear(); }
  getItem(k: string): string | null { return this.store.get(k) ?? null; }
  setItem(k: string, v: string): void { this.store.set(k, String(v)); }
  removeItem(k: string): void { this.store.delete(k); }
  key(i: number): string | null { return Array.from(this.store.keys())[i] ?? null; }
}

const polyfill = new MemoryStorage();
Object.defineProperty(globalThis, 'localStorage', {
  configurable: true,
  enumerable: true,
  value: polyfill,
});
if (typeof window !== 'undefined') {
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    enumerable: true,
    value: polyfill,
  });
}

// No unit case reaches a Scryfall host (DEC-1131). A component that mounts card
// rows enqueues lookups, and without this a case that does not stub fetch sends
// them to the live API. A fetch to a Scryfall host rejects, as the e2e suite's
// DNS block makes it; the limiter takes that as a lost network. A case that
// wants an answer spies on globalThis.fetch or gives the limiter its own fetch.
const realFetch = globalThis.fetch;
const SCRYFALL_DOMAINS = ['scryfall.com', 'scryfall.io'];
globalThis.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
  const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
  let host = '';
  try {
    host = new URL(url, 'http://localhost').hostname;
  } catch {
    // Not an address: the real fetch says so.
  }
  if (SCRYFALL_DOMAINS.some((d) => host === d || host.endsWith(`.${d}`))) {
    return Promise.reject(new TypeError(`setupTests: a unit case may not fetch ${url}`));
  }
  return realFetch(input, init);
}) as typeof fetch;
