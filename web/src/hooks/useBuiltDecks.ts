import { useCallback, useState } from 'react';
import {
  getBuiltDecks,
  setBuiltDecks as persistBuiltDecks,
} from '../data/builtDecks';

export interface UseBuiltDecks {
  built: Set<string>;
  toggle: (id: string) => void;
  setAll: (ids: string[]) => void;
  clear: () => void;
}

/**
 * Hook for the built-decks Set, persisted to localStorage under
 * `grimoire-built-decks`. Read once on mount, write on every change.
 */
export function useBuiltDecks(): UseBuiltDecks {
  const [built, setBuilt] = useState<Set<string>>(() => getBuiltDecks());

  const toggle = useCallback((id: string) => {
    setBuilt((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      persistBuiltDecks(next);
      return next;
    });
  }, []);

  const setAll = useCallback((ids: string[]) => {
    const next = new Set(ids);
    persistBuiltDecks(next);
    setBuilt(next);
  }, []);

  const clear = useCallback(() => {
    const next = new Set<string>();
    persistBuiltDecks(next);
    setBuilt(next);
  }, []);

  return { built, toggle, setAll, clear };
}
