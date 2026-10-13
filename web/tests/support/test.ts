// The `test` that every spec imports (DEC-1045).
//
// It answers each request to a Scryfall host from repository data (./scryfall),
// so a spec never calls the live API and reads the same card data on every run.
// A request to a Scryfall host that the stub did not answer fails the test and
// is named in the error. playwright.config.ts rejects a spec that imports
// '@playwright/test' directly (./guard).
//
//   test.use({ cards: 'seeded' })    every card answer is in before first paint
//   test.use({ cards: 'none' })      every lookup fails: the layout with no prices
//   test.use({ fonts: 'blocked' })   the web fonts do not load

import { test as base, type Request } from '@playwright/test';
import { isScryfallHost } from './guard';
import { answerFor, cardCacheSeed, type AnswerKind } from './scryfall';

export * from '@playwright/test';

export interface StubOptions {
  /**
   * 'repo'    The app looks each card up, and the stub answers. The app's own
   *           queue paces the lookups, one every 120 ms.
   * 'seeded'  As 'repo', and the app's card cache holds every card before the
   *           first script runs. Use it when a spec needs every price in.
   * 'none'    Every lookup and every card image fails.
   */
  cards: 'repo' | 'seeded' | 'none';
  /** 'blocked' fails every request to the Google Fonts hosts. */
  fonts: 'live' | 'blocked';
}

const FONT_HOSTS = ['fonts.googleapis.com', 'fonts.gstatic.com'];

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

export const test = base.extend<StubOptions>({
  cards: ['repo', { option: true }],
  fonts: ['live', { option: true }],

  context: async ({ context, cards, fonts }, runTest, testInfo) => {
    const answered = new WeakSet<Request>();
    const unanswered: string[] = [];
    const counts: Partial<Record<AnswerKind, number>> = {};
    const notFound = new Set<string>();

    await context.route(
      (url) => isScryfallHost(url.hostname),
      async (route) => {
        const request = route.request();
        answered.add(request);
        const answer = answerFor(new URL(request.url()));
        if (!answer) {
          unanswered.push(`${request.method()} ${request.url()} (the stub has no answer for it)`);
        } else {
          counts[answer.kind] = (counts[answer.kind] ?? 0) + 1;
        }
        // The app keeps asking while a test ends, and the page may close first.
        const pageGone = () => undefined;
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
    if (cards === 'seeded') await context.addInitScript(seedCardCache, cardCacheSeed());

    // A spec can take a request away from the stub: its own route, or unroute().
    // Such a request ends here without the mark the stub leaves.
    const onEnd = (request: Request) => {
      if (answered.has(request) || !isScryfallHost(new URL(request.url()).hostname)) return;
      const outcome = request.failure()?.errorText ?? 'the network answered it';
      // A page that moves on cancels its open requests, also one that the stub
      // has not seen yet. That one never left the browser, so it is no leak.
      if (outcome === 'net::ERR_ABORTED') return;
      unanswered.push(`${request.method()} ${request.url()} (${outcome})`);
    };
    context.on('requestfinished', onEnd);
    context.on('requestfailed', onEnd);

    await runTest(context);

    if (Object.keys(counts).length > 0) {
      await testInfo.attach('scryfall-stub', {
        contentType: 'application/json',
        body: JSON.stringify({ cards, requests: counts, notFound: [...notFound].sort() }, null, 2),
      });
    }
    if (unanswered.length > 0) {
      throw new Error(
        `${unanswered.length} request${unanswered.length === 1 ? '' : 's'} to a Scryfall host got no answer from the stub:\n` +
          unanswered.map((line) => `  ${line}`).join('\n') +
          `\nThe e2e suite does not call Scryfall (web/README.md, "End-to-end tests").`,
      );
    }
  },
});
