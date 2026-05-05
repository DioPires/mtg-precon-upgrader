import { useParams } from 'react-router-dom';

export function DeckGuide() {
  const { id } = useParams();
  return (
    <section aria-labelledby="deck-title">
      <h1 id="deck-title" className="gv1-stub-title">§II Deck Guide</h1>
      <p className="gv1-stub">deck = {id ?? '—'} · port in Phase 2.</p>
    </section>
  );
}
