// Loads every deck bundle, normalizes them, and exposes the array.
// Used by cross-deck surfaces (Codex, Compare).

import { useEffect, useMemo, useState } from 'react';
import { deckLoader } from '../data/loader';
import { normalizeDecks } from '../data/normalize';
import type { DeckFull, RawDeckBundle } from '../data/types';

interface AllDecksState {
  status: 'loading' | 'loaded' | 'error';
  decks: DeckFull[];
  error?: string;
}

export function useAllDecks(): AllDecksState {
  const [bundles, setBundles] = useState<RawDeckBundle[]>([]);
  const [status, setStatus] = useState<AllDecksState['status']>('loading');
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    let cancelled = false;
    setStatus('loading');
    setError(undefined);
    (async () => {
      try {
        const all = await deckLoader.loadAll();
        if (cancelled) return;
        setBundles(all);
        setStatus('loaded');
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : String(err));
        setStatus('error');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const decks = useMemo(() => normalizeDecks(bundles), [bundles]);
  return { status, decks, error };
}
