// DEC-1151 kill case (reviewer scratch, offered only): a role whose `count`
// differs from the length of its card list. No code builds such a role today
// (normalize.ts:201-205), so rule 4 makes E2 and E5 N items.

import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Engine } from '../../components/organisms/Engine';
import type { DeckCardTile, DeckEngineSection } from '../../data/types';

vi.mock('../../components/molecules/CardTile', () => ({
  CardTile: ({ card }: { card: DeckCardTile }) => <div>{card.n}</div>,
}));

const ROLE: DeckEngineSection = {
  title: 'Ramp',
  count: 1,
  cards: ['Sol Ring', 'Arcane Signet'].map((n) => ({ n, mv: '—', type: '—', price: '—', gc: false })),
  isGameChangers: false,
};

describe('Engine count line follows `count` (DEC-1151 offered kill)', () => {
  it('reads `1 card` for a role of count 1 that lists two tiles', () => {
    render(<Engine engine={[ROLE]} />);
    expect(screen.getByRole('tabpanel')).toHaveTextContent('1 card · hover for full frame');
  });
});
