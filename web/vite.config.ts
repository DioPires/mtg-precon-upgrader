/// <reference types="vitest" />
import { defineConfig, type Plugin } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { readFile } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const dataRoot = resolve(__dirname, '..', 'data');

// Dev/preview-only middleware: serve the parent repo's data/ tree at /data/*.
// Production build (Phase 6 cutover per DEC-149-plan.md) places dist/ next to
// data/ at the host root, so this dependency only matters in development.
function serveDeckData(): Plugin {
  return {
    name: 'gv1-serve-deck-data',
    configureServer(server) {
      server.middlewares.use('/data', async (req, res, next) => {
        try {
          if (!req.url) return next();
          const cleaned = req.url.split('?')[0];
          if (cleaned.includes('..')) {
            res.statusCode = 400;
            res.end('bad path');
            return;
          }
          const filePath = resolve(dataRoot, '.' + cleaned);
          const buf = await readFile(filePath);
          res.setHeader('content-type', cleaned.endsWith('.json') ? 'application/json' : 'application/octet-stream');
          res.setHeader('cache-control', 'no-cache');
          res.end(buf);
        } catch (err) {
          // Mirror production (Vercel rewrite excludes /data/) — return 404 for
          // missing files instead of falling through to the SPA index.html,
          // which would otherwise crash JSON-parsing loaders with `Unexpected
          // token '<', "<!DOCTYPE"...`.
          if ((err as NodeJS.ErrnoException)?.code === 'ENOENT') {
            res.statusCode = 404;
            res.end('not found');
            return;
          }
          next();
        }
      });
    },
    configurePreviewServer(server) {
      server.middlewares.use('/data', async (req, res, next) => {
        try {
          if (!req.url) return next();
          const cleaned = req.url.split('?')[0];
          if (cleaned.includes('..')) {
            res.statusCode = 400;
            res.end('bad path');
            return;
          }
          const filePath = resolve(dataRoot, '.' + cleaned);
          const buf = await readFile(filePath);
          res.setHeader('content-type', cleaned.endsWith('.json') ? 'application/json' : 'application/octet-stream');
          res.end(buf);
        } catch (err) {
          if ((err as NodeJS.ErrnoException)?.code === 'ENOENT') {
            res.statusCode = 404;
            res.end('not found');
            return;
          }
          next();
        }
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), serveDeckData()],
  server: { port: 5173 },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
    css: false,
    exclude: ['node_modules', 'dist', 'tests/**'],
  },
});
