import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import {
  Decklist,
  byCmcThenName,
  groupByType,
  serializeFullList,
} from '../../components/organisms/Decklist';
import { cardCache } from '../../data/cardCache';
import type { DeckCardTile, DeckListGroup } from '../../data/types';

// Decklist subscribes to cardCache for cmc lookup. Reset between tests so
// background Scryfall fetches don't bleed across them; mocked fetch keeps
// jsdom from reaching the network.
beforeEach(() => {
  cardCache._reset();
  // Stall the Scryfall fetch — we don't want async cache writes to fire
  // re-renders (force()) after the test has finished asserting.
  vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise(() => {}));
});

afterEach(() => {
  vi.restoreAllMocks();
});

function tile(n: string, type: string, qty?: number, cmc?: number): DeckCardTile {
  return {
    n, mv: '—', type, price: '—', gc: false,
    ...(qty ? { qty } : {}),
    ...(cmc != null ? { cmc } : {}),
  };
}

function group(name: string, cards: DeckCardTile[]): DeckListGroup {
  return { name, cards };
}

const SAMPLE_LIST: DeckListGroup[] = [
  group('Commander', [tile('Captain', 'Commander')]),
  group('Ramp (3)', [tile('Sol Ring', 'Artifact'), tile('Arcane Signet', 'Artifact')]),
  group('Removal (2)', [tile('Swords to Plowshares', 'Instant'), tile('Counterspell', 'Instant')]),
  group('Lands (4)', [
    tile('Plains', 'Land', 7),
    tile('Island', 'Land', 6),
    tile('Command Tower', 'Land'),
  ]),
  group('Threats (2)', [tile('Serra Angel', 'Creature'), tile('Bident of Thassa', 'Enchantment')]),
];

describe('byCmcThenName', () => {
  it('sorts by mana value ascending with alphabetical tiebreak', () => {
    const cards: DeckCardTile[] = [
      tile('Sol Ring', 'Artifact', undefined, 1),
      tile('Mox Diamond', 'Artifact', undefined, 0),
      tile('Black Lotus', 'Artifact', undefined, 0),
    ];
    expect([...cards].sort(byCmcThenName).map((c) => c.n)).toEqual([
      'Black Lotus', 'Mox Diamond', 'Sol Ring',
    ]);
  });

  it('treats missing cmc as 0 (collapses with lands to alpha tiebreak)', () => {
    const cards: DeckCardTile[] = [
      tile('Plains', 'Land'),
      tile('Command Tower', 'Land'),
      tile('Island', 'Land'),
    ];
    expect([...cards].sort(byCmcThenName).map((c) => c.n)).toEqual([
      'Command Tower', 'Island', 'Plains',
    ]);
  });

  it('orders mixed cmc subsection ascending', () => {
    const cards: DeckCardTile[] = [
      tile('Worldspine Wurm', 'Creature', undefined, 11),
      tile('Lightning Bolt', 'Instant', undefined, 1),
      tile('Counterspell', 'Instant', undefined, 2),
      tile('Birds of Paradise', 'Creature', undefined, 1),
    ];
    expect([...cards].sort(byCmcThenName).map((c) => c.n)).toEqual([
      'Birds of Paradise', 'Lightning Bolt', 'Counterspell', 'Worldspine Wurm',
    ]);
  });
});

describe('groupByType', () => {
  it('orders buckets per TYPE_ORDER and pins commander at top', () => {
    const out = groupByType(SAMPLE_LIST, 'Captain');
    expect(out.map((g) => g.name.split(' ')[0])).toEqual([
      'Commander', 'Creature', 'Artifact', 'Enchantment', 'Instant', 'Land',
    ]);
    expect(out[0].cards[0].n).toBe('Captain');
  });

  it('sorts cards within each bucket by mana value, alpha tiebreak', () => {
    const out = groupByType(SAMPLE_LIST, 'Captain');
    // No cmc on these tiles → all cmc=0 → alpha tiebreak.
    const artifacts = out.find((g) => g.name.startsWith('Artifact'))!;
    expect(artifacts.cards.map((c) => c.n)).toEqual(['Arcane Signet', 'Sol Ring']);
    const lands = out.find((g) => g.name.startsWith('Land'))!;
    expect(lands.cards.map((c) => c.n)).toEqual(['Command Tower', 'Island', 'Plains']);
  });

  it('ascends by cmc inside a bucket when cards expose it', () => {
    const list: DeckListGroup[] = [
      group('Commander', [tile('Captain', 'Commander')]),
      group('Threats', [
        tile('Worldspine Wurm', 'Creature', undefined, 11),
        tile('Birds of Paradise', 'Creature', undefined, 1),
        tile('Serra Angel', 'Creature', undefined, 5),
      ]),
    ];
    const out = groupByType(list, 'Captain');
    const creatures = out.find((g) => g.name.startsWith('Creature'))!;
    expect(creatures.cards.map((c) => c.n)).toEqual([
      'Birds of Paradise', 'Serra Angel', 'Worldspine Wurm',
    ]);
  });

  it('counts basics by quantity in the bucket header', () => {
    const out = groupByType(SAMPLE_LIST, 'Captain');
    const lands = out.find((g) => g.name.startsWith('Land'))!;
    // Plains x7 + Island x6 + Command Tower x1 = 14
    expect(lands.name).toBe('Land (14)');
  });
});

describe('serializeFullList', () => {
  it('emits commander first, then alphabetical Nx CardName lines', () => {
    expect(serializeFullList(SAMPLE_LIST, 'Captain')).toBe(
      [
        '1x Captain',
        '1x Arcane Signet',
        '1x Bident of Thassa',
        '1x Command Tower',
        '1x Counterspell',
        '6x Island',
        '7x Plains',
        '1x Serra Angel',
        '1x Sol Ring',
        '1x Swords to Plowshares',
      ].join('\n'),
    );
  });

  it('is deterministic across calls', () => {
    expect(serializeFullList(SAMPLE_LIST, 'Captain')).toBe(
      serializeFullList(SAMPLE_LIST, 'Captain'),
    );
  });

  it('skips the synthetic Commander group cards', () => {
    const text = serializeFullList(SAMPLE_LIST, 'Captain');
    // Commander appears exactly once (as the leading "1x Captain" line).
    expect(text.match(/Captain/g)).toHaveLength(1);
  });
});

describe('Decklist component', () => {
  function renderWith(initialEntry = '/deck/x') {
    return render(
      <MemoryRouter initialEntries={[initialEntry]}>
        <Decklist list={SAMPLE_LIST} commander="Captain" />
      </MemoryRouter>,
    );
  }

  it('renders role grouping by default', () => {
    renderWith();
    expect(screen.getByText(/sorted by function/)).toBeTruthy();
    const roleSwitch = screen.getByRole('switch', { name: /group by role/i });
    expect(roleSwitch.getAttribute('aria-checked')).toBe('true');
  });

  it('switches to type grouping when toggle is clicked', () => {
    renderWith();
    fireEvent.click(screen.getByRole('switch', { name: /group by type/i }));
    expect(screen.getByText(/sorted by type/)).toBeTruthy();
    expect(screen.getByText('Artifact (2)')).toBeTruthy();
    expect(screen.getByText('Land (14)')).toBeTruthy();
  });

  it('respects ?manifest=type from URL', () => {
    renderWith('/deck/x?manifest=type');
    expect(screen.getByText(/sorted by type/)).toBeTruthy();
    const typeSwitch = screen.getByRole('switch', { name: /group by type/i });
    expect(typeSwitch.getAttribute('aria-checked')).toBe('true');
  });

  describe('copy button', () => {
    let writeText: ReturnType<typeof vi.fn>;

    beforeEach(() => {
      writeText = vi.fn().mockResolvedValue(undefined);
      Object.defineProperty(navigator, 'clipboard', {
        value: { writeText },
        configurable: true,
        writable: true,
      });
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('copies the serialized full list and announces success', async () => {
      renderWith();
      const btn = screen.getByRole('button', { name: /copy decklist/i });
      fireEvent.click(btn);
      const expected = serializeFullList(SAMPLE_LIST, 'Captain');
      await vi.waitFor(() => {
        expect(writeText).toHaveBeenCalledWith(expected);
      });
      // Button reflects success and live region announces it.
      await screen.findByRole('button', { name: /copied/i });
      const live = document.querySelector('[role="status"]') as HTMLElement;
      expect(within(live).getByText(/copied to clipboard/i)).toBeTruthy();
    });

    it('shows failure badge when clipboard rejects', async () => {
      writeText.mockRejectedValueOnce(new Error('denied'));
      renderWith();
      const btn = screen.getByRole('button', { name: /copy decklist/i });
      fireEvent.click(btn);
      await screen.findByText(/failed/i);
    });
  });
});
