import { useParams } from 'react-router-dom';
import { useDeckBundle } from '../hooks/useDeckBundle';
import { useDeckColorTheme } from '../hooks/useDeckColorTheme';
import { Mobile as MobileOrganism } from '../components/organisms/Mobile';

export function Mobile() {
  const { id } = useParams<{ id: string }>();
  const { status, deck, error } = useDeckBundle(id);
  useDeckColorTheme(id);

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
