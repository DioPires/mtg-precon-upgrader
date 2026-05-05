// Apply per-deck color-identity theming to <body> while a deck route is mounted.
//
// Mirrors the legacy `selectDeck()` behavior in legacy/app.js:1726-1729 — strips
// any prior `colors-*` class, then re-applies `colors-{sortedLetters}` derived
// from the deck's color identity in data/index.json. CSS overrides for each
// combo live in web/src/styles/deck-theme.css.

import { useEffect, useState } from 'react';
import { deckLoader } from '../data/loader';

const COLOR_CLASS_PATTERN = /\bcolors-[A-Z]+\b/g;

function clearColorClasses(): void {
  if (typeof document === 'undefined') return;
  document.body.className = document.body.className
    .replace(COLOR_CLASS_PATTERN, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function applyColorClass(letters: string[]): void {
  if (typeof document === 'undefined' || letters.length === 0) return;
  const cls = 'colors-' + [...letters].sort().join('');
  clearColorClasses();
  document.body.classList.add(cls);
}

export function useDeckColorTheme(deckId: string | undefined): void {
  const [colors, setColors] = useState<string[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!deckId) {
      setColors(null);
      return;
    }
    deckLoader
      .loadIndex()
      .then((idx) => {
        if (cancelled) return;
        const entry = idx.commanders.find((c) => c.id === deckId);
        setColors(entry?.colors ?? null);
      })
      .catch(() => {
        if (cancelled) return;
        setColors(null);
      });
    return () => {
      cancelled = true;
    };
  }, [deckId]);

  useEffect(() => {
    if (!colors) return;
    applyColorClass(colors);
    return () => clearColorClasses();
  }, [colors]);
}
