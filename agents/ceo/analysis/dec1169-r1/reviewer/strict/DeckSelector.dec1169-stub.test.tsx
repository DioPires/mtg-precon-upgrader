// DEC-1169 check 1.3: a click on a stub pill, then a deck change that no key started.
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render } from '@testing-library/react';
import { useState } from 'react';
import { DeckSelector } from '../../components/organisms/DeckSelector';
import type { DeckStub } from '../../data/types';

function makeDecks(n: number): DeckStub[] {
  return Array.from({ length: n }, (_, i) => ({
    idx: i + 1, slug: `deck-${i + 1}`, name: `Deck ${i + 1}`, cmd: `Commander ${i + 1}`,
    colors: '🔴', bracket: '4', hasDetail: i !== 4, status: 'physical',
  }));
}
let route: (idx: number) => void = () => {};
function Harness({ start }: { start: number }) {
  const [active, setActive] = useState(start);
  route = setActive;
  return <DeckSelector decks={makeDecks(5)} activeIdx={active} onSelect={setActive} />;
}

describe('DEC-1169 stub pill', () => {
  afterEach(() => vi.restoreAllMocks());
  it('S9 a click on the stub pill opens nothing; Back then moves focus from it to the active pill', () => {
    const onSel = vi.fn();
    const { getAllByRole } = render(<Harness start={3} />);
    const tabs = getAllByRole('tab');
    expect(tabs[4]).toHaveClass('gv1-stub');
    expect(tabs[4]).toHaveAttribute('aria-disabled', 'true');
    act(() => tabs[4].focus()); // Chromium focuses the button on the press
    fireEvent.click(tabs[4]);
    expect(tabs[2]).toHaveAttribute('aria-selected', 'true');
    expect(onSel).not.toHaveBeenCalled();
    const focus = vi.spyOn(HTMLElement.prototype, 'focus');
    act(() => route(2));
    expect(document.activeElement).toBe(tabs[1]);
    expect(focus).toHaveBeenCalledTimes(1);
    expect(focus).toHaveBeenCalledWith({ preventScroll: true });
  });
});
