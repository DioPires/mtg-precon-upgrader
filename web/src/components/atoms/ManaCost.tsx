// Mana cost pip rendering. Handles the full Scryfall mana symbol set:
// numeric, colorless, mono WUBRG, variable X/Y/Z, hybrid, monocolor hybrid
// ({2/W}), phyrexian ({W/P}), hybrid phyrexian ({B/G/P}), snow ({S}).
// CSS-only — no SVG / asset deps. Colors come from --gv1-mana-* tokens.

import type { CSSProperties } from 'react';

interface ManaCostProps {
  mv?: string;
}

type Pip =
  | { kind: 'num'; label: string }
  | { kind: 'c' }
  | { kind: 's' }
  | { kind: 'var'; label: 'X' | 'Y' | 'Z' }
  | { kind: 'mono'; color: Color }
  | { kind: 'hybrid'; a: Color; b: Color }
  | { kind: 'mono-hybrid'; color: Color }
  | { kind: 'phy'; color: Color }
  | { kind: 'phy-hybrid'; a: Color; b: Color }
  | { kind: 'unknown'; label: string };

type Color = 'W' | 'U' | 'B' | 'R' | 'G';

const COLORS = new Set<Color>(['W', 'U', 'B', 'R', 'G']);

function isColor(s: string): s is Color {
  return COLORS.has(s as Color);
}

export function classifySymbol(raw: string): Pip {
  const sym = raw.toUpperCase();
  if (/^\d+$/.test(sym)) return { kind: 'num', label: sym };
  if (sym === 'C') return { kind: 'c' };
  if (sym === 'S') return { kind: 's' };
  if (sym === 'X' || sym === 'Y' || sym === 'Z') return { kind: 'var', label: sym };
  if (isColor(sym)) return { kind: 'mono', color: sym };

  const parts = sym.split('/');
  if (parts[parts.length - 1] === 'P') {
    const colors = parts.slice(0, -1);
    if (colors.length === 1 && isColor(colors[0])) {
      return { kind: 'phy', color: colors[0] };
    }
    if (colors.length === 2 && isColor(colors[0]) && isColor(colors[1])) {
      return { kind: 'phy-hybrid', a: colors[0], b: colors[1] };
    }
  }
  if (parts.length === 2 && parts[0] === '2' && isColor(parts[1])) {
    return { kind: 'mono-hybrid', color: parts[1] };
  }
  if (parts.length === 2 && isColor(parts[0]) && isColor(parts[1])) {
    return { kind: 'hybrid', a: parts[0], b: parts[1] };
  }
  return { kind: 'unknown', label: raw };
}

function colorVar(c: Color): string {
  return `var(--gv1-mana-${c.toLowerCase()})`;
}
function colorStrokeVar(c: Color): string {
  return `var(--gv1-mana-${c.toLowerCase()}-stroke)`;
}

function pipFor(p: Pip, key: number) {
  switch (p.kind) {
    case 'num':
      return (
        <span key={key} className="gv1-mv-pip gv1-mv-n" aria-label={`${p.label} generic mana`}>
          {p.label}
        </span>
      );
    case 'c':
      return (
        <span key={key} className="gv1-mv-pip gv1-mv-c" aria-label="colorless mana">
          C
        </span>
      );
    case 's':
      return (
        <span key={key} className="gv1-mv-pip gv1-mv-s" aria-label="snow mana">
          ❄
        </span>
      );
    case 'var':
      return (
        <span key={key} className="gv1-mv-pip gv1-mv-x" aria-label={`${p.label} variable mana`}>
          {p.label}
        </span>
      );
    case 'mono':
      return (
        <span
          key={key}
          className={`gv1-mv-pip gv1-mv-${p.color}`}
          aria-label={`${p.color} mana`}
        >
          {p.color}
        </span>
      );
    case 'hybrid':
      return (
        <span
          key={key}
          className="gv1-mv-pip gv1-mv-hyb"
          style={
            {
              '--gv1-mv-a': colorVar(p.a),
              '--gv1-mv-b': colorVar(p.b),
              '--gv1-mv-stroke': colorStrokeVar(p.a),
            } as CSSProperties
          }
          aria-label={`${p.a} or ${p.b} hybrid mana`}
        >
          <span className="gv1-mv-hyb-a">{p.a}</span>
          <span className="gv1-mv-hyb-b">{p.b}</span>
        </span>
      );
    case 'mono-hybrid':
      return (
        <span
          key={key}
          className="gv1-mv-pip gv1-mv-mhy"
          style={
            {
              '--gv1-mv-a': 'var(--gv1-mana-c)',
              '--gv1-mv-b': colorVar(p.color),
              '--gv1-mv-stroke': colorStrokeVar(p.color),
            } as CSSProperties
          }
          aria-label={`2 or ${p.color} hybrid mana`}
        >
          <span className="gv1-mv-hyb-a">2</span>
          <span className="gv1-mv-hyb-b">{p.color}</span>
        </span>
      );
    case 'phy':
      return (
        <span
          key={key}
          className={`gv1-mv-pip gv1-mv-phy gv1-mv-phy-${p.color}`}
          aria-label={`${p.color} or 2 life phyrexian mana`}
        >
          Φ
        </span>
      );
    case 'phy-hybrid':
      return (
        <span
          key={key}
          className="gv1-mv-pip gv1-mv-hyb gv1-mv-phy-hyb"
          style={
            {
              '--gv1-mv-a': colorVar(p.a),
              '--gv1-mv-b': colorVar(p.b),
              '--gv1-mv-stroke': colorStrokeVar(p.a),
            } as CSSProperties
          }
          aria-label={`${p.a}/${p.b} or 2 life phyrexian mana`}
        >
          <span className="gv1-mv-hyb-a">{p.a}</span>
          <span className="gv1-mv-hyb-b">{p.b}</span>
          <span className="gv1-mv-phy-glyph" aria-hidden="true">Φ</span>
        </span>
      );
    case 'unknown':
      return (
        <span key={key} className="gv1-mv-pip gv1-mv-g" aria-label={`mana ${p.label}`}>
          {p.label}
        </span>
      );
  }
}

export function ManaCost({ mv }: ManaCostProps) {
  if (!mv || mv === 'LAND' || mv === '—') {
    return <span className="gv1-mv gv1-mv-land">{mv || '—'}</span>;
  }
  const parts = mv.match(/\{[^}]+\}/g) || [];
  if (!parts.length) {
    return <span className="gv1-mv gv1-mv-land">—</span>;
  }
  return (
    <span className="gv1-mv" aria-label={`mana cost ${mv}`}>
      {parts.map((p, i) => pipFor(classifySymbol(p.slice(1, -1)), i))}
    </span>
  );
}
