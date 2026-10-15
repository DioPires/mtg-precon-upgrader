// DEC-1131 R2 and delta N2: /shopping's line while a stop holds the price refresh.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import { PricePausedLine } from '../../components/molecules/PricePausedLine';
import { createCardCache } from '../../data/cardCache';
import { createScryfallLimiter, STOP_KEY } from '../../data/scryfallLimiter';
import { clockTime } from '../../lib/pricesDate';
import { fakeScryfall, MemoryStorage } from '../data/scryfallFakes';

const T0 = Date.UTC(2026, 9, 14, 12, 0, 0);
const HOUR_MS = 3_600_000;

let storage: MemoryStorage;

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(T0);
  storage = new MemoryStorage();
});

afterEach(() => {
  vi.useRealTimers();
});

const advance = (ms: number) => act(() => vi.advanceTimersByTimeAsync(ms));
const line = () => screen.getByRole('status');

describe('PricePausedLine', () => {
  it('says that the refresh is paused, the date of the prices shown and the clock time of the next try', () => {
    storage.setItem(STOP_KEY, JSON.stringify({ until: T0 + 30_000, ms: 30_000, n: 1 }));
    const limiter = createScryfallLimiter({ fetchImpl: fakeScryfall().fetch, storage, locks: null });
    render(<PricePausedLine waiting pricesDate="13 Oct 2026" limiter={limiter} />);
    expect(line()).toHaveTextContent(
      `Price refresh paused. Prices shown are from 13 Oct 2026. Next try at ${clockTime(T0 + 30_000)}.`,
    );
    expect(line().textContent).not.toMatch(/scryfall|429|limit/i);
    expect(line().firstElementChild).toHaveClass('gv1-mono-xs', 'gv1-shop-paused');
    expect(line().firstElementChild?.tagName).toBe('P');
  });

  it('leaves out the date of the prices when it is unknown', () => {
    storage.setItem(STOP_KEY, JSON.stringify({ until: T0 + 30_000, ms: 30_000, n: 1 }));
    const limiter = createScryfallLimiter({ fetchImpl: fakeScryfall().fetch, storage, locks: null });
    render(<PricePausedLine waiting pricesDate={null} limiter={limiter} />);
    expect(line().textContent).toBe(`Price refresh paused. Next try at ${clockTime(T0 + 30_000)}.`);
  });

  it('leaves its region empty when no row waits for a refresh, or when no stop holds', () => {
    storage.setItem(STOP_KEY, JSON.stringify({ until: T0 + 30_000, ms: 30_000, n: 1 }));
    const stopped = createScryfallLimiter({ fetchImpl: fakeScryfall().fetch, storage, locks: null });
    const { rerender } = render(<PricePausedLine waiting={false} pricesDate="13 Oct 2026" limiter={stopped} />);
    expect(line()).toBeEmptyDOMElement();
    const free = createScryfallLimiter({ fetchImpl: fakeScryfall().fetch, storage: new MemoryStorage(), locks: null });
    rerender(<PricePausedLine waiting pricesDate="13 Oct 2026" limiter={free} />);
    expect(line()).toBeEmptyDOMElement();
  });

  it('comes when a batch meets a stop, and goes at the end of the stop, also when no request waits', async () => {
    const scry = fakeScryfall({ outcome: () => 429 });
    const limiter = createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks: null });
    render(<PricePausedLine waiting pricesDate="13 Oct 2026" limiter={limiter} />);
    // The status region is in the page before the line (DEC-1154), and the line comes into it.
    const region = line();
    expect(region).toBeEmptyDOMElement();
    // The caller leaves while its request is out: after the 429, nothing waits.
    const caller = new AbortController();
    const out = limiter.fetch(autocompleteAddress, { signal: caller.signal }).catch(() => 'gone');
    await advance(0);
    caller.abort();
    await out;
    expect(line()).toHaveTextContent(`Next try at ${clockTime(T0 + 30_000)}.`);
    expect(line()).toBe(region);
    await advance(30_000 - 1);
    expect(line()).not.toBeEmptyDOMElement();
    await advance(2);
    expect(line()).toBeEmptyDOMElement();
    expect(line()).toBe(region);
    expect(scry.sends).toHaveLength(1);
  });

  it('delta N2: after the clock goes back 10 h, shows the capped end in the tab that capped, not the end that the listener heard', async () => {
    const scry = fakeScryfall({ outcome: () => 429 });
    const limiter = createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks: null });
    const cache = createCardCache({ storage, limiter });
    const { rerender } = render(<PricePausedLine waiting pricesDate="13 Oct 2026" limiter={limiter} />);
    cache.enqueue('Sol Ring');
    await advance(0);
    expect(line()).toHaveTextContent(`Next try at ${clockTime(T0 + 30_000)}.`);

    const back = T0 - 10 * HOUR_MS;
    vi.setSystemTime(back);
    // A render of the page (its 1.5 s tick) reads the stop again, and the read caps it.
    rerender(<PricePausedLine waiting pricesDate="13 Oct 2026" limiter={limiter} />);
    expect(line()).toHaveTextContent(`Next try at ${clockTime(back + 30_000)}.`);
    expect(clockTime(back + 30_000)).not.toBe(clockTime(T0 + 30_000));
  });
});

const autocompleteAddress = 'https://api.scryfall.com/cards/autocomplete?q=sol';
