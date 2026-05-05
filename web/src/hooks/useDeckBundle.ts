// Loads a single deck bundle + the index, normalizes both, and exposes the
// active DeckFull plus the selector list. Components stay synchronous on
// re-render and never see RawDeckBundle directly.

import { useEffect, useMemo, useState } from 'react';
import { deckLoader } from '../data/loader';
import { buildDeckStubs, normalizeDecks } from '../data/normalize';
import type { DeckFull, DeckStub, RawDeckBundle } from '../data/types';

interface DeckBundleState {
  status: 'loading' | 'loaded' | 'error' | 'not-found';
  deck: DeckFull | null;
  stubs: DeckStub[];
  error?: string;
}

export function useDeckBundle(id: string | undefined): DeckBundleState {
  const [bundles, setBundles] = useState<RawDeckBundle[]>([]);
  const [status, setStatus] = useState<DeckBundleState['status']>('loading');
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    let cancelled = false;
    setStatus('loading');
    setError(undefined);
    if (!id) {
      setStatus('not-found');
      return;
    }
    (async () => {
      try {
        const idx = await deckLoader.loadIndex();
        if (cancelled) return;
        if (!idx.commanders.find((c) => c.id === id)) {
          setStatus('not-found');
          return;
        }
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
  }, [id]);

  const decks = useMemo(() => normalizeDecks(bundles), [bundles]);
  const stubs = useMemo(() => buildDeckStubs(decks), [decks]);
  const deck = useMemo(() => decks.find((d) => d.slug === id) ?? null, [decks, id]);

  return { status, deck, stubs, error };
}
