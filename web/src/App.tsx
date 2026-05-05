import { Navigate, Route, Routes, useParams } from 'react-router-dom';
import { Topbar } from './components/Topbar';
import { GV1CardHoverLayer } from './components/global/GV1CardHoverLayer';
import { Home } from './routes/Home';
import { Codex } from './routes/Codex';
import { DeckGuide } from './routes/DeckGuide';
import { Compare } from './routes/Compare';
import { Shopping } from './routes/Shopping';
import { Scrying } from './routes/Scrying';
import { Mobile } from './routes/Mobile';
import { Dev } from './routes/Dev';
import { NotFound } from './routes/NotFound';

export function App() {
  return (
    <div className="gv1-app gv1-root" data-gv1-screen="app">
      <Topbar />
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/codex" element={<Codex />} />
          <Route path="/deck/:id" element={<DeckGuide />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/shopping" element={<Shopping />} />
          <Route path="/scrying/:id" element={<Scrying />} />
          <Route path="/m/:id" element={<Mobile />} />
          <Route path="/mobile/:id" element={<MobileRedirect />} />
          <Route path="/_dev" element={<Dev />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <GV1CardHoverLayer />
    </div>
  );
}

function MobileRedirect() {
  const { id } = useParams();
  return <Navigate to={`/m/${id}`} replace />;
}
