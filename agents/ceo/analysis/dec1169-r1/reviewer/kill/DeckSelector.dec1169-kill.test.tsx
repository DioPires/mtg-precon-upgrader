// DEC-1169 review of PR #69: kill case for the surviving mutant R1
// (`const left = !before.isConnected;`, no test that focus fell to `body`).
import { describe, expect, it } from 'vitest';
import { act, render } from '@testing-library/react';
import { useState } from 'react';
import { DeckSelector } from '../../components/organisms/DeckSelector';
import type { DeckStub } from '../../data/types';

function makeDecks(n: number): DeckStub[] {
  return Array.from({ length: n }, (_, i) => ({
    idx: i + 1,
    slug: `deck-${i + 1}`,
    name: `Deck ${i + 1}`,
    cmd: `Commander ${i + 1}`,
    colors: '🔴',
    bracket: '4',
    hasDetail: true,
    status: 'physical',
  }));
}

let route: (idx: number) => void = () => {};

// The guide around the selector: a chip that each deck mounts anew, and a
// field that deck 5 brings and that takes focus as it mounts (`autoFocus`).
// The deck change removes the focused chip and focuses the field in one
// commit, so focus does not fall to `body`.
function AutoFocusGuide({ decks, start }: { decks: DeckStub[]; start: number }) {
  const [active, setActive] = useState(start);
  route = setActive;
  return (
    <>
      <DeckSelector decks={decks} activeIdx={active} onSelect={setActive} />
      <button key={active} type="button">
        Board Wipes
      </button>
      {active === 5 && <input aria-label="Search" autoFocus />}
    </>
  );
}

describe('DEC-1169 kill cases for PR #69', () => {
  it('K1: moves no focus when the focused element left the page and another element took focus in the same update', () => {
    const { getAllByRole, getByRole } = render(<AutoFocusGuide decks={makeDecks(5)} start={3} />);
    const tabs = getAllByRole('tab');
    const chip = getByRole('button', { name: 'Board Wipes' });
    act(() => chip.focus());

    act(() => route(5));
    expect(chip.isConnected).toBe(false);
    expect(tabs[4]).toHaveAttribute('aria-selected', 'true');
    expect(document.activeElement).toBe(getByRole('textbox', { name: 'Search' }));
  });
});
