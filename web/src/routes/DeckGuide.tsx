import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useDeckBundle } from '../hooks/useDeckBundle';
import { useDeckColorTheme } from '../hooks/useDeckColorTheme';
import { rememberLastDeck } from '../data/lastDeck';
import { Commander } from '../components/organisms/Commander';
import { DeckSelector } from '../components/organisms/DeckSelector';
import { WinCons } from '../components/organisms/WinCons';
import { Engine } from '../components/organisms/Engine';
import { Combos } from '../components/organisms/Combos';
import { Performance } from '../components/organisms/Performance';
import { Apothecary } from '../components/organisms/Apothecary';
import { Decklist } from '../components/organisms/Decklist';

export function DeckGuide() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { status, deck, stubs, error } = useDeckBundle(id);
  useDeckColorTheme(id);
  useEffect(() => {
    if (status === 'loaded' && deck) rememberLastDeck(id);
  }, [status, deck, id]);

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

  const onSelect = (idx: number) => {
    const next = stubs.find((s) => s.idx === idx);
    if (next) navigate(`/deck/${next.slug}`);
  };

  return (
    <div className="gv1-deck-guide">
      <DeckSelector decks={stubs} activeIdx={deck.idx} onSelect={onSelect} />
      <Commander deck={deck} />
      <WinCons wincons={deck.wincons} />
      <Engine engine={deck.engine} />
      <Combos combos={deck.combos} />
      <Performance
        curve={deck.curve}
        func={deck.func}
        sources={deck.sources}
        health={deck.health}
        composition={deck.composition}
        assessment={deck.assessment}
      />
      <Apothecary apothecary={deck.apothecary} />
      <Decklist list={deck.list} />
    </div>
  );
}
