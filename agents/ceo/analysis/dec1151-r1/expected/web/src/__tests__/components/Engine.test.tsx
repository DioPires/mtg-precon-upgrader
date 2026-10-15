// DEC-1142 — the count of cards in the active Engine role.

import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { Engine } from '../../components/organisms/Engine';
import type { DeckCardTile, DeckEngineSection } from '../../data/types';

// The tile fetches card data; this file reads only the panel's count line.
vi.mock('../../components/molecules/CardTile', () => ({
  CardTile: ({ card }: { card: DeckCardTile }) => <div>{card.n}</div>,
}));

function role(title: string, names: string[]): DeckEngineSection {
  // normalize.ts sets `count` to the length of the role's card list.
  return {
    title,
    count: names.length,
    cards: names.map((n) => ({ n, mv: '—', type: '—', price: '—', gc: false })),
    isGameChangers: false,
  };
}

// Two roles of 1 and 2 cards: the section holds 3 cards across 2 roles.
const ENGINE = [role('Commander Engine', ['Sol Ring']), role('Ramp', ['Arcane Signet', 'Mind Stone'])];

describe('Engine', () => {
  it('reads `1 card` for the active role of one card', () => {
    render(<Engine engine={ENGINE} />);
    expect(screen.getByRole('tabpanel')).toHaveTextContent('1 card · hover for full frame');
  });

  it('reads `2 cards` for the active role of two cards', () => {
    render(<Engine engine={ENGINE} />);
    fireEvent.click(screen.getByRole('tab', { name: /Ramp/ }));
    expect(screen.getByRole('tabpanel')).toHaveTextContent('2 cards · hover for full frame');
  });

  // A role keeps `count` and `cards` apart, and the line reads `count`. normalize.ts
  // builds no role whose two differ today; this case holds the line to its type.
  it('reads `1 card` for a role of count 1 that lists two tiles', () => {
    render(<Engine engine={[{ ...role('Ramp', ['Sol Ring', 'Arcane Signet']), count: 1 }]} />);
    expect(screen.getByRole('tabpanel')).toHaveTextContent('1 card · hover for full frame');
  });
});
