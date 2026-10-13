import { defineConfig, devices } from '@playwright/test';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { BLOCK_SCRYFALL_DNS, assertSpecsImportStub } from './tests/support/guard';

const testDir = resolve(dirname(fileURLToPath(import.meta.url)), 'tests');
assertSpecsImportStub(testDir);

// GRIMOIRE_E2E_PORT moves the preview server off 4173. With it set, the run
// always builds and serves this tree, and never reuses a server that some
// other checkout left on the port (DEC-1045).
const portVar = process.env.GRIMOIRE_E2E_PORT;
const port = Number(portVar ?? 4173);
if (!Number.isInteger(port) || port < 1024 || port > 65535) {
  throw new Error(`GRIMOIRE_E2E_PORT must be a port from 1024 to 65535, got "${portVar}"`);
}
const origin = `http://127.0.0.1:${port}`;

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
  webServer: {
    command: `npm run build && npx vite preview --host 127.0.0.1 --port ${port} --strictPort`,
    url: origin,
    reuseExistingServer: !process.env.CI && !portVar,
    timeout: 120_000,
  },
});
