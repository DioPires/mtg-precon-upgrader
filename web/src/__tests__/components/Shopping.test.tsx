import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import {
  Shopping,
  aggregateCards,
  parseCsvRows,
  parseOwnedFile,
  splitOwnership,
} from '../../components/organisms/Shopping';
import { cardCache } from '../../data/cardCache';
import { deckLoader } from '../../data/loader';
import { COLLECTION_URL } from '../../data/scryfallLimiter';
import type { DeckFull, DeckListGroup, RawCardMetadata } from '../../data/types';
import { formatPricesDate } from '../../lib/pricesDate';
import { identifiersOf } from '../data/scryfallFakes';

function makeDeck(over: Partial<DeckFull>): DeckFull {
  return {
    idx: 1,
    slug: 'alpha',
    deckName: 'Alpha',
    commander: 'Alpha Commander',
    commanderMv: '—',
    type: 'Commander · Theme',
    colors: '🔴',
    bracket: '4',
    status: 'physical',
    pt: '—',
    winTurn: '—',
    winRate: null,
    flavor: '',
    oracle: [],
    strategy: '',
    wincons: [],
    engine: [],
    combos: [],
    apothecary: null,
    curve: [],
    func: [],
    sources: [],
    list: [],
    health: { score: 70, grade: 'B' },
    assessment: null,
    composition: { totalCards: 100, lands: 36, avgCmc: 2.8 },
    sim: null,
    rawDecklist: [],
    physicalDecklist: [],
    synergies: [],
    gameChangers: 0,
    tokens: [],
    ...over,
  };
}

function group(name: string, names: string[], type = 'Creature'): DeckListGroup {
  return {
    name,
    cards: names.map((n) => ({ n, mv: '—', type, price: '—', gc: false })),
  };
}

const ALPHA: DeckFull = makeDeck({
  slug: 'alpha',
  deckName: 'Alpha',
  commander: 'Alpha Commander',
  list: [
    group('Commander', ['Alpha Commander']),
    group('Ramp (3)', ['Sol Ring', 'Arcane Signet', 'Forest']),
    group('Removal (1)', ['Swords to Plowshares']),
  ],
});

const BETA: DeckFull = makeDeck({
  idx: 2,
  slug: 'beta',
  deckName: 'Beta',
  commander: 'Beta Commander',
  colors: '🔵',
  list: [
    group('Commander', ['Beta Commander']),
    group('Ramp (1)', ['Sol Ring', 'Island']),
    group('Draw (1)', ['Rhystic Study']),
  ],
});

describe('parseCsvRows', () => {
  it('parses basic CSV', () => {
    expect(parseCsvRows('a,b,c\n1,2,3')).toEqual([
      ['a', 'b', 'c'],
      ['1', '2', '3'],
    ]);
  });

  it('respects quoted fields with commas inside', () => {
    expect(parseCsvRows('Name,Quantity\n"Smith, John",2')).toEqual([
      ['Name', 'Quantity'],
      ['Smith, John', '2'],
    ]);
  });
});

describe('parseOwnedFile', () => {
  it('reads the CSV path with Name,Quantity headers', () => {
    const map = parseOwnedFile('Name,Quantity\nSol Ring,1\nRhystic Study,1\n');
    expect(map.get('Sol Ring')).toBe(1);
    expect(map.get('Rhystic Study')).toBe(1);
    expect(map.size).toBe(2);
  });

  it('reads the text path with `1x Card` lines', () => {
    const map = parseOwnedFile('1x Sol Ring\n2x Forest\nIsland\n');
    expect(map.get('Sol Ring')).toBe(1);
    expect(map.get('Forest')).toBe(2);
    expect(map.get('Island')).toBe(1);
  });

  it('sums duplicates', () => {
    const map = parseOwnedFile('Name,Quantity\nSol Ring,1\nSol Ring,2\n');
    expect(map.get('Sol Ring')).toBe(3);
  });

  it('keys DFC owned entries by front face (DEC-178)', () => {
    const map = parseOwnedFile('Name,Quantity\nBrazen Borrower // Petty Theft,1\n');
    expect(map.get('Brazen Borrower')).toBe(1);
    expect(map.has('Brazen Borrower // Petty Theft')).toBe(false);
  });

  it('counts a CSV quantity below 1 as 1 and keeps a quantity of 1 or more (DEC-1141)', () => {
    expect(parseOwnedFile('Name,Quantity\nSol Ring,-1\n').get('Sol Ring')).toBe(1);
    expect(parseOwnedFile('Name,Quantity\nSol Ring,0\n').get('Sol Ring')).toBe(1);
    expect(parseOwnedFile('Name,Quantity\nSol Ring,3\n').get('Sol Ring')).toBe(3);
    expect(parseOwnedFile('Name,Quantity\nSol Ring,2.5\n').get('Sol Ring')).toBe(2);
  });

  // 400 digits read as Infinity, which is not a whole number (DEC-1150 N2).
  it('counts a CSV quantity cell of 400 digits as 1 (DEC-1150)', () => {
    expect(parseOwnedFile(`Name,Quantity\nSol Ring,${'1'.repeat(400)}\n`).get('Sol Ring')).toBe(1);
  });

  it('counts a text line count of 400 digits as 1 (DEC-1150)', () => {
    expect(parseOwnedFile(`${'1'.repeat(400)}x Sol Ring\n`).get('Sol Ring')).toBe(1);
  });
});

describe('aggregateCards', () => {
  it('skips basic lands and the Commander group', () => {
    const map = aggregateCards(new Set(['alpha']), [ALPHA, BETA]);
    expect(map.has('Forest')).toBe(false);
    // Commander still added (via deck.commander, isCommander=true)
    expect(map.get('Alpha Commander')?.isCommander).toBe(true);
    // Cards from non-Commander groups are present
    expect(map.has('Sol Ring')).toBe(true);
    expect(map.has('Swords to Plowshares')).toBe(true);
  });

  it('dedupes shared cards across decks and tracks deck attribution', () => {
    const map = aggregateCards(new Set(['alpha', 'beta']), [ALPHA, BETA]);
    const sol = map.get('Sol Ring');
    expect(sol).toBeTruthy();
    expect(sol!.decks.has('alpha')).toBe(true);
    expect(sol!.decks.has('beta')).toBe(true);
  });

  it('respects multi-copy non-basic tiles via tile.qty (DEC-177)', () => {
    const RATS: DeckFull = makeDeck({
      slug: 'rats',
      deckName: 'Rats',
      commander: 'Marrow-Gnawer',
      list: [
        group('Commander', ['Marrow-Gnawer']),
        {
          name: 'Threats (4)',
          cards: [{ n: 'Relentless Rats', mv: '{1}{B}{B}', type: 'Creature', price: '—', gc: false, qty: 4 }],
        },
      ],
    });
    const map = aggregateCards(new Set(['rats']), [RATS]);
    expect(map.get('Relentless Rats')?.qty).toBe(4);
  });

  it('sums qty across decks for shared entries (DEC-209)', () => {
    // Two decks each needing 1 Demonic Tutor → planned qty = 2.
    const A: DeckFull = makeDeck({
      slug: 'a', deckName: 'A', commander: 'A Cmd',
      list: [
        group('Commander', ['A Cmd']),
        { name: 'Tutors', cards: [{ n: 'Demonic Tutor', mv: '{1}{B}', type: 'Sorcery', price: '—', gc: false }] },
      ],
    });
    const B: DeckFull = makeDeck({
      slug: 'b', deckName: 'B', commander: 'B Cmd',
      list: [
        group('Commander', ['B Cmd']),
        { name: 'Tutors', cards: [{ n: 'Demonic Tutor', mv: '{1}{B}', type: 'Sorcery', price: '—', gc: false }] },
      ],
    });
    const map = aggregateCards(new Set(['a', 'b']), [A, B]);
    expect(map.get('Demonic Tutor')?.qty).toBe(2);
  });

  it('does not double-count commander/partner in partner decks (DEC-211)', () => {
    // normalize.ts names the commander group `'Commanders'` (plural) when a
    // partner is present. aggregateCards adds the commander + partner
    // explicitly; the group iteration must skip both names so qty stays at 1.
    const PARTNER_DECK: DeckFull = makeDeck({
      slug: 'partners',
      deckName: 'Partner Deck',
      commander: 'Leonardo, the Balance',
      partner: 'Donatello, the Brains',
      list: [
        group('Commanders', ['Leonardo, the Balance', 'Donatello, the Brains']),
        group('Ramp', ['Sol Ring']),
      ],
    });
    const map = aggregateCards(new Set(['partners']), [PARTNER_DECK]);
    expect(map.get('Leonardo, the Balance')?.qty).toBe(1);
    expect(map.get('Donatello, the Brains')?.qty).toBe(1);
  });

  it('sums multi-copy qty across decks (DEC-209, generalizes DEC-177)', () => {
    // Two decks running Relentless Rats x2 and x4 → planned qty = 6.
    const A: DeckFull = makeDeck({
      slug: 'a', deckName: 'A', commander: 'A Cmd',
      list: [
        group('Commander', ['A Cmd']),
        { name: 'Threats', cards: [{ n: 'Relentless Rats', mv: '—', type: 'Creature', price: '—', gc: false, qty: 2 }] },
      ],
    });
    const B: DeckFull = makeDeck({
      slug: 'b', deckName: 'B', commander: 'B Cmd',
      list: [
        group('Commander', ['B Cmd']),
        { name: 'Threats', cards: [{ n: 'Relentless Rats', mv: '—', type: 'Creature', price: '—', gc: false, qty: 4 }] },
      ],
    });
    const map = aggregateCards(new Set(['a', 'b']), [A, B]);
    expect(map.get('Relentless Rats')?.qty).toBe(6);
  });
});

describe('splitOwnership', () => {
  it('routes cards to buy or own based on owned quantity', () => {
    const cardMap = aggregateCards(new Set(['alpha']), [ALPHA, BETA]);
    const owned = new Map<string, number>([['Sol Ring', 1]]);
    const { buy, own } = splitOwnership(cardMap, owned);
    expect(buy.find((c) => c.name === 'Sol Ring')).toBeUndefined();
    expect(own.find((c) => c.name === 'Sol Ring')?.qty).toBe(1);
    expect(buy.find((c) => c.name === 'Swords to Plowshares')).toBeTruthy();
  });

  it('surfaces a buy quantity when two selected decks share a card the user only owns once (DEC-209)', () => {
    // Repro for DEC-209: two decks each need 1 Demonic Tutor, user owns 1 →
    // buy list should show qty 1, own list should show qty 1.
    const A = makeDeck({
      slug: 'eternal-agony', deckName: 'Eternal Agony', commander: 'EA Cmd',
      list: [
        group('Commander', ['EA Cmd']),
        { name: 'Tutors', cards: [{ n: 'Demonic Tutor', mv: '{1}{B}', type: 'Sorcery', price: '—', gc: false }] },
      ],
    });
    const B = makeDeck({
      slug: 'gathering-shadow', deckName: 'Gathering Shadow', commander: 'DD Cmd',
      list: [
        group('Commander', ['DD Cmd']),
        { name: 'Tutors', cards: [{ n: 'Demonic Tutor', mv: '{1}{B}', type: 'Sorcery', price: '—', gc: false }] },
      ],
    });
    const cardMap = aggregateCards(new Set(['eternal-agony', 'gathering-shadow']), [A, B]);
    const owned = new Map<string, number>([['Demonic Tutor', 1]]);
    const { buy, own } = splitOwnership(cardMap, owned);
    expect(buy.find((c) => c.name === 'Demonic Tutor')?.qty).toBe(1);
    expect(own.find((c) => c.name === 'Demonic Tutor')?.qty).toBe(1);
  });

  it('routes owned commander + partner to own (not buy) for partner decks (DEC-211)', () => {
    const PARTNER_DECK: DeckFull = makeDeck({
      slug: 'partners',
      deckName: 'Partner Deck',
      commander: 'Leonardo, the Balance',
      partner: 'Donatello, the Brains',
      list: [
        group('Commanders', ['Leonardo, the Balance', 'Donatello, the Brains']),
        group('Ramp', ['Sol Ring']),
      ],
    });
    const cardMap = aggregateCards(new Set(['partners']), [PARTNER_DECK]);
    const owned = new Map<string, number>([
      ['Leonardo, the Balance', 1],
      ['Donatello, the Brains', 1],
    ]);
    const { buy, own } = splitOwnership(cardMap, owned);
    expect(buy.find((c) => c.name === 'Leonardo, the Balance')).toBeUndefined();
    expect(buy.find((c) => c.name === 'Donatello, the Brains')).toBeUndefined();
    expect(own.find((c) => c.name === 'Leonardo, the Balance')?.qty).toBe(1);
    expect(own.find((c) => c.name === 'Donatello, the Brains')?.qty).toBe(1);
  });

  it('reconciles DFC deck entries against front-face owned names and shows the full DFC name (DEC-178)', () => {
    const DFC = makeDeck({
      slug: 'dfc',
      deckName: 'DFC Deck',
      commander: 'DFC Commander',
      list: [
        group('Commander', ['DFC Commander']),
        group('Threats', ['Sephiroth, Fabled SOLDIER // Final Heaven']),
      ],
    });
    const cardMap = aggregateCards(new Set(['dfc']), [DFC]);
    const owned = new Map<string, number>([['Sephiroth, Fabled SOLDIER', 1]]);
    const { buy, own } = splitOwnership(cardMap, owned);
    expect(buy.find((c) => c.name.startsWith('Sephiroth'))).toBeUndefined();
    const ownedRow = own.find((c) => c.name.startsWith('Sephiroth'));
    expect(ownedRow?.name).toBe('Sephiroth, Fabled SOLDIER // Final Heaven');
    expect(ownedRow?.qty).toBe(1);
  });
});

const STORAGE_KEY = 'grimoire-owned-cards';

describe('Shopping organism', () => {
  beforeEach(() => {
    localStorage.removeItem(STORAGE_KEY);
  });
  afterEach(() => {
    localStorage.removeItem(STORAGE_KEY);
  });

  function renderShopping(decks: DeckFull[]) {
    return render(<Shopping decks={decks} />);
  }

  // The import message's two regions, in the section of the import button.
  // The stop line of the summary is a status region too (DEC-1154).
  const importSection = () => screen.getByRole('button', { name: 'Import owned cards' }).closest('section')!;
  const importStatus = () => within(importSection()).getByRole('status');
  const importAlert = () => within(importSection()).getByRole('alert');

  it('preselects the first deck and renders its non-basic non-commander cards in the buy list', () => {
    renderShopping([ALPHA, BETA]);
    expect(screen.getByRole('heading', { name: /Shopping List/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Need to buy/i })).toBeInTheDocument();
    // Sol Ring + Arcane Signet + Swords to Plowshares from alpha (Forest excluded as basic)
    expect(screen.getByText('Sol Ring')).toBeInTheDocument();
    expect(screen.getByText('Arcane Signet')).toBeInTheDocument();
    expect(screen.getByText('Swords to Plowshares')).toBeInTheDocument();
    expect(screen.queryByText('Forest')).not.toBeInTheDocument();
  });

  it('toggles a deck chip selection via aria-pressed', () => {
    renderShopping([ALPHA, BETA]);
    const betaChip = screen.getByRole('button', { name: /Add Beta/i });
    expect(betaChip).toHaveAttribute('aria-pressed', 'false');
    fireEvent.click(betaChip);
    expect(screen.getByRole('button', { name: /Remove Beta/i })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText('Rhystic Study')).toBeInTheDocument();
  });

  it('selects all decks with the Select all action', () => {
    renderShopping([ALPHA, BETA]);
    fireEvent.click(screen.getByRole('button', { name: /Select all/i }));
    expect(screen.getByRole('button', { name: /Remove Alpha/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Remove Beta/i })).toBeInTheDocument();
  });

  it('Clear empties the selection and does not re-select the first deck (DEC-172)', () => {
    renderShopping([ALPHA, BETA]);
    // First deck is preselected on mount.
    expect(screen.getByRole('button', { name: /Remove Alpha/i })).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(screen.getByRole('button', { name: /^Clear$/i }));
    // After clear, no deck chip should be aria-pressed.
    expect(screen.getByRole('button', { name: /Add Alpha/i })).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByRole('button', { name: /Add Beta/i })).toHaveAttribute('aria-pressed', 'false');
    // Counter reads "0 of 2".
    expect(screen.getByText(/· 0 of 2/)).toBeInTheDocument();
  });

  it('excludes brewing decks from the picker by default but includes them via the toggle (DEC-338)', () => {
    const BREW: DeckFull = makeDeck({
      idx: 3,
      slug: 'hivebound',
      deckName: 'Hivebound Cascade',
      commander: 'Sliver Commander',
      colors: '🟢',
      status: 'brewing',
      list: [
        group('Commander', ['Sliver Commander']),
        group('Threats (1)', ['Sliver Hivelord']),
      ],
    });
    renderShopping([ALPHA, BREW]);
    // Default: brewing deck absent from the picker, production deck present.
    expect(screen.queryByRole('button', { name: /Add Hivebound Cascade/i })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Remove Alpha/i })).toBeInTheDocument();

    // Opt brewing in.
    const toggle = screen.getByRole('button', { name: /Include brewing/i });
    expect(toggle).toHaveAttribute('aria-pressed', 'false');
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-pressed', 'true');

    // Select the brewing deck and confirm its buy-list renders.
    fireEvent.click(screen.getByRole('button', { name: /Add Hivebound Cascade/i }));
    expect(screen.getByText('Sliver Hivelord')).toBeInTheDocument();
  });

  it('keeps brewing decks out of the Built rail even when opted into the picker (DEC-336 follow-up)', () => {
    const BREW: DeckFull = makeDeck({
      idx: 3,
      slug: 'hivebound',
      deckName: 'Hivebound Cascade',
      commander: 'Sliver Commander',
      status: 'brewing',
      list: [
        group('Commander', ['Sliver Commander']),
        group('Threats (1)', ['Sliver Hivelord']),
      ],
    });
    renderShopping([ALPHA, BREW]);
    // Production deck is markable as built; brewing deck never is.
    expect(screen.getByRole('button', { name: /Mark Alpha as built/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Mark Hivebound Cascade as built/i })).not.toBeInTheDocument();

    // Opt brewing into the picker — it shows in Select decks but still NOT in the Built rail.
    fireEvent.click(screen.getByRole('button', { name: /Include brewing/i }));
    expect(screen.getByRole('button', { name: /Add Hivebound Cascade/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Mark Hivebound Cascade as built/i })).not.toBeInTheDocument();
  });

  it('drops brewing decks from the selection when the toggle is turned back off (DEC-338)', () => {
    const BREW: DeckFull = makeDeck({
      idx: 3,
      slug: 'hivebound',
      deckName: 'Hivebound Cascade',
      commander: 'Sliver Commander',
      status: 'brewing',
      list: [
        group('Commander', ['Sliver Commander']),
        group('Threats (1)', ['Sliver Hivelord']),
      ],
    });
    renderShopping([ALPHA, BREW]);
    fireEvent.click(screen.getByRole('button', { name: /Include brewing/i }));
    fireEvent.click(screen.getByRole('button', { name: /Add Hivebound Cascade/i }));
    expect(screen.getByText('Sliver Hivelord')).toBeInTheDocument();
    // Toggle brewing off → brewing card leaves the buy list, counter excludes
    // the pruned brewing deck (only the preselected production deck remains).
    fireEvent.click(screen.getByRole('button', { name: /Include brewing/i }));
    expect(screen.queryByText('Sliver Hivelord')).not.toBeInTheDocument();
    expect(screen.getByText(/· 1 of 1/)).toBeInTheDocument();
  });

  it('hides the Include-brewing toggle when no brewing decks are present (DEC-338)', () => {
    renderShopping([ALPHA, BETA]);
    expect(screen.queryByRole('button', { name: /Include brewing/i })).not.toBeInTheDocument();
  });

  it('persists imported owned cards in localStorage on mount and removes them from the buy list', () => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify([['Sol Ring', 1], ['Swords to Plowshares', 1]]),
    );
    renderShopping([ALPHA, BETA]);
    expect(screen.getByText(/cards loaded — saved locally/i)).toBeInTheDocument();
    // Pre-owned cards should not appear in the Need-to-buy list
    expect(screen.queryByText('Swords to Plowshares')).not.toBeInTheDocument();
  });

  it('puts the import control in the tab order, and a click on it clicks the file input (DEC-1083)', () => {
    const { container } = renderShopping([ALPHA]);
    const button = screen.getByRole('button', { name: 'Import owned cards' });
    expect(button).toHaveAttribute('type', 'button');
    // The class alone gives the button the look the label had (DEC-1088 B1).
    expect(button.className).toBe('gv1-shop-btn');
    expect(button.tabIndex).not.toBe(-1);

    // The input stays out of the tab order and the accessibility tree.
    const input = container.querySelector<HTMLInputElement>('#gv1-shop-owned-file')!;
    expect(input).toHaveAttribute('type', 'file');
    expect(input.tabIndex).toBe(-1);
    expect(input).toHaveAttribute('aria-hidden', 'true');

    const click = vi.spyOn(input, 'click');
    fireEvent.click(button);
    expect(click).toHaveBeenCalledTimes(1);
  });

  it('says that an import adds to the cards loaded, when one file is imported twice (DEC-1094)', async () => {
    const { container } = renderShopping([ALPHA]);
    const input = container.querySelector<HTMLInputElement>('#gv1-shop-owned-file')!;
    // Two lines, three cards. jsdom's File has no text(), so the test gives it one.
    const body = 'Sol Ring\n2x Arcane Signet\n';
    const file = new File([body], 'owned.txt', { type: 'text/plain' });
    Object.defineProperty(file, 'text', { value: () => Promise.resolve(body) });
    const hint = 'To replace the list, use Clear owned first.';

    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => expect(importStatus()).toHaveTextContent(
      `Added 2 unique cards (3 total). 3 cards loaded. ${hint}`,
    ));
    expect(screen.getByText('3 cards loaded — saved locally')).toBeInTheDocument();

    // The same file again: the counts add, and the new total is twice the first.
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => expect(importStatus()).toHaveTextContent(
      `Added 2 unique cards (3 total). 6 cards loaded. ${hint}`,
    ));
    expect(screen.getByText('6 cards loaded — saved locally')).toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')).toEqual([['Sol Ring', 2], ['Arcane Signet', 4]]);
  });

  it('counts the file, not the list, when a second file shares one name with the first (DEC-1117 B1)', async () => {
    const { container } = renderShopping([ALPHA]);
    const input = container.querySelector<HTMLInputElement>('#gv1-shop-owned-file')!;
    // jsdom's File has no text(), so the test gives it one.
    const pick = (body: string) => {
      const file = new File([body], 'owned.txt', { type: 'text/plain' });
      Object.defineProperty(file, 'text', { value: () => Promise.resolve(body) });
      fireEvent.change(input, { target: { files: [file] } });
    };
    const hint = 'To replace the list, use Clear owned first.';

    pick('Sol Ring\n2x Arcane Signet\n');
    await waitFor(() => expect(importStatus()).toHaveTextContent(
      `Added 2 unique cards (3 total). 3 cards loaded. ${hint}`,
    ));

    // Arcane Signet is loaded already; Swords to Plowshares is new. The file
    // holds 2 unique cards; the list then holds 3 unique cards and 5 cards.
    pick('Arcane Signet\nSwords to Plowshares\n');
    await waitFor(() => expect(importStatus()).toHaveTextContent(
      `Added 2 unique cards (2 total). 5 cards loaded. ${hint}`,
    ));
    expect(screen.getByText('5 cards loaded — saved locally')).toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')).toEqual(
      [['Sol Ring', 1], ['Arcane Signet', 3], ['Swords to Plowshares', 1]],
    );
  });

  describe('the singular noun for a count of one (DEC-1123)', () => {
    // jsdom's File has no text(), so the test gives it one.
    const pick = (input: HTMLInputElement, body: string) => {
      const file = new File([body], 'owned.txt', { type: 'text/plain' });
      Object.defineProperty(file, 'text', { value: () => Promise.resolve(body) });
      fireEvent.change(input, { target: { files: [file] } });
    };
    const hint = 'To replace the list, use Clear owned first.';

    it('reads `1 unique card` and `1 card loaded` for a one-line file of one copy', async () => {
      const { container } = renderShopping([ALPHA]);
      const input = container.querySelector<HTMLInputElement>('#gv1-shop-owned-file')!;
      pick(input, 'Sol Ring\n');
      await waitFor(() => expect(importStatus()).toHaveTextContent(
        `Added 1 unique card (1 total). 1 card loaded. ${hint}`,
      ));
      expect(screen.getByText('1 card loaded — saved locally')).toBeInTheDocument();

      // The same file again: the file still holds 1 card, and the list now holds 2.
      pick(input, 'Sol Ring\n');
      await waitFor(() => expect(importStatus()).toHaveTextContent(
        `Added 1 unique card (1 total). 2 cards loaded. ${hint}`,
      ));
      expect(screen.getByText('2 cards loaded — saved locally')).toBeInTheDocument();
    });

    it('reads `1 unique card` and `4 cards loaded` for a one-line file of four copies', async () => {
      const { container } = renderShopping([ALPHA]);
      pick(container.querySelector<HTMLInputElement>('#gv1-shop-owned-file')!, '4x Sol Ring\n');
      // One message holds both forms: the unique count is 1 and the card count is 4.
      await waitFor(() => expect(importStatus()).toHaveTextContent(
        `Added 1 unique card (4 total). 4 cards loaded. ${hint}`,
      ));
      expect(screen.getByText('4 cards loaded — saved locally')).toBeInTheDocument();
    });

    it('reads `1 unique card` for a one-name file when the list already holds another name (DEC-1139 B1)', async () => {
      const { container } = renderShopping([ALPHA]);
      const input = container.querySelector<HTMLInputElement>('#gv1-shop-owned-file')!;
      pick(input, 'Sol Ring\n');
      await waitFor(() => expect(importStatus()).toHaveTextContent(
        `Added 1 unique card (1 total). 1 card loaded. ${hint}`,
      ));

      // The file holds 1 unique card; the list then holds 2 unique cards and 2 cards.
      pick(input, 'Arcane Signet\n');
      await waitFor(() => expect(importStatus()).toHaveTextContent(
        `Added 1 unique card (1 total). 2 cards loaded. ${hint}`,
      ));
      expect(screen.getByText('2 cards loaded — saved locally')).toBeInTheDocument();
    });
  });

  it('keeps the status and the alert region of the import in the page, empty until a message comes (DEC-1154)', async () => {
    const { container } = renderShopping([ALPHA]);
    const input = container.querySelector<HTMLInputElement>('#gv1-shop-owned-file')!;
    // jsdom's File has no text(), so the test gives it one.
    const pick = (body: string) => {
      const file = new File([body], 'owned.txt', { type: 'text/plain' });
      Object.defineProperty(file, 'text', { value: () => Promise.resolve(body) });
      fireEvent.change(input, { target: { files: [file] } });
    };

    // Before any import, both regions are in the page, and both are empty.
    const status = importStatus();
    const alert = importAlert();
    expect(status).toBeEmptyDOMElement();
    expect(alert).toBeEmptyDOMElement();

    // A file of cards: the status region holds the count, and the alert region stays empty.
    pick('Sol Ring\n');
    await waitFor(() => expect(status).toHaveTextContent('Added 1 unique card (1 total). 1 card loaded.'));
    expect(status.textContent).toMatch(/^◆Added /);
    expect(status.firstElementChild).toHaveClass('gv1-shop-import-msg', 'gv1-shop-import-ok');
    expect([...status.firstElementChild!.children].map((el) => el.className)).toEqual(['gv1-mono-xs', 'gv1-mono-xs']);
    expect(alert).toBeEmptyDOMElement();

    // A file with no card: the alert region holds the error, and the status region is empty again.
    pick('\n');
    await waitFor(() => expect(alert).toHaveTextContent('No cards detected in that file.'));
    expect(alert.textContent).toMatch(/^⚠No cards /);
    expect(alert.firstElementChild).toHaveClass('gv1-shop-import-msg', 'gv1-shop-import-err');
    expect([...alert.firstElementChild!.children].map((el) => el.className)).toEqual(['gv1-mono-xs', 'gv1-mono-xs']);
    expect(status).toBeEmptyDOMElement();

    // The regions that hold the messages are the nodes of the first paint.
    expect(importStatus()).toBe(status);
    expect(importAlert()).toBe(alert);
  });

  it('hides the sigil of each import message from screen readers, so each region reads the message alone (DEC-1167)', async () => {
    const { container } = renderShopping([ALPHA]);
    const input = container.querySelector<HTMLInputElement>('#gv1-shop-owned-file')!;
    // jsdom's File has no text(), so the test gives it one.
    const pick = (body: string) => {
      const file = new File([body], 'owned.txt', { type: 'text/plain' });
      Object.defineProperty(file, 'text', { value: () => Promise.resolve(body) });
      fireEvent.change(input, { target: { files: [file] } });
    };
    // The region's text without the elements that aria-hidden takes out of the accessibility tree.
    const spoken = (region: HTMLElement) => {
      const copy = region.cloneNode(true) as HTMLElement;
      copy.querySelectorAll('[aria-hidden="true"]').forEach((el) => el.remove());
      return copy.textContent;
    };

    // A file of cards: the ◆ is hidden, and the status region reads the count alone.
    pick('Sol Ring\n');
    const count = 'Added 1 unique card (1 total). 1 card loaded. To replace the list, use Clear owned first.';
    await waitFor(() => expect(importStatus()).toHaveTextContent(count));
    const [okSigil, okText] = importStatus().firstElementChild!.children;
    expect(okSigil).toHaveAttribute('aria-hidden', 'true');
    expect(okSigil.textContent).toBe('◆');
    expect(okText).not.toHaveAttribute('aria-hidden');
    expect(spoken(importStatus())).toBe(count);

    // A file with no card: the ⚠ is hidden, and the alert region reads the error alone.
    pick('\n');
    await waitFor(() => expect(importAlert()).toHaveTextContent('No cards detected in that file.'));
    const [errSigil, errText] = importAlert().firstElementChild!.children;
    expect(errSigil).toHaveAttribute('aria-hidden', 'true');
    expect(errSigil.textContent).toBe('⚠');
    expect(errText).not.toHaveAttribute('aria-hidden');
    expect(spoken(importAlert())).toBe('No cards detected in that file.');
  });

  describe('an owned quantity is a whole number of 1 or more (DEC-1141)', () => {
    const loadStore = (raw: string) => {
      localStorage.setItem(STORAGE_KEY, raw);
      renderShopping([ALPHA]);
    };

    it('counts a CSV quantity of -1 as 1 in the import message and the owned bar', async () => {
      const { container } = renderShopping([ALPHA]);
      const input = container.querySelector<HTMLInputElement>('#gv1-shop-owned-file')!;
      // jsdom's File has no text(), so the test gives it one.
      const body = 'Name,Quantity\nSol Ring,-1\nArcane Signet,1\n';
      const file = new File([body], 'owned.csv', { type: 'text/csv' });
      Object.defineProperty(file, 'text', { value: () => Promise.resolve(body) });
      fireEvent.change(input, { target: { files: [file] } });
      await waitFor(() => expect(importStatus()).toHaveTextContent(
        'Added 2 unique cards (2 total). 2 cards loaded. To replace the list, use Clear owned first.',
      ));
      expect(screen.getByText('2 cards loaded — saved locally')).toBeInTheDocument();
      expect(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')).toEqual([['Sol Ring', 1], ['Arcane Signet', 1]]);
    });

    it('drops a stored quantity that is not a whole number, and writes nothing back', () => {
      const raw = JSON.stringify([['Sol Ring', 0.5], ['Arcane Signet', 2]]);
      loadStore(raw);
      expect(screen.getByText('2 cards loaded — saved locally')).toBeInTheDocument();
      expect(localStorage.getItem(STORAGE_KEY)).toBe(raw);
    });

    it('drops a stored quantity of 1 or more that is not a whole number', () => {
      loadStore(JSON.stringify([['Sol Ring', 1.5], ['Swords to Plowshares', '2'], ['Arcane Signet', 1]]));
      expect(screen.getByText('1 card loaded — saved locally')).toBeInTheDocument();
    });

    it('drops a stored quantity below 1', () => {
      loadStore(JSON.stringify([['Sol Ring', -1], ['Arcane Signet', 1]]));
      expect(screen.getByText('1 card loaded — saved locally')).toBeInTheDocument();
    });

    it('shows the empty list for a store whose one entry has no quantity', () => {
      const raw = JSON.stringify([['Sol Ring']]);
      loadStore(raw);
      expect(screen.getByText('// .csv (Name,Quantity) or .txt (one card per line)')).toBeInTheDocument();
      expect(screen.queryByText(/loaded —/)).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Clear owned' })).not.toBeInTheDocument();
      expect(localStorage.getItem(STORAGE_KEY)).toBe(raw);
    });

    it('drops a stored entry whose name is not a string', () => {
      loadStore(JSON.stringify([[7, 2], ['Arcane Signet', 1]]));
      expect(screen.getByText('1 card loaded — saved locally')).toBeInTheDocument();
    });

    it('drops a stored entry whose name has no text', () => {
      loadStore(JSON.stringify([['  ', 2], ['Arcane Signet', 1]]));
      expect(screen.getByText('1 card loaded — saved locally')).toBeInTheDocument();
    });

    it('drops a stored entry that is not a two-item array', () => {
      loadStore(JSON.stringify([null, ['Sol Ring', 2, 'foil'], ['Arcane Signet', 1]]));
      expect(screen.getByText('1 card loaded — saved locally')).toBeInTheDocument();
    });

    // Two decks each want Brazen Borrower. The store holds one copy under the
    // double-faced name and one under the front face; the load adds them into
    // one owned card of quantity 2 (DEC-1150).
    it('adds a stored double-faced name and its front face into one card', () => {
      const dfcDeck = (slug: string, idx: number) =>
        makeDeck({
          idx,
          slug,
          deckName: slug,
          commander: `${slug} Commander`,
          list: [group('Commander', [`${slug} Commander`]), group('Tempo (1)', ['Brazen Borrower // Petty Theft'])],
        });
      localStorage.setItem(STORAGE_KEY, JSON.stringify([['Brazen Borrower // Petty Theft', 1], ['Brazen Borrower', 1]]));
      renderShopping([dfcDeck('dfc-a', 1), dfcDeck('dfc-b', 2)]);
      fireEvent.click(screen.getByRole('button', { name: /Select all/i }));
      const ownHead = screen.getByRole('button', { name: /Already own/ });
      expect(within(ownHead).getByText('· 1 unique · 2 cards')).toBeInTheDocument();
    });
  });

  describe('the count of cards in the Need to buy and Already own headers (DEC-1142)', () => {
    // Each deck holds its commander and one other card, Sol Ring. With both decks
    // selected, a header holds 1 unique card and 2 cards, so the noun follows the
    // card count.
    const SOLO_A = makeDeck({
      slug: 'solo-a',
      deckName: 'Solo A',
      commander: 'Solo A Commander',
      list: [group('Commander', ['Solo A Commander']), group('Ramp (1)', ['Sol Ring'])],
    });
    const SOLO_B = makeDeck({
      idx: 2,
      slug: 'solo-b',
      deckName: 'Solo B',
      commander: 'Solo B Commander',
      list: [group('Commander', ['Solo B Commander']), group('Ramp (1)', ['Sol Ring'])],
    });
    const buyHead = () => screen.getByRole('heading', { name: 'Need to buy' }).parentElement!;
    const ownHead = () => screen.getByRole('button', { name: /Already own/ });

    // The user owns both commanders, so Need to buy holds Sol Ring alone.
    const ownCommanders = () =>
      localStorage.setItem(STORAGE_KEY, JSON.stringify([['Solo A Commander', 1], ['Solo B Commander', 1]]));

    it('reads `1 unique · 1 card` to buy for one deck that wants one Sol Ring', () => {
      ownCommanders();
      renderShopping([SOLO_A, SOLO_B]);
      expect(within(buyHead()).getByText('· 1 unique · 1 card')).toBeInTheDocument();
    });

    it('reads `1 unique · 2 cards` to buy for two decks that each want one Sol Ring', () => {
      ownCommanders();
      renderShopping([SOLO_A, SOLO_B]);
      fireEvent.click(screen.getByRole('button', { name: /Select all/i }));
      expect(within(buyHead()).getByText('· 1 unique · 2 cards')).toBeInTheDocument();
    });

    it('reads `1 unique · 1 card` owned for an import of one Sol Ring and a deck that holds it', () => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify([['Sol Ring', 1]]));
      renderShopping([SOLO_A]);
      expect(within(ownHead()).getByText('· 1 unique · 1 card')).toBeInTheDocument();
    });

    it('reads `1 unique · 2 cards` owned for an import of two Sol Rings and two decks that hold it', () => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify([['Sol Ring', 2]]));
      renderShopping([SOLO_A, SOLO_B]);
      fireEvent.click(screen.getByRole('button', { name: /Select all/i }));
      expect(within(ownHead()).getByText('· 1 unique · 2 cards')).toBeInTheDocument();
    });

    // The user owns Solo A Commander alone. With both decks selected, Need to buy holds
    // Solo B Commander and two Sol Rings (2 unique, 3 cards) and Already own holds one
    // card, so each header must read the counts of its own section.
    it('reads `2 unique · 3 cards` to buy and `1 unique · 1 card` owned when the sections hold different counts', () => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify([['Solo A Commander', 1]]));
      renderShopping([SOLO_A, SOLO_B]);
      fireEvent.click(screen.getByRole('button', { name: /Select all/i }));
      expect(within(buyHead()).getByText('· 2 unique · 3 cards')).toBeInTheDocument();
      expect(within(ownHead()).getByText('· 1 unique · 1 card')).toBeInTheDocument();
    });
  });

  it('hides the sigil of each empty state from screen readers, so each state reads its message alone (DEC-1177)', () => {
    // The state's text without the elements that aria-hidden takes out of the accessibility tree.
    const spoken = (el: Element) => {
      const copy = el.cloneNode(true) as Element;
      copy.querySelectorAll('[aria-hidden="true"]').forEach((hidden) => hidden.remove());
      return copy.textContent;
    };
    const expectHiddenSigil = (sigil: string, message: string) => {
      const empty = screen.getByText(message).closest('.gv1-empty')!;
      // The box shows its own sigil alone: the modifier turns its `::before` off (DEC-1199).
      expect(empty).toHaveClass('gv1-empty--own-rune');
      expect(empty.children).toHaveLength(2);
      const [glyph, text] = empty.children;
      expect(glyph).toHaveAttribute('aria-hidden', 'true');
      expect(glyph).toHaveClass('gv1-rune');
      expect(glyph.textContent).toBe(sigil);
      expect(text).not.toHaveAttribute('aria-hidden');
      expect(spoken(empty)).toBe(message);
    };

    // No deck is loaded.
    const noDecks = renderShopping([]);
    expectHiddenSigil('◇', 'No decks loaded.');
    noDecks.unmount();

    // The user owns every card that the selected deck needs.
    const alphaCards = ['Alpha Commander', 'Sol Ring', 'Arcane Signet', 'Swords to Plowshares'];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(alphaCards.map((name) => [name, 1])));
    const allOwned = renderShopping([ALPHA]);
    expectHiddenSigil('◆', 'All cards owned. The grimoire is complete.');
    allOwned.unmount();
    localStorage.removeItem(STORAGE_KEY);

    // No deck is selected.
    renderShopping([ALPHA, BETA]);
    fireEvent.click(screen.getByRole('button', { name: /^Clear$/i }));
    expectHiddenSigil('◇', 'No decks selected. Pick at least one above to build a list.');
  });
});

describe('the date of the prices in the footer (DEC-1102)', () => {
  it("shows card-metadata.meta.json's prices_as_of as a UTC date", () => {
    expect(formatPricesDate('2026-10-13T21:56:40+00:00')).toBe('13 Oct 2026');
    expect(formatPricesDate('2026-10-13T23:30:00-05:00')).toBe('14 Oct 2026');
    expect(formatPricesDate('2026-09-05T00:00:00Z')).toBe('5 Sep 2026');
    expect(formatPricesDate(undefined)).toBeNull();
    expect(formatPricesDate('not a date')).toBeNull();
  });
});

// DEC-1131 rulings 3 and 7: the rows show the file's prices at first paint, then
// ask for the prices older than 24 h. The footer gives the oldest date among the
// priced rows.
describe('the price refresh of /shopping (DEC-1131)', () => {
  const OLD = '2026-10-10T08:00:00+00:00';
  const meta = (usd: number | null) => ({ cmc: 1, image: 'front/a/b/x.jpg', mana_cost: '{1}', type_line: 'Artifact', usd, eur: null });
  const FILE: RawCardMetadata = {
    'Alpha Commander': meta(null),
    'Sol Ring': meta(1.5),
    'Arcane Signet': meta(0.5),
    'Swords to Plowshares': meta(2),
  };
  let fetchSpy: MockInstance<typeof fetch>;
  let batches: string[][];

  beforeEach(() => {
    cardCache._reset();
    deckLoader._reset();
    localStorage.clear();
    cardCache.seed(FILE, OLD);
    batches = [];
    // Each usd of a batch's answer is $1.00 more than the file's.
    fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/card-metadata.meta.json')) {
        return new Response(JSON.stringify({ prices_as_of: OLD }), { status: 200 });
      }
      if (url === COLLECTION_URL) {
        const names = identifiersOf(init?.body);
        batches.push(names);
        const data = names.map((name) => ({
          name,
          prices: { usd: FILE[name].usd == null ? null : (FILE[name].usd! + 1).toFixed(2) },
        }));
        return new Response(JSON.stringify({ object: 'list', not_found: [], data }), { status: 200 });
      }
      throw new TypeError(`unexpected fetch ${url}`);
    });
  });

  afterEach(() => {
    fetchSpy.mockRestore();
    cardCache._reset();
  });

  const estimate = () => screen.getByText('EST. COST').parentElement!.querySelector('.gv1-serif-xl')!.textContent;
  const foot = () => document.querySelector('.gv1-shop-foot')!.textContent;

  it("shows the file's prices first, then the refreshed ones, and the footer moves to the date of the refresh", async () => {
    render(<Shopping decks={[ALPHA]} />);
    expect(estimate()).toBe('$4');
    await waitFor(() => expect(foot()).toContain('Prices are USD from Scryfall, as of 10 Oct 2026.'));

    await waitFor(() => expect(estimate()).toBe('$7'));
    expect(batches).toHaveLength(1);
    expect([...batches[0]].sort()).toEqual(['Alpha Commander', 'Arcane Signet', 'Sol Ring', 'Swords to Plowshares']);
    expect(screen.getByText('$2.50')).toBeInTheDocument();
    expect(foot()).toContain(`Prices are USD from Scryfall, as of ${formatPricesDate(new Date().toISOString())}.`);
  });

  it("keeps the file's date while one priced row keeps the file's price", async () => {
    fetchSpy.mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/card-metadata.meta.json')) return new Response(JSON.stringify({ prices_as_of: OLD }), { status: 200 });
      const names = identifiersOf(init?.body);
      batches.push(names);
      // Scryfall has no usd for Sol Ring today: the row keeps the file's price.
      // The commander has none in the file either, and stays unpriced.
      const data = names.map((name) => ({
        name,
        prices: { usd: name === 'Sol Ring' || name === 'Alpha Commander' ? null : '9.00' },
      }));
      return new Response(JSON.stringify({ object: 'list', not_found: [], data }), { status: 200 });
    });
    render(<Shopping decks={[ALPHA]} />);
    // $1.50 + $9.00 + $9.00
    await waitFor(() => expect(estimate()).toBe('$20'));
    expect(screen.getByText('$1.50')).toBeInTheDocument();
    expect(foot()).toContain('as of 10 Oct 2026.');
  });
});

// DEC-1160: JSX drops the line break before the footer's date expression, so the
// footer read `… in the buy list.Prices are USD …`. The cases read the whole text.
describe("the footer's text (DEC-1160)", () => {
  const FOOT_HEAD =
    'Basic lands (Plains, Island, Swamp, Mountain, Forest, Wastes, snow-covered) are excluded. ' +
    'Cards needed by multiple decks count once per deck — three decks each wanting Sol Ring shows 3 in the buy list. ';
  let metaSpy: MockInstance<typeof deckLoader.loadCardMetadataMeta>;

  // The loader keeps the fetch that it had at import, so a spy on globalThis.fetch
  // does not reach the meta file: the cases answer for the loader. No row gets a
  // price (the setup's fetch rejects a Scryfall host), so the footer gives the
  // meta file's date.
  beforeEach(() => {
    cardCache._reset();
    deckLoader._reset();
    localStorage.clear();
  });

  afterEach(() => {
    metaSpy.mockRestore();
    cardCache._reset();
  });

  const foot = () => document.querySelector('.gv1-shop-foot')!.textContent;

  it('puts one space between `buy list.` and `Prices` when the prices have a date', async () => {
    metaSpy = vi.spyOn(deckLoader, 'loadCardMetadataMeta').mockResolvedValue({ prices_as_of: '2026-10-10T08:00:00+00:00' });
    render(<Shopping decks={[ALPHA]} />);
    await waitFor(() => expect(foot()).toContain('as of'));
    expect(foot()).toBe(`${FOOT_HEAD}Prices are USD from Scryfall, as of 10 Oct 2026.`);
  });

  it('puts one space between `buy list.` and `Prices` when the prices have no date', async () => {
    metaSpy = vi.spyOn(deckLoader, 'loadCardMetadataMeta').mockResolvedValue(null);
    render(<Shopping decks={[ALPHA]} />);
    // The footer reads the same before the meta file answers: wait for its answer.
    expect(metaSpy).toHaveBeenCalledTimes(1);
    await act(async () => {
      await metaSpy.mock.results[0].value;
    });
    expect(foot()).toBe(`${FOOT_HEAD}Prices are USD from Scryfall.`);
  });
});
