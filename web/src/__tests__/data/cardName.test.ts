import { describe, expect, it } from 'vitest';
import { frontFace } from '../../data/cardName';

describe('frontFace', () => {
  it('strips the back face from a DFC name', () => {
    expect(frontFace('Sephiroth, Fabled SOLDIER // Final Heaven')).toBe('Sephiroth, Fabled SOLDIER');
  });

  it('strips the back face from a split / aftermath name', () => {
    expect(frontFace('Dusk // Dawn')).toBe('Dusk');
  });

  it('strips the adventure back face', () => {
    expect(frontFace('Brazen Borrower // Petty Theft')).toBe('Brazen Borrower');
  });

  it('returns the name unchanged when no back face is present', () => {
    expect(frontFace('Sol Ring')).toBe('Sol Ring');
  });

  it('does not split on a single-slash name (no surrounding spaces)', () => {
    expect(frontFace('Foo/Bar')).toBe('Foo/Bar');
  });
});
