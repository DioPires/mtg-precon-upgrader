import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { App } from './App';

import './styles/tokens.css';
import './styles/deck-theme.css';
import './styles/states.css';
import './styles/styles.css';
import './styles/app.css';
import './styles/combo-lab.css';

const container = document.getElementById('root');
if (!container) throw new Error('#root not found');

createRoot(container).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
