import { describe, expect, it, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { CardTile } from '../../components/molecules/CardTile';
import { cardCache } from '../../data/cardCache';

function clearStorage() {
  for (let i = window.localStorage.length - 1; i >= 0; i--) {
    const k = window.localStorage.key(i);
    if (k) window.localStorage.removeItem(k);
  }
}

beforeEach(() => {
  cardCache._reset();
  clearStorage();
});

describe('CardTile', () => {
  it('renders the image_normal Scryfall URL, not image_small', async () => {
    window.localStorage.setItem(
      'gv1-card:sol ring',
      JSON.stringify({
        status: 'loaded',
        name: 'Sol Ring',
        image_small: 'https://cards.scryfall.io/small/foo.jpg',
        image_normal: 'https://cards.scryfall.io/normal/foo.jpg',
        image_large: 'https://cards.scryfall.io/large/foo.jpg',
        fetchedAt: Date.now(),
      }),
    );
    render(<CardTile card={{ n: 'Sol Ring' }} />);
    await waitFor(() => {
      const img = screen.getByRole('presentation', { hidden: true }) as HTMLImageElement | null;
      expect(img).toBeTruthy();
    });
    const img = document.querySelector<HTMLImageElement>('img.gv1-card-tile-img')!;
    expect(img.src).toContain('/normal/');
    expect(img.src).not.toContain('/small/');
  });

  it('falls back to image_small when image_normal is missing', async () => {
    window.localStorage.setItem(
      'gv1-card:sol ring',
      JSON.stringify({
        status: 'loaded',
        name: 'Sol Ring',
        image_small: 'https://cards.scryfall.io/small/foo.jpg',
        fetchedAt: Date.now(),
      }),
    );
    render(<CardTile card={{ n: 'Sol Ring' }} />);
    await waitFor(() => {
      expect(document.querySelector('img.gv1-card-tile-img')).toBeTruthy();
    });
    const img = document.querySelector<HTMLImageElement>('img.gv1-card-tile-img')!;
    expect(img.src).toContain('/small/');
  });
});
