// The `test` that every spec imports (DEC-1045).
//
// It answers each request to a Scryfall host from repository data (./scryfall),
// so a spec never calls the live API and reads the same card data on every run.
// A request to a Scryfall host that the stub did not answer fails the test and
// is named in the error. playwright.config.ts rejects a spec that imports
// '@playwright/test' directly (./guard).
//
// The rate check (DEC-1102): a test fails when one browser context sent more
// than 2 requests to /cards/named and /cards/collection (bucket 1 of
// src/data/scryfallLimiter.ts) in any 1 s. The stub counts them at its route,
// in real time, so every case proves the app's limit.
//
//   test.use({ cards: 'seeded' })        as 'repo', plus a `gv1-card:` entry for each name before first paint
//   test.use({ cards: 'none' })          every lookup and picture fails, and card-metadata.json has no price
//   test.use({ fonts: 'blocked' })       the web fonts do not load
//   test.use({ scryfall429From: 3 })     bucket 1 answers 429 from its 3rd request on
//   test.use({ rateClock: 'page' })      the rate check reads the page's clock (a spec that moves page.clock)

import { test as base, type BrowserContext, type Request } from '@playwright/test';
import { isScryfallHost, withScryfallDnsBlock } from './guard';
import { answerFor, cardCacheSeed, cardMetadataWithoutPrices, type AnswerKind } from './scryfall';

export * from '@playwright/test';

export interface StubOptions {
  /**
   * 'repo'    The app takes every name of data/card-metadata.json from that
   *           file (DEC-1102) and looks up only the names outside it; the stub
   *           answers. The limiter paces the lookups, one every 600 ms or more.
   * 'seeded'  As 'repo', and localStorage holds a `gv1-card:` entry for every
   *           name of the file, and for each face of a `//` name, before the
   *           first script runs. The app drops the entries of the file's names
   *           when it seeds them, so for those names the page is the page of
   *           'repo'. Only a face name that the file lacks reads differently.
   * 'none'    Every lookup and every card picture fails, and
   *           /data/card-metadata.json comes without prices (`usd` and `eur`
   *           null): the layout with no prices.
   */
  cards: 'repo' | 'seeded' | 'none';
  /** 'blocked' fails every request to the Google Fonts hosts. */
  fonts: 'live' | 'blocked';
  /**
   * From this request of bucket 1 on (counted over the test, from 1), the stub
   * answers 429 with a CORS header for another origin. The browser blocks it, as
   * it blocks Scryfall's own 429 (which has no CORS header), and shows the app a
   * fetch that rejects. 0 means never.
   */
  scryfall429From: number;
  /**
   * The clock of the rate check. 'real' counts at the stub's route in real time.
   * A spec that moves page.clock sets 'page': its fake time can start several
   * requests in one real second. The check then reads the page's own clock at
   * each bucket 1 fetch that the app makes, so the limit holds in the time that
   * the app sees. Every other case keeps 'real'.
   */
  rateClock: 'real' | 'page';
}

interface StubFixtures {
  /** Gives one context the stub and the per-test check. `context` and `browser.newContext()` call it. */
  scryfallStub: (context: BrowserContext) => Promise<void>;
}

const FONT_HOSTS = ['fonts.googleapis.com', 'fonts.gstatic.com'];

/** The methods of bucket 1: Scryfall allows them 2 requests a second. */
const BUCKET_ONE = /^\/cards\/(named|collection)$/;
const RATE_LIMIT = 2;
const RATE_WINDOW_MS = 1000;
const PAGE_CLOCK_BINDING = '__grimoireBucketOneSent';

/** The most requests that any window of RATE_WINDOW_MS holds. */
export function peakPerWindow(times: number[], windowMs = RATE_WINDOW_MS): number {
  const sorted = [...times].sort((a, b) => a - b);
  let peak = 0;
  for (let i = 0, j = 0; i < sorted.length; i += 1) {
    while (sorted[i] - sorted[j] >= windowMs) j += 1;
    peak = Math.max(peak, i - j + 1);
  }
  return peak;
}

// Runs in the page for `rateClock: 'page'`. It reads the page's clock when the
// app calls fetch for a bucket 1 address, and passes that time to the fixture.
function reportBucketOneSends(binding: string): void {
  const send = window.fetch;
  window.fetch = function (input: RequestInfo | URL, init?: RequestInit) {
    try {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
      if (/^https:\/\/api\.scryfall\.com\/cards\/(named|collection)\?/.test(url)) {
        const report = (window as unknown as Record<string, ((t: number) => Promise<void>) | undefined>)[binding];
        // A page that closes drops the report; that is no failure of the app.
        report?.(Date.now())?.catch(() => undefined);
      }
    } catch {
      // The report never stands in the app's way.
    }
    return send.call(this, input, init);
  };
}

// Runs in the page. `fetchedAt` is the page's own clock, so an entry is never stale.
function seedCardCache(entries: Record<string, object>): void {
  try {
    const fetchedAt = Date.now();
    for (const [key, entry] of Object.entries(entries)) {
      localStorage.setItem(`gv1-card:${key}`, JSON.stringify({ ...entry, fetchedAt }));
    }
  } catch {
    // about:blank has no storage.
  }
}

// What became of a request that got an answer or failed without the mark the
// stub leaves. Null means that it never left the browser and that no one
// answered it.
function outcomeOf(request: Request): string | null {
  const failure = request.failure()?.errorText;
  // A page that moves on cancels its open requests, also one that the stub
  // has not seen yet. That one never left the browser, so it is no leak.
  if (failure === 'net::ERR_ABORTED') return null;
  if (failure) return failure;
  // The browser sets no send time on a request that a route answers.
  return request.timing().requestStart < 0
    ? 'a route of the spec answered it, and the browser did not send it'
    : 'the network answered it';
}

export const test = base.extend<StubOptions & StubFixtures>({
  cards: ['repo', { option: true }],
  fonts: ['live', { option: true }],
  scryfall429From: [0, { option: true }],
  rateClock: ['real', { option: true }],

  // Playwright's own `browser`, with one change: the DNS block is in the
  // arguments also when a spec sets `launchOptions`, which replaces the
  // project's value.
  browser: [
    async ({ playwright, browserName, launchOptions }, runWorker) => {
      const browser = await playwright[browserName].launch({
        ...launchOptions,
        args: withScryfallDnsBlock(launchOptions.args),
      });
      await runWorker(browser);
      await browser.close();
    },
    { scope: 'worker', timeout: 0 },
  ],

  scryfallStub: [
    async ({ browser, cards, fonts, scryfall429From, rateClock }, runTest, testInfo) => {
      const stubbed = new WeakSet<BrowserContext>();
      const answered = new WeakSet<Request>();
      const unanswered: string[] = [];
      const counts: Partial<Record<AnswerKind, number>> = {};
      const notFound = new Set<string>();
      // The rate check: the times of each context's bucket 1 requests.
      const bucketOne = new Map<BrowserContext, number[]>();
      let bucketOneCount = 0;
      let limited = 0;
      const stamp = (context: BrowserContext, time: number) => {
        const times = bucketOne.get(context) ?? [];
        times.push(time);
        bucketOne.set(context, times);
      };

      // A spec can take a request away from the stub: its own route, or unroute().
      // Such a request comes here without the mark the stub leaves, when its
      // answer arrives or when it fails. The check does not wait for the end of
      // the body: a test that reads only the status can end before that.
      const named = new WeakSet<Request>();
      const judge = (request: Request) => {
        if (answered.has(request) || named.has(request)) return;
        if (!isScryfallHost(new URL(request.url()).hostname)) return;
        named.add(request);
        const outcome = outcomeOf(request);
        if (outcome) unanswered.push(`${request.method()} ${request.url()} (${outcome})`);
      };

      const stub = async (context: BrowserContext) => {
        if (stubbed.has(context)) return;
        stubbed.add(context);
        await context.route(
          (url) => isScryfallHost(url.hostname),
          async (route) => {
            const request = route.request();
            answered.add(request);
            const url = new URL(request.url());
            const answer = answerFor(url);
            if (!answer) {
              unanswered.push(`${request.method()} ${request.url()} (the stub has no answer for it)`);
            } else {
              counts[answer.kind] = (counts[answer.kind] ?? 0) + 1;
            }
            // The app keeps asking while a test ends, and the page may close first.
            const pageGone = () => undefined;
            if (url.hostname === 'api.scryfall.com' && BUCKET_ONE.test(url.pathname)) {
              bucketOneCount += 1;
              if (rateClock === 'real') stamp(context, Date.now());
              if (scryfall429From > 0 && bucketOneCount >= scryfall429From) {
                limited += 1;
                // Scryfall's own 429 has no CORS header, so the browser blocks it and
                // the app's fetch rejects. Playwright adds the header to an answer
                // without one (its issue #12929); a header for another origin gives
                // the same block.
                return route
                  .fulfill({
                    status: 429,
                    contentType: 'application/json',
                    headers: { 'access-control-allow-origin': 'https://scryfall.com' },
                    body: '{"object":"error","status":429}',
                  })
                  .catch(pageGone);
              }
            }
            if (!answer || cards === 'none') return route.abort().catch(pageGone);
            if (answer.notFound) notFound.add(answer.notFound);
            return route
              .fulfill({
                status: answer.status,
                contentType: answer.contentType,
                headers: { 'access-control-allow-origin': '*' },
                body: answer.body,
              })
              .catch(pageGone);
          },
        );
        if (fonts === 'blocked') {
          await context.route(
            (url) => FONT_HOSTS.includes(url.hostname),
            (route) => route.abort().catch(() => undefined),
          );
        }
        if (cards === 'none') {
          await context.route(
            (url) => url.pathname === '/data/card-metadata.json',
            (route) =>
              route
                .fulfill({ status: 200, contentType: 'application/json', body: cardMetadataWithoutPrices() })
                .catch(() => undefined),
          );
        }
        if (rateClock === 'page') {
          await context.exposeBinding(PAGE_CLOCK_BINDING, (_source, time: number) => stamp(context, time));
          await context.addInitScript(reportBucketOneSends, PAGE_CLOCK_BINDING);
        }
        if (cards === 'seeded') await context.addInitScript(seedCardCache, cardCacheSeed());
        context.on('response', (response) => judge(response.request()));
        context.on('requestfailed', judge);
      };

      // While the test runs, every context that this browser opens gets the stub.
      const newContext = browser.newContext;
      browser.newContext = async (options) => {
        const context = await newContext.call(browser, options);
        await stub(context);
        return context;
      };
      await runTest(stub);
      browser.newContext = newContext;

      const peaks = [...bucketOne.values()].map((times) => peakPerWindow(times));
      const peak = Math.max(0, ...peaks);
      if (Object.keys(counts).length > 0) {
        await testInfo.attach('scryfall-stub', {
          contentType: 'application/json',
          body: JSON.stringify(
            {
              cards,
              requests: counts,
              notFound: [...notFound].sort(),
              bucketOne: { count: bucketOneCount, peakPerSecond: peak, clock: rateClock, answered429: limited },
            },
            null,
            2,
          ),
        });
      }
      const failures: string[] = [];
      if (unanswered.length > 0) {
        failures.push(
          `${unanswered.length} request${unanswered.length === 1 ? '' : 's'} to a Scryfall host got no answer from the stub:\n` +
            unanswered.map((line) => `  ${line}`).join('\n') +
            `\nThe e2e suite does not call Scryfall, and only the stub answers for it: the check cannot\n` +
            `see where a spec's own route took its answer from (web/README.md, "End-to-end tests").`,
        );
      }
      if (peak > RATE_LIMIT) {
        const worst = [...bucketOne.values()][peaks.indexOf(peak)];
        const start = Math.min(...worst);
        failures.push(
          `One browser context sent ${peak} requests to /cards/named and /cards/collection in 1 s; Scryfall allows ${RATE_LIMIT}.\n` +
            `  Send times (ms after the first, ${rateClock === 'page' ? "the page's clock" : 'real time'}): ` +
            worst.map((t) => t - start).join(', ') +
            `\nEvery request to api.scryfall.com goes through src/data/scryfallLimiter.ts (web/README.md, "Scryfall requests").`,
        );
      }
      if (failures.length > 0) throw new Error(failures.join('\n'));
    },
    { auto: true },
  ],

  context: async ({ scryfallStub, context }, runTest) => {
    await scryfallStub(context);
    await runTest(context);
  },
});
