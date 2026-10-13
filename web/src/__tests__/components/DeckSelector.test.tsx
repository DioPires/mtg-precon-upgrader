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

describe('DeckSelector brewing pill (DEC-1021)', () => {
  it('marks only the brewing deck with the brewing class and the BREWING badge', () => {
    const decks = makeDecks(3);
    decks[2].status = 'brewing';
    const { getAllByRole } = render(<DeckSelector decks={decks} activeIdx={3} onSelect={() => {}} />);
    const [built, , brewing] = getAllByRole('tab');

    expect(brewing).toHaveClass('gv1-sel-pill', 'gv1-sel-pill-brewing', 'gv1-active');
    expect(brewing.querySelector('.gv1-brewing-pill')).toHaveTextContent('BREWING');
    // The active brewing pill carries the badge and the flag together.
    expect(brewing.querySelector('.gv1-sel-pill-flag')).toHaveTextContent('NOW SCRYING');

    expect(built).toHaveClass('gv1-sel-pill');
    expect(built).not.toHaveClass('gv1-sel-pill-brewing');
    expect(built.querySelector('.gv1-brewing-pill')).toBeNull();
  });

  it('keeps the brewing class and the badge on a brewing pill that is not active', () => {
    const decks = makeDecks(3);
    decks[2].status = 'brewing';
    const { getAllByRole } = render(<DeckSelector decks={decks} activeIdx={1} onSelect={() => {}} />);
    const brewing = getAllByRole('tab')[2];

    expect(brewing).toHaveClass('gv1-sel-pill-brewing');
    expect(brewing).not.toHaveClass('gv1-active');
    expect(brewing.querySelector('.gv1-brewing-pill')).toHaveTextContent('BREWING');
    expect(brewing.querySelector('.gv1-sel-pill-flag')).toBeNull();
  });
});
