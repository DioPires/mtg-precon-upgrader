// DEC-1127: normalize.ts reads `title` for each win-condition and combo card.
// An item without one shows no heading in the deck guide. slivers and
// stampede-acres held `name` there, and witherbloom-the-balancer held nothing.

import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '..', '..', '..', '..'); // web/src/__tests__/data → repo root
const readJson = <T>(rel: string): T => JSON.parse(readFileSync(resolve(repoRoot, rel), 'utf-8')) as T;

type TitledItem = { title?: unknown };
type DeckItems = { winConditions?: TitledItem[]; synergies?: TitledItem[] };

describe('deck guide titles', () => {
  it('gives every win condition and every synergy a title', () => {
    const { commanders } = readJson<{ commanders: Array<{ id: string }> }>('data/index.json');
    const untitled = commanders.flatMap(({ id }) => {
      const deck = readJson<DeckItems>(`data/commanders/${id}/deck.json`);
      return (['winConditions', 'synergies'] as const).flatMap((field) =>
        (deck[field] || []).flatMap((item, i) =>
          typeof item.title === 'string' && item.title !== '' ? [] : [`${id}: ${field}[${i}]`],
        ),
      );
    });

    expect(commanders.length).toBeGreaterThan(0);
    expect(untitled).toEqual([]);
  });
});
