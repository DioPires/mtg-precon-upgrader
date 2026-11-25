// DEC-1153: two follow-ups of the PR #54 review (DEC-1149) that a page shows.
//
// N4: the loader fetches card-metadata.meta.json only with card-metadata.json,
// and stores the file with its own date. A load from storage sends no request
// for either file.
//
// N5: bucket 1 of the limiter frees its lock only after the card cache has
// stored the answer. A tab whose turn comes while another tab's answer is out
// finds those names in storage, also when the answer takes longer than the
// 1,200 ms between starts, and also when the browser brings the first tab's
// writes to the second tab after the lock (the hand-over, src/data/
// scryfallLimiter.ts). The fixture's rate check (support/test.ts) holds in each
// case. The last two cases run the hand-over's IndexedDB side on the browser's
// own IndexedDB, held up by another page of the origin.
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { normalizeName } from '../src/lib/spellbookMatch';
import { expect, test, type Page } from './support/test';

const DATA = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..', 'data');
const read = (file: string) => JSON.parse(readFileSync(resolve(DATA, file), 'utf8'));
const FILE_NAMES = new Set(Object.keys(read('card-metadata.json') as Record<string, unknown>).map((name) => name.toLowerCase()));
const PRICES_AS_OF = (read('card-metadata.meta.json') as { prices_as_of: string }).prices_as_of;
const HOUR_MS = 3_600_000;
const COLLECTION = 'https://api.scryfall.com/cards/collection';
const BUCKET_ONE_LOCK = 'grimoire-scryfall-bucket-1';
const TURN_KEY = 'grimoire-scryfall-turn';
const TURN_DB = { name: 'grimoire-scryfall', store: 'turn', id: 'last' };
/**
 * 5,000 localStorage writes of 200 characters: the other tab gets the writes after
 * them that much later. Many small writes delay it more than a few large ones: with
 * 50 of 20,000 characters, a turn that did not wait for the mark still found the
 * entries in Chrome 9 runs in 10 (2026-11-24). No WebKit-only receiver test: real
 * WebKit delivers the pending localStorage writes on the IndexedDB read alone
 * (never-waits missed 0/10, no hand-over missed 10/10, under a 5,000-write
 * ballast), so the two-tab spec guards the read there and the wait is covered by
 * Chrome and by the laggingStorages unit cases.
 */
const BALLAST = { keys: 5_000, size: 200 };

/** A page clock at which every price of the file is older than 24 h, also on the day the file was made. */
const pricesAreOld = () => Math.max(Date.now(), Date.parse(PRICES_AS_OF) + 25 * HOUR_MS);
const front = (name: string) => name.split(' // ')[0].trim();

/**
 * True once a tab of the origin waits for the lock of bucket 1, as `page` sees
 * navigator.locks; false when `ms` passes first, also while a query is still
 * out. An error of the page's own query rejects.
 */
async function bucketOneWaiter(page: Page, ms: number): Promise<boolean> {
  let over = false;
  let timer: ReturnType<typeof setTimeout> | undefined;
  const deadline = new Promise<false>((done) => {
    timer = setTimeout(() => {
      over = true;
      done(false);
    }, ms);
  });
  const poll = (async () => {
    while (!over) {
      const waiting = await page.evaluate(
        async (name) => ((await navigator.locks.query()).pending ?? []).some((lock) => lock.name === name),
        BUCKET_ONE_LOCK,
      );
      if (waiting) return true;
      await new Promise((done) => setTimeout(done, 50));
    }
    return false;
  })();
  try {
    return await Promise.race([poll, deadline]);
  } finally {
    over = true;
    clearTimeout(timer);
  }
}

/** The arts of /combos: each card's name, its picture, and whether it shows the glyph. */
async function arts(page: Page) {
  return page.locator('.gv1-lab-art').evaluateAll((els) =>
    els.map((el) => ({
      name: el.getAttribute('data-card-name') ?? '',
      src: el.querySelector('img')?.getAttribute('src') ?? null,
      glyph: !!el.querySelector('.gv1-lab-art-fallback'),
    })),
  );
}

/** The token in the turn database; a database without the store rejects. */
async function readTurn(page: Page): Promise<unknown> {
  return page.evaluate(
    ({ name, store, id }) =>
      new Promise<unknown>((done, fail) => {
        const open = indexedDB.open(name);
        open.onerror = () => fail(open.error);
        open.onsuccess = () => {
          const db = open.result;
          try {
            const request = db.transaction(store, 'readonly').objectStore(store).get(id);
            request.onerror = () => fail(request.error);
            request.onsuccess = () => {
              db.close();
              done(request.result);
            };
          } catch (error) {
            // No such store: no turn has written a token.
            db.close();
            fail(error);
          }
        };
      }),
    TURN_DB,
  );
}

/** Before the app runs: the turn database at version 1 holds `token`, and localStorage shows the same mark. */
async function seedTurn(page: Page, token: string): Promise<void> {
  await page.evaluate(
    ({ db: { name, store, id }, key, token }) =>
      new Promise<void>((done, fail) => {
        const open = indexedDB.open(name, 1);
        open.onupgradeneeded = () => open.result.createObjectStore(store);
        open.onerror = () => fail(open.error);
        open.onsuccess = () => {
          const transaction = open.result.transaction(store, 'readwrite');
          transaction.objectStore(store).put(token, id);
          transaction.onerror = () => fail(transaction.error);
          transaction.oncomplete = () => {
            open.result.close();
            localStorage.setItem(key, token);
            done();
          };
        };
      }),
    { db: TURN_DB, key: TURN_KEY, token },
  );
}

/**
 * Holds a read-write transaction on the turn store, kept alive by one read after
 * another, until releaseTurnStore(): every transaction that begins after it on
 * the store waits.
 */
async function holdTurnStore(page: Page): Promise<void> {
  await page.evaluate(
    ({ name, store, id }) =>
      new Promise<void>((done, fail) => {
        const open = indexedDB.open(name, 1);
        open.onerror = () => fail(open.error);
        open.onsuccess = () => {
          const db = open.result;
          const transaction = db.transaction(store, 'readwrite');
          const turns = transaction.objectStore(store);
          const w = window as unknown as { __releaseTurnStore?: () => Promise<void> };
          let held = true;
          const keep = () => {
            if (held) turns.get(id).onsuccess = keep;
          };
          keep();
          const ended = new Promise<void>((end) => {
            transaction.oncomplete = () => end();
            transaction.onabort = () => end();
          });
          w.__releaseTurnStore = async () => {
            held = false;
            await ended;
            db.close();
          };
          done();
        };
      }),
    TURN_DB,
  );
}

async function releaseTurnStore(page: Page): Promise<void> {
  await page.evaluate(() => (window as unknown as { __releaseTurnStore: () => Promise<void> }).__releaseTurnStore());
}

// Runs in each tab before the app. Once the test arms it (window.__ballast), the
// tab's next card cache write, the first of the stored answer, comes after the
// BALLAST writes: the other tab gets the answer's entries and the turn's mark that
// much later.
function ballastBeforeTheAnswer(): void {
  const set = Storage.prototype.setItem;
  const w = window as unknown as { __ballast?: { keys: number; size: number } };
  Storage.prototype.setItem = function (this: Storage, key: string, value: string) {
    const ballast = w.__ballast;
    if (ballast && key.startsWith('gv1-card:')) {
      w.__ballast = undefined;
      const filler = 'x'.repeat(ballast.size);
      for (let i = 0; i < ballast.keys; i += 1) set.call(this, `e2e-ballast-${i}`, `${i}:${filler}`);
    }
    set.call(this, key, value);
  };
}

// Runs in the page before the app: the value of each put on the turn store
// that IndexedDB accepted (put() returned its request; it throws when it does not).
function traceTurnPuts(store: string): void {
  const w = window as unknown as { __turnPuts: unknown[] };
  w.__turnPuts = [];
  const put = IDBObjectStore.prototype.put;
  IDBObjectStore.prototype.put = function (this: IDBObjectStore, value: unknown, key?: IDBValidKey) {
    const request = put.call(this, value, key);
    if (this.name === store) w.__turnPuts.push(value);
    return request;
  };
}

// Runs in the page before the app: the time of each grant and release of the
// lock of bucket 1, and of each /cards/collection fetch and its answer, on the
// page's clock.
function traceBucketOne(lock: string): void {
  const log: Array<[string, number]> = [];
  (window as unknown as { __bucketOne: typeof log }).__bucketOne = log;
  const at = (what: string) => log.push([what, performance.now()]);
  const request = LockManager.prototype.request as unknown as (this: LockManager, ...args: unknown[]) => Promise<unknown>;
  (LockManager.prototype as unknown as { request: unknown }).request = function (this: LockManager, name: string, ...rest: unknown[]) {
    if (name !== lock) return request.call(this, name, ...rest);
    const callback = rest[rest.length - 1] as (held: Lock | null) => unknown;
    const traced = async (held: Lock | null) => {
      at('grant');
      try {
        return await callback(held);
      } finally {
        at('release');
      }
    };
    return rest.length > 1 ? request.call(this, name, rest[0], traced) : request.call(this, name, traced);
  };
  const send = window.fetch;
  window.fetch = function (input: RequestInfo | URL, init?: RequestInit) {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
    if (!url.startsWith('https://api.scryfall.com/cards/collection')) return send.call(this, input, init);
    at('fetch');
    return send.call(this, input, init).then((response) => {
      at('answer');
      return response;
    });
  };
}

/**
 * The hand-over's own time in the first turn of bucket 1 that sent a request:
 * from the grant to the fetch, plus from the answer to the release (ms).
 */
async function firstTurnHandover(page: Page): Promise<number | null> {
  const log = await page.evaluate(() => (window as unknown as { __bucketOne: Array<[string, number]> }).__bucketOne);
  const at: Record<string, number> = {};
  for (const [what, t] of log) {
    if (what === 'grant' && at.fetch === undefined) at.grant = t;
    else if ((what === 'fetch' || what === 'answer') && at[what] === undefined) at[what] = t;
    else if (what === 'release' && at.answer !== undefined && at.release === undefined) at.release = t;
  }
  const { grant, fetch, answer, release } = at;
  return [grant, fetch, answer, release].every((t) => t !== undefined) ? fetch - grant + (release - answer) : null;
}

/** Each turn of bucket 1 in the page: ms from the grant to its fetch (null for a turn that sent nothing). */
async function bucketOneTurns(page: Page): Promise<Array<number | null>> {
  const log = await page.evaluate(() => (window as unknown as { __bucketOne: Array<[string, number]> }).__bucketOne);
  const turns: Array<number | null> = [];
  let grant: number | null = null;
  let fetch: number | null = null;
  for (const [what, t] of log) {
    if (what === 'grant') [grant, fetch] = [t, null];
    else if (what === 'fetch' && grant !== null && fetch === null) fetch = t - grant;
    else if (what === 'release' && grant !== null) {
      turns.push(fetch);
      grant = null;
    }
  }
  return turns;
}

test('a deck guide sends 1 meta request cold, none after a reload, and none on the way to /shopping', async ({
  page,
  context,
}) => {
  const meta: string[] = [];
  const file: string[] = [];
  let phase = 'cold';
  context.on('request', (request) => {
    const path = new URL(request.url()).pathname;
    if (path === '/data/card-metadata.meta.json') meta.push(phase);
    if (path === '/data/card-metadata.json') file.push(phase);
  });
  await page.goto('/deck/creeping-corruption');
  await page.locator('.gv1-card-tile').first().waitFor();
  await page.waitForTimeout(1_000);

  phase = 'reload';
  await page.reload();
  await page.locator('.gv1-card-tile').first().waitFor();
  await page.waitForTimeout(1_000);

  phase = 'spa-nav';
  await page.locator('a[href="/shopping"]').first().click();
  await expect(page).toHaveURL(/\/shopping$/);
  await expect(page.locator('.gv1-shop-foot')).toContainText('Prices are USD from Scryfall, as of ');
  await page.waitForTimeout(1_000);

  expect({ meta, file }).toEqual({ meta: ['cold'], file: ['cold'] });
});

test('two tabs open /combos at once; the first answer is held until the other tab waits for bucket 1, and is stored after 5,000 other localStorage writes: each name of the page goes out once, and both tabs show their cards', async ({
  context,
}) => {
  test.setTimeout(90_000);
  const batches: Array<{ at: number; names: string[] }> = [];
  const t0 = Date.now();
  context.on('request', (request) => {
    if (request.url() === COLLECTION && request.method() === 'POST') {
      const body = JSON.parse(request.postData() ?? '{}') as { identifiers?: Array<{ name: string }> };
      batches.push({ at: Date.now() - t0, names: (body.identifiers ?? []).map((id) => id.name) });
    }
  });
  let answers = 0;
  let held: { waited: boolean; error: string | null } | null = null;
  // This route comes before the stub's: it holds each answer 1.5 s, then the stub answers.
  // The first answer also waits until the other tab asks for the lock of bucket 1 (a
  // deadline under the 20 s request timeout). Then the tab that asked stores the answer
  // after 5,000 other writes (ballastBeforeTheAnswer), so its card entries and its mark
  // reach the other tab late: in Chrome the other tab's batch finds them only if its turn
  // waits for the mark.
  await context.addInitScript(ballastBeforeTheAnswer);
  await context.route(COLLECTION, async (route) => {
    const first = ++answers === 1;
    const asker = route.request().frame().page();
    const waiting = first
      ? bucketOneWaiter(asker, 15_000).then(
          (waited) => ({ waited, error: null }),
          (error: unknown) => ({ waited: false, error: String(error) }),
        )
      : null;
    const [, wait] = await Promise.all([new Promise((done) => setTimeout(done, 1_500)), waiting]);
    if (wait) {
      held = wait;
      if (wait.waited) {
        await asker
          .evaluate((ballast) => {
            (window as unknown as { __ballast?: typeof ballast }).__ballast = ballast;
          }, BALLAST)
          .catch((error: unknown) => (held = { waited: true, error: String(error) }));
      }
    }
    await route.fallback();
  });
  const tabs = await Promise.all([context.newPage(), context.newPage()]);
  await Promise.all(tabs.map((tab) => tab.goto('/combos')));
  for (const tab of tabs) {
    await tab.locator('.gv1-lab-art').first().waitFor();
    await expect(tab.locator('.gv1-lab-skeleton')).toHaveCount(0, { timeout: 60_000 });
  }
  await tabs[0].waitForTimeout(2_000);
  test.info().annotations.push({
    type: 'batches',
    description: JSON.stringify(batches.map((batch) => ({ at: batch.at, n: batch.names.length }))),
  });
  expect(held).toEqual({ waited: true, error: null });

  // The page's names that card-metadata.json lacks, as the front faces that a batch sends, each once.
  const [left, right] = await Promise.all(tabs.map(arts));
  const outside = (cards: typeof left) =>
    [...new Set(cards.map((art) => art.name).filter((name) => !FILE_NAMES.has(name.toLowerCase())).map((name) => normalizeName(front(name))))].sort();
  expect(outside(right)).toEqual(outside(left));
  expect(outside(left).length).toBeGreaterThan(5);
  expect(batches.flatMap((batch) => batch.names).map(normalizeName).sort()).toEqual(outside(left));
  for (const cards of [left, right]) {
    for (const art of cards) {
      if (FILE_NAMES.has(art.name.toLowerCase())) expect(art.src, art.name).toMatch(/^https:\/\/cards\.scryfall\.io\/small\//);
      // The stub knows only the file's names: Scryfall's not_found shows the glyph.
      else expect(art.glyph, art.name).toBe(true);
    }
  }

  // The last turn's token is in IndexedDB, and each tab's localStorage shows it.
  const stored = await readTurn(tabs[0]);
  expect(typeof stored === 'string' && stored.length > 0, String(stored)).toBe(true);
  for (const tab of tabs) expect(await tab.evaluate((key) => localStorage.getItem(key), TURN_KEY)).toBe(stored);
});

test.describe('the hand-over on IndexedDB that another page holds up', () => {
  test('the start read waits behind a read-write transaction: the first batch goes about 1 s after the turn starts, the hand-over goes off, the next batch does not wait, and the token stays', async ({
    context,
    page,
  }) => {
    test.setTimeout(90_000);
    const other = await context.newPage();
    await other.goto('/data/index.json');
    await seedTurn(other, 'e2e-token-before');
    await holdTurnStore(other);
    await page.addInitScript(traceBucketOne, BUCKET_ONE_LOCK);
    // /shopping refreshes prices older than 24 h in two batches or more.
    await page.clock.install({ time: pricesAreOld() });
    await page.goto('/shopping');
    await expect
      .poll(async () => (await bucketOneTurns(page)).filter((turn) => turn !== null).length, { timeout: 30_000 })
      .toBeGreaterThanOrEqual(2);
    const turns = await bucketOneTurns(page);
    test.info().annotations.push({ type: 'grant-to-fetch ms', description: JSON.stringify(turns) });
    // The first turn: the read waits the whole allowance (1,000 ms), then the request goes.
    expect(turns[0]).toBeGreaterThanOrEqual(950);
    expect(turns[0]).toBeLessThan(2_000);
    // Each later turn uses no IndexedDB.
    for (const turn of turns.slice(1)) if (turn !== null) expect(turn).toBeLessThan(300);
    await releaseTurnStore(other);
    expect(await readTurn(other)).toBe('e2e-token-before');
    expect(await page.evaluate((key) => localStorage.getItem(key), TURN_KEY)).toBe('e2e-token-before');
  });

  test('the end write waits behind a read-write transaction: it is aborted at the end of the allowance and never lands, while localStorage shows the new mark', async ({
    context,
    page,
  }) => {
    test.setTimeout(60_000);
    const other = await context.newPage();
    await other.goto('/data/index.json');
    await seedTurn(other, 'e2e-token-before');
    let holding = false;
    // The hold starts with the first answer: the turn's start read has gone, its end write has not.
    await context.route(COLLECTION, async (route) => {
      if (!holding) {
        holding = true;
        await holdTurnStore(other);
      }
      await route.fallback();
    });
    await page.addInitScript(traceTurnPuts, TURN_DB.store);
    await page.addInitScript(traceBucketOne, BUCKET_ONE_LOCK);
    await page.goto('/combos');
    await expect.poll(() => holding, { timeout: 30_000 }).toBe(true);
    // The turn ends: the lock is free, and localStorage shows a new mark: a token, not the seed.
    const turnEnd = () =>
      page.evaluate(
        async ({ lock, key }) => ({
          held: ((await navigator.locks.query()).held ?? []).some((held) => held.name === lock),
          mark: localStorage.getItem(key),
        }),
        { lock: BUCKET_ONE_LOCK, key: TURN_KEY },
      );
    await expect
      .poll(async () => {
        const { held, mark } = await turnEnd();
        return !held && typeof mark === 'string' && mark.length > 0 && mark !== 'e2e-token-before';
      }, { timeout: 30_000 })
      .toBe(true);
    const { mark } = await turnEnd();
    // The turn's combined hand-over time (lock grant to fetch, plus answer to lock release)
    // is about the allowance, 1,000 ms plus the storing. It does not measure the end write
    // alone: a delayed read with a short end write also fits the window, and it cannot tell
    // what was left of the allowance from a fresh 1,000 ms at the end; the unit case "a read
    // that answers at 900 ms and a write that never settles" pins that.
    const handover = await firstTurnHandover(page);
    test.info().annotations.push({ type: 'hand-over ms', description: String(handover) });
    expect(handover).toBeGreaterThanOrEqual(990);
    expect(handover).toBeLessThan(1_500);
    // IndexedDB accepted the end write, with that token.
    expect(await page.evaluate(() => (window as unknown as { __turnPuts: unknown[] }).__turnPuts)).toEqual([mark]);
    await releaseTurnStore(other);
    // A transaction begun now comes after the end write, had it still been waiting: it did not land.
    expect(await readTurn(other)).toBe('e2e-token-before');
  });
});
