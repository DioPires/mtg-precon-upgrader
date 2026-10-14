// The stub's Moxfield route and the per-test check (DEC-1071). The first two cases
// send their Moxfield request through a proxy that the test starts on 127.0.0.1.
// That proxy answers a plain HTTP request itself and refuses every CONNECT, so a
// request that gets past the stub stops there and never reaches a Moxfield host.
// The third case opens no proxy: the DNS block (./support/guard) applies only
// without one, and it fails the lookup of the request.
import { createServer } from 'node:http';
import type { AddressInfo } from 'node:net';
import { expect, test } from './support/test';

async function localProxy(seen: string[]) {
  const server = createServer((req, res) => {
    seen.push(`${req.method} ${req.url}`);
    res.writeHead(200, { 'access-control-allow-origin': '*' }).end('{}');
  });
  server.on('connect', (req, socket) => {
    seen.push(`CONNECT ${req.url}`);
    socket.end('HTTP/1.1 403 Forbidden\r\n\r\n');
  });
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  const { port } = server.address() as AddressInfo;
  return {
    proxy: { server: `http://127.0.0.1:${port}`, bypass: '127.0.0.1' },
    close: () => new Promise<void>((resolve) => server.close(() => resolve())),
  };
}

for (const fonts of ['live', 'blocked'] as const) {
  test.describe(`Moxfield check (fonts ${fonts})`, () => {
    test.use({ fonts });

    test('the stub stops and names a Moxfield request that no route of the spec answers', async ({ browser, baseURL }) => {
      const seen: string[] = [];
      const local = await localProxy(seen);
      const context = await browser.newContext({ proxy: local.proxy });
      const page = await context.newPage();
      await page.goto(`${baseURL}/data/index.json`);
      await page.evaluate(() => fetch('https://api2.moxfield.com/v3/decks/all/dec1071').catch(() => undefined));
      await context.close();
      await local.close();
      // The check names the request and fails the test, but only when the
      // request never reached the network.
      test.fail(seen.length === 0, 'the stub names the request');
      expect(seen, 'Moxfield requests that reached the network').toEqual([]);
    });

    test('the check names a Moxfield request that a route of the spec sends on and the network answers', async ({ browser, baseURL }) => {
      const seen: string[] = [];
      const local = await localProxy(seen);
      const context = await browser.newContext({ proxy: local.proxy });
      const page = await context.newPage();
      await page.route('http://api2.moxfield.com/**', (route) => route.continue());
      await page.goto(`${baseURL}/data/index.json`);
      const status = await page.evaluate(() =>
        fetch('http://api2.moxfield.com/v3/decks/all/dec1071').then((r) => r.status, () => 0),
      );
      await context.close();
      await local.close();
      // The proxy in the test answered, as the network would.
      expect(status).toBe(200);
      expect(seen).toEqual(['GET http://api2.moxfield.com/v3/decks/all/dec1071']);
      test.fail(true, 'the check names the request');
    });

    test('the check names a Moxfield request that a route of the spec sends on and the DNS block stops', async ({ page, baseURL }) => {
      await page.route('https://api2.moxfield.com/**', (route) => route.continue());
      await page.goto(`${baseURL}/data/index.json`);
      // The lookup fails with net::ERR_NAME_NOT_RESOLVED, so the fetch rejects.
      await page.evaluate(() => fetch('https://api2.moxfield.com/v3/decks/all/dec1071').catch(() => undefined));
      test.fail(true, 'the check names the request that the DNS block stopped');
    });
  });
}
