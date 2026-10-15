// DEC-1149 kill case (reviewer of PR #54) for R22: a tile that gets another card
// (tiles are keyed by index in Engine, WinCons and Combos) asks for that card's price.
import { afterEach, describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/react';
import { CardTile } from '../../../components/molecules/CardTile';
import { cardCache } from '../../../data/cardCache';

afterEach(() => {
  vi.restoreAllMocks();
  cardCache._reset();
});

describe('R22 (reviewer kill)', () => {
  it('asks for the refresh of the new card when the tile gets another card', () => {
    const spy = vi.spyOn(cardCache, 'refreshPrice').mockImplementation(() => undefined);
    const tile = (n: string) => ({ n, mv: '—', type: 'Artifact', price: '—', gc: false });
    const { rerender } = render(<CardTile card={tile('Sol Ring')} />);
    rerender(<CardTile card={tile('Arcane Signet')} />);
    expect(spy.mock.calls.map(([name]) => name)).toEqual(['Sol Ring', 'Arcane Signet']);
  });
});
