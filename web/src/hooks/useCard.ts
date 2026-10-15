import { useEffect, useState } from 'react';
import { cardCache, type CardEntry, type EnqueueOptions } from '../data/cardCache';

export function useCard(name: string | undefined, options: EnqueueOptions = {}): CardEntry | null {
  const [entry, setEntry] = useState<CardEntry | null>(() => (name ? cardCache.get(name) : null));
  const first = options.first ?? false;
  useEffect(() => {
    if (!name) {
      setEntry(null);
      return;
    }
    const cur = cardCache.get(name);
    setEntry(cur);
    const unsub = cardCache.subscribe(name, setEntry);
    if (!cur || cur.status === 'error') cardCache.enqueue(name, { first });
    return unsub;
  }, [name, first]);
  return entry;
}
