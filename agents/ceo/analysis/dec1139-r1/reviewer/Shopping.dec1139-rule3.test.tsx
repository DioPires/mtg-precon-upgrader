// DEC-1139 review: evidence for the rule-3 class (counts of 0 or below, and the
// non-integer counts that only a hand-edited storage value gives). Not a kill
// case for the pull request. Each case logs the texts, then asserts the head's.
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

const pickCsv = (input: HTMLInputElement, body: string) => {
  const file = new File([body], 'owned.csv', { type: 'text/csv' });
  Object.defineProperty(file, 'text', { value: () => Promise.resolve(body) });
  fireEvent.change(input, { target: { files: [file] } });
};
const barText = (c: HTMLElement) => c.querySelector('.gv1-shop-owned-bar .gv1-mono-xs.gv1-dim')?.textContent;

describe('DEC-1139 rule-3 evidence', () => {
  beforeEach(() => localStorage.removeItem(STORAGE_KEY));
  afterEach(() => localStorage.removeItem(STORAGE_KEY));

  it('E1: CSV `Sol Ring,-1`', async () => {
    const { container } = render(<Shopping decks={[ALPHA]} />);
    pickCsv(container.querySelector<HTMLInputElement>('#gv1-shop-owned-file')!, 'Name,Quantity\nSol Ring,-1\n');
    await waitFor(() => expect(screen.getByRole('status')).toBeInTheDocument());
    console.log(`E1 message=[${screen.getByRole('status').textContent}] bar=[${barText(container)}]`);
    expect(screen.getByRole('status')).toHaveTextContent(`Added 1 unique card (-1 total). -1 cards loaded. ${hint}`);
    expect(barText(container)).toBe('-1 cards loaded — saved locally');
  });

  it('E2: CSV `Sol Ring,-1` and `Arcane Signet,1`', async () => {
    const { container } = render(<Shopping decks={[ALPHA]} />);
    pickCsv(container.querySelector<HTMLInputElement>('#gv1-shop-owned-file')!,
      'Name,Quantity\nSol Ring,-1\nArcane Signet,1\n');
    await waitFor(() => expect(screen.getByRole('status')).toBeInTheDocument());
    console.log(`E2 message=[${screen.getByRole('status').textContent}] bar=[${barText(container)}]`);
    expect(screen.getByRole('status')).toHaveTextContent(`Added 2 unique cards (0 total). 0 cards loaded. ${hint}`);
    expect(barText(container)).toBe('0 cards loaded — saved locally');
  });

  it.each([
    ['E3', '[["Sol Ring",0.5]]', '0.5 cards loaded — saved locally'],
    ['E4', '[["Sol Ring",1.5]]', '1.5 cards loaded — saved locally'],
    ['E5', '[["Sol Ring"]]', 'NaN cards loaded — saved locally'],
  ])('%s: storage %s', (id, raw, want) => {
    localStorage.setItem(STORAGE_KEY, raw);
    const { container } = render(<Shopping decks={[ALPHA]} />);
    console.log(`${id} bar=[${barText(container)}]`);
    expect(barText(container)).toBe(want);
  });
});
