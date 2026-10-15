import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { CardTile } from '../../components/molecules/CardTile';
import { cardCache } from '../../data/cardCache';
import type { RawCardMetadata } from '../../data/types';
import { COLLECTION_URL } from '../../data/scryfallLimiter';
import { cardJson, collectionJson, identifiersOf } from '../data/scryfallFakes';

const SOL_RING = 'front/8/e/8ee443cc-e17a-493b-9c93-1f9e141a30e4.jpg?1789644446';
const FILE: RawCardMetadata = {
  'Sol Ring': { cmc: 1, image: SOL_RING, mana_cost: '{1}', type_line: 'Artifact', usd: 1.42, eur: 1.06 },
  "Agadeem's Awakening": {
    cmc: 3,
    image: 'front/6/7/67f4c93b-080c-4196-b095-6a120a221988.jpg?1783929388',
    mana_cost: '{X}{B}{B}{B}',
    type_line: 'Sorcery // Land',
    usd: null,
    eur: null,
  },
};

// The date of the file's prices: now, so that no price is older than 24 h; and two days ago.
const fresh = () => new Date().toISOString();
const old = () => new Date(Date.now() - 2 * 24 * 3_600_000).toISOString();
const batchAnswer = (cards: object[]) =>
  new Response(JSON.stringify({ object: 'list', not_found: [], data: cards }), { status: 200 });

function clearStorage() {
  for (let i = window.localStorage.length - 1; i >= 0; i--) {
    const k = window.localStorage.key(i);
    if (k) window.localStorage.removeItem(k);
  }
}

const tileImg = () => document.querySelector<HTMLImageElement>('img.gv1-card-tile-img');
let fetchSpy: MockInstance<typeof fetch>;

beforeEach(() => {
  cardCache._reset();
  clearStorage();
  fetchSpy = vi.spyOn(globalThis, 'fetch');
});

afterEach(() => {
  fetchSpy.mockRestore();
});

describe('CardTile', () => {
  it("takes a deck card's picture from card-metadata.json and sends no request", async () => {
    cardCache.seed(FILE, fresh());
    render(<CardTile card={{ n: 'Sol Ring', mv: '{1}', type: 'Artifact' }} />);
    expect(tileImg()?.getAttribute('src')).toBe(`https://cards.scryfall.io/normal/${SOL_RING}`);
    expect(screen.getByText('$1.42')).toBeInTheDocument();
    await new Promise((r) => setTimeout(r, 50));
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("keeps the deck file's price first; the card entry fills only a blank", () => {
    cardCache.seed(FILE, fresh());
    render(<CardTile card={{ n: 'Sol Ring', price: '$9.99' }} />);
    expect(screen.getByText('$9.99')).toBeInTheDocument();
    expect(screen.queryByText('$1.42')).toBeNull();
  });

  it('shows no price for a card whose USD price is null', () => {
    cardCache.seed(FILE, fresh());
    render(<CardTile card={{ n: "Agadeem's Awakening" }} />);
    expect(tileImg()?.getAttribute('src')).toContain('https://cards.scryfall.io/normal/front/6/7/');
    expect(screen.getByText('—', { selector: '.gv1-card-tile-foot .gv1-rune' })).toBeInTheDocument();
  });

  it('looks a seeded card up once when its picture fails, and shows the new address', async () => {
    fetchSpy.mockResolvedValue(new Response(JSON.stringify(collectionJson(['Sol Ring'])), { status: 200 }));
    cardCache.seed(FILE, fresh());
    render(<CardTile card={{ n: 'Sol Ring' }} />);
    fireEvent.error(tileImg()!);
    await waitFor(() => expect(tileImg()?.getAttribute('src')).toBe(cardJson('Sol Ring').image_uris.normal));
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(String(fetchSpy.mock.calls[0][0])).toBe(COLLECTION_URL);
    expect(identifiersOf(fetchSpy.mock.calls[0][1]?.body)).toEqual(['Sol Ring']);

    // The new address fails too: the glyph shows, and nothing more is sent.
    fireEvent.error(tileImg()!);
    await new Promise((r) => setTimeout(r, 50));
    expect(tileImg()).toBeNull();
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it('looks up a name that the file lacks, and takes image_small when image_normal is missing', async () => {
    const card = { ...cardJson('Mana Crypt'), image_uris: { small: 'https://cards.scryfall.io/small/mc.jpg' } };
    fetchSpy.mockResolvedValue(batchAnswer([card]));
    render(<CardTile card={{ n: 'Mana Crypt' }} />);
    expect(tileImg()).toBeNull();
    await waitFor(() => expect(tileImg()?.getAttribute('src')).toBe('https://cards.scryfall.io/small/mc.jpg'));
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  // DEC-1131 R1, option B: the tile foot refreshes a price older than 24 h.
  it("asks once for the cache's price when it is older than 24 h, and shows the new one", async () => {
    fetchSpy.mockResolvedValue(batchAnswer([{ ...cardJson('Sol Ring'), prices: { usd: '2.50' } }]));
    cardCache.seed(FILE, old());
    render(<CardTile card={{ n: 'Sol Ring' }} />);
    expect(screen.getByText('$1.42')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('$2.50')).toBeInTheDocument());
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(identifiersOf(fetchSpy.mock.calls[0][1]?.body)).toEqual(['Sol Ring']);
    // The picture stays the file's.
    expect(tileImg()?.getAttribute('src')).toBe(`https://cards.scryfall.io/normal/${SOL_RING}`);
  });

  it('asks nothing for a tile that shows the deck file\'s highlight price', async () => {
    cardCache.seed(FILE, old());
    render(<CardTile card={{ n: 'Sol Ring', price: '$9.99' }} />);
    await new Promise((r) => setTimeout(r, 50));
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(cardCache.pricePending('Sol Ring')).toBe(false);
  });
});
