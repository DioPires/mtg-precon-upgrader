import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { ManaCost, classifySymbol } from '../../components/atoms/ManaCost';

describe('classifySymbol', () => {
  it('classifies numeric symbols', () => {
    expect(classifySymbol('0')).toEqual({ kind: 'num', label: '0' });
    expect(classifySymbol('7')).toEqual({ kind: 'num', label: '7' });
    expect(classifySymbol('20')).toEqual({ kind: 'num', label: '20' });
  });

  it('classifies colorless and snow', () => {
    expect(classifySymbol('C')).toEqual({ kind: 'c' });
    expect(classifySymbol('S')).toEqual({ kind: 's' });
  });

  it('classifies variable mana X/Y/Z', () => {
    expect(classifySymbol('X')).toEqual({ kind: 'var', label: 'X' });
    expect(classifySymbol('Y')).toEqual({ kind: 'var', label: 'Y' });
    expect(classifySymbol('Z')).toEqual({ kind: 'var', label: 'Z' });
  });

  it('classifies mono colors WUBRG', () => {
    for (const c of ['W', 'U', 'B', 'R', 'G'] as const) {
      expect(classifySymbol(c)).toEqual({ kind: 'mono', color: c });
    }
  });

  it('classifies hybrid pairs', () => {
    expect(classifySymbol('W/U')).toEqual({ kind: 'hybrid', a: 'W', b: 'U' });
    expect(classifySymbol('B/G')).toEqual({ kind: 'hybrid', a: 'B', b: 'G' });
  });

  it('classifies monocolor hybrid {2/X}', () => {
    expect(classifySymbol('2/W')).toEqual({ kind: 'mono-hybrid', color: 'W' });
    expect(classifySymbol('2/G')).toEqual({ kind: 'mono-hybrid', color: 'G' });
  });

  it('classifies phyrexian {C/P}', () => {
    expect(classifySymbol('B/P')).toEqual({ kind: 'phy', color: 'B' });
    expect(classifySymbol('W/P')).toEqual({ kind: 'phy', color: 'W' });
  });

  it('classifies hybrid phyrexian {C/C/P}', () => {
    expect(classifySymbol('B/G/P')).toEqual({ kind: 'phy-hybrid', a: 'B', b: 'G' });
  });

  it('falls back to unknown without crashing', () => {
    expect(classifySymbol('FOO')).toEqual({ kind: 'unknown', label: 'FOO' });
  });
});

describe('<ManaCost>', () => {
  it('renders LAND sentinel as styled placeholder', () => {
    const { container } = render(<ManaCost mv="LAND" />);
    const span = container.querySelector('.gv1-mv-land');
    expect(span?.textContent).toBe('LAND');
  });

  it('renders empty / em-dash as land placeholder', () => {
    const { container } = render(<ManaCost mv="—" />);
    expect(container.querySelector('.gv1-mv-land')?.textContent).toBe('—');
  });

  it('renders {2}{B}{G} as numeric + black + green pips', () => {
    const { container } = render(<ManaCost mv="{2}{B}{G}" />);
    const pips = container.querySelectorAll('.gv1-mv-pip');
    expect(pips).toHaveLength(3);
    expect(pips[0].className).toContain('gv1-mv-n');
    expect(pips[0].textContent).toBe('2');
    expect(pips[1].className).toContain('gv1-mv-B');
    expect(pips[1].textContent).toBe('B');
    expect(pips[2].className).toContain('gv1-mv-G');
    expect(pips[2].textContent).toBe('G');
  });

  it('renders {X}{R}{R} (Fireball) as variable + 2 red pips', () => {
    const { container } = render(<ManaCost mv="{X}{R}{R}" />);
    const pips = container.querySelectorAll('.gv1-mv-pip');
    expect(pips).toHaveLength(3);
    expect(pips[0].className).toContain('gv1-mv-x');
    expect(pips[0].textContent).toBe('X');
    expect(pips[1].className).toContain('gv1-mv-R');
    expect(pips[2].className).toContain('gv1-mv-R');
  });

  it('renders {B/P}{B/P} (Gut Shot) with phyrexian glyph + correct color', () => {
    const { container } = render(<ManaCost mv="{B/P}{B/P}" />);
    const pips = container.querySelectorAll('.gv1-mv-pip');
    expect(pips).toHaveLength(2);
    pips.forEach((pip) => {
      expect(pip.className).toContain('gv1-mv-phy');
      expect(pip.className).toContain('gv1-mv-phy-B');
      expect(pip.textContent).toBe('Φ');
    });
  });

  it('renders {2/W}{2/W} (Spectral Procession) as monocolor-hybrid pips', () => {
    const { container } = render(<ManaCost mv="{2/W}{2/W}" />);
    const pips = container.querySelectorAll('.gv1-mv-pip');
    expect(pips).toHaveLength(2);
    pips.forEach((pip) => {
      expect(pip.className).toContain('gv1-mv-mhy');
      expect(pip.querySelector('.gv1-mv-hyb-a')?.textContent).toBe('2');
      expect(pip.querySelector('.gv1-mv-hyb-b')?.textContent).toBe('W');
    });
  });

  it('renders hybrid {W/U} as split-color pip with both letters', () => {
    const { container } = render(<ManaCost mv="{W/U}" />);
    const pip = container.querySelector('.gv1-mv-pip')!;
    expect(pip.className).toContain('gv1-mv-hyb');
    expect(pip.querySelector('.gv1-mv-hyb-a')?.textContent).toBe('W');
    expect(pip.querySelector('.gv1-mv-hyb-b')?.textContent).toBe('U');
  });

  it('renders {S} as a snow pip', () => {
    const { container } = render(<ManaCost mv="{S}" />);
    const pip = container.querySelector('.gv1-mv-pip')!;
    expect(pip.className).toContain('gv1-mv-s');
    expect(pip.textContent).toBe('❄');
  });

  it('renders {C} as a colorless pip', () => {
    const { container } = render(<ManaCost mv="{C}" />);
    const pip = container.querySelector('.gv1-mv-pip')!;
    expect(pip.className).toContain('gv1-mv-c');
    expect(pip.textContent).toBe('C');
  });

  it('renders unknown symbols as fallback without throwing', () => {
    const { container } = render(<ManaCost mv="{HALF}" />);
    const pip = container.querySelector('.gv1-mv-pip')!;
    expect(pip.className).toContain('gv1-mv-g');
    expect(pip.textContent).toBe('HALF');
  });

  it('renders an aria-label describing the full cost', () => {
    const { container } = render(<ManaCost mv="{2}{B}{G}" />);
    const root = container.querySelector('.gv1-mv')!;
    expect(root.getAttribute('aria-label')).toBe('mana cost {2}{B}{G}');
  });
});
