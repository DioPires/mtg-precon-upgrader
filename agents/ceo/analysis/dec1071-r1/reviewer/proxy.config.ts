// Scratch config (DEC-1103 review, R5): a tree's own config, with Chromium behind the
// counter proxy on 127.0.0.1:14623. PROXY_WEB names the tree's web/ folder.
import { defineConfig } from '@playwright/test';

const WEB = process.env.PROXY_WEB!;
const base = (await import(`${WEB}/playwright.config.ts`)).default;
const ws = base.webServer as Record<string, unknown>;
const project = base.projects![0];
export default defineConfig({
  ...base,
  outputDir: '/tmp/dec1071-review/proxy-results',
  reporter: 'list',
  webServer: { ...ws, cwd: WEB } as never,
  projects: [
    {
      ...project,
      use: {
        ...project.use,
        launchOptions: {
          ...project.use!.launchOptions,
          proxy: { server: 'http://127.0.0.1:14623', bypass: '127.0.0.1' },
        },
      },
    },
  ],
});
