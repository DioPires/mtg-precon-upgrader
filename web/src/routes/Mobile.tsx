import { Navigate, useLocation, useParams } from 'react-router-dom';

// DEC-183: the iPhone-bezel artboard retired. Existing /m/:id bookmarks land on
// the responsive deck guide so user-shared links don't 404. App.tsx route stays
// wired for one release, then deletes in a follow-up.
export function Mobile() {
  const { id } = useParams<{ id: string }>();
  const { search } = useLocation();
  if (!id) return <Navigate to="/codex" replace />;
  return <Navigate to={`/deck/${id}${search}`} replace />;
}
