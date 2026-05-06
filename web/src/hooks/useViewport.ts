import { useEffect, useState } from 'react';

const MOBILE_QUERY = '(max-width: 768px)';

function safeMatchMedia(query: string): MediaQueryList | null {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return null;
  try {
    return window.matchMedia(query);
  } catch {
    return null;
  }
}

export function useIsMobileViewport(): boolean {
  const [isMobile, setIsMobile] = useState<boolean>(() => {
    const mq = safeMatchMedia(MOBILE_QUERY);
    return mq ? mq.matches : false;
  });

  useEffect(() => {
    const mq = safeMatchMedia(MOBILE_QUERY);
    if (!mq) return;
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    setIsMobile(mq.matches);
    if (typeof mq.addEventListener === 'function') {
      mq.addEventListener('change', handler);
      return () => mq.removeEventListener('change', handler);
    }
    mq.addListener(handler);
    return () => mq.removeListener(handler);
  }, []);

  return isMobile;
}
