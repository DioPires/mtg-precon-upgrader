// Tracks the deck the user most recently viewed on a deck-scoped surface
// (Deck Guide / Scrying). Topbar reads this to point Guide/Scrying nav links
// at a real deck instead of a hard-coded sentinel.

export const LAST_DECK_KEY = 'grimoire-last-deck';

export function rememberLastDeck(id: string | undefined | null): void {
  if (!id || id === '_') return;
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(LAST_DECK_KEY, id);
  } catch {
    // localStorage unavailable / quota — best effort.
  }
}
