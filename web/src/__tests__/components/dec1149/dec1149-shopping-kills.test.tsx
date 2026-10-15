// DEC-1149 kill case (reviewer of PR #54) for R9: while a refresh of the buy rows
// is out, a new selection recomputes the estimate at once (ruling R7 of DEC-1149).
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Shopping } from '../../../components/organisms/Shopping';
import { cardCache } from '../../../data/cardCache';
import { deckLoader } from '../../../data/loader';
import { COLLECTION_URL } from '../../../data/scryfallLimiter';
import type { DeckFull, DeckListGroup, RawCardMetadata } from '../../../data/types';
import { identifiersOf } from '../../data/scryfallFakes';

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
  slug: 'alpha', deckName: 'Alpha', commander: 'Alpha Commander',
  list: [group('Commander', ['Alpha Commander']), group('Ramp (2)', ['Sol Ring', 'Arcane Signet']), group('Removal (1)', ['Swords to Plowshares'])],
});
const BETA = makeDeck({
  idx: 2, slug: 'beta', deckName: 'Beta', commander: 'Beta Commander',
  list: [group('Commander', ['Beta Commander']), group('Ramp (1)', ['Sol Ring']), group('Draw (1)', ['Rhystic Study'])],
});

const OLD = '2026-10-10T08:00:00+00:00';
const meta = (usd: number | null) => ({ cmc: 1, image: 'front/a/b/x.jpg', mana_cost: '{1}', type_line: 'Artifact', usd, eur: null });
const FILE: RawCardMetadata = {
  'Alpha Commander': meta(null), 'Sol Ring': meta(1.5), 'Arcane Signet': meta(0.5), 'Swords to Plowshares': meta(2),
  'Beta Commander': meta(5), 'Rhystic Study': meta(30.5),
};

let fetchSpy: MockInstance<typeof fetch>;
let release: () => void = () => undefined;

beforeEach(() => {
  cardCache._reset();
  deckLoader._reset();
  localStorage.clear();
  cardCache.seed(FILE, OLD);
  const held = new Promise<void>((resolve) => { release = resolve; });
  fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input);
    if (url.endsWith('/card-metadata.meta.json')) return new Response(JSON.stringify({ prices_as_of: OLD }), { status: 200 });
    if (url === COLLECTION_URL) {
      const names = identifiersOf(init?.body);
      await held;
      const data = names.map((name) => ({ name, prices: { usd: FILE[name].usd == null ? null : (FILE[name].usd! + 1).toFixed(2) } }));
      return new Response(JSON.stringify({ object: 'list', not_found: [], data }), { status: 200 });
    }
    throw new TypeError(`unexpected fetch ${url}`);
  });
});
afterEach(() => {
  release();
  fetchSpy.mockRestore();
  cardCache._reset();
});

const estimate = () => screen.getByText('EST. COST').parentElement!.querySelector('.gv1-serif-xl')!.textContent;

describe('R9 (reviewer kill)', () => {
  it('a new selection recomputes the estimate at once, also while a refresh of the buy rows is out', async () => {
    render(<Shopping decks={[ALPHA, BETA]} />);
    expect(estimate()).toBe('$4');
    await waitFor(() => expect(cardCache.pricePending('Sol Ring')).toBe(true));
    fireEvent.click(screen.getByRole('button', { name: /Add Beta/i }));
    // $4 + Beta Commander $5 + Sol Ring again $1.50 + Rhystic Study $30.50
    expect(estimate()).toBe('$41');
  });
});

describe('R12 (reviewer kill)', () => {
  it('the stop line shows when only the rows of "Already own" wait for a refresh', async () => {
    const { saveOwned } = await import('../../../data/ownedCards');
    const { STOP_KEY } = await import('../../../data/scryfallLimiter');
    saveOwned(new Map([['Alpha Commander', 1], ['Sol Ring', 1], ['Arcane Signet', 1], ['Swords to Plowshares', 1]]));
    fetchSpy.mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/card-metadata.meta.json')) return new Response(JSON.stringify({ prices_as_of: OLD }), { status: 200 });
      throw new TypeError('Failed to fetch');
    });
    render(<Shopping decks={[ALPHA, BETA]} />);
    fireEvent.click(screen.getByRole('button', { name: /Already own/i }));
    await waitFor(() => expect(localStorage.getItem(STOP_KEY)).not.toBeNull());
    expect(cardCache.pricePending('Sol Ring')).toBe(true);
    await waitFor(() => expect(screen.getByText(/Price refresh paused/)).toBeInTheDocument(), { timeout: 3_000 });
  });
});
