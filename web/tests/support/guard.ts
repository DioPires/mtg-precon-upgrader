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
const RESOLVER_RULES = '--host-resolver-rules=';
export const BLOCK_SCRYFALL_DNS =
  RESOLVER_RULES +
  SCRYFALL_DOMAINS.flatMap((d) => [`MAP ${d} ~NOTFOUND`, `MAP *.${d} ~NOTFOUND`]).join(', ');

// Browser arguments with the block in. Chromium takes one set of resolver
// rules, so rules that a spec passes itself give way to the block.
export function withScryfallDnsBlock(args: string[] = []): string[] {
  return [...args.filter((arg) => !arg.startsWith(RESOLVER_RULES)), BLOCK_SCRYFALL_DNS];
}

const STUB_MODULE = join('support', 'test.ts');
const PLAYWRIGHT_IMPORT =
  /(?:from|import|require)\s*\(?\s*['"](?:@playwright\/test|playwright(?:-core)?(?:\/test)?)['"]/g;

// A spec that imports Playwright directly runs without the stub and without the
// per-test guard. Stop the run before it starts, and name the line. The scan
// reads the file as one text, so an import that breaks before the module name
// does not pass; the line it names is the one that holds the module name.
export function assertSpecsImportStub(testDir: string): void {
  const offenders: string[] = [];
  for (const entry of readdirSync(testDir, { recursive: true, encoding: 'utf8' })) {
    if (!/\.[cm]?[jt]sx?$/.test(entry) || entry === STUB_MODULE) continue;
    const text = readFileSync(join(testDir, entry), 'utf8');
    for (const match of text.matchAll(PLAYWRIGHT_IMPORT)) {
      const line = text.slice(0, match.index + match[0].length).split('\n').length;
      const source = text.split('\n')[line - 1].trim();
      offenders.push(`  ${relative(process.cwd(), join(testDir, entry))}:${line}  ${source}`);
    }
  }
  if (offenders.length === 0) return;
  throw new Error(
    `These lines import Playwright directly, so the file runs without the Scryfall stub:\n` +
      `${offenders.join('\n')}\n` +
      `Import test and expect from './support/test' instead. That module answers Scryfall from\n` +
      `repository data, so the spec does not call the live API (web/README.md, "End-to-end tests").`,
  );
}
