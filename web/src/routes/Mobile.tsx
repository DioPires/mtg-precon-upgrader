import { useParams } from 'react-router-dom';

export function Mobile() {
  const { id } = useParams();
  return (
    <section aria-labelledby="mobile-title">
      <h1 id="mobile-title" className="gv1-stub-title">Mobile Guide</h1>
      <p className="gv1-stub">deck = {id ?? '—'} · responsive guide artboard — port in Phase 4.</p>
    </section>
  );
}
