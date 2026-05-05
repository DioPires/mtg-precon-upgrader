import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { App } from '../App';

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe('App shell', () => {
  it('renders topbar landmarks', () => {
    renderAt('/');
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: /surfaces/i })).toBeInTheDocument();
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('routes /codex to the codex stub', () => {
    renderAt('/codex');
    expect(screen.getByRole('heading', { name: /codex/i })).toBeInTheDocument();
  });

  it('routes /deck/:id and reads the param', () => {
    renderAt('/deck/titan-convergence');
    expect(screen.getByText(/titan-convergence/)).toBeInTheDocument();
  });

  it('renders 404 for unknown routes', () => {
    renderAt('/no-such-surface');
    expect(screen.getByRole('heading', { name: /404/ })).toBeInTheDocument();
  });
});
