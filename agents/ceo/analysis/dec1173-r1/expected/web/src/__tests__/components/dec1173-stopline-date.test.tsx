// DEC-1173 kill case (reviewer of PR #72) for the props of `<PricePausedLine … />`
// at Shopping.tsx:804. The stop line gives the date of the prices shown: the
// oldest date among the priced rows of the buy list (DEC-1131), as the footer
// does. Here every buy row has a price from a refresh 1 h ago, and only the row
// of "Already own" waits for a refresh when the stop starts. So the date of the
// prices shown (the refresh's) is not the date of the file (3 days ago).
//   E4 `pricesDate={null}`        drops the date from the line.
//   E5 `pricesDate={pricesDate}`  gives the file's date, not the date of the prices shown.
// Copy it to web/src/__tests__/components/ to run it.
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Shopping } from '../../components/organisms/Shopping';
import { cardCache } from '../../data/cardCache';
import { deckLoader } from '../../data/loader';
import { saveOwned } from '../../data/ownedCards';
import { COLLECTION_URL, STOP_KEY, scryfallLimiter } from '../../data/scryfallLimiter';
import type { DeckFull, DeckListGroup, RawCardMetadata } from '../../data/types';
import { formatPricesDate } from '../../lib/pricesDate';

function makeDeck(over: Partial<DeckFull>): DeckFull {
  return {
    idx: 1, slug: 'alpha', deckName: 'Alpha', commander: 'Alpha Commander', commanderMv: '—', type: 'Commander · Theme',
    colors: '🔴', bracket: '4', status: 'physical', pt: '—', winTurn: '—', winRate: null, flavor: '', oracle: [],
    strategy: '', wincons: [], engine: [], combos: [], apothecary: null, curve: [], func: [], sources: [], list: [],
    health: { score: 70, grade: 'B' }, assessment: null, composition: { totalCards: 100, lands: 36, avgCmc: 2.8 },
    sim: null, rawDecklist: [], physicalDecklist: [], synergies: [], gameChangers: 0, tokens: [], ...over,
  };
}
const group = (name: string, names: string[]): DeckListGroup => ({
  name,
  cards: names.map((n) => ({ n, mv: '—', type: 'Creature', price: '—', gc: false })),
});
const ALPHA = makeDeck({
  list: [group('Commander', ['Alpha Commander']), group('Ramp (2)', ['Sol Ring', 'Arcane Signet']), group('Removal (1)', ['Swords to Plowshares'])],
});

const DAY = 24 * 3_600_000;
// The file's prices: 3 days old, so each row of the file asks for a refresh.
const OLD = new Date(Date.now() - 3 * DAY).toISOString();
// The refresh of the buy rows: 1 h ago, so they ask for no refresh.
const FRESH = Date.now() - 3_600_000;
const meta = (usd: number) => ({ cmc: 1, image: 'front/a/b/x.jpg', mana_cost: '{1}', type_line: 'Artifact', usd, eur: null });
const FILE: RawCardMetadata = {
  'Alpha Commander': meta(5), 'Sol Ring': meta(1.5), 'Arcane Signet': meta(0.5), 'Swords to Plowshares': meta(2),
};
const BUY = ['Alpha Commander', 'Arcane Signet', 'Swords to Plowshares'];

let fetchSpy: MockInstance<typeof fetch>;
let metaSpy: MockInstance<typeof deckLoader.loadCardMetadataMeta>;

beforeEach(() => {
  cardCache._reset();
  deckLoader._reset();
  scryfallLimiter._reset?.();
  localStorage.clear();
  // A live price overlay for each buy row, as a refresh 1 h ago leaves it; seed() keeps it.
  for (const name of BUY) {
    localStorage.setItem(`gv1-card:${name.toLowerCase()}`, JSON.stringify({ fetchedAt: FRESH, priceCheckedAt: FRESH, price: '$9.00', priceAsOf: FRESH }));
  }
  cardCache.seed(FILE, OLD);
  saveOwned(new Map([['Sol Ring', 1]]));
  // The loader keeps the fetch of module load, so the spy below never answers
  // its meta request: the meta comes from this stub, with the file's date.
  metaSpy = vi.spyOn(deckLoader, 'loadCardMetadataMeta').mockResolvedValue({ prices_as_of: OLD });
  fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = String(input);
    // The refresh of Sol Ring meets a lost network: the stop starts.
    if (url === COLLECTION_URL) throw new TypeError('Failed to fetch');
    throw new TypeError(`unexpected fetch ${url}`);
  });
});
afterEach(() => {
  metaSpy.mockRestore();
  fetchSpy.mockRestore();
  cardCache._reset();
  scryfallLimiter._reset?.();
});

describe('the stop line at Shopping.tsx:804 (DEC-1173 kill case for E4 and E5)', () => {
  it('gives the date of the prices shown, as the footer does, also when the file is older', async () => {
    const shown = formatPricesDate(new Date(FRESH).toISOString())!;
    const file = formatPricesDate(OLD)!;
    expect(shown).not.toBe(file);

    const { container } = render(<Shopping decks={[ALPHA]} />);
    for (const name of BUY) expect(cardCache.get(name)?.priceAsOf).toBe(FRESH);
    await waitFor(() => expect(metaSpy).toHaveBeenCalled());
    // The row of "Already own" shows, and it asks for its old price again.
    fireEvent.click(screen.getByRole('button', { name: /Already own/i }));
    await waitFor(() => expect(localStorage.getItem(STOP_KEY)).not.toBeNull());
    expect(cardCache.pricePending('Sol Ring')).toBe(true);
    for (const name of BUY) expect(cardCache.pricePending(name)).toBe(false);

    await waitFor(() => expect(screen.getByText(/Price refresh paused/)).toBeInTheDocument(), { timeout: 3_000 });
    const line = container.querySelector('.gv1-shop-paused')!;
    expect(line.textContent).toMatch(new RegExp(`^Price refresh paused\\. Prices shown are from ${shown}\\. Next try at `));
    expect(line.textContent).not.toContain(file);
    // The footer gives the same date.
    expect(container.querySelector('.gv1-shop-foot')!.textContent).toContain(`as of ${shown}.`);
  });
});
