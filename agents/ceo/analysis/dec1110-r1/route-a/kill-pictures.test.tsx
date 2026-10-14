// DEC-1110 reviewer's kill cases for the picture components. Each passes on
// 58ca0b3 and fails on the mutant named in its title.
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import type { MockInstance } from 'vitest';
import { GV1CardHoverLayer } from '../../components/global/GV1CardHoverLayer';
import { GV1CommanderArt } from '../../components/molecules/GV1CommanderArt';
import { cardCache } from '../../data/cardCache';
import type { RawCardMetadata } from '../../data/types';
import { cardJson } from '../data/scryfallFakes';

const ATLA = 'front/1/2/12345678-0000-0000-0000-000000000000.jpg?1700000000';
const NAME = 'Atla Palani, Nest Tender';
const FILE: RawCardMetadata = {
  [NAME]: { cmc: 4, image: ATLA, mana_cost: '{1}{R}{G}{W}', type_line: 'Legendary Creature', usd: 0.31, eur: 0.2 },
};
const LOOKUP = 'https://api.scryfall.com/cards/named?fuzzy=Atla%20Palani%2C%20Nest%20Tender';

let fetchSpy: MockInstance<typeof fetch>;
let answer: (response: Response) => void;

beforeEach(() => {
  cardCache._reset();
  window.localStorage.clear();
  fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(
    () => new Promise<Response>((resolve) => { answer = resolve; }),
  );
  cardCache.seed(FILE);
});
afterEach(() => {
  fetchSpy.mockRestore();
});

describe('K13b, A8: GV1CommanderArt when the picture from the file fails', () => {
  it('K13b, A8: shows the glyph, looks the card up once, and shows the new art_crop', async () => {
    render(<GV1CommanderArt name={NAME} slug="broodfire-hatchery" />);
    const img = document.querySelector<HTMLImageElement>('img.gv1-cmd-art-img')!;
    expect(img.getAttribute('src')).toBe(`https://cards.scryfall.io/art_crop/${ATLA}`);
    fireEvent.error(img);
    expect(document.querySelector('img.gv1-cmd-art-img')).toBeNull();
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(1));
    expect(String(fetchSpy.mock.calls[0][0])).toBe(LOOKUP);
    await act(async () => answer(new Response(JSON.stringify(cardJson(NAME)), { status: 200 })));
    await waitFor(() =>
      expect(document.querySelector('img.gv1-cmd-art-img')?.getAttribute('src')).toBe(cardJson(NAME).image_uris.art_crop),
    );
  });
});

describe('K13c, A9: GV1CardHoverLayer when the frame from the file fails', () => {
  it('K13c, A9: shows the frame unavailable, looks the card up once, and shows the new frame', async () => {
    render(
      <>
        <span data-card-name={NAME}>Atla</span>
        <GV1CardHoverLayer />
      </>,
    );
    fireEvent.mouseOver(screen.getByText('Atla'));
    await act(() => new Promise((r) => setTimeout(r, 160)));
    const img = document.querySelector<HTMLImageElement>('.gv1-cardhover img')!;
    expect(img.getAttribute('src')).toBe(`https://cards.scryfall.io/large/${ATLA}`);
    fireEvent.error(img);
    expect(screen.getByText('◇ frame unavailable')).toBeInTheDocument();
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(1));
    expect(String(fetchSpy.mock.calls[0][0])).toBe(LOOKUP);
    await act(async () => answer(new Response(JSON.stringify(cardJson(NAME)), { status: 200 })));
    await waitFor(() =>
      expect(document.querySelector('.gv1-cardhover img')?.getAttribute('src')).toBe(cardJson(NAME).image_uris.large),
    );
  });
});
