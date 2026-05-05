import { useParams } from 'react-router-dom';

export function Scrying() {
  const { id } = useParams();
  return (
    <section aria-labelledby="scrying-title">
      <h1 id="scrying-title" className="gv1-stub-title">§VIII Scrying Pool</h1>
      <p className="gv1-stub">deck = {id ?? '—'} · hand sim + swap analyzer — port in Phase 5.</p>
    </section>
  );
}
