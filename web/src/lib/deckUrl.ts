// Deck-URL input — DEC-516 (DEC-476 Phase 4, IN-2).
//
// Accept a Moxfield or Archidekt deck URL and resolve it to a decklist, with the
// commander(s) propagated (IN-4). The Grimoire is a static, backendless app, so
// resolution is a direct client-side fetch of the host's public deck API. Both
// hosts currently gate cross-origin browser access (Archidekt pins its CORS origin;
// Moxfield returns 403 to non-browser agents), so a direct fetch may be blocked in
// production — `resolveDeckUrl` degrades with an actionable message ("paste the list
// instead") rather than failing opaquely. The URL parser and the response mappers
// are pure and unit-tested; only the fetch is environment-dependent.

export type DeckSite = 'moxfield' | 'archidekt';

export interface DeckRef {
  site: DeckSite;
  id: string;
  /** Public deck-API endpoint for this ref. */
  apiUrl: string;
}

export interface ResolvedDeckList {
  site: DeckSite;
  /** Display name of the source deck, when the API provides it. */
  name: string;
  cardNames: string[];
  commanderNames: string[];
  /** Rows the mapper could not read a name from (parity with matcher IN-6). */
  unresolved: string[];
}

/** Thrown when resolution fails; `.reason` distinguishes the degradation path. */
export class DeckUrlError extends Error {
  reason: 'unrecognized' | 'network' | 'not-found' | 'empty' | 'shape';
  constructor(reason: DeckUrlError['reason'], message: string) {
    super(message);
    this.name = 'DeckUrlError';
    this.reason = reason;
  }
}

const MOXFIELD_RE = /moxfield\.com\/decks\/([A-Za-z0-9_-]+)/i;
const ARCHIDEKT_RE = /archidekt\.com\/(?:decks|api\/decks)\/(\d+)/i;

/** Recognize a Moxfield/Archidekt deck URL (or a bare id is NOT accepted — a URL
 * is required so the host is unambiguous). Returns null when unrecognized. */
export function parseDeckUrl(input: string): DeckRef | null {
  const s = input.trim();
  if (!s) return null;
  const mox = s.match(MOXFIELD_RE);
  if (mox) {
    const id = mox[1];
    // v3 public deck endpoint (all boards).
    return { site: 'moxfield', id, apiUrl: `https://api2.moxfield.com/v3/decks/all/${id}` };
  }
  const arch = s.match(ARCHIDEKT_RE);
  if (arch) {
    const id = arch[1];
    return { site: 'archidekt', id, apiUrl: `https://archidekt.com/api/decks/${id}/` };
  }
  return null;
}

// ─── Pure response mappers ─────────────────────────────────────────────────────────

/** Map a Moxfield v3 (or legacy v2) deck payload to a decklist. Defensive across
 * both board shapes; commanders come from the commander board (IN-4). */
export function mapMoxfield(json: unknown): ResolvedDeckList {
  const doc = (json ?? {}) as Record<string, unknown>;
  const name = typeof doc.name === 'string' ? doc.name : 'Moxfield deck';
  const cardNames: string[] = [];
  const commanderNames: string[] = [];
  const unresolved: string[] = [];

  const boards = doc.boards as Record<string, unknown> | undefined;
  const collectFrom = (board: unknown, into: string[]): void => {
    // v3: board = { cards: { <id>: { card: { name } } } }; v2: board = { <name>: { card:{name} } }.
    const cards =
      board && typeof board === 'object' && 'cards' in (board as object)
        ? (board as { cards: unknown }).cards
        : board;
    if (!cards || typeof cards !== 'object') return;
    for (const entry of Object.values(cards as Record<string, unknown>)) {
      const nm = pickCardName(entry);
      if (nm) into.push(nm);
      else unresolved.push('(unreadable Moxfield row)');
    }
  };

  if (boards) {
    collectFrom(boards.mainboard, cardNames);
    collectFrom(boards.commanders, commanderNames);
  } else {
    collectFrom(doc.mainboard, cardNames);
    collectFrom(doc.commanders, commanderNames);
  }
  return { site: 'moxfield', name, cardNames, commanderNames, unresolved };
}

/** Map an Archidekt deck payload to a decklist. Commanders are the cards whose
 * category set includes "Commander" (IN-4). */
export function mapArchidekt(json: unknown): ResolvedDeckList {
  const doc = (json ?? {}) as Record<string, unknown>;
  const name = typeof doc.name === 'string' ? doc.name : 'Archidekt deck';
  const cardNames: string[] = [];
  const commanderNames: string[] = [];
  const unresolved: string[] = [];

  const cards = Array.isArray(doc.cards) ? doc.cards : [];
  for (const entry of cards) {
    const rec = (entry ?? {}) as Record<string, unknown>;
    const nm = pickArchidektName(rec);
    if (!nm) {
      unresolved.push('(unreadable Archidekt row)');
      continue;
    }
    const cats = Array.isArray(rec.categories) ? (rec.categories as unknown[]).map(String) : [];
    // Archidekt marks maybeboard/sideboard rows; skip anything not in the deck.
    if (cats.some((c) => /maybeboard|sideboard/i.test(c))) continue;
    if (cats.some((c) => /^commander$/i.test(c))) commanderNames.push(nm);
    else cardNames.push(nm);
  }
  return { site: 'archidekt', name, cardNames, commanderNames, unresolved };
}

function pickCardName(entry: unknown): string | null {
  const rec = (entry ?? {}) as Record<string, unknown>;
  const card = (rec.card ?? {}) as Record<string, unknown>;
  const nm = card.name ?? rec.name;
  return typeof nm === 'string' && nm.trim() ? nm.trim() : null;
}

function pickArchidektName(rec: Record<string, unknown>): string | null {
  const card = (rec.card ?? {}) as Record<string, unknown>;
  const oracle = (card.oracleCard ?? {}) as Record<string, unknown>;
  const nm = oracle.name ?? card.name ?? rec.name;
  return typeof nm === 'string' && nm.trim() ? nm.trim() : null;
}

// ─── Fetch + resolve ────────────────────────────────────────────────────────────

/** Resolve a deck URL to a decklist. Throws DeckUrlError with an actionable message
 * on any failure so the UI can steer the user to the paste path. */
export async function resolveDeckUrl(
  input: string,
  fetchImpl: typeof fetch = fetch,
): Promise<ResolvedDeckList> {
  const ref = parseDeckUrl(input);
  if (!ref) {
    throw new DeckUrlError(
      'unrecognized',
      'Not a recognized Moxfield or Archidekt deck URL.',
    );
  }
  let resp: Response;
  try {
    resp = await fetchImpl(ref.apiUrl, { headers: { Accept: 'application/json' } });
  } catch {
    throw new DeckUrlError(
      'network',
      `Could not reach ${ref.site}. Deck hosts often block in-browser access — ` +
        'open the deck, export the list, and paste it below.',
    );
  }
  if (resp.status === 404) {
    throw new DeckUrlError('not-found', `${ref.site} deck ${ref.id} was not found.`);
  }
  if (!resp.ok) {
    throw new DeckUrlError(
      'network',
      `${ref.site} returned HTTP ${resp.status}. If this deck is private or the host ` +
        'blocks browser access, export the list and paste it below.',
    );
  }
  let json: unknown;
  try {
    json = await resp.json();
  } catch {
    throw new DeckUrlError('shape', `${ref.site} returned an unreadable response.`);
  }
  const result = ref.site === 'moxfield' ? mapMoxfield(json) : mapArchidekt(json);
  if (result.cardNames.length + result.commanderNames.length === 0) {
    throw new DeckUrlError(
      'empty',
      `No cards could be read from that ${ref.site} deck. Export the list and paste it below.`,
    );
  }
  return result;
}

/** Flatten a resolved deck to the paste-mode text the matcher already parses,
 * tagging commanders so IN-4 propagation survives the round-trip. */
export function resolvedToPasteText(deck: ResolvedDeckList): {
  decklist: string;
  commanders: string;
} {
  return {
    decklist: deck.cardNames.join('\n'),
    commanders: deck.commanderNames.join('\n'),
  };
}
