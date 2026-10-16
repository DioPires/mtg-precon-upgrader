// DEC-1190: the words that a screen reader hears for a colour or a colour
// identity. It reads the emoji of `colorsToGlyphs` (⚪ 🔵 ⚫ 🔴 🟢 ◇) and the
// letters W U B R G C, in the order given.

const COLOR_WORD: Record<string, string> = {
  W: 'white',
  '⚪': 'white',
  U: 'blue',
  '🔵': 'blue',
  B: 'black',
  '⚫': 'black',
  R: 'red',
  '🔴': 'red',
  G: 'green',
  '🟢': 'green',
};

/** "blue, red" for "🔵🔴" or "UR"; "colorless" for "", "◇" or "C". */
export function colorWords(colors: string): string {
  const words = Array.from(colors.toUpperCase())
    .map((c) => COLOR_WORD[c])
    .filter(Boolean);
  return words.length ? words.join(', ') : 'colorless';
}
