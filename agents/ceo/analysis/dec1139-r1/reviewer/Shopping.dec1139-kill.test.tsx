// DEC-1139 review: kill cases. K1 kills M2e (the `unique card` noun reads
// `merged.size` in place of `parsed.size`). K2 kills M1e (`count < 2`) and M1f
// (`count > 1 ? 'cards' : 'card'`): both give `card` for a count of 0.5, which
// the declared type `count: number` allows and a stored list can hold. Kept
// outside the tree; copied into web/src/__tests__/components/ only for the run.
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Shopping } from '../../components/organisms/Shopping';
import type { DeckFull, DeckListGroup } from '../../data/types';

function group(name: string, names: string[], type = 'Creature'): DeckListGroup {
  return { name, cards: names.map((n) => ({ n, mv: '—', type, price: '—', gc: false })) };
}

const ALPHA = {
  idx: 1, slug: 'alpha', deckName: 'Alpha', commander: 'Alpha Commander', commanderMv: '—',
  type: 'Commander · Theme', colors: '🔴', bracket: '4', status: 'physical', pt: '—', winTurn: '—',
  winRate: null, flavor: '', oracle: [], strategy: '', wincons: [], engine: [], combos: [],
  apothecary: null, curve: [], func: [], sources: [],
  list: [
    group('Commander', ['Alpha Commander']),
    group('Ramp (3)', ['Sol Ring', 'Arcane Signet', 'Forest']),
    group('Removal (1)', ['Swords to Plowshares']),
  ],
  health: { score: 70, grade: 'B' }, assessment: null,
  composition: { totalCards: 100, lands: 36, avgCmc: 2.8 }, sim: null, rawDecklist: [],
  physicalDecklist: [], synergies: [], gameChangers: 0, tokens: [],
} as DeckFull;

const STORAGE_KEY = 'grimoire-owned-cards';
const hint = 'To replace the list, use Clear owned first.';

// jsdom's File has no text(), so the test gives it one.
const pick = (input: HTMLInputElement, body: string) => {
  const file = new File([body], 'owned.txt', { type: 'text/plain' });
  Object.defineProperty(file, 'text', { value: () => Promise.resolve(body) });
  fireEvent.change(input, { target: { files: [file] } });
};

describe('DEC-1139 kill cases', () => {
  beforeEach(() => localStorage.removeItem(STORAGE_KEY));
  afterEach(() => localStorage.removeItem(STORAGE_KEY));

  it('K1: reads `1 unique card` for a one-name file when the list already holds another name', async () => {
    const { container } = render(<Shopping decks={[ALPHA]} />);
    const input = container.querySelector<HTMLInputElement>('#gv1-shop-owned-file')!;
    pick(input, 'Sol Ring\n');
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent(
      `Added 1 unique card (1 total). 1 card loaded. ${hint}`,
    ));

    // The file holds 1 unique card; the list then holds 2 unique cards and 2 cards.
    pick(input, 'Arcane Signet\n');
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent(
      `Added 1 unique card (1 total). 2 cards loaded. ${hint}`,
    ));
    expect(screen.getByText('2 cards loaded — saved locally')).toBeInTheDocument();
  });

  it('K2: reads `0.5 cards loaded` for a stored quantity of 0.5', () => {
    localStorage.setItem(STORAGE_KEY, '[["Sol Ring",0.5]]');
    render(<Shopping decks={[ALPHA]} />);
    expect(screen.getByText('0.5 cards loaded — saved locally')).toBeInTheDocument();
  });
});
