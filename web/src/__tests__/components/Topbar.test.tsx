// The top bar's Guide and Scrying links. A deck id from the URL, else the deck
// saved in localStorage (grimoire-last-deck), is the link target unless the
// loaded index does not list it (the five decks removed on 2026-11-27): then
// the next one is tried (the URL's, then the saved one), and the first
// commander after both. Before the index has loaded, or when it fails to
// load, an id is used as it is. The URL's id is read decoded.
//
// The index comes through the network boundary: a stubbed fetch answers
// /data/index.json. The deck loader takes the global fetch when its module
// loads, so each case stubs fetch, resets the module registry and imports
// Topbar and the loader again; localStorage (where the loader keeps the index)
// is cleared between cases. The ids under test are not the first commander,
// so a bar that always takes the first one fails.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import type { RawDeckIndexEntry } from '../../data/types';

const LAST_DECK_KEY = 'grimoire-last-deck';

const entry = (id: string): RawDeckIndexEntry => ({
  id,
  name: id,
  commander: `${id} commander`,
  colors: ['W'],
  theme: 'Theme',
  bracket: '4',
});
const INDEX = { commanders: [entry('alpha'), entry('beta'), entry('gamma')] };

type IndexAnswer = 'index' | 'fails' | 'never';

// Stub the network, then import a fresh Topbar and loader (the loader keeps
// the fetch it found when its module loaded).
async function freshModules(answer: IndexAnswer) {
  const fetchStub = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (!url.endsWith('/data/index.json')) throw new TypeError(`unexpected fetch ${url}`);
    if (answer === 'never') return new Promise<Response>(() => {});
    if (answer === 'fails') return new Response('', { status: 500 });
    return new Response(JSON.stringify(INDEX), { status: 200, headers: { 'Content-Type': 'application/json' } });
  });
  vi.stubGlobal('fetch', fetchStub);
  vi.resetModules();
  const { Topbar } = await import('../../components/Topbar');
  const { deckLoader } = await import('../../data/loader');
  return { Topbar, deckLoader, fetchStub };
}

async function renderAt(path: string, answer: IndexAnswer) {
  const { Topbar, deckLoader, fetchStub } = await freshModules(answer);
  render(
    <MemoryRouter initialEntries={[path]}>
      <Topbar />
    </MemoryRouter>,
  );
  // The mobile menu renders its own links only while it is open.
  fireEvent.click(screen.getByRole('button', { name: /open navigation menu/i }));
  return { deckLoader, fetchStub };
}

// Let the index load settle, the bar's update included: the bar asked the
// loader first, so its callback has run when this await returns.
async function settle(deckLoader: { loadIndex(): Promise<unknown> }) {
  await act(async () => {
    await deckLoader.loadIndex().catch(() => undefined);
  });
}

// Every Guide and Scrying link the bar renders: the desktop nav and the mobile menu.
function hrefs(): { guide: (string | null)[]; scrying: (string | null)[] } {
  const read = (name: RegExp) => screen.getAllByRole('link', { name }).map((a) => a.getAttribute('href'));
  return { guide: read(/guide/i), scrying: read(/scrying/i) };
}
const both = (id: string) => ({ guide: [`/deck/${id}`, `/deck/${id}`], scrying: [`/scrying/${id}`, `/scrying/${id}`] });

describe('Topbar deck links', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  describe('with the index loaded', () => {
    it('keeps a saved deck the index lists', async () => {
      window.localStorage.setItem(LAST_DECK_KEY, 'gamma');
      const { deckLoader, fetchStub } = await renderAt('/codex', 'index');
      await settle(deckLoader);
      expect(fetchStub).toHaveBeenCalledTimes(1);
      expect(hrefs()).toEqual(both('gamma'));
    });

    it('drops a saved deck the index does not list for the first commander', async () => {
      window.localStorage.setItem(LAST_DECK_KEY, 'removed-deck');
      const { deckLoader } = await renderAt('/codex', 'index');
      await settle(deckLoader);
      expect(hrefs()).toEqual(both('alpha'));
    });

    it('drops a deck in the URL the index does not list for the saved deck', async () => {
      window.localStorage.setItem(LAST_DECK_KEY, 'gamma');
      const { deckLoader } = await renderAt('/deck/removed-deck', 'index');
      await settle(deckLoader);
      expect(hrefs()).toEqual(both('gamma'));
    });

    it('keeps a deck in the URL the index lists', async () => {
      window.localStorage.setItem(LAST_DECK_KEY, 'gamma');
      const { deckLoader } = await renderAt('/deck/beta', 'index');
      await settle(deckLoader);
      expect(hrefs()).toEqual(both('beta'));
    });

    it('reads the deck in the URL decoded', async () => {
      window.localStorage.setItem(LAST_DECK_KEY, 'gamma');
      const { deckLoader } = await renderAt('/deck/%62eta', 'index');
      await settle(deckLoader);
      expect(hrefs()).toEqual(both('beta'));
    });
  });

  it('uses a saved deck before the index has loaded', async () => {
    window.localStorage.setItem(LAST_DECK_KEY, 'gamma');
    const { fetchStub } = await renderAt('/codex', 'never');
    expect(fetchStub).toHaveBeenCalledTimes(1);
    expect(hrefs()).toEqual(both('gamma'));
  });

  it('keeps using the saved deck when the index fails to load', async () => {
    window.localStorage.setItem(LAST_DECK_KEY, 'gamma');
    const { deckLoader, fetchStub } = await renderAt('/codex', 'fails');
    await settle(deckLoader);
    expect(fetchStub).toHaveBeenCalled();
    await expect(deckLoader.loadIndex()).rejects.toThrow('HTTP 500');
    expect(hrefs()).toEqual(both('gamma'));
  });
});
