import { Link } from 'react-router-dom';

export function NotFound() {
  return (
    <section aria-labelledby="nf-title">
      <h1 id="nf-title" className="gv1-stub-title">404</h1>
      <p className="gv1-stub">No such surface. <Link to="/">Return to the grimoire.</Link></p>
    </section>
  );
}
