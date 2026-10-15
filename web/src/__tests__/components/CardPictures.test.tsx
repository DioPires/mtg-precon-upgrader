// DEC-1102: the hover frame and the commander art take their pictures from the
// card entry. No `format=image` address, no request to our own host.

import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { GV1CardHoverLayer } from '../../components/global/GV1CardHoverLayer';
import { GV1CommanderArt } from '../../components/molecules/GV1CommanderArt';
import { cardCache } from '../../data/cardCache';
import type { RawCardMetadata } from '../../data/types';
import { cardJson } from '../data/scryfallFakes';

const ATLA = 'front/1/2/12345678-0000-0000-0000-000000000000.jpg?1700000000';
const FILE: RawCardMetadata = {
  'Atla Palani, Nest Tender': {
    cmc: 4,
    image: ATLA,
    mana_cost: '{1}{R}{G}{W}',
    type_line: 'Legendary Creature — Human Shaman',
    usd: 0.31,
    eur: 0.2,
  },
};

function clearStorage() {
  for (let i = window.localStorage.length - 1; i >= 0; i--) {
    const k = window.localStorage.key(i);
    if (k) window.localStorage.removeItem(k);
  }
}

let fetchSpy: MockInstance<typeof fetch>;
let answer: (response: Response) => void;

beforeEach(() => {
  cardCache._reset();
  clearStorage();
  // A lookup stays out until the case answers it.
  fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(
    () => new Promise<Response>((resolve) => { answer = resolve; }),
  );
});

afterEach(() => {
  fetchSpy.mockRestore();
});

const hoverImg = () => document.querySelector<HTMLImageElement>('.gv1-cardhover img');
const noFormatImage = () =>
  expect(document.body.innerHTML).not.toMatch(/format=image|api\.scryfall\.com|\/data\/images\/cards/);

async function hover(name: string) {
  fireEvent.mouseOver(screen.getByText(name));
  // HOVER_DELAY_MS is 140.
  await act(() => new Promise((r) => setTimeout(r, 160)));
}

describe('GV1CardHoverLayer', () => {
  it("shows a deck card's image_large from the file and sends no request", async () => {
    cardCache.seed(FILE);
    render(
      <>
        <span data-card-name="Atla Palani, Nest Tender">Atla</span>
        <GV1CardHoverLayer />
      </>,
    );
    await hover('Atla');
    expect(hoverImg()?.getAttribute('src')).toBe(`https://cards.scryfall.io/large/${ATLA}`);
    expect(fetchSpy).not.toHaveBeenCalled();
    noFormatImage();
  });

  it('puts a name with no entry first in the queue and shows the scrying frame until the entry arrives', async () => {
    const enqueue = vi.spyOn(cardCache, 'enqueue');
    render(
      <>
        <span data-card-name="Mana Crypt">Crypt</span>
        <GV1CardHoverLayer />
      </>,
    );
    await hover('Crypt');
    expect(enqueue).toHaveBeenCalledWith('Mana Crypt', { first: true });
    expect(screen.getByText('◆ scrying scryfall ◆')).toBeInTheDocument();
    expect(hoverImg()).toBeNull();
    noFormatImage();
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(1));
    expect(String(fetchSpy.mock.calls[0][0])).toBe('https://api.scryfall.com/cards/named?fuzzy=Mana%20Crypt');

    await act(async () => answer(new Response(JSON.stringify(cardJson('Mana Crypt')), { status: 200 })));
    await waitFor(() => expect(hoverImg()?.getAttribute('src')).toBe(cardJson('Mana Crypt').image_uris.large));
    enqueue.mockRestore();
  });

  it('shows the frame unavailable when the lookup fails', async () => {
    render(
      <>
        <span data-card-name="Nonesuch">Nonesuch</span>
        <GV1CardHoverLayer />
      </>,
    );
    await hover('Nonesuch');
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(1));
    await act(async () => answer(new Response('{}', { status: 404 })));
    await waitFor(() => expect(screen.getByText('◇ frame unavailable')).toBeInTheDocument());
    expect(hoverImg()).toBeNull();
  });
});

describe('GV1CommanderArt', () => {
  it("takes art_crop from the file's entry and sends no request", async () => {
    cardCache.seed(FILE);
    render(<GV1CommanderArt name="Atla Palani, Nest Tender" slug="broodfire-hatchery" />);
    const img = document.querySelector<HTMLImageElement>('img.gv1-cmd-art-img')!;
    expect(img.getAttribute('src')).toBe(`https://cards.scryfall.io/art_crop/${ATLA}`);
    fireEvent.load(img);
    expect(img.className).toContain('gv1-loaded');
    expect(screen.getByText('◇ scryfall.com · art_crop')).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
    noFormatImage();
  });

  it('looks up a commander that the file lacks before the queue, and scries until it arrives', async () => {
    const enqueue = vi.spyOn(cardCache, 'enqueue');
    render(<GV1CommanderArt name="Mana Crypt" slug="x" />);
    expect(enqueue).toHaveBeenCalledWith('Mana Crypt', { first: true });
    expect(screen.getByText('◆ SCRYING SCRYFALL ◆')).toBeInTheDocument();
    expect(document.querySelector('img.gv1-cmd-art-img')).toBeNull();
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(1));
    await act(async () => answer(new Response(JSON.stringify(cardJson('Mana Crypt')), { status: 200 })));
    await waitFor(() =>
      expect(document.querySelector('img.gv1-cmd-art-img')?.getAttribute('src')).toBe(
        cardJson('Mana Crypt').image_uris.art_crop,
      ),
    );
    enqueue.mockRestore();
  });
});
