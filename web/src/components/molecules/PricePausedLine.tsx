import { useEffect, useState } from 'react';
import { scryfallLimiter, type ScryfallLimiter } from '../../data/scryfallLimiter';
import { clockTime } from '../../lib/pricesDate';

interface PricePausedLineProps {
  /** True while at least one row of the page waits for a price refresh. */
  waiting: boolean;
  /** The date of the prices shown, e.g. "13 Oct 2026"; null when it is unknown. */
  pricesDate: string | null;
  limiter?: ScryfallLimiter;
}

/**
 * /shopping's line while a stop holds the price refresh (DEC-1131 R2). The line
 * does not say that Scryfall asked for the pause: the app cannot tell a 429 from
 * a lost network.
 *
 * It reads stoppedUntil() at each render. A listener only renders it again: in
 * the tab that caps a stop after its clock went back, the listener's value is
 * the end from before the cap. A timer renders it again at the end of the stop,
 * so the line goes then, also when no request waits to end the stop.
 */
export function PricePausedLine({ waiting, pricesDate, limiter = scryfallLimiter }: PricePausedLineProps) {
  const [, rerender] = useState(0);
  useEffect(() => limiter.subscribe(() => rerender((n) => n + 1)), [limiter]);
  const until = limiter.stoppedUntil();
  useEffect(() => {
    if (until === null) return;
    const id = window.setTimeout(() => rerender((n) => n + 1), Math.max(0, until - Date.now()) + 1);
    return () => window.clearTimeout(id);
  }, [until]);
  if (until === null || !waiting) return null;
  return (
    <p className="gv1-mono-xs gv1-shop-paused" role="status">
      Price refresh paused.
      {pricesDate ? ` Prices shown are from ${pricesDate}.` : ''}
      {` Next try at ${clockTime(until)}.`}
    </p>
  );
}
