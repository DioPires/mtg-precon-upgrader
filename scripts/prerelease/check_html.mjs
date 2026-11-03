// Browser check of DIR/cheat_sheet.html (DEC-1223).
//
//   PLAYWRIGHT_BROWSERS_PATH=... node scripts/prerelease/check_html.mjs \
//     [--set-dir analysis/prerelease/trk] [--shots DIR]
//
// Runs every check three times: system Chrome from disk; WebKit with Playwright's
// iPhone 13 profile from disk; and the same over HTTP, from a static server
// that this script starts on web/public/ (Chrome on an iPhone draws with
// WebKit, and the site serves web/public/prerelease/<set>.html). Uses
// Playwright from web/node_modules (this tree's, or the main checkout's when
// this is a worktree without one). Sends no request to the network: every
// request other than the page itself is refused and counted. Calls
// build_html.py (`uv run python`) for SEARCH_EXAMPLES, CHECK_POOLS and
// pool_summary(), the reference for the Pool view. Prints a summary for each
// run and exits 1 when a check fails. --shots also writes the screenshots with
// WebKit at 390 x 844, light and dark.

import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, statSync } from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..", "..");

const args = process.argv.slice(2);
function arg(name, fallback) {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : fallback;
}
const setDir = path.resolve(root, arg("--set-dir", "analysis/prerelease/trk"));
const shots = arg("--shots", null);
const pagePath = path.join(setDir, "cheat_sheet.html");
const fileUrl = pathToFileURL(pagePath).href;
const setName = path.basename(setDir);

function playwrightPath() {
  const roots = [root];
  try {
    const common = execFileSync("git", ["-C", root, "rev-parse", "--path-format=absolute", "--git-common-dir"], {
      encoding: "utf8",
    }).trim();
    roots.push(path.dirname(common));
  } catch {
    /* not a git checkout: this tree only */
  }
  for (const r of roots) {
    const p = path.join(r, "web", "node_modules", "playwright", "index.mjs");
    if (existsSync(p)) return p;
  }
  throw new Error("Playwright not found in web/node_modules; run `npm ci` in web/");
}
const { chromium, webkit, devices } = await import(pathToFileURL(playwrightPath()).href);

// web/public/ on 127.0.0.1, as the site serves it: /prerelease/<set>.html.
const publicDir = path.join(root, "web", "public");
const server = http.createServer((req, res) => {
  const rel = path.normalize(decodeURIComponent(new URL(req.url, "http://x").pathname)).replace(/^[/\\]+/, "");
  const file = path.join(publicDir, rel);
  if (!file.startsWith(publicDir + path.sep) || !existsSync(file) || statSync(file).isDirectory()) {
    res.writeHead(404);
    res.end();
    return;
  }
  res.writeHead(200, { "content-type": file.endsWith(".html") ? "text/html; charset=utf-8" : "application/octet-stream" });
  res.end(readFileSync(file));
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
const httpUrl = `${origin}/prerelease/${setName}.html`;
const published = path.join(publicDir, "prerelease", `${setName}.html`);

const phone = { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true };
const runs = [
  { name: "Chrome, from disk", type: chromium, launch: { channel: "chrome" }, device: phone, url: fileUrl },
  { name: "WebKit (iPhone 13), from disk", type: webkit, device: devices["iPhone 13"], url: fileUrl },
  { name: "WebKit (iPhone 13), over HTTP", type: webkit, device: devices["iPhone 13"], url: httpUrl },
];

function python(extra, input) {
  return JSON.parse(
    execFileSync("uv", ["run", "python", "scripts/prerelease/build_html.py", "--set-dir", setDir, ...extra], {
      cwd: root,
      encoding: "utf8",
      input,
      stdio: ["pipe", "pipe", "ignore"],
    }),
  );
}
const checkData = python(["--check-data"]);
const grades = JSON.parse(readFileSync(path.join(setDir, "grades.json"), "utf8"));
const total = grades.length;

let run = null; // the run in progress: its browser and counts
function report(ok, line) {
  run.checks++;
  if (!ok) run.failures++;
  console.log(`${ok ? "ok  " : "FAIL"} ${line}`);
}

// A seeded draw, so the 85-card pool is the same on every run.
function mulberry32(seed) {
  return function () {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function drawPool(n, seed) {
  const rand = mulberry32(seed);
  const pool = {};
  for (let i = 0; i < n; i++) {
    const name = grades[Math.floor(rand() * grades.length)].name;
    pool[name] = (pool[name] || 0) + 1;
  }
  return pool;
}

async function newPage(options = {}) {
  const ctx = await run.browser.newContext({ ...run.device, reducedMotion: "reduce", ...options });
  await ctx.route("**/*", (route) => {
    const url = route.request().url();
    if (url.startsWith("file://") || url.startsWith(origin + "/")) return route.continue();
    run.blocked++;
    return route.abort();
  });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => report(false, `page error: ${e.message}`));
  page.on("dialog", (d) => d.accept());
  await page.goto(run.url);
  return page;
}
async function setPool(page, pool) {
  await page.evaluate((p) => localStorage.setItem("prerelease-pool-" + document.documentElement.dataset.set, JSON.stringify(p)), pool);
  await page.reload();
}
// The cards the browser lays out, not the ones marked hidden: a CSS rule could show a hidden card.
async function visibleNames(page) {
  return page.evaluate(() =>
    Array.from(document.querySelectorAll("#list .card")).filter((el) => el.getClientRects().length).map((el) => el.dataset.name),
  );
}
async function shownText(page) {
  return (await page.textContent("#shown")).trim();
}

const pool85 = drawPool(85, 20261106);

async function checks() {
// ------------------------------------------------------------------- layout
console.log("\n# Layout");
for (const width of [360, 390]) {
  for (const scheme of ["light", "dark"]) {
    const page = await newPage({ viewport: { width, height: run.device.viewport.height }, colorScheme: scheme });
    const plain = await page.evaluate(() => [document.documentElement.scrollWidth, innerWidth]);
    // The widest state: the 85-card pool counted, every toggle open, the filters out.
    await setPool(page, pool85);
    await page.evaluate(() => document.querySelectorAll("details").forEach((d) => (d.open = true)));
    await page.click("#ftoggle");
    const wide = await page.evaluate(() => [document.documentElement.scrollWidth, innerWidth]);
    const bar = await page.evaluate(() => {
      const ul = document.querySelector("#bar ul");
      const links = Array.from(document.querySelectorAll("#bar a"));
      return {
        fits: ul.scrollWidth <= ul.clientWidth && links.every((a) => a.scrollWidth <= a.clientWidth),
        narrowest: Math.round(Math.min(...links.map((a) => a.getBoundingClientRect().width))),
      };
    });
    report(
      plain[0] <= plain[1] && wide[0] <= wide[1] && bar.fits && bar.narrowest >= 44,
      `${width} px ${scheme}: scrollWidth ${plain[0]} <= ${plain[1]}; every toggle open and the pool counted: ${wide[0]} <= ${wide[1]}; bar fits: ${bar.fits}, narrowest link ${bar.narrowest} px`,
    );
    if (width === 390) {
      // WCAG AA: 4.5:1 for every piece of text, against the first opaque background behind it.
      const contrast = await page.evaluate(() => {
        function rgb(s) {
          const m = s.match(/rgba?\(([^)]+)\)/);
          if (!m) return null;
          const [r, g, b, a = 1] = m[1].split(/[ ,/]+/).filter(Boolean).map(Number);
          return { r, g, b, a };
        }
        function lum(c) {
          const f = (v) => ((v /= 255) <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
          return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
        }
        function background(el) {
          for (let e = el; e; e = e.parentElement) {
            const c = rgb(getComputedStyle(e).backgroundColor);
            if (c && c.a > 0) return c;
          }
          return rgb(getComputedStyle(document.documentElement).backgroundColor) || { r: 255, g: 255, b: 255, a: 1 };
        }
        let min = 99, worst = "", n = 0;
        const low = [];
        for (const el of document.querySelectorAll("body *")) {
          const own = Array.from(el.childNodes).some((t) => t.nodeType === 3 && t.textContent.trim());
          if (!own || !el.getClientRects().length || el.closest(".vh")) continue;
          const style = getComputedStyle(el);
          if (style.visibility === "hidden") continue;
          const fg = rgb(style.color), bg = background(el);
          const [hi, lo] = [lum(fg), lum(bg)].sort((a, b) => b - a);
          const ratio = (hi + 0.05) / (lo + 0.05);
          n++;
          if (ratio < min) { min = ratio; worst = `${el.tagName.toLowerCase()}.${el.className} "${el.textContent.trim().slice(0, 20)}"`; }
          if (ratio < 4.5) low.push(worst);
        }
        return { min: min.toFixed(2), worst, n, low: low.length };
      });
      report(contrast.low === 0, `${scheme} contrast: ${contrast.n} text elements, lowest ${contrast.min}:1 (${contrast.worst}); under 4.5:1: ${contrast.low}`);
    }
    await page.context().close();
  }
}
{
  const page = await newPage();
  const sizes = await page.evaluate(() => {
    let min = 99, at = "";
    for (const el of document.querySelectorAll("main *")) {
      const own = Array.from(el.childNodes).some((t) => t.nodeType === 3 && t.textContent.trim());
      if (!own || !el.getClientRects().length || el.closest(".ms") || el.closest(".vh")) continue;
      const px = parseFloat(getComputedStyle(el).fontSize);
      if (px < min) { min = px; at = `${el.tagName.toLowerCase()}.${el.className}`; }
    }
    const bar = parseFloat(getComputedStyle(document.querySelector("#bar a")).fontSize);
    return { min, at, bar };
  });
  report(sizes.min >= 16, `text in the sheet: at least ${sizes.min} px (${sizes.at}); mana symbol letters and the bar's labels (${sizes.bar} px) aside`);
  const links = await page.evaluate(() => {
    const out = Array.from(document.querySelectorAll('a[href^="http"]'));
    return { n: out.length, newTab: out.filter((a) => a.target === "_blank" && a.rel === "noopener").length };
  });
  report(links.n === links.newTab, `card links: ${links.n}, opening in a new tab: ${links.newTab}`);

  // Each link of the bar: the heading lands on screen, above the bar, and the bar marks it.
  const bar = [];
  for (const href of await page.$$eval("#bar a", (as) => as.map((a) => a.getAttribute("href")))) {
    await page.click(`#bar a[href="${href}"]`);
    await page.waitForTimeout(100);
    const r = await page.evaluate((h) => {
      const head = document.querySelector(h + " h2");
      const top = head.getBoundingClientRect().top, bottom = head.getBoundingClientRect().bottom;
      const barTop = document.getElementById("bar").getBoundingClientRect().top;
      const marked = document.querySelector("#bar a[aria-current]");
      return { visible: top >= -1 && bottom <= barTop, marked: marked && marked.getAttribute("href") === h };
    }, href);
    bar.push(`${href} ${r.visible && r.marked ? "ok" : `visible ${r.visible} marked ${r.marked}`}`);
  }
  report(bar.every((b) => b.endsWith("ok")), `bar: each heading lands on screen and is marked: ${bar.join(", ")}`);

  // iOS zooms the page when a field under 16 px takes focus; a finger needs 44 x 44 px.
  const q = await page.evaluate(() => parseFloat(getComputedStyle(document.getElementById("q")).fontSize));
  report(q >= 16, `search field font size: ${q} px`);
  await page.click('#bar a[href="#cards"]');
  await page.locator("#list .card").first().locator(".inc").tap(); // the first card shows its −
  await page.click("#ftoggle");
  const targets = await page.evaluate(() =>
    ["#list .ctr button", ".chip", "#q-clear", "#ftoggle", "#freset", "#pool-link", "#bar a", "#archetypes summary", "#clear-pool"].map((sel) => {
      const els = Array.from(document.querySelectorAll(sel)).filter((e) => e.getClientRects().length);
      const rects = els.map((e) => e.getBoundingClientRect());
      return [sel, els.length, Math.round(Math.min(...rects.map((r) => r.width))), Math.round(Math.min(...rects.map((r) => r.height)))];
    }),
  );
  report(
    targets.every(([, n, w, h]) => n && w >= 44 && h >= 44),
    `tap targets at least 44 x 44 px (narrowest x lowest): ${targets.map(([sel, , w, h]) => `${sel} ${w}x${h}`).join("; ")}`,
  );
  await page.context().close();
}

// ------------------------------------------------------------------- search
console.log("\n# Search");
{
  const page = await newPage();
  const mismatched = await page.evaluate(() =>
    Array.from(document.querySelectorAll("#list .card"))
      .filter((el) => window.cheatSheet.norm(el.dataset.name) !== el.dataset.q)
      .map((el) => el.dataset.name),
  );
  report(!mismatched.length, `the page's normalisation equals build_html.py's on all ${total} names${mismatched.length ? ": " + mismatched.join("; ") : ""}`);
  for (const [query, expected] of checkData.search_examples) {
    await page.fill("#q", query);
    const names = await visibleNames(page);
    const ok = JSON.stringify([...names].sort()) === JSON.stringify([...expected].sort()) && (await shownText(page)) === `${names.length} of ${total}`;
    report(ok, `"${query}": ${await shownText(page)}: ${names.join("; ")}`);
  }
  await page.click("#q-clear");
  report((await page.inputValue("#q")) === "" && (await shownText(page)) === `${total} of ${total}`, `the clear button empties the field: ${await shownText(page)}`);
  await page.context().close();
}

// -------------------------------------------------------------------- chips
console.log("\n# Filters");
{
  const page = await newPage();
  const hybrid = (e) => e.colors.length === 2 && /\{[WUBRG]\/[WUBRG]\}/.test(e.mana_cost.split(" // ")[0]);
  const inColour = (e, c) => (e.colors.length === 1 && e.colors[0] === c) || (hybrid(e) && e.colors.includes(c));
  const cases = [
    ["colour W", [["c", "W"]], (e) => inColour(e, "W")],
    ["colour W or U", [["c", "W"], ["c", "U"]], (e) => inColour(e, "W") || inColour(e, "U")],
    ["colour gold", [["c", "gold"]], (e) => e.colors.length >= 2 && !hybrid(e)],
    ["rarity M", [["r", "M"]], (e) => e.rarity === "mythic"],
    ["tag ★", [["t", "★"]], (e) => e.roles.includes("bomb")],
    ["grade 6+", [["g", "6"]], (e) => e.grade >= 6],
    ["colour W and grade 6+", [["c", "W"], ["g", "6"]], (e) => inColour(e, "W") && e.grade >= 6],
    ["search \"enterprise\" and rarity R", [["r", "R"]], (e) => e.rarity === "rare" && /enterprise/i.test(e.name), "enterprise"],
  ];
  await page.click("#ftoggle");
  for (const [label, chips, test, query] of cases) {
    await page.click("#freset");
    await page.fill("#q", query || "");
    for (const [f, v] of chips) await page.click(`.chip[data-f="${f}"][data-v="${v}"]`);
    const shown = await shownText(page);
    const n = (await visibleNames(page)).length;
    const expected = grades.filter(test).length;
    const groupsOk = await page.evaluate(() =>
      Array.from(document.querySelectorAll("#list .grp")).every(
        (g) => !g.getClientRects().length === !Array.from(g.querySelectorAll(".card")).some((c) => c.getClientRects().length),
      ),
    );
    report(shown === `${n} of ${total}` && n === expected && groupsOk, `${label}: shows ${shown} (from grades.json: ${expected}); empty groups hidden: ${groupsOk}`);
  }
  await page.context().close();
}

// ------------------------------------------------------------ no JavaScript
console.log("\n# Without JavaScript");
{
  const page = await newPage({ javaScriptEnabled: false });
  const r = await page.evaluate(() => {
    const vis = (el) => !!el && el.getClientRects().length > 0;
    return {
      sections: ["build", "rules", "removal", "tricks", "archetypes", "cards"].filter((id) => vis(document.getElementById(id))),
      cards: Array.from(document.querySelectorAll("#list .card")).filter(vis).length,
      search: vis(document.getElementById("q")),
      chips: vis(document.getElementById("fpanel")) || vis(document.getElementById("controls")),
      pool: vis(document.getElementById("pool")) || vis(document.querySelector('#bar a[href="#pool"]')),
    };
  });
  report(
    r.sections.length === 6 && r.cards === total && !r.search && !r.chips && !r.pool,
    `sections shown: ${r.sections.length} (${r.sections.join(", ")}); card blocks shown: ${r.cards}; search field shown: ${r.search}; chips shown: ${r.chips}; Pool view shown: ${r.pool}`,
  );
  await page.context().close();
}

// --------------------------------------------------------------- Part B pool
console.log("\n# Pool");
let compared = 0;
const differences = [];
async function compare(page, label, pool) {
  const dom = await page.evaluate(() =>
    Object.fromEntries(Array.from(document.querySelectorAll("#pool [data-num]")).map((el) => [el.dataset.num, el.textContent.trim()])),
  );
  const ref = python(["--pool-summary", "-"], JSON.stringify(pool));
  const keys = new Set([...Object.keys(dom), ...Object.keys(ref)]);
  let diff = 0;
  for (const k of keys) {
    compared++;
    if (dom[k] !== ref[k]) {
      diff++;
      differences.push(`${label} ${k}: page ${dom[k]}, pool_summary ${ref[k]}`);
    }
  }
  const top = [1, 2, 3].map((i) => `${dom[`rank.${i}.pair`]} ${dom[`rank.${i}.score`]}`).join(", ");
  console.log(`     ${label}: ${dom.cards} cards, ${keys.size} numbers, ${diff} differ; top three ${top}`);
}
{
  const page = await newPage();
  const five = ["Captain Jean-Luc Picard", "Constable Odo", "Borg Cube", "Crystalline Entity", "Khaaaaaaaaaaaannn!"];
  await page.click("#q");
  for (const name of five) {
    await page.click("#q-clear");
    await page.fill("#q", name.split(/[ ,!]/)[0].slice(0, 5));
    const i = await page.evaluate((n) => Array.from(document.querySelectorAll("#list .card")).findIndex((el) => el.dataset.name === n), name);
    await page.locator("#list .card").nth(i).locator(".inc").tap();
  }
  const focus = await page.evaluate(() => document.activeElement && document.activeElement.id);
  report(focus === "q", `after a tap on +, the focus stays in the search field: ${focus === "q"}`);
  // Two more taps on one card, then one on its −: two copies.
  const odo = page.locator("#list .card", { has: page.locator('a:text-is("Constable Odo")') });
  await page.fill("#q", "odo");
  await odo.locator(".inc").tap();
  await odo.locator(".dec").tap();
  await odo.locator(".inc").tap();
  const stored = await page.evaluate(() => JSON.parse(localStorage.getItem("prerelease-pool-" + document.documentElement.dataset.set)));
  const want = Object.fromEntries(five.map((n) => [n, n === "Constable Odo" ? 2 : 1]));
  report(JSON.stringify(stored, Object.keys(want).sort()) === JSON.stringify(want, Object.keys(want).sort()), `+ tapped on five cards (Constable Odo twice): stored ${JSON.stringify(stored)}`);
  await page.click("#q-clear");
  await page.click("#ftoggle");
  await page.click('.chip[data-f="p"]');
  report((await visibleNames(page)).length === 5, `chip "In my pool": shows ${await shownText(page)}`);
  await page.click('#bar a[href="#pool"]');
  await compare(page, "five tapped", stored);

  for (const [label, pool] of [
    ["sample (every kind of card)", checkData.pools.sample],
    ["ties (★, ✚, ✕, pair order)", checkData.pools.ties],
    ["85 cards, seed 20261106", pool85],
  ]) {
    await setPool(page, pool);
    await compare(page, label, pool);
  }
  report(!differences.length, `pool check: ${compared} numbers, ${differences.length} differ`);
  for (const d of differences) console.log("     " + d);

  // "Clear pool" asks first: refused, nothing changes; accepted, the pool is empty.
  page.removeAllListeners("dialog");
  page.once("dialog", (d) => d.dismiss());
  await page.click("#clear-pool");
  const kept = await page.textContent('[data-num="cards"]');
  page.once("dialog", (d) => d.accept());
  await page.click("#clear-pool");
  const cleared = await page.textContent('[data-num="cards"]');
  report(kept === "85" && cleared === "0", `Clear pool asks first: refused keeps ${kept} cards, accepted leaves ${cleared}`);
  await page.context().close();
}
}

console.log(`page: ${pagePath} (${readFileSync(pagePath).length} bytes)`);
const copyOk = existsSync(published) && readFileSync(published).equals(readFileSync(pagePath));
console.log(`${copyOk ? "ok  " : "FAIL"} the copy that the HTTP run serves, ${path.relative(root, published)}, equals the page: ${copyOk}`);
for (const r of runs) {
  run = Object.assign(r, { checks: 0, failures: 0, blocked: 0 });
  console.log(`\n## ${r.name}: ${r.url}`);
  r.browser = await r.type.launch(r.launch);
  await checks();
  report(r.blocked === 0, `network requests refused: ${r.blocked}`);
  await r.browser.close();
}

// --------------------------------------------------------------- screenshots
if (shots) {
  // WebKit, the engine of Chrome on an iPhone, at 390 x 844.
  mkdirSync(shots, { recursive: true });
  run = { ...runs[1], checks: 0, failures: 0, blocked: 0 };
  run.browser = await webkit.launch();
  for (const scheme of ["light", "dark"]) {
    const page = await newPage({ colorScheme: scheme, viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
    const at = async (selector) => {
      await page.evaluate((s) => document.querySelector(s).scrollIntoView(), selector);
      await page.waitForTimeout(100);
    };
    await page.screenshot({ path: path.join(shots, `1-top-${scheme}.png`) });
    await at("#build");
    await page.screenshot({ path: path.join(shots, `2-build-${scheme}.png`) });
    await at("#removal");
    await page.screenshot({ path: path.join(shots, `3-removal-${scheme}.png`) });
    await page.evaluate(() => document.querySelectorAll("#archetypes .arch")[0].querySelectorAll("details").forEach((d) => (d.open = true)));
    await at("#archetypes .arch");
    await page.screenshot({ path: path.join(shots, `4-archetypes-${scheme}.png`) });
    await at("#cards");
    await page.fill("#q", "spock");
    await at("#cards");
    await page.screenshot({ path: path.join(shots, `5-cards-spock-${scheme}.png`) });
    await setPool(page, pool85);
    await at("#pool");
    await page.screenshot({ path: path.join(shots, `6-pool-85-${scheme}.png`) });
    await page.context().close();
  }
  await run.browser.close();
  console.log(`\nscreenshots (WebKit, 390 x 844): ${shots}`);
}
server.close();

console.log("\n# Summary");
for (const r of runs) console.log(`${r.failures ? "FAIL" : "ok  "} ${r.name}: ${r.checks} checks, ${r.failures} failed`);
const failed = runs.reduce((n, r) => n + r.failures, 0) + (copyOk ? 0 : 1);
console.log(failed ? `${failed} check(s) failed` : "all checks passed");
process.exit(failed ? 1 : 0);
