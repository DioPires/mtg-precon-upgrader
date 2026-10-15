/** The noun for a count of cards: `card` for one, `cards` for any other count (DEC-1123, DEC-1142). */
export function cardNoun(count: number): string {
  return count === 1 ? 'card' : 'cards';
}
