// DEC-1148 review: kill cases for the surviving mutants M4, M5, M15 and M18.
// Each passes on the merged head and fails on its mutant.
import { afterEach, describe, expect, it, vi } from 'vitest';
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
function Harness({ decks, start }: { decks: DeckStub[]; start: number }) {
  const [active, setActive] = useState(start);
  route = setActive;
  return <DeckSelector decks={decks} activeIdx={active} onSelect={setActive} />;
}

describe('DEC-1148 kill cases', () => {
  afterEach(() => vi.restoreAllMocks());

  it('M4: moves no focus when a route returns to the deck that an earlier key picked', () => {
    const { getAllByRole } = render(<Harness decks={makeDecks(5)} start={3} />);
    const tabs = getAllByRole('tab');
    act(() => tabs[2].focus());
    fireEvent.keyDown(tabs[2], { key: 'End' });
    expect(document.activeElement).toBe(tabs[4]);
    // A click on deck 1. A browser focuses the pill on the press.
    act(() => tabs[0].focus());
    fireEvent.click(tabs[0]);
    // Browser Back to deck 5: no key started this change.
    act(() => route(5));
    expect(tabs[4]).toHaveAttribute('aria-selected', 'true');
    expect(document.activeElement).toBe(tabs[0]);
  });

  it('M5: focuses with preventScroll, so the focus does not cut the centring short', () => {
    const { getAllByRole } = render(<Harness decks={makeDecks(5)} start={3} />);
    const tabs = getAllByRole('tab');
    act(() => tabs[2].focus());
    const focus = vi.spyOn(HTMLElement.prototype, 'focus');
    fireEvent.keyDown(tabs[2], { key: 'ArrowRight' });
    expect(focus).toHaveBeenCalledTimes(1);
    expect(focus).toHaveBeenCalledWith({ preventScroll: true });
  });

  it('M15: focuses the pill, not an active element earlier in the page', () => {
    // The topbar's nav item for the open page carries `gv1-active` too.
    const { getAllByRole } = render(
      <>
        <a className="gv1-nav-item gv1-active" href="/deck/deck-3">
          Guide
        </a>
        <Harness decks={makeDecks(5)} start={3} />
      </>,
    );
    const tabs = getAllByRole('tab');
    act(() => tabs[2].focus());
    fireEvent.keyDown(tabs[2], { key: 'End' });
    expect(document.activeElement).toBe(tabs[4]);
  });

  it("M18: reports the key's pick to onSelect when the key picks the open deck", () => {
    const onSelect = vi.fn();
    const { getAllByRole } = render(
      <DeckSelector decks={makeDecks(5)} activeIdx={1} onSelect={onSelect} />,
    );
    const tabs = getAllByRole('tab');
    act(() => tabs[0].focus());
    fireEvent.keyDown(tabs[0], { key: 'Home' });
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(1);
  });
});
