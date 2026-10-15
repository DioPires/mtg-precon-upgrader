// DEC-1163 kill case (review of PR #65, DEC-1154): the import message keeps the style of each
// of its parts in its new region. Put in src/__tests__/components/ to run.

import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { Shopping } from '../../components/organisms/Shopping';
import type { DeckFull } from '../../data/types';

const STORAGE_KEY = 'grimoire-owned-cards';

const ALPHA = {
  idx: 1, slug: 'alpha', deckName: 'Alpha', commander: 'Alpha Commander', commanderMv: '—',
  type: 'Commander · Theme', colors: '🔴', bracket: '4', status: 'physical', pt: '—', winTurn: '—',
  winRate: null, flavor: '', oracle: [], strategy: '', wincons: [], engine: [], combos: [], apothecary: null,
  curve: [], func: [], sources: [],
  list: [
    { name: 'Commander', cards: [{ n: 'Alpha Commander', mv: '—', type: 'Creature', price: '—', gc: false }] },
    { name: 'Ramp (1)', cards: [{ n: 'Sol Ring', mv: '—', type: 'Artifact', price: '—', gc: false }] },
  ],
  health: { score: 70, grade: 'B' }, assessment: null, composition: { totalCards: 100, lands: 36, avgCmc: 2.8 },
  sim: null, rawDecklist: [], physicalDecklist: [], synergies: [], gameChangers: 0, tokens: [],
} satisfies DeckFull;

beforeEach(() => localStorage.removeItem(STORAGE_KEY));
afterEach(() => localStorage.removeItem(STORAGE_KEY));

// Each part of the message box: its tag, its class and its text.
const parts = (region: HTMLElement) =>
  [...(region.firstElementChild?.children ?? [])].map((el) => [el.tagName, el.className, el.textContent]);

describe('the import message keeps its style in its region (DEC-1163 kill case)', () => {
  it('gives the sigil and the text of a count and of an error the mono class', async () => {
    const { container } = render(<Shopping decks={[ALPHA]} />);
    const input = container.querySelector<HTMLInputElement>('#gv1-shop-owned-file')!;
    // jsdom's File has no text(), so the test gives it one.
    const pick = (body: string) => {
      const file = new File([body], 'owned.txt', { type: 'text/plain' });
      Object.defineProperty(file, 'text', { value: () => Promise.resolve(body) });
      fireEvent.change(input, { target: { files: [file] } });
    };
    const section = screen.getByRole('button', { name: 'Import owned cards' }).closest('section')!;
    const status = within(section).getByRole('status');
    const alert = within(section).getByRole('alert');

    pick('Sol Ring\n');
    await waitFor(() => expect(status).toHaveTextContent('Added 1 unique card (1 total).'));
    expect(parts(status)).toEqual([
      ['SPAN', 'gv1-mono-xs', '◆'],
      ['SPAN', 'gv1-mono-xs', 'Added 1 unique card (1 total). 1 card loaded. To replace the list, use Clear owned first.'],
    ]);

    pick('\n');
    await waitFor(() => expect(alert).toHaveTextContent('No cards detected in that file.'));
    expect(parts(alert)).toEqual([
      ['SPAN', 'gv1-mono-xs', '⚠'],
      ['SPAN', 'gv1-mono-xs', 'No cards detected in that file.'],
    ]);
  });
});
