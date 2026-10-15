// DEC-1110 reviewer's kill cases for cardEntry.ts. Each passes on 58ca0b3 and
// fails on the mutant named in its title.
import { cardEntryFromFile, formatUsd } from '../../data/cardEntry';

describe('K9 formatUsd(): two decimals', () => {
  it('K9: a file price of 0.9 shows as $0.90, and 27 as $27.00', () => {
    expect(cardEntryFromFile("Agna Qel'a", { usd: 0.9, eur: null, image: 'front/a/b/x.jpg' }).price).toBe('$0.90');
    expect(formatUsd(27)).toBe('$27.00');
    expect(formatUsd('16.1')).toBe('$16.10');
  });
});
