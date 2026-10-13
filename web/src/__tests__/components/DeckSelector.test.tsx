import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render } from '@testing-library/react';
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

  it('scrolls the track to the active pill and never calls scrollIntoView', () => {
    const decks = makeDecks(5);
    const { rerender } = render(<DeckSelector decks={decks} activeIdx={5} onSelect={() => {}} />);

    expect(scrollTo).toHaveBeenCalledTimes(1);
    expect(scrollTo).toHaveBeenLastCalledWith(expect.objectContaining({ behavior: 'smooth' }));

    rerender(<DeckSelector decks={decks} activeIdx={2} onSelect={() => {}} />);
    expect(scrollTo).toHaveBeenCalledTimes(2);
    // On the pill it scrolls every ancestor, `.gv1-root` included (DEC-1008).
    // On the track it moves Chromium's focus starting point (DEC-1048).
    expect(intoViewTargets).toEqual([]);
  });

  describe('bringing the rail into view (DEC-1048)', () => {
    const root = document.documentElement;
    let scrollBy: ReturnType<typeof vi.spyOn>;
    beforeEach(() => {
      scrollBy = vi.spyOn(window, 'scrollBy').mockImplementation(() => {});
      Object.defineProperty(root, 'clientHeight', { configurable: true, value: 768 });
    });
    afterEach(() => {
      scrollBy.mockRestore();
      delete (root as { clientHeight?: number }).clientHeight;
    });

    // jsdom has no layout: give the track a rect, and the viewport 768px.
    const trackAt = (top: number) =>
      vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (
        this: HTMLElement,
      ) {
        return this.classList.contains('gv1-selector-track')
          ? new DOMRect(0, top, 300, 150)
          : new DOMRect(0, 0, 0, 0);
      });

    it.each([
      ['above the viewport', -400, -400],
      ['below the viewport', 900, 900 + 150 - 768],
    ])('scrolls the page by the least amount when the track is %s', (_, top, dy) => {
      const rect = trackAt(top);
      render(<DeckSelector decks={makeDecks(5)} activeIdx={3} onSelect={() => {}} />);
      expect(scrollBy).toHaveBeenCalledTimes(1);
      expect(scrollBy).toHaveBeenCalledWith({ top: dy, behavior: 'smooth' });
      rect.mockRestore();
    });

    it('leaves the page alone when the track is in view', () => {
      const rect = trackAt(200);
      render(<DeckSelector decks={makeDecks(5)} activeIdx={3} onSelect={() => {}} />);
      expect(scrollBy).not.toHaveBeenCalled();
      rect.mockRestore();
    });
  });
});

describe('DeckSelector right-edge fade (DEC-1048)', () => {
  // jsdom has no layout: give the track its scroll metrics by hand.
  function setTrack(track: HTMLElement, scrollLeft: number, clientWidth: number, scrollWidth: number) {
    Object.defineProperty(track, 'clientWidth', { configurable: true, value: clientWidth });
    Object.defineProperty(track, 'scrollWidth', { configurable: true, value: scrollWidth });
    track.scrollLeft = scrollLeft;
    fireEvent.scroll(track);
  }

  it('marks the selector while the track is scrolled to its end', () => {
    const { getByRole, container } = render(
      <DeckSelector decks={makeDecks(5)} activeIdx={1} onSelect={() => {}} />,
    );
    const nav = getByRole('tablist');
    const track = container.querySelector<HTMLElement>('.gv1-selector-track')!;

    setTrack(track, 0, 300, 1200);
    expect(nav).not.toHaveAttribute('data-at-end');

    setTrack(track, 899.5, 300, 1200);
    expect(nav).toHaveAttribute('data-at-end');

    setTrack(track, 400, 300, 1200);
    expect(nav).not.toHaveAttribute('data-at-end');
  });

  it('marks the selector when the track does not overflow', () => {
    const { getByRole, container } = render(
      <DeckSelector decks={makeDecks(2)} activeIdx={1} onSelect={() => {}} />,
    );
    setTrack(container.querySelector<HTMLElement>('.gv1-selector-track')!, 0, 600, 600);
    expect(getByRole('tablist')).toHaveAttribute('data-at-end');
  });
});

// jsdom has no ResizeObserver. This one records what it observes and lets a
// test deliver an observation.
class StubResizeObserver {
  static made: StubResizeObserver[] = [];
  observed: Element[] = [];
  disconnected = false;
  constructor(private callback: ResizeObserverCallback) {
    StubResizeObserver.made.push(this);
  }
  observe(el: Element) {
    this.observed.push(el);
  }
  unobserve() {}
  disconnect() {
    this.disconnected = true;
  }
  deliver() {
    act(() => this.callback([], this as unknown as ResizeObserver));
  }
}

describe('DeckSelector track size (DEC-1063)', () => {
  beforeEach(() => {
    StubResizeObserver.made = [];
    vi.stubGlobal('ResizeObserver', StubResizeObserver);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  // The track's metrics change with no scroll event and no window resize.
  function sizeTrack(track: HTMLElement, clientWidth: number, scrollWidth: number) {
    Object.defineProperty(track, 'clientWidth', { configurable: true, value: clientWidth });
    Object.defineProperty(track, 'scrollWidth', { configurable: true, value: scrollWidth });
  }

  it('re-reads the fade when the track changes size', () => {
    const { getByRole, container } = render(
      <DeckSelector decks={makeDecks(5)} activeIdx={1} onSelect={() => {}} />,
    );
    const nav = getByRole('tablist');
    const track = container.querySelector<HTMLElement>('.gv1-selector-track')!;
    const [observer] = StubResizeObserver.made;
    expect(StubResizeObserver.made).toHaveLength(1);
    expect(observer.observed).toEqual([track]);

    // Mounted before the stylesheets applied: the unstyled track reads no
    // overflow, so the selector is marked.
    expect(nav).toHaveAttribute('data-at-end');

    // The styles apply: the track overflows and sits at its start.
    sizeTrack(track, 330, 5641);
    observer.deliver();
    expect(nav).not.toHaveAttribute('data-at-end');

    // It grows until nothing overflows.
    sizeTrack(track, 6340, 6340);
    observer.deliver();
    expect(nav).toHaveAttribute('data-at-end');
  });

  it('disconnects the observer on unmount', () => {
    const { unmount } = render(
      <DeckSelector decks={makeDecks(5)} activeIdx={1} onSelect={() => {}} />,
    );
    const [observer] = StubResizeObserver.made;
    expect(observer.disconnected).toBe(false);

    unmount();
    expect(observer.disconnected).toBe(true);
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
