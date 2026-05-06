import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useDeckBundle } from '../hooks/useDeckBundle';
import { useDeckColorTheme } from '../hooks/useDeckColorTheme';
import { useAllDecks } from '../hooks/useAllDecks';
import { rememberLastDeck } from '../data/lastDeck';
import { Scrying as ScryingOrganism } from '../components/organisms/Scrying';
import { DeckSelector } from '../components/organisms/DeckSelector';

export function Scrying() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { status, deck, stubs, error } = useDeckBundle(id);
  const all = useAllDecks();
  useDeckColorTheme(id);
  useEffect(() => {
    if (status === 'loaded' && deck) rememberLastDeck(id);
  }, [status, deck, id]);

  if (status === 'loading' || all.status === 'loading') {
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
  if (status === 'error' || all.status === 'error' || !deck) {
    return (
      <section className="gv1-stub" role="alert">
        <h1 className="gv1-stub-title">Could not scry the codex</h1>
        <p className="gv1-mono-xs gv1-dim">{error ?? all.error ?? 'unknown error'}</p>
      </section>
    );
  }

  const onSelect = (idx: number) => {
    const next = stubs.find((s) => s.idx === idx);
    if (next) navigate(`/scrying/${next.slug}`);
  };

  return (
    <div className="gv1-deck-guide">
      <DeckSelector decks={stubs} activeIdx={deck.idx} onSelect={onSelect} />
      <ScryingOrganism deck={deck} allDecks={all.decks} />
    </div>
  );
}
