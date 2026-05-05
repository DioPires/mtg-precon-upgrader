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
