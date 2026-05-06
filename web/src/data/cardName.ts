// Shared card-name normalization for Shopping / built-decks reservation.
//
// deck.json stores multi-face cards in their canonical Scryfall
// `Front // Back` form (DFC, MDFC, transform, split, aftermath, adventure).
// Owned-card CSVs typically list only the front face. Routing both sides of
// every name-keyed comparison through `frontFace` so that lookups don't miss.

export function frontFace(name: string): string {
  const i = name.indexOf(' // ');
  return i === -1 ? name : name.slice(0, i);
}
