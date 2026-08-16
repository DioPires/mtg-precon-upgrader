// DEC-516 (DEC-476 Phase 4, IN-2) — deck-URL parsing + response mappers.
// The fetch path is environment-dependent (host CORS); these tests lock the pure
// URL parser and the Moxfield/Archidekt → decklist mappers, plus the degradation
// contract via an injected fetch.

import { describe, it, expect, vi } from 'vitest';
import {
  parseDeckUrl,
  mapMoxfield,
  mapArchidekt,
  resolveDeckUrl,
  resolvedToPasteText,
  DeckUrlError,
} from './deckUrl';

describe('parseDeckUrl', () => {
  it('recognizes Moxfield deck URLs', () => {
    const ref = parseDeckUrl('https://www.moxfield.com/decks/AbC-123_x/some-slug');
    expect(ref?.site).toBe('moxfield');
    expect(ref?.id).toBe('AbC-123_x');
    expect(ref?.apiUrl).toContain('api2.moxfield.com/v3/decks/all/AbC-123_x');
  });

  it('recognizes Archidekt deck URLs and API URLs', () => {
    expect(parseDeckUrl('https://archidekt.com/decks/1234567/my_deck')?.id).toBe('1234567');
    expect(parseDeckUrl('archidekt.com/api/decks/999/')?.site).toBe('archidekt');
  });

  it('rejects unrelated or bare input', () => {
    expect(parseDeckUrl('https://example.com/decks/1')).toBeNull();
    expect(parseDeckUrl('Sol Ring')).toBeNull();
    expect(parseDeckUrl('')).toBeNull();
  });
});

describe('mapMoxfield', () => {
  it('maps the v3 board shape with commanders (IN-4)', () => {
    const json = {
      name: 'Meren Value',
      boards: {
        mainboard: {
          cards: {
            a: { card: { name: 'Blood Artist' }, quantity: 1 },
            b: { card: { name: 'Grave Pact' }, quantity: 1 },
          },
        },
        commanders: { cards: { c: { card: { name: 'Meren of Clan Nel Toth' } } } },
      },
    };
    const out = mapMoxfield(json);
    expect(out.name).toBe('Meren Value');
    expect(out.cardNames).toEqual(['Blood Artist', 'Grave Pact']);
    expect(out.commanderNames).toEqual(['Meren of Clan Nel Toth']);
  });

  it('maps the legacy v2 board shape', () => {
    const json = {
      mainboard: { 'Sol Ring': { card: { name: 'Sol Ring' } } },
      commanders: { Meren: { card: { name: 'Meren of Clan Nel Toth' } } },
    };
    const out = mapMoxfield(json);
    expect(out.cardNames).toEqual(['Sol Ring']);
    expect(out.commanderNames).toEqual(['Meren of Clan Nel Toth']);
  });
});

describe('mapArchidekt', () => {
  it('splits commanders by category and skips maybeboard/sideboard', () => {
    const json = {
      name: 'Aristocrats',
      cards: [
        { card: { oracleCard: { name: 'Blood Artist' } }, categories: [] },
        { card: { oracleCard: { name: 'Meren of Clan Nel Toth' } }, categories: ['Commander'] },
        { card: { oracleCard: { name: 'Demonic Tutor' } }, categories: ['Maybeboard'] },
      ],
    };
    const out = mapArchidekt(json);
    expect(out.cardNames).toEqual(['Blood Artist']);
    expect(out.commanderNames).toEqual(['Meren of Clan Nel Toth']);
  });
});

describe('resolveDeckUrl', () => {
  it('resolves via an injected fetch', async () => {
    const fake = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        name: 'X',
        cards: [{ card: { oracleCard: { name: 'Sol Ring' } }, categories: [] }],
      }),
    })) as unknown as typeof fetch;
    const out = await resolveDeckUrl('https://archidekt.com/decks/1/', fake);
    expect(out.cardNames).toEqual(['Sol Ring']);
  });

  it('degrades with an actionable message on a blocked/failed fetch', async () => {
    const fake = vi.fn(async () => {
      throw new TypeError('Failed to fetch');
    }) as unknown as typeof fetch;
    await expect(resolveDeckUrl('https://www.moxfield.com/decks/abc', fake)).rejects.toMatchObject({
      reason: 'network',
    });
  });

  it('rejects an unrecognized URL', async () => {
    await expect(resolveDeckUrl('https://example.com/x')).rejects.toBeInstanceOf(DeckUrlError);
  });

  it('flattens to paste text preserving commander tags', () => {
    const text = resolvedToPasteText({
      site: 'archidekt',
      name: 'X',
      cardNames: ['Sol Ring', 'Grave Pact'],
      commanderNames: ['Meren of Clan Nel Toth'],
      unresolved: [],
    });
    expect(text.decklist).toBe('Sol Ring\nGrave Pact');
    expect(text.commanders).toBe('Meren of Clan Nel Toth');
  });
});
