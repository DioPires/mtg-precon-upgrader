import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
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

    // DEC-1063: a track taller than the viewport, y 100 to 1000 against 768.
    // Its bottom is 232px past the edge, but 100px already brings its top to
    // the viewport's: `Math.min` picks the top, so the start of the rail
    // stays in view.
    it('stops at the top of a track that is taller than the viewport', () => {
      const rect = vi
        .spyOn(HTMLElement.prototype, 'getBoundingClientRect')
        .mockImplementation(function (this: HTMLElement) {
          return this.classList.contains('gv1-selector-track')
            ? new DOMRect(0, 100, 300, 900)
            : new DOMRect(0, 0, 0, 0);
        });
      render(<DeckSelector decks={makeDecks(5)} activeIdx={3} onSelect={() => {}} />);
      expect(scrollBy).toHaveBeenCalledTimes(1);
      expect(scrollBy).toHaveBeenCalledWith({ top: 100, behavior: 'smooth' });
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

  // The cleanup ends the window listener too. After unmount the listener
  // finds no track and does nothing, so only the calls show that it is gone.
  it('removes its resize listener on unmount', () => {
    const add = vi.spyOn(window, 'addEventListener');
    const remove = vi.spyOn(window, 'removeEventListener');
    const { unmount } = render(
      <DeckSelector decks={makeDecks(5)} activeIdx={1} onSelect={() => {}} />,
    );
    const added = add.mock.calls.filter(([type]) => type === 'resize').map(([, listener]) => listener);
    expect(added).toHaveLength(1);

    unmount();
    expect(remove).toHaveBeenCalledWith('resize', added[0]);
    add.mockRestore();
    remove.mockRestore();
  });

  // More pills change the track's `scrollWidth`, not its own box: no
  // observation, no scroll event and no window resize follows.
  it('re-reads the fade when the number of decks changes', () => {
    const { getByRole, container, rerender } = render(
      <DeckSelector decks={makeDecks(2)} activeIdx={1} onSelect={() => {}} />,
    );
    const nav = getByRole('tablist');
    expect(nav).toHaveAttribute('data-at-end');

    sizeTrack(container.querySelector<HTMLElement>('.gv1-selector-track')!, 330, 5641);
    rerender(<DeckSelector decks={makeDecks(40)} activeIdx={1} onSelect={() => {}} />);
    expect(nav).not.toHaveAttribute('data-at-end');
  });

  describe('centring a selector that mounted before the styles applied', () => {
    const proto = Element.prototype as unknown as Scrollable;
    const originalScrollTo = proto.scrollTo;
    const root = document.documentElement;
    let scrollTo: ReturnType<typeof vi.fn>;
    let scrollBy: ReturnType<typeof vi.spyOn>;
    let rect: ReturnType<typeof vi.spyOn>;
    let sheet: HTMLStyleElement;

    beforeEach(() => {
      scrollTo = vi.fn();
      proto.scrollTo = scrollTo;
      scrollBy = vi.spyOn(window, 'scrollBy').mockImplementation(() => {});
      // The track sits 400px above a 768px viewport.
      Object.defineProperty(root, 'clientHeight', { configurable: true, value: 768 });
      rect = vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (
        this: HTMLElement,
      ) {
        return this.classList.contains('gv1-selector-track')
          ? new DOMRect(0, -400, 300, 150)
          : new DOMRect(0, 0, 0, 0);
      });
      sheet = document.createElement('style');
      document.head.appendChild(sheet);
    });
    afterEach(() => {
      proto.scrollTo = originalScrollTo;
      scrollBy.mockRestore();
      rect.mockRestore();
      delete (root as { clientHeight?: number }).clientHeight;
      sheet.remove();
    });

    // jsdom computes no initial values. A browser computes `overflow-x:
    // visible` on the track until the stylesheet sets `auto`.
    const stylesOut = () => {
      sheet.textContent = '.gv1-selector-track { overflow-x: visible; }';
    };
    const stylesIn = () => {
      sheet.textContent = '.gv1-selector-track { overflow-x: auto; }';
    };

    it('waits for the styles, then scrolls the track and the page once', () => {
      stylesOut();
      render(<DeckSelector decks={makeDecks(5)} activeIdx={5} onSelect={() => {}} />);
      const [observer] = StubResizeObserver.made;
      expect(scrollTo).not.toHaveBeenCalled();
      expect(scrollBy).not.toHaveBeenCalled();

      // The observation that follows observe(): the track is still unstyled.
      observer.deliver();
      expect(scrollTo).not.toHaveBeenCalled();
      expect(scrollBy).not.toHaveBeenCalled();

      stylesIn();
      observer.deliver();
      expect(scrollTo).toHaveBeenCalledTimes(1);
      expect(scrollTo).toHaveBeenLastCalledWith(expect.objectContaining({ behavior: 'smooth' }));
      expect(scrollBy).toHaveBeenCalledTimes(1);
      expect(scrollBy).toHaveBeenCalledWith({ top: -400, behavior: 'smooth' });

      // Centred on a styled track: a later size change leaves the rail alone.
      observer.deliver();
      expect(scrollTo).toHaveBeenCalledTimes(1);
      expect(scrollBy).toHaveBeenCalledTimes(1);
    });

    it('keeps waiting through a deck change made while the styles are out', () => {
      stylesOut();
      const decks = makeDecks(5);
      const { rerender } = render(<DeckSelector decks={decks} activeIdx={5} onSelect={() => {}} />);
      rerender(<DeckSelector decks={decks} activeIdx={2} onSelect={() => {}} />);
      expect(scrollTo).not.toHaveBeenCalled();

      stylesIn();
      StubResizeObserver.made[0].deliver();
      expect(scrollTo).toHaveBeenCalledTimes(1);

      // A later size change (the font swap) leaves the rail alone.
      StubResizeObserver.made[0].deliver();
      expect(scrollTo).toHaveBeenCalledTimes(1);
    });

    it('scrolls a styled mount once for each deck change, whatever the observer reports', () => {
      stylesIn();
      const decks = makeDecks(5);
      const { rerender } = render(<DeckSelector decks={decks} activeIdx={5} onSelect={() => {}} />);
      const [observer] = StubResizeObserver.made;
      expect(scrollTo).toHaveBeenCalledTimes(1);

      // The observation that follows observe().
      observer.deliver();
      expect(scrollTo).toHaveBeenCalledTimes(1);

      rerender(<DeckSelector decks={decks} activeIdx={2} onSelect={() => {}} />);
      expect(scrollTo).toHaveBeenCalledTimes(2);
      observer.deliver();
      expect(scrollTo).toHaveBeenCalledTimes(2);
      expect(scrollBy).toHaveBeenCalledTimes(2);
      expect(StubResizeObserver.made).toHaveLength(1);
    });

    // An absent pill is not a pending centring. If it were, a pill that
    // arrived under the same `activeIdx` would be centred at the next size
    // change, which can come after the user has scrolled the rail.
    it('leaves no centring pending when the active pill is absent', () => {
      stylesIn();
      const decks = makeDecks(5);
      const { container, rerender } = render(
        <DeckSelector decks={decks} activeIdx={9} onSelect={() => {}} />,
      );
      const [observer] = StubResizeObserver.made;
      expect(container.querySelector('.gv1-active')).toBeNull();
      observer.deliver();
      expect(scrollTo).not.toHaveBeenCalled();

      // The pill arrives under the same activeIdx, with the same deck count.
      const next = decks.map((d, i) => (i === 4 ? { ...d, idx: 9 } : d));
      rerender(<DeckSelector decks={next} activeIdx={9} onSelect={() => {}} />);
      expect(container.querySelector('.gv1-active')).not.toBeNull();
      expect(StubResizeObserver.made).toHaveLength(1);
      observer.deliver();
      expect(scrollTo).not.toHaveBeenCalled();

      // A deck change still centres, once.
      rerender(<DeckSelector decks={next} activeIdx={2} onSelect={() => {}} />);
      expect(scrollTo).toHaveBeenCalledTimes(1);
    });
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

// The parent owns the open deck, as the routes do through the URL. `route`
// changes it with no key, as browser Back does.
let route: (idx: number) => void = () => {};
function Harness({ decks, start }: { decks: DeckStub[]; start: number }) {
  const [active, setActive] = useState(start);
  route = setActive;
  return <DeckSelector decks={decks} activeIdx={active} onSelect={setActive} />;
}

describe('DeckSelector focus after a key switch (DEC-1135)', () => {
  // Each focus records the pill as it was at that moment. A focus that ran
  // before the pill rendered as active would record `aria-selected` false.
  type Seen = { name: string | null | undefined; selected: string | null; tabIndex: number };
  let seen: Seen[];
  const record = (e: FocusEvent) => {
    const el = e.target as HTMLElement;
    seen.push({
      name: el.querySelector('.gv1-sel-pill-name')?.textContent,
      selected: el.getAttribute('aria-selected'),
      tabIndex: el.tabIndex,
    });
  };
  beforeEach(() => {
    seen = [];
    document.addEventListener('focusin', record);
  });
  afterEach(() => document.removeEventListener('focusin', record));

  const startOn = (tab: HTMLElement) => {
    act(() => tab.focus());
    seen = [];
  };

  it.each([
    ['ArrowRight', 4],
    ['ArrowLeft', 2],
    ['Home', 1],
    ['End', 5],
  ])('%s moves focus to the pill that becomes active', (key, idx) => {
    const { getAllByRole } = render(<Harness decks={makeDecks(5)} start={3} />);
    const tabs = getAllByRole('tab');
    startOn(tabs[2]);

    fireEvent.keyDown(tabs[2], { key });
    const el = document.activeElement as HTMLElement;
    expect(el).toBe(tabs[idx - 1]);
    expect(el).toHaveAttribute('aria-selected', 'true');
    expect(el.tabIndex).toBe(0);
    expect(tabs[2]).toHaveAttribute('aria-selected', 'false');
    expect(seen).toEqual([{ name: `Deck ${idx}`, selected: 'true', tabIndex: 0 }]);
  });

  it('moves focus to the open deck\'s pill when the key picks that deck', () => {
    const decks = makeDecks(5);
    decks[4].hasDetail = false;
    const { getAllByRole } = render(<Harness decks={decks} start={1} />);
    const tabs = getAllByRole('tab');
    // A press on the unscribed pill focuses it and opens nothing.
    startOn(tabs[4]);

    fireEvent.keyDown(tabs[4], { key: 'Home' });
    expect(document.activeElement).toBe(tabs[0]);
    expect(seen).toEqual([{ name: 'Deck 1', selected: 'true', tabIndex: 0 }]);
  });

  it('leaves focus on a clicked pill and makes no focus call', () => {
    const { getAllByRole } = render(<Harness decks={makeDecks(5)} start={3} />);
    const tabs = getAllByRole('tab');
    // A browser focuses the button on the press, before the click.
    startOn(tabs[3]);
    const focus = vi.spyOn(HTMLElement.prototype, 'focus');

    fireEvent.click(tabs[3]);
    expect(tabs[3]).toHaveAttribute('aria-selected', 'true');
    expect(document.activeElement).toBe(tabs[3]);
    expect(focus).not.toHaveBeenCalled();
    focus.mockRestore();
  });

  it('moves no focus at a deck change that no key started, before or after a key switch', () => {
    const { getAllByRole } = render(<Harness decks={makeDecks(5)} start={3} />);
    const tabs = getAllByRole('tab');

    act(() => route(1));
    expect(document.activeElement).toBe(document.body);

    startOn(tabs[0]);
    fireEvent.keyDown(tabs[0], { key: 'End' });
    expect(document.activeElement).toBe(tabs[4]);

    // Back to the deck that the key left: focus stays on the pill it has.
    act(() => route(1));
    expect(tabs[0]).toHaveAttribute('aria-selected', 'true');
    expect(document.activeElement).toBe(tabs[4]);
    expect(seen).toHaveLength(1);
  });
});

// The review's cases (DEC-1148 B1 to B4). Each one fails on one mutant that the
// cases above let pass.
describe('DeckSelector focus after a key switch: review cases (DEC-1148)', () => {
  afterEach(() => vi.restoreAllMocks());

  it('moves no focus when a route returns to the deck that an earlier key picked', () => {
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

  it('focuses with preventScroll, so the focus does not cut the centring short', () => {
    const { getAllByRole } = render(<Harness decks={makeDecks(5)} start={3} />);
    const tabs = getAllByRole('tab');
    act(() => tabs[2].focus());
    const focus = vi.spyOn(HTMLElement.prototype, 'focus');
    fireEvent.keyDown(tabs[2], { key: 'ArrowRight' });
    expect(focus).toHaveBeenCalledTimes(1);
    expect(focus).toHaveBeenCalledWith({ preventScroll: true });
  });

  it('focuses the pill, not an active element earlier in the page', () => {
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

  it("reports the key's pick to onSelect when the key picks the open deck", () => {
    const onSelect = vi.fn();
    const { getAllByRole } = render(
      <DeckSelector decks={makeDecks(5)} activeIdx={1} onSelect={onSelect} />,
    );
    const tabs = getAllByRole('tab');
    act(() => tabs[0].focus());
    fireEvent.keyDown(tabs[0], { key: 'Home' });
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(2);
  });
});
