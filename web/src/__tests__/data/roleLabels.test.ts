// DEC-1074: a role key without a display name shows raw in the role chart,
// Function mix, the decklist's group names and Card Atlas. hidden-legion's
// chart showed `mana-fixing` until the map held it.

import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { ROLE_LABEL } from '../../data/roleLabels';
import type { RawDeck } from '../../data/types';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '..', '..', '..', '..'); // web/src/__tests__/data → repo root
const readJson = <T>(rel: string): T => JSON.parse(readFileSync(resolve(repoRoot, rel), 'utf-8')) as T;

describe('ROLE_LABEL', () => {
  it('names the primary role of every card in every deck', () => {
    const { commanders } = readJson<{ commanders: Array<{ id: string }> }>('data/index.json');
    const unnamed = commanders.flatMap(({ id }) =>
      (readJson<RawDeck>(`data/commanders/${id}/deck.json`).decklist || [])
        .filter((c) => !ROLE_LABEL[c.primary_role || 'other'])
        .map((c) => `${id}: ${c.name} (${c.primary_role})`),
    );

    expect(commanders.length).toBeGreaterThan(0);
    expect(unnamed).toEqual([]);
  });
});
