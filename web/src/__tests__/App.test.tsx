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

  it('routes /codex to the codex surface (loading state shown synchronously)', () => {
    renderAt('/codex');
    expect(screen.getByText(/scrying the codex/i)).toBeInTheDocument();
  });

  it('routes /atlas to the card atlas surface (loading state shown synchronously)', () => {
    renderAt('/atlas');
    expect(screen.getByText(/charting the atlas/i)).toBeInTheDocument();
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
