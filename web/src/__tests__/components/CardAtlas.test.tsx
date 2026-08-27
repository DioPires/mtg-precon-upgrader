// DEC-568 — brewing-deck usage renders in its own section, never merged into
// the built-deck list, and never counted in USED IN.

import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { CardAtlas } from '../../components/organisms/CardAtlas';
import type { DeckFull } from '../../data/types';

function makeDeck(over: Partial<DeckFull>): DeckFull {
  return {
    idx: 1,
    slug: 'alpha',
    deckName: 'Alpha',
    commander: 'Commander A',
    commanderMv: '—',
    type: 'Commander · Theme',
    colors: '🔴',
    bracket: '4',
    status: 'physical',
    pt: '—',
    winTurn: '—',
    winRate: null,
    flavor: '',
    oracle: [],
    strategy: '',
    wincons: [],
    engine: [],
    combos: [],
    apothecary: null,
    curve: [],
    func: [],
    sources: [],
    list: [],
    health: null,
    assessment: null,
    composition: null,
    sim: null,
    rawDecklist: [],
    physicalDecklist: [],
    synergies: [],
    gameChangers: 0,
    tokens: [],
    ...over,
  };
}

const DECKS: DeckFull[] = [
  makeDeck({
    slug: 'physical-deck',
    deckName: 'Physical Tome',
    commander: 'Commander P',
    status: 'physical',
    rawDecklist: [{ name: 'Sol Ring', type: 'Artifact', primary_role: 'ramp' }],
  }),
  makeDeck({
    slug: 'brewing-deck',
    deckName: 'Brewing Tome',
    commander: 'Commander B',
    status: 'brewing',
    rawDecklist: [
      { name: 'Sol Ring', type: 'Artifact', primary_role: 'ramp' },
      { name: 'Teferi, Hero of Dominaria', type: 'Planeswalker', primary_role: 'engine' },
    ],
  }),
];

function renderAtlas() {
  // The suggestion list is local-first; block the Scryfall fallback so the
  // debounced fetch cannot bleed into assertions.
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, json: async () => ({}) })));
  return render(
    <MemoryRouter>
      <CardAtlas decks={DECKS} />
    </MemoryRouter>,
  );
}

function search(name: string) {
  const input = screen.getByLabelText('card name');
  fireEvent.change(input, { target: { value: name } });
  fireEvent.keyDown(input, { key: 'Enter' });
}

/** The `<div>` holding a header stat, located by its label. */
function stat(label: string): HTMLElement {
  return screen.getByText(label).parentElement as HTMLElement;
}

describe('CardAtlas brewing section (DEC-568)', () => {
  it('counts only built decks in USED IN and reports brewing separately', () => {
    renderAtlas();
    search('Sol Ring');

    expect(within(stat('USED IN')).getByText('1')).toBeTruthy();
    expect(within(stat('BREWING')).getByText('1')).toBeTruthy();

    // Both decks are listed, but in separate sections.
    expect(screen.getByText('Physical Tome')).toBeTruthy();
    const brewingSection = screen.getByRole('region', { name: /IN BREWING DECKS/i });
    expect(within(brewingSection).getByText('Brewing Tome')).toBeTruthy();
    expect(within(brewingSection).queryByText('Physical Tome')).toBeNull();
  });

  it('shows a brewing-only card with an empty built list and a brewing row', () => {
    renderAtlas();
    search('Teferi, Hero of Dominaria');

    expect(within(stat('USED IN')).getByText('0')).toBeTruthy();
    expect(within(stat('BREWING')).getByText('1')).toBeTruthy();
    expect(screen.getByText(/only appears in the brewing decks below/i)).toBeTruthy();

    const brewingSection = screen.getByRole('region', { name: /IN BREWING DECKS/i });
    expect(within(brewingSection).getByText('Brewing Tome')).toBeTruthy();
    expect(within(brewingSection).getByText('Engine')).toBeTruthy();
  });

  it('omits the brewing section for a card no brewing deck uses', () => {
    renderAtlas();
    search('Commander P');

    expect(within(stat('USED IN')).getByText('1')).toBeTruthy();
    expect(within(stat('BREWING')).getByText('—')).toBeTruthy();
    expect(screen.queryByRole('region', { name: /IN BREWING DECKS/i })).toBeNull();
  });

  it('badges brewing-only names in the autocomplete instead of falling through to Scryfall', () => {
    renderAtlas();
    const input = screen.getByLabelText('card name');
    fireEvent.change(input, { target: { value: 'Teferi' } });

    const option = screen.getByRole('option', { name: /Teferi, Hero of Dominaria/ });
    expect(within(option).getByText('brewing')).toBeTruthy();
    expect(within(option).queryByText('scryfall')).toBeNull();

    fireEvent.change(input, { target: { value: 'Sol Ring' } });
    const built = screen.getByRole('option', { name: /Sol Ring/ });
    expect(within(built).getByText('in tomes')).toBeTruthy();
  });
});
