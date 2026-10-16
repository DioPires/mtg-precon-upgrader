// DEC-1190: the words that a screen reader hears for a glyph, a colour and a mana cost.

import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Glyph, GlyphText, GlyphWords } from '../../components/atoms/Glyph';
import { GV1ManaPips } from '../../components/atoms/GV1ManaPips';
import { ManaCost } from '../../components/atoms/ManaCost';
import { colorWords } from '../../components/atoms/colorWords';

describe('colorWords', () => {
  it('names the emoji and the letters in the order given', () => {
    expect(colorWords('🔵🔴')).toBe('blue, red');
    expect(colorWords('⚪⚫🟢')).toBe('white, black, green');
    expect(colorWords('BR')).toBe('black, red');
    expect(colorWords('wu')).toBe('white, blue');
  });

  it('reads an empty identity, ◇ and C as colorless', () => {
    expect(colorWords('')).toBe('colorless');
    expect(colorWords('◇')).toBe('colorless');
    expect(colorWords('C')).toBe('colorless');
  });
});

describe('GV1ManaPips', () => {
  it('names the colours of the identity', () => {
    const { container } = render(<GV1ManaPips colors="🔵🔴" />);
    expect(container.querySelector('.gv1-pips')!.getAttribute('aria-label')).toBe('Color identity: blue, red');
  });

  it('reads no colour as colorless', () => {
    for (const colors of ['', '◇', undefined]) {
      const { container } = render(<GV1ManaPips colors={colors} />);
      expect(container.querySelector('.gv1-pips')!.getAttribute('aria-label')).toBe('Color identity: colorless');
    }
  });
});

describe('ManaCost', () => {
  const label = (mv: string) => {
    const { container } = render(<ManaCost mv={mv} />);
    return container.querySelector('.gv1-mv')!.getAttribute('aria-label');
  };

  it('names every kind of pip with colour words', () => {
    expect(label('{2}{U}{U}')).toBe('Mana cost: 2 generic, blue, blue');
    expect(label('{X}{R}')).toBe('Mana cost: X variable, red');
    expect(label('{C}{S}')).toBe('Mana cost: colorless, snow');
    expect(label('{W/U}')).toBe('Mana cost: white or blue hybrid');
    expect(label('{2/W}')).toBe('Mana cost: 2 or white hybrid');
    expect(label('{W/P}')).toBe('Mana cost: white or 2 life phyrexian');
    expect(label('{B/G/P}')).toBe('Mana cost: black or green or 2 life phyrexian');
  });

  it('keeps the land and the dash as they were', () => {
    for (const mv of ['LAND', '—']) {
      const { container } = render(<ManaCost mv={mv} />);
      const root = container.querySelector('.gv1-mv')!;
      expect(root.getAttribute('role')).toBeNull();
      expect(root.textContent).toBe(mv);
    }
  });
});

describe('Glyph, GlyphWords and GlyphText', () => {
  it('hides a decorative glyph', () => {
    const { container } = render(<p>Copied<Glyph> ◆</Glyph></p>);
    expect(container.querySelector('[aria-hidden="true"]')!.textContent).toBe(' ◆');
    expect(container.textContent).toBe('Copied ◆');
  });

  it('gives a meaning glyph its words, and keeps a space at their edge', () => {
    const { container } = render(
      <a>
        spellbook<GlyphWords words=" (opens in a new tab)"> ↗</GlyphWords>
      </a>,
    );
    expect(container.querySelector('[aria-hidden="true"]')!.textContent).toBe(' ↗');
    expect(container.querySelector('.gv1-sr-only')!.textContent).toBe(' (opens in a new tab)');
  });

  it('splits a data string at each glyph that it names, and changes no character that shows', () => {
    const { container } = render(<p><GlyphText text="Adds mana ↔ Untaps a permanent" words={{ '↔': 'pairs with' }} /></p>);
    const p = container.querySelector('p')!;
    expect(p.querySelector('[aria-hidden="true"]')!.textContent).toBe('↔');
    expect(p.querySelector('.gv1-sr-only')!.textContent).toBe('pairs with');
    const shown = [...p.childNodes].filter((n) => !(n instanceof HTMLElement && n.classList.contains('gv1-sr-only')));
    expect(shown.map((n) => n.textContent).join('')).toBe('Adds mana ↔ Untaps a permanent');
  });

  it('renders a string with none of the glyphs as it is', () => {
    const { container } = render(<p><GlyphText text="GC for GC — count unchanged" words={{ '→': 'to' }} /></p>);
    expect(container.querySelector('p')!.innerHTML).toBe('GC for GC — count unchanged');
  });
});
