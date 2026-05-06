import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import {
  Decklist,
  groupByType,
  serializeFullList,
} from '../../components/organisms/Decklist';
import type { DeckCardTile, DeckListGroup } from '../../data/types';

function tile(n: string, type: string, qty?: number): DeckCardTile {
  return { n, mv: '—', type, price: '—', gc: false, ...(qty ? { qty } : {}) };
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

describe('groupByType', () => {
  it('orders buckets per TYPE_ORDER and pins commander at top', () => {
    const out = groupByType(SAMPLE_LIST, 'Captain');
    expect(out.map((g) => g.name.split(' ')[0])).toEqual([
      'Commander', 'Creature', 'Artifact', 'Enchantment', 'Instant', 'Land',
    ]);
    expect(out[0].cards[0].n).toBe('Captain');
  });

  it('alpha-sorts cards within each bucket', () => {
    const out = groupByType(SAMPLE_LIST, 'Captain');
    const artifacts = out.find((g) => g.name.startsWith('Artifact'))!;
    expect(artifacts.cards.map((c) => c.n)).toEqual(['Arcane Signet', 'Sol Ring']);
    const lands = out.find((g) => g.name.startsWith('Land'))!;
    expect(lands.cards.map((c) => c.n)).toEqual(['Command Tower', 'Island', 'Plains']);
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
