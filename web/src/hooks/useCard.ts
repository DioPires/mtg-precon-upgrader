import { useEffect, useState } from 'react';
import { cardCache, type CardEntry } from '../data/cardCache';

export function useCard(name: string | undefined): CardEntry | null {
  const [entry, setEntry] = useState<CardEntry | null>(() => (name ? cardCache.get(name) : null));
  useEffect(() => {
    if (!name) {
      setEntry(null);
      return;
    }
    const cur = cardCache.get(name);
    setEntry(cur);
    const unsub = cardCache.subscribe(name, setEntry);
    if (!cur) cardCache.enqueue(name);
    return unsub;
  }, [name]);
  return entry;
}
