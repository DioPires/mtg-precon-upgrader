// DEC-1142 — the Combo Lab's message after it loads a deck URL.

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ComboLab } from '../../routes/ComboLab';
import { deckLoader } from '../../data/loader';
import { resolveDeckUrl, type ResolvedDeckList } from '../../lib/deckUrl';

vi.mock('../../lib/deckUrl', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../lib/deckUrl')>()),
  resolveDeckUrl: vi.fn(),
}));

const URL_FIELD = /Deck URL/;

function deck(cardNames: string[], commanderNames: string[]): ResolvedDeckList {
  return { site: 'archidekt', name: 'Test', cardNames, commanderNames, unresolved: [] };
}

async function load(resolved: ResolvedDeckList): Promise<void> {
  vi.mocked(resolveDeckUrl).mockResolvedValueOnce(resolved);
  render(
    <MemoryRouter initialEntries={['/combos?mode=paste']}>
      <ComboLab />
    </MemoryRouter>,
  );
  fireEvent.change(screen.getByLabelText(URL_FIELD), {
    target: { value: 'https://archidekt.com/decks/1/test' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Load' }));
  await screen.findByText(/^Loaded /);
}

describe('the Combo Lab load message', () => {
  beforeEach(() => {
    // The rail's deck index plays no part here; it stays pending.
    vi.spyOn(deckLoader, 'loadIndex').mockReturnValue(new Promise(() => {}));
  });

  // resolveDeckUrl refuses only a deck with no cards and no commander, so a deck
  // of one card and two commanders loads. The noun follows the card count.
  it('reads `Loaded 1 card` for a deck of one card', async () => {
    await load(deck(['Sol Ring'], ['Kraum, Ludevic’s Opus', 'Tymna the Weaver']));
    expect(screen.getByText('Loaded 1 card from archidekt — “Test”. Review, then Analyze.')).toBeInTheDocument();
  });

  it('reads `Loaded 2 cards` for a deck of two cards', async () => {
    await load(deck(['Sol Ring', 'Arcane Signet'], ['Meren of Clan Nel Toth']));
    expect(screen.getByText('Loaded 2 cards from archidekt — “Test”. Review, then Analyze.')).toBeInTheDocument();
  });
});
