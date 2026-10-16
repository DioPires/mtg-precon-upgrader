// DEC-1190: the source check, built from the DEC-1182 census (census.mjs).
//
// It parses each web/src/**/*.tsx outside the tests with the TypeScript
// compiler. It fails when JSX text, or a string literal that is a JSX child,
// holds a glyph and has no ancestor element with aria-hidden="true". `Glyph`
// and `GlyphWords` (components/atoms/Glyph.tsx) count as such an ancestor.
//
// A glyph: a character outside letters, marks, decimal digits, printable ASCII,
// white space, – — ‘ ’ “ ” …, the middle dot and the R0 signs below. A minus
// sign before a digit ("−1") is the sign of that number, as "-1" would be.
//
// Its limits:
// - R0 is a list of characters, not of places: an R0 sign in a decorative place passes.
// - It sees the JSX of one file: an aria-hidden ancestor that another component
//   renders around this JSX does not count, and such a site needs `Glyph`.
// - A string that reaches JSX through a variable, a call or a .ts module is not
//   a JSX child here. The Playwright spec tests/dec1190-glyph-names.spec.ts reads
//   those in Chromium's tree, in the states that it visits.
// - A string literal is a JSX child when only parentheses, `? :`, `&&`, `||`
//   and `??` stand between it and the `{ }` of a JSX child.

import { readFileSync, readdirSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';
import { describe, expect, it } from 'vitest';

const src = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');

// R0: a standard sign that sits in a number or a word (DEC-1182).
const R0 = ['№', '×', '±', '€', '©', '§', '∞'];
const HIDING_COMPONENTS = new Set(['Glyph', 'GlyphWords']);
// Imported by no module, so it never renders (DEC-1182 census). A case below fails once a module imports it.
const NEVER_RENDERED = ['components/organisms/Hero.tsx'];

export function glyphsIn(text: string): string[] {
  return [...text.replace(/−(?=\d)/g, '')].filter((ch) => {
    const cp = ch.codePointAt(0)!;
    if (cp >= 0x20 && cp <= 0x7e) return false;
    if (/\s/u.test(ch) || '–—‘’“”…·'.includes(ch) || R0.includes(ch)) return false;
    return !/[\p{L}\p{M}\p{Nd}]/u.test(ch);
  });
}

function sourceFiles(): string[] {
  return readdirSync(src, { recursive: true, encoding: 'utf8' })
    .filter((f) => f.endsWith('.tsx') && !f.includes('__tests__') && !f.endsWith('.test.tsx'))
    .map((f) => f.split('\\').join('/'))
    .sort();
}

function isHidden(el: ts.JsxElement | ts.JsxSelfClosingElement): boolean {
  const opening = ts.isJsxElement(el) ? el.openingElement : el;
  if (HIDING_COMPONENTS.has(opening.tagName.getText())) return true;
  return opening.attributes.properties.some((a) => {
    if (!ts.isJsxAttribute(a) || a.name.getText() !== 'aria-hidden') return false;
    const init = a.initializer;
    if (!init) return true;
    if (ts.isStringLiteral(init)) return init.text === 'true';
    return ts.isJsxExpression(init) && init.expression?.kind === ts.SyntaxKind.TrueKeyword;
  });
}

function hasHiddenAncestor(node: ts.Node): boolean {
  for (let p = node.parent; p; p = p.parent) {
    if ((ts.isJsxElement(p) || ts.isJsxSelfClosingElement(p)) && isHidden(p)) return true;
  }
  return false;
}

/** True when the literal is the value of a JSX child `{ }`, through parentheses, `? :`, `&&`, `||` and `??` only. */
function isJsxChild(node: ts.Node): boolean {
  let child = node;
  for (let p = node.parent; p; child = p, p = p.parent) {
    if (ts.isParenthesizedExpression(p)) continue;
    if (ts.isConditionalExpression(p) && child !== p.condition) continue;
    if (
      ts.isBinaryExpression(p) &&
      [ts.SyntaxKind.AmpersandAmpersandToken, ts.SyntaxKind.BarBarToken, ts.SyntaxKind.QuestionQuestionToken].includes(
        p.operatorToken.kind,
      )
    ) {
      continue;
    }
    return ts.isJsxExpression(p) && !!p.parent && (ts.isJsxElement(p.parent) || ts.isJsxFragment(p.parent));
  }
  return false;
}

interface Site {
  file: string;
  line: number;
  glyphs: string;
  text: string;
}

/** Every JSX text and JSX-child string literal of `code` that shows a glyph with no aria-hidden ancestor. */
export function uncovered(file: string, code: string): Site[] {
  const sf = ts.createSourceFile(file, code, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const out: Site[] = [];
  const check = (node: ts.Node, text: string) => {
    const glyphs = glyphsIn(text);
    if (!glyphs.length || hasHiddenAncestor(node)) return;
    const line = sf.getLineAndCharacterOfPosition(node.getStart()).line + 1;
    out.push({ file, line, glyphs: [...new Set(glyphs)].join(''), text: text.replace(/\s+/g, ' ').trim().slice(0, 60) });
  };
  const walk = (node: ts.Node) => {
    if (ts.isJsxText(node)) check(node, node.text);
    else if ((ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) && isJsxChild(node)) {
      check(node, node.text);
    } else if (ts.isTemplateExpression(node) && isJsxChild(node)) {
      check(node, [node.head.text, ...node.templateSpans.map((s) => s.literal.text)].join(''));
    }
    ts.forEachChild(node, walk);
  };
  walk(sf);
  return out;
}

describe('DEC-1190: no rendered JSX text shows a glyph to a screen reader', () => {
  it('finds no uncovered glyph in web/src/**/*.tsx', () => {
    const files = sourceFiles().filter((f) => !NEVER_RENDERED.includes(f));
    expect(files.length).toBeGreaterThan(30);
    const sites = files.flatMap((f) => uncovered(f, readFileSync(join(src, f), 'utf8')));
    expect(sites.map((s) => `${s.file}:${s.line} ${s.glyphs} "${s.text}"`)).toEqual([]);
  });

  it('skips only files that no module imports', () => {
    const importers = readdirSync(src, { recursive: true, encoding: 'utf8' })
      .filter((f) => /\.tsx?$/.test(f) && !f.includes('__tests__') && !/\.test\.tsx?$/.test(f))
      .filter((f) => NEVER_RENDERED.some((n) => readFileSync(join(src, f), 'utf8').includes(`/${n.split('/').pop()!.replace(/\.tsx$/, '')}'`)))
      .map((f) => relative(src, join(src, f)));
    expect(importers).toEqual([]);
  });

  it('flags a glyph in JSX text and in a JSX-child string, and passes it under aria-hidden or Glyph', () => {
    const code = `
      export const A = () => <p>◇ test</p>;
      export const B = ({ ok }: { ok: boolean }) => <b>{ok ? '✓ Copied' : 'Copy'}</b>;
      export const C = () => <p><span aria-hidden="true">◇ </span>test</p>;
      export const D = () => <p><Glyph>◇ </Glyph>test</p>;
      export const E = () => <p>№ 01 · ×3 · −1</p>;
      export const F = () => <p title="◇">{fmt('◇')}</p>;
    `;
    expect(uncovered('x.tsx', code).map((s) => `${s.line} ${s.glyphs}`)).toEqual(['2 ◇', '3 ✓']);
  });
});
