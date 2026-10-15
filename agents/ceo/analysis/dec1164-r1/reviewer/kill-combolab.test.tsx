// DEC-1164 kill case for R1 (`count = q;`) and R2 (`count = Math.max(count, q);`)
// at ComboLab.tsx:121. A store with two kept entries: count is their sum (ruling 4).
// Route A: add the one row of the it.each table below to the table at
// src/__tests__/routes/ComboLab.test.tsx:169-173.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ComboLab } from '../../routes/ComboLab';
import { cardCache } from '../../data/cardCache';
import { deckLoader } from '../../data/loader';
import { loadPriceIndex } from '../../data/prices';
import {
  loadFeatureIndex,
  loadSynergyConfig,
  type FeatureIndex,
  type SynergyConfig,
} from '../../data/synergy';
import type { RawDeckBundle, RawDeckIndexEntry } from '../../data/types';

vi.mock('../../data/synergy', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../data/synergy')>()),
  loadFeatureIndex: vi.fn(),
  loadSynergyConfig: vi.fn(),
}));

vi.mock('../../data/prices', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../data/prices')>()),
  loadPriceIndex: vi.fn(),
}));
const OWNED_KEY = 'grimoire-owned-cards';

const ALPHA_ENTRY: RawDeckIndexEntry = {
  id: 'alpha',
  name: 'Alpha',
  commander: 'Alpha Commander',
  colors: ['C'],
  theme: 'Test',
  bracket: '4',
};

// A fleet deck of one card. It has no curated combo, so § XII·e is the only
// section that reads the owned list.
const ALPHA_BUNDLE = {
  id: 'alpha',
  index: ALPHA_ENTRY,
  deck: {
    id: 'alpha',
    type: 'Commander',
    name: 'Alpha',
    commander: 'Alpha Commander',
    bracket: '4',
    decklist: [{ name: 'Sol Ring', type: 'Artifact' }],
  },
  spellbookCombos: {
    meta: { deckId: 'alpha', source: 'test', corpusVersion: 'test', generatedAt: '', matchingModel: '' },
    commander: [],
    counts: { included: 0, nearMisses: 0, nearMissesTotal: 0 },
    included: [],
    nearMisses: [],
  },
} as unknown as RawDeckBundle;

// Sol Ring provides `mana`; `mana` pairs with `sink`. Brazen Borrower and Arcane
// Signet carry `sink`, so both are Tier-C completions of the deck.
const FEATURES: FeatureIndex = {
  cards: {
    o1: { n: 'Sol Ring', ci: '', p: [['mana', 1]] },
    o2: { n: 'Brazen Borrower', ci: '', p: [['sink', 1]] },
    o3: { n: 'Arcane Signet', ci: '', p: [['sink', 1]] },
  },
};

const CONFIG: SynergyConfig = {
  schema: 'test',
  compat: { mana: ['sink'], sink: ['mana'] },
  idf: {},
  labels: {},
  economies: {},
  noisePairs: [],
  constants: {
    EDGE_MIN_SIGNAL: 0,
    EDGE_WEIGHT_SCALE: 1,
    DEEP_EDGE_LIMIT: 0,
    STRONG_BAND_CUT: 1,
    PAIR_CAP: 0,
    TRIPLE_CAP: 0,
    CYCLE_CAP: 0,
    W_MAGNITUDE: 1,
    W_DECK_FIT: 1,
    W_CROWD_PRIOR: 0,
    IDF_FALLBACK: 1,
  },
};

describe('the owned list in Complete a Near-Miss (DEC-1150)', () => {
  beforeEach(() => {
    vi.spyOn(deckLoader, 'loadIndex').mockResolvedValue({ commanders: [ALPHA_ENTRY] });
    vi.spyOn(deckLoader, 'loadDeck').mockResolvedValue(ALPHA_BUNDLE);
    vi.spyOn(cardCache, 'enqueue').mockImplementation(() => {});
    vi.mocked(loadFeatureIndex).mockResolvedValue(FEATURES);
    vi.mocked(loadSynergyConfig).mockResolvedValue(CONFIG);
    vi.mocked(loadPriceIndex).mockResolvedValue(null);
  });

  afterEach(() => {
    localStorage.removeItem(OWNED_KEY);
    vi.restoreAllMocks();
  });

  async function openFleet(store: unknown): Promise<HTMLElement> {
    localStorage.setItem(OWNED_KEY, JSON.stringify(store));
    render(
      <MemoryRouter initialEntries={['/combos?mode=fleet&deck=alpha']}>
        <ComboLab />
      </MemoryRouter>,
    );
    const panel = await screen.findByRole('region', { name: 'Complete a near-miss' });
    await within(panel).findByText('Arcane Signet');
    return panel;
  }

  it.each([
    [[['Sol Ring', 2], ['Arcane Signet', 1]], '3 owned cards on file'],
  ])('counts the cards of the store %j: %s', async (store, text) => {
    const panel = await openFleet(store);
    const chip = within(panel).getByRole('button', { name: 'Owned only' });
    expect(chip).toBeEnabled();
    expect(chip).toHaveAttribute('title', text);
    expect(within(panel).getByText(`${text} — imported in § IX Shopping`)).toBeInTheDocument();
  });
});
