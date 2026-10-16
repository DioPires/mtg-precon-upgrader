// DEC-1190: glyphs and screen readers.
//
// `Glyph` holds a glyph that only decorates: it still shows, and a screen
// reader skips it. Put a space that sits next to the glyph inside `Glyph`.
// Chromium keeps a space left outside a hidden span, so
// `Copied <Glyph>◆</Glyph>` reads "Copied " with a trailing space.
//
// `GlyphWords` holds a glyph that carries meaning: the glyph shows, and a
// screen reader hears `words` in its place. A space at either end of `words`
// becomes a no-break space: the words sit in their own box (`gv1-sr-only`), and
// Chromium drops a plain space at the edge of a box. A plain space in a text
// node of its own right after the words is dropped too, so keep a space that
// shows after the glyph in the same text node as the text that follows it.
//
// `GlyphText` renders a string that comes from data (a `.ts` module). Each
// glyph that `words` names shows, and a screen reader hears its words. The
// string itself does not change.

import { Fragment, type ReactNode } from 'react';

export function Glyph({ children }: { children: ReactNode }) {
  return <span aria-hidden="true">{children}</span>;
}

export function GlyphWords({ children, words }: { children: ReactNode; words: string }) {
  return (
    <>
      <Glyph>{children}</Glyph>
      <span className="gv1-sr-only">{words.replace(/^ | $/g, '\u00a0')}</span>
    </>
  );
}

export function GlyphText({ text, words }: { text: string; words: Readonly<Record<string, string>> }) {
  const glyphs = Object.keys(words);
  if (!glyphs.some((g) => text.includes(g))) return <>{text}</>;
  const parts = text.split(new RegExp(`(${glyphs.map((g) => g.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'u'));
  return (
    <>
      {parts.map((part, i) =>
        i % 2 === 1 ? (
          <GlyphWords key={i} words={words[part]}>
            {part}
          </GlyphWords>
        ) : (
          <Fragment key={i}>{part}</Fragment>
        ),
      )}
    </>
  );
}
