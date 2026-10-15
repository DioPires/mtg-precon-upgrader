import { describe, it, expect, beforeEach, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import { useCard } from '../../hooks/useCard';
import { cardCache } from '../../data/cardCache';
import { identifiersOf } from '../data/scryfallFakes';

/** The answer to one batch: the given cards. */
const batch = (...data: object[]) =>
  new Response(JSON.stringify({ object: 'list', not_found: [], data }), { status: 200 });

function clearStorage() {
  for (let i = window.localStorage.length - 1; i >= 0; i--) {
    const k = window.localStorage.key(i);
    if (k) window.localStorage.removeItem(k);
  }
}

beforeEach(() => {
  cardCache._reset();
  clearStorage();
});

describe('useCard', () => {
  it('transitions to loaded once the underlying fetch resolves', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      batch({
        name: 'Sol Ring',
        mana_cost: '{1}',
        cmc: 1,
        type_line: 'Artifact',
        image_uris: { small: 's', normal: 'n', art_crop: 'a' },
        prices: { usd: '0.42' },
      }),
    );
    const { result } = renderHook(() => useCard('Sol Ring'));
    // Before the fetch resolves, status is null or loading — never loaded.
    expect(result.current?.status === 'loaded').toBe(false);
    await waitFor(() => expect(result.current?.status).toBe('loaded'));
    expect(result.current?.image_small).toBe('s');
    fetchSpy.mockRestore();
  });

  it('returns the cached entry synchronously when already loaded', async () => {
    // Seed cache directly (no network).
    const seed = {
      status: 'loaded' as const,
      name: 'Sol Ring',
      image_small: 'cached',
      fetchedAt: Date.now(),
    };
    window.localStorage.setItem('gv1-card:sol ring', JSON.stringify(seed));
    const { result } = renderHook(() => useCard('Sol Ring'));
    expect(result.current?.status).toBe('loaded');
    expect(result.current?.image_small).toBe('cached');
  });

  it('updates when the requested name changes', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_url, init) => {
      const [name] = identifiersOf(init?.body);
      return batch({
        name,
        mana_cost: '{0}',
        type_line: 'Artifact',
        image_uris: { small: `s-${name}`, normal: '', art_crop: '' },
        prices: { usd: '1.00' },
      });
    });
    const { result, rerender } = renderHook(({ name }: { name: string }) => useCard(name), {
      initialProps: { name: 'Sol Ring' },
    });
    await waitFor(() => expect(result.current?.name).toBe('Sol Ring'));
    act(() => { rerender({ name: 'Mana Crypt' }); });
    // The second batch goes 1,200 ms after the first (DEC-1131).
    await waitFor(() => expect(result.current?.name).toBe('Mana Crypt'), { timeout: 3_000 });
    fetchSpy.mockRestore();
  });
});
