import { useAllDecks } from '../hooks/useAllDecks';
import { Glyph } from '../components/atoms/Glyph';
import { Shopping as ShoppingOrganism } from '../components/organisms/Shopping';

export function Shopping() {
  const { status, decks, error } = useAllDecks();

  if (status === 'loading') {
    return (
      <section className="gv1-stub" aria-busy="true">
        <p className="gv1-mono-xs gv1-dim"><Glyph>◇ </Glyph>shelving the tomes …</p>
      </section>
    );
  }
  if (status === 'error') {
    return (
      <section className="gv1-stub" role="alert">
        <h1 className="gv1-stub-title">Could not scry the codex</h1>
        <p className="gv1-mono-xs gv1-dim">{error ?? 'unknown error'}</p>
      </section>
    );
  }
  return <ShoppingOrganism decks={decks} />;
}
