// The two checks that hold for a spec even when it does not use ./test (DEC-1045).
// playwright.config.ts applies both, so no spec can opt out of them.

import { readdirSync, readFileSync } from 'node:fs';
import { join, relative } from 'node:path';

const SCRYFALL_DOMAINS = ['scryfall.com', 'scryfall.io'];

export function isScryfallHost(hostname: string): boolean {
  return SCRYFALL_DOMAINS.some((d) => hostname === d || hostname.endsWith(`.${d}`));
}

// Chromium fails the name lookup for every Scryfall host, so a request that the
// stub in ./test did not answer ends in net::ERR_NAME_NOT_RESOLVED on this
// machine. It never reaches Scryfall and never counts against its rate limit.
export const BLOCK_SCRYFALL_DNS =
  '--host-resolver-rules=' +
  SCRYFALL_DOMAINS.flatMap((d) => [`MAP ${d} ~NOTFOUND`, `MAP *.${d} ~NOTFOUND`]).join(', ');

const STUB_MODULE = join('support', 'test.ts');
const PLAYWRIGHT_IMPORT =
  /(?:from|import|require)\s*\(?\s*['"](?:@playwright\/test|playwright(?:-core)?(?:\/test)?)['"]/;

// A spec that imports Playwright directly runs without the stub and without the
// per-test guard. Stop the run before it starts, and name the line.
export function assertSpecsImportStub(testDir: string): void {
  const offenders: string[] = [];
  for (const entry of readdirSync(testDir, { recursive: true, encoding: 'utf8' })) {
    if (!/\.[cm]?[jt]sx?$/.test(entry) || entry === STUB_MODULE) continue;
    readFileSync(join(testDir, entry), 'utf8')
      .split('\n')
      .forEach((line, i) => {
        if (PLAYWRIGHT_IMPORT.test(line)) {
          offenders.push(`  ${relative(process.cwd(), join(testDir, entry))}:${i + 1}  ${line.trim()}`);
        }
      });
  }
  if (offenders.length === 0) return;
  throw new Error(
    `These lines import Playwright directly, so the file runs without the Scryfall stub:\n` +
      `${offenders.join('\n')}\n` +
      `Import test and expect from './support/test' instead. That module answers Scryfall from\n` +
      `repository data, so the spec does not call the live API (web/README.md, "End-to-end tests").`,
  );
}
