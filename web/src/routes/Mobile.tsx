import { useEffect } from 'react';
import { Navigate, useLocation, useParams } from 'react-router-dom';
import { useDeckBundle } from '../hooks/useDeckBundle';
import { useDeckColorTheme } from '../hooks/useDeckColorTheme';
import { useIsMobileViewport } from '../hooks/useViewport';
import { rememberLastDeck } from '../data/lastDeck';
import { Mobile as MobileOrganism } from '../components/organisms/Mobile';

export function Mobile() {
  const { id } = useParams<{ id: string }>();
  const isMobile = useIsMobileViewport();
  const { search } = useLocation();
  const { status, deck, error } = useDeckBundle(id);
  useDeckColorTheme(id);
  useEffect(() => {
    if (status === 'loaded' && deck) rememberLastDeck(id);
  }, [status, deck, id]);

  // At >768px viewports, redirect to the desktop Guide so a window resize doesn't
  // strand the user on a phone-bezel artboard. The /m/:id URL still works as a
  // direct entry point on phone-sized viewports per SCOPE § 4.
  if (!isMobile && id) {
    return <Navigate to={`/deck/${id}${search}`} replace />;
  }

  if (status === 'loading') {
    return (
      <section className="gv1-stub" aria-busy="true">
        <p className="gv1-mono-xs gv1-dim">◇ scrying {id ?? '—'} …</p>
      </section>
    );
  }
  if (status === 'not-found') {
    return (
      <section className="gv1-stub">
        <h1 className="gv1-stub-title">Tomus not found</h1>
        <p className="gv1-mono-xs gv1-dim">Deck slug "{id}" is not in the codex.</p>
      </section>
    );
  }
  if (status === 'error' || !deck) {
    return (
      <section className="gv1-stub" role="alert">
        <h1 className="gv1-stub-title">Could not scry the codex</h1>
        <p className="gv1-mono-xs gv1-dim">{error ?? 'unknown error'}</p>
      </section>
    );
  }
  return <MobileOrganism deck={deck} />;
}
