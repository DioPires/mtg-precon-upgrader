// DEC-1169 review of PR #69, check 1.2: the record in render under StrictMode,
// a render that React throws away, and a render with the same activeIdx.
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render } from '@testing-library/react';
import { StrictMode, useState } from 'react';
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
let tick: () => void = () => {};
let throwAt = -1;
let renders = 0;

// Throws on its first render at deck `throwAt`; React renders the update again.
function ThrowOnce({ active }: { active: number }) {
  renders += 1;
  if (active === throwAt) {
    throwAt = -1;
    throw new Error('thrown away');
  }
  return null;
}

function Guide({ start }: { start: number }) {
  const [active, setActive] = useState(start);
  const [, setN] = useState(0);
  route = setActive;
  tick = () => setN((n) => n + 1);
  return (
    <>
      <DeckSelector decks={makeDecks(5)} activeIdx={active} onSelect={setActive} />
      <ThrowOnce active={active} />
      <button key={active} type="button">
        Board Wipes
      </button>
      <button type="button">Stays</button>
    </>
  );
}

const strict = (start: number) => render(<StrictMode><Guide start={start} /></StrictMode>);

describe('DEC-1169 check 1.2 (StrictMode)', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    throwAt = -1;
  });

  it('S1 case (a): one focus call, on the active pill', () => {
    const { getAllByRole, getByRole } = strict(3);
    const tabs = getAllByRole('tab');
    const chip = getByRole('button', { name: 'Board Wipes' });
    act(() => chip.focus());
    const focus = vi.spyOn(HTMLElement.prototype, 'focus');
    renders = 0;
    act(() => route(5));
    expect(renders).toBe(2); // StrictMode renders the update twice
    expect(document.activeElement).toBe(tabs[4]);
    expect(focus).toHaveBeenCalledTimes(1);
    expect(focus).toHaveBeenCalledWith({ preventScroll: true });
  });

  it('S2 case (b): click switch, then Back', () => {
    const { getAllByRole } = strict(3);
    const tabs = getAllByRole('tab');
    act(() => tabs[3].focus());
    const focus = vi.spyOn(HTMLElement.prototype, 'focus');
    fireEvent.click(tabs[3]);
    expect(document.activeElement).toBe(tabs[3]);
    expect(focus).not.toHaveBeenCalled();
    act(() => route(3));
    expect(document.activeElement).toBe(tabs[2]);
    expect(focus).toHaveBeenCalledTimes(1);
  });

  it('S3 first mount that removes a focused element: no focus', () => {
    let load = () => {};
    function Loading() {
      const [ready, setReady] = useState(false);
      load = () => setReady(true);
      return ready ? <Guide start={3} /> : <button type="button">Retry</button>;
    }
    const { getByRole } = render(<StrictMode><Loading /></StrictMode>);
    const retry = getByRole('button', { name: 'Retry' });
    act(() => retry.focus());
    const focus = vi.spyOn(HTMLElement.prototype, 'focus');
    act(() => load());
    expect(document.activeElement).toBe(document.body);
    expect(focus).not.toHaveBeenCalled();
  });

  it('S4 nothing focused, and S5 focus outside the track that stays: no focus', () => {
    const { getAllByRole, getByRole } = strict(3);
    const tabs = getAllByRole('tab');
    const focus = vi.spyOn(HTMLElement.prototype, 'focus');
    act(() => route(5));
    expect(tabs[4]).toHaveAttribute('aria-selected', 'true');
    expect(document.activeElement).toBe(document.body);
    expect(focus).not.toHaveBeenCalled();
    const stays = getByRole('button', { name: 'Stays' });
    act(() => stays.focus());
    focus.mockClear();
    act(() => route(1));
    expect(document.activeElement).toBe(stays);
    expect(focus).not.toHaveBeenCalled();
  });

  it('S6 a render that React throws away and renders again: case (a) still focuses once', () => {
    const err = vi.spyOn(console, 'error').mockImplementation(() => {});
    const { getAllByRole, getByRole } = strict(3);
    const tabs = getAllByRole('tab');
    const chip = getByRole('button', { name: 'Board Wipes' });
    act(() => chip.focus());
    const focus = vi.spyOn(HTMLElement.prototype, 'focus');
    throwAt = 5;
    renders = 0;
    act(() => route(5));
    expect(renders).toBeGreaterThan(2); // the thrown render, then the retry
    expect(chip.isConnected).toBe(false);
    expect(document.activeElement).toBe(tabs[4]);
    expect(focus).toHaveBeenCalledTimes(1);
    err.mockRestore();
  });

  it('S7 a render that React throws away with nothing focused: no focus', () => {
    const err = vi.spyOn(console, 'error').mockImplementation(() => {});
    const { getAllByRole } = strict(3);
    const tabs = getAllByRole('tab');
    const focus = vi.spyOn(HTMLElement.prototype, 'focus');
    throwAt = 5;
    act(() => route(5));
    expect(tabs[4]).toHaveAttribute('aria-selected', 'true');
    expect(document.activeElement).toBe(document.body);
    expect(focus).not.toHaveBeenCalled();
    err.mockRestore();
  });

  it('S8 a render with the same activeIdx records nothing: the next change reads the focus of its own render', () => {
    const { getAllByRole, getByRole } = strict(3);
    const tabs = getAllByRole('tab');
    const chip = getByRole('button', { name: 'Board Wipes' });
    act(() => chip.focus());
    const focus = vi.spyOn(HTMLElement.prototype, 'focus');
    act(() => tick()); // same activeIdx, chip focused
    expect(focus).not.toHaveBeenCalled();
    const stays = getByRole('button', { name: 'Stays' });
    act(() => stays.focus());
    focus.mockClear();
    act(() => route(5)); // removes the chip; focus is on Stays
    expect(tabs[4]).toHaveAttribute('aria-selected', 'true');
    expect(document.activeElement).toBe(stays);
    expect(focus).not.toHaveBeenCalled();
  });
});
