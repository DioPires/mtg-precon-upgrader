// DEC-1148 review, note N1: the two paths that leave the key target set.
// These cases pass on the merged head: they show the stale target, not a fix.
import { describe, expect, it } from 'vitest';
import { act, fireEvent, render } from '@testing-library/react';
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
function Parent({ start, refuse }: { start: number; refuse: boolean }) {
  const [active, setActive] = useState(start);
  route = setActive;
  return (
    <DeckSelector decks={makeDecks(5)} activeIdx={active} onSelect={refuse ? () => {} : setActive} />
  );
}

describe('DEC-1148 N1 demo: a stale key target', () => {
  it('a parent that refuses the pick: a later route to that deck takes focus', () => {
    const { getAllByRole } = render(<Parent start={3} refuse />);
    const tabs = getAllByRole('tab');
    act(() => tabs[2].focus());
    fireEvent.keyDown(tabs[2], { key: 'End' });
    expect(tabs[2]).toHaveAttribute('aria-selected', 'true');
    act(() => route(5));
    expect(document.activeElement).toBe(tabs[4]);
  });

  it('two keys before one commit, the second on the open deck: a later route takes focus', () => {
    const { getAllByRole } = render(<Parent start={1} refuse={false} />);
    const tabs = getAllByRole('tab');
    act(() => tabs[0].focus());
    act(() => {
      fireEvent.keyDown(tabs[0], { key: 'End' });
      fireEvent.keyDown(tabs[0], { key: 'Home' });
    });
    expect(tabs[0]).toHaveAttribute('aria-selected', 'true');
    expect(document.activeElement).toBe(tabs[0]);
    act(() => route(5));
    expect(document.activeElement).toBe(tabs[4]);
  });
});
