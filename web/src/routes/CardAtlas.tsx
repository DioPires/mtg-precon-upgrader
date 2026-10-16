import { useAllDecks } from '../hooks/useAllDecks';
import { Glyph } from '../components/atoms/Glyph';
import { CardAtlas as CardAtlasOrganism } from '../components/organisms/CardAtlas';

export function CardAtlas() {
  const { status, decks, error } = useAllDecks();

  if (status === 'loading') {
    return (
      <section className="gv1-stub" aria-busy="true">
        <p className="gv1-mono-xs gv1-dim"><Glyph>◇ </Glyph>charting the atlas …</p>
      </section>
    );
  }
  if (status === 'error') {
    return (
      <section className="gv1-stub" role="alert">
        <h1 className="gv1-stub-title">Could not chart the atlas</h1>
        <p className="gv1-mono-xs gv1-dim">{error ?? 'unknown error'}</p>
      </section>
    );
  }
  return <CardAtlasOrganism decks={decks} />;
}
