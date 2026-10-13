import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/react';
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

// jsdom implements neither method; install recorders for the duration.
type Scrollable = {
  scrollTo?: (opts: ScrollToOptions) => void;
  scrollIntoView?: (opts: ScrollIntoViewOptions) => void;
};

describe('DeckSelector scroll (DEC-1008)', () => {
  const proto = Element.prototype as unknown as Scrollable;
  const original = { scrollTo: proto.scrollTo, scrollIntoView: proto.scrollIntoView };
  let scrollTo: ReturnType<typeof vi.fn>;
  let intoViewTargets: string[];

  beforeEach(() => {
    scrollTo = vi.fn();
    intoViewTargets = [];
    proto.scrollTo = scrollTo;
    proto.scrollIntoView = function (this: Element) {
      intoViewTargets.push(this.className);
    };
  });
  afterEach(() => {
    proto.scrollTo = original.scrollTo;
    proto.scrollIntoView = original.scrollIntoView;
  });

  it('scrolls the track to the active pill and never calls scrollIntoView on the pill', () => {
    const decks = makeDecks(5);
    const { rerender } = render(<DeckSelector decks={decks} activeIdx={5} onSelect={() => {}} />);

    expect(scrollTo).toHaveBeenCalledTimes(1);
    expect(scrollTo).toHaveBeenLastCalledWith(expect.objectContaining({ behavior: 'smooth' }));
    // scrollIntoView on the pill scrolls every ancestor, `.gv1-root` included.
    expect(intoViewTargets).toEqual(['gv1-selector-track']);

    rerender(<DeckSelector decks={decks} activeIdx={2} onSelect={() => {}} />);
    expect(scrollTo).toHaveBeenCalledTimes(2);
    expect(intoViewTargets).toEqual(['gv1-selector-track', 'gv1-selector-track']);
  });
});
