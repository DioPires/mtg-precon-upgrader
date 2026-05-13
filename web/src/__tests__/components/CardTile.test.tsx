import { describe, expect, it, beforeEach } from 'vitest';
import { fireEvent, render, waitFor } from '@testing-library/react';
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
  it('prefers the local downloaded card image before live Scryfall art', () => {
    render(<CardTile card={{ n: 'Sol Ring', mv: '{1}', type: 'Artifact' }} />);

    const img = document.querySelector<HTMLImageElement>('img.gv1-card-tile-img')!;
    expect(img.src).toContain('/data/images/cards/sol-ring-normal.jpg');
  });

  it('falls back to live Scryfall image_normal when the local image is missing', async () => {
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
    const img = document.querySelector<HTMLImageElement>('img.gv1-card-tile-img')!;
    const initialSrc = img.src;
    fireEvent.error(img);
    await waitFor(() => expect(document.querySelector<HTMLImageElement>('img.gv1-card-tile-img')?.src).toContain('/normal/'));
    expect(initialSrc).toContain('/data/images/cards/sol-ring-normal.jpg');
    const liveImg = document.querySelector<HTMLImageElement>('img.gv1-card-tile-img')!;
    expect(liveImg.src).toContain('/normal/');
    expect(liveImg.src).not.toContain('/small/');
  });

  it('falls back to live Scryfall image_small when image_normal is missing', async () => {
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
    const img = document.querySelector<HTMLImageElement>('img.gv1-card-tile-img')!;
    fireEvent.error(img);
    await waitFor(() => {
      expect(document.querySelector<HTMLImageElement>('img.gv1-card-tile-img')?.src).toContain('/small/');
    });
    const liveImg = document.querySelector<HTMLImageElement>('img.gv1-card-tile-img')!;
    expect(liveImg.src).toContain('/small/');
  });

  it('renders the local image file slug for punctuation-heavy names', () => {
    render(<CardTile card={{ n: "Agadeem's Awakening", mv: '{X}{B}{B}{B}', type: 'Sorcery' }} />);
    const img = document.querySelector<HTMLImageElement>('img.gv1-card-tile-img')!;
    expect(img.src).toContain('/data/images/cards/agadeem-s-awakening-normal.jpg');
  });
});
