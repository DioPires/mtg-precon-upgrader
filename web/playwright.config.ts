import { defineConfig, devices } from '@playwright/test';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { BLOCK_SCRYFALL_DNS, assertSpecsImportStub } from './tests/support/guard';

const testDir = resolve(dirname(fileURLToPath(import.meta.url)), 'tests');
assertSpecsImportStub(testDir);

// GRIMOIRE_E2E_PORT moves the preview server off 4173. With it set, the run
// builds and serves this tree and accepts no other server (DEC-1045, DEC-1073).
const portVar = process.env.GRIMOIRE_E2E_PORT;
const port = Number(portVar ?? 4173);
if (!Number.isInteger(port) || port < 1024 || port > 65535) {
  throw new Error(`GRIMOIRE_E2E_PORT must be a port from 1024 to 65535, got "${portVar}"`);
}
const origin = `http://127.0.0.1:${port}`;
const command = `npm run build && npx vite preview --host 127.0.0.1 --port ${port} --strictPort`;

// The line that `vite preview` prints once it holds the port. Playwright turns
// colours on for the server, so a colour code can stand between the parts.
const sgr = '(?:\\x1b\\[[\\d;]*m)*';
const ownServerLine = new RegExp(`Local${sgr}:\\s+${sgr}http://127\\.0\\.0\\.1:${sgr}${port}${sgr}/`);

// Without the variable a local run reuses a server that already answers on 4173.
// With it, the run never asks the port who is there: a second server that takes
// the port during the build would answer in place of this tree's. It waits for
// its own server's line. `--strictPort` makes that server exit when the port is
// taken, and the run stops with Vite's "Port ... is already in use".
const webServer =
  portVar === undefined
    ? { command, url: origin, reuseExistingServer: !process.env.CI, timeout: 120_000 }
    : { command, wait: { stdout: ownServerLine }, timeout: 120_000 };

export default defineConfig({
  testDir,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: origin,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], launchOptions: { args: [BLOCK_SCRYFALL_DNS] } },
    },
  ],
  webServer,
});
