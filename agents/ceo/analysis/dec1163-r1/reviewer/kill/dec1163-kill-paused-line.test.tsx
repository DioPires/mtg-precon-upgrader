// DEC-1163 kill cases (review of PR #65, DEC-1154): the stop line's element and its words
// when the date of the prices is unknown. Put in src/__tests__/components/ to run.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PricePausedLine } from '../../components/molecules/PricePausedLine';
import { createScryfallLimiter, STOP_KEY } from '../../data/scryfallLimiter';
import { clockTime } from '../../lib/pricesDate';
import { fakeScryfall, MemoryStorage } from '../data/scryfallFakes';

const T0 = Date.UTC(2026, 9, 14, 12, 0, 0);

let storage: MemoryStorage;

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(T0);
  storage = new MemoryStorage();
  storage.setItem(STOP_KEY, JSON.stringify({ until: T0 + 30_000, ms: 30_000, n: 1 }));
});

afterEach(() => {
  vi.useRealTimers();
});

const line = () => screen.getByRole('status');

describe('PricePausedLine (DEC-1163 kill cases)', () => {
  it('shows the line as a paragraph in its region', () => {
    const limiter = createScryfallLimiter({ fetchImpl: fakeScryfall().fetch, storage, locks: null });
    render(<PricePausedLine waiting pricesDate="13 Oct 2026" limiter={limiter} />);
    expect(line().children).toHaveLength(1);
    expect(line().firstElementChild?.tagName).toBe('P');
  });

  it('leaves out the date of the prices when it is unknown', () => {
    const limiter = createScryfallLimiter({ fetchImpl: fakeScryfall().fetch, storage, locks: null });
    render(<PricePausedLine waiting pricesDate={null} limiter={limiter} />);
    expect(line().textContent).toBe(`Price refresh paused. Next try at ${clockTime(T0 + 30_000)}.`);
  });
});
