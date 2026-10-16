// DEC-1174 reviewer kill case for M10 (a price refresh beside Decklist's enqueue,
// Decklist.tsx:147). Passes on the head of PR #75 and fails on M10.
// The deck list's cmc pass enqueues a card with no cmc or with mv '—' (a card
// with no mana cost, such as Ancestral Vision). For a name of the file the cache
// has a loaded entry, so that enqueue sends nothing, at any date (DEC-1172).
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Decklist } from '../../components/organisms/Decklist';
import { cardCache } from '../../data/cardCache';
import { LOOKUP_SPACING_MS } from '../../data/scryfallLimiter';
import type { DeckListGroup, RawCardMetadata } from '../../data/types';

const FILE: RawCardMetadata = {
  // No mana cost: the deck list shows mv '—' and asks the cache for its cmc.
  'Ancestral Vision': { cmc: 0, image: 'front/a/v/av.jpg?1', mana_cost: '', type_line: 'Sorcery', usd: 3.1, eur: 2.8 },
  // No cmc in the file (the field is optional).
  'Sol Ring': { image: 'front/s/r/sr.jpg?1', mana_cost: '{1}', type_line: 'Artifact', usd: 1.42, eur: 1.06 },
};
const old = () => new Date(Date.now() - 2 * 24 * 3_600_000).toISOString();

const LIST: DeckListGroup[] = [
  { name: 'Card draw (1)', cards: [{ n: 'Ancestral Vision', mv: '—', type: 'Sorcery', price: '—', gc: false, cmc: 0 }] },
  { name: 'Ramp (1)', cards: [{ n: 'Sol Ring', mv: '{1}', type: 'Artifact', price: '—', gc: false }] },
];

function clearStorage() {
  for (let i = window.localStorage.length - 1; i >= 0; i--) {
    const k = window.localStorage.key(i);
    if (k) window.localStorage.removeItem(k);
  }
}

let fetchSpy: MockInstance<typeof fetch>;

beforeEach(() => {
  cardCache._reset();
  clearStorage();
  fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(
    async () => new Response(JSON.stringify({ object: 'list', not_found: [], data: [] }), { status: 200 }),
  );
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('DEC-1174 kill: the deck list of a deck page', () => {
  it('asks for no price for a name of the file that it looks up for its cmc, with prices older than 24 h', async () => {
    const refreshSpy = vi.spyOn(cardCache, 'refreshPrice');
    cardCache.seed(FILE, old());
    render(
      <MemoryRouter initialEntries={['/deck/x']}>
        <Decklist list={LIST} commander="Captain" />
      </MemoryRouter>,
    );
    await new Promise((r) => setTimeout(r, LOOKUP_SPACING_MS + 300));
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(refreshSpy).not.toHaveBeenCalled();
    expect(cardCache.pricePending('Ancestral Vision')).toBe(false);
    expect(cardCache.pricePending('Sol Ring')).toBe(false);
  });
});
