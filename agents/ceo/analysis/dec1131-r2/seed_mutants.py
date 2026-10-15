# DEC-1149 item 5b: apply one seed mutant (S1-S12) or one reviewer mutant (R*) to the tree named by argv[1].
# Each edit must match once.
import sys
TREE = sys.argv[1]
NAME = sys.argv[2]
L = 'web/src/data/scryfallLimiter.ts'
C = 'web/src/data/cardCache.ts'
S = 'web/src/components/organisms/Shopping.tsx'
P = 'web/src/components/molecules/PricePausedLine.tsx'
LD = 'web/src/data/loader.ts'
ST = 'web/tests/support/scryfall.ts'
T = 'web/tests/support/test.ts'
MUTANTS = {
  # ── The seeds of the brief ──
  'S1': [(C, "const rank = (w: Wanted) => (w.first ? 0 : w.lookup ? 1 : 2);", "const rank = (w: Wanted) => (w.first ? 0 : w.lookup ? 2 : 1);")],
  'S2': [(C, "      const id = normalizeName(identifier);", "      const id = wanted.key;")],
  'S3': [(C, "      for (const key of nameKeys(card.name)) if (!cards.has(key)) cards.set(key, card);",
             "      for (const key of [normalizeName(card.name)]) if (!cards.has(key)) cards.set(key, card);")],
  'S4': [(C, "overlay.priceAsOf !== undefined && !fileIsNewer) {", "overlay.priceAsOf !== undefined && (true || !fileIsNewer)) {")],
  'S5': [(C, "        if (overlayIsLive(overlay)) overlays.set(key, overlay);", "        if (overlayIsLive(overlay) && false) overlays.set(key, overlay);")],
  'S6': [(C, "    const overlay: Overlay = { ...picturePart(overlays.get(wanted.key)), fetchedAt: t, priceCheckedAt: t };",
             "    const overlay: Overlay = { ...picturePart(overlays.get(wanted.key)), fetchedAt: t };"),
         (C, "    if (price) {\n      overlay.price = price;", "    if (price) {\n      overlay.priceCheckedAt = t;\n      overlay.price = price;")],
  'S7': [(S, "  const waiting = buy.some((c) => cardCache.pricePending(c.name));", "  const waiting = false as boolean;")],
  'S8': [(P, "  useEffect(() => {\n    if (until === null) return;\n    const id = window.setTimeout(() => rerender((n) => n + 1), Math.max(0, until - Date.now()) + 1);\n    return () => window.clearTimeout(id);\n  }, [until]);\n", "")],
  'S9': [(L, "    return new URL(url).origin === SCRYFALL_API;", "    return url.length >= 0;")],
  'S10': [(L, "    signal?.addEventListener('abort', forward, { once: true });\n", "    void forward;\n")],
  'S11': [(L, "      bucket.jobs.unshift(job);\n      fail(noted);", "      bucket.jobs.push(job);\n      fail(noted);")],
  'S12': [(LD, "      seedCards(data, meta?.prices_as_of);", "      seedCards(data, meta ? undefined : undefined);")],

  # ── The reviewer's own mutants (lines that the pull request adds or rewrites) ──
  # R1: a refresh does not adopt the price that another tab stored while this one waited.
  'R1': [(C, "      if (stored && isLive(stored.priceCheckedAt) && !isLive(overlays.get(wanted.key)?.priceCheckedAt)) {",
             "      if (stored && isLive(stored.priceCheckedAt) && !isLive(overlays.get(wanted.key)?.priceCheckedAt) && false) {")],
  # R2: a price refresh is not dropped when the overlay is already live (another tab or this one refreshed).
  'R2': [(C, "      if (isLive(overlays.get(wanted.key)?.priceCheckedAt)) wanted.price = false;", "      void 0;")],
  # R3: the file's price wins only when strictly newer (boundary of compose()).
  'R3': [(C, "file.priceAsOf >= overlay.priceAsOf;", "file.priceAsOf > overlay.priceAsOf;")],
  # R4: imageFailed() drops the stored price part.
  'R4': [(C, "    writeOverlay(key, { ...pricePart(overlays.get(key)), fetchedAt: t, refreshedAt: t });",
             "    writeOverlay(key, { fetchedAt: t, refreshedAt: t });")],
  # R5: settlePrice() drops the stored picture part.
  'R5': [(C, "    const overlay: Overlay = { ...picturePart(overlays.get(wanted.key)), fetchedAt: t, priceCheckedAt: t };",
             "    const overlay: Overlay = { fetchedAt: t, priceCheckedAt: t };")],
  # R6: settlePictures() drops the stored price part.
  'R6': [(C, "      ...pricePart(overlays.get(wanted.key)),\n      refreshedAt: overlays.get(wanted.key)?.refreshedAt ?? t,",
             "      refreshedAt: overlays.get(wanted.key)?.refreshedAt ?? t,")],
  # R7: the cap stops the batch at the first name that does not fit (a later name with a front face already in the batch waits).
  'R7': [(C, "        if (identifiers.size >= BATCH_MAX) continue;", "        if (identifiers.size >= BATCH_MAX) break;")],
  # R8: the seed that arrives while a lookup is out is overwritten by the answer.
  'R8': [(C, "    if (fileEntries.has(key) && cache.get(key)?.status === 'loaded') return;\n", "")],
  # R9: the held summary holds also after the selection changes.
  'R9': [(S, "  if (waiting && held.current?.rows === rows) return held.current.summary;",
             "  if (waiting && held.current) return held.current.summary;")],
  # R10: the footer shows the newest date, not the oldest.
  'R10': [(S, "(oldest === null || e.priceAsOf < oldest)", "(oldest === null || e.priceAsOf > oldest)")],
  # R11: the stop line shows when no row waits.
  'R11': [(P, "  if (until === null || !waiting) return null;", "  void waiting;\n  if (until === null) return null;")],
  # R12: the stop line counts only the buy rows, not the own rows.
  'R12': [(S, "  const waitingForPrice = [...buy, ...own].some((c) => cardCache.pricePending(c.name));",
              "  const waitingForPrice = buy.some((c) => cardCache.pricePending(c.name));")],
  # R13: a PR #38 stop record (no number) reads with an undefined number.
  'R13': [(L, "      const stop: Stop = { until: parsed.until, ms: parsed.ms, n: typeof parsed.n === 'number' ? parsed.n : 0 };",
              "      const stop: Stop = { until: parsed.until, ms: parsed.ms, n: parsed.n as number };")],
  # R14: an empty stored card-metadata.json counts as a file.
  'R14': [(LD, "      const cached = stored && Object.keys(stored).length > 0 ? stored : null;", "      const cached = stored;")],
  # R15: a stored file is written again on each cold load (its hour starts again).
  'R15': [(LD, "      if (!cached) writePersisted('card-metadata', data);", "      writePersisted('card-metadata', data);")],
  # R16: the meta file's failure is kept: the next load does not ask again.
  'R16': [(LD, "    metaPromise ??= fetchJson<RawCardMetadataMeta>('/data/card-metadata.meta.json').catch(() => {\n      metaPromise = null;\n      return null;\n    });",
              "    metaPromise ??= fetchJson<RawCardMetadataMeta>('/data/card-metadata.meta.json').catch(() => null);")],
  # R17: the stub matches a full `//` name too.
  'R17': [(ST, "    const match = name.includes('//') ? undefined : byIdentifier.get(normalizeName(name));",
               "    const match = byIdentifier.get(normalizeName(name)) ?? (name.includes('//') ? byIdentifier.get(normalizeName(name.split(' // ')[0])) : undefined);")],
  # R18: the stub gives data in reverse order (the control of item 5c: must survive).
  'R18': [(ST, "  return { ...json('collection', 200, { object: 'list', not_found, data }), notFound: not_found.map((n) => n.name) };",
               "  data.reverse();\n  return { ...json('collection', 200, { object: 'list', not_found, data }), notFound: not_found.map((n) => n.name) };")],
  # R19: the real clock's stamp ignores /cards/collection (only /cards/named counts).
  'R19': [(T, "            if (url.hostname === 'api.scryfall.com' && BUCKET_ONE.test(url.pathname)) stamp(context, Date.now());",
              "            if (url.hostname === 'api.scryfall.com' && url.pathname === '/cards/named') stamp(context, Date.now());")],
  # R20: the timeout timer is 60 s, not 20 s.
  'R20': [(L, "export const REQUEST_TIMEOUT_MS = 20_000;", "export const REQUEST_TIMEOUT_MS = 60_000;")],
  # R21: the refresh asks also when a refresh was tried in the last 24 h.
  'R21': [(C, "    if (isLive(entry.priceCheckedAt)) return;\n    if (pricePending(name)) return;", "    if (pricePending(name)) return;")],
  # R22: the tile's refresh effect does not run again when the tile's card changes.
  'R22': [('web/src/components/molecules/CardTile.tsx', "  }, [card.n, highlightPrice]);", "    // eslint-disable-next-line react-hooks/exhaustive-deps\n  }, []);")],
  # Variants of R1 and R5 that compile (tsc stops R1 on the narrowing, R5 on an unused function).
  'R1v': [(C, "        overlays.set(wanted.key, stored);\n        recompose(wanted.key);\n", "        void stored;\n")],
  'R5v': [(C, "    const overlay: Overlay = { ...picturePart(overlays.get(wanted.key)), fetchedAt: t, priceCheckedAt: t };",
              "    void picturePart;\n    const overlay: Overlay = { fetchedAt: t, priceCheckedAt: t };")],
  # ── Item 9: my PR #38 kill mutants, written on the head's code ──
  'K1': [(L, "    if (prev && prev.n !== noted) return;\n", "    void noted;\n")],
  'K2': [(L, "    if (prev && prev.n === noted) writeStop(null);", "    void noted;\n    if (prev) writeStop(null);")],
  'K10': [(C, "    if (wanted?.lookup && !options.first) return;", "    if (wanted?.lookup) return;")],
  'A4': [(C, "    if (fileEntries.has(key) && cache.get(key)?.status === 'loaded') return;\n", "")],
  'A11': [(L, "        stopInMemoryOnly = true;\n", "")],
  'K13b': [('web/src/components/molecules/GV1CommanderArt.tsx', "              cardCache.imageFailed(name);\n", "              void cardCache;\n")],
  'K13c': [('web/src/components/global/GV1CardHoverLayer.tsx', "              cardCache.imageFailed(shownName);\n", "              void cardCache;\n")],
  'A1': [('web/src/routes/ComboLab.tsx', " onError={() => cardCache.imageFailed(name)} />", " onError={() => void cardCache} />")],
}
for path, old, new in MUTANTS[NAME]:
    full = f'{TREE}/{path}'
    text = open(full).read()
    count = text.count(old)
    if count != 1:
        sys.exit(f'{NAME}: {path}: the edit matches {count} times')
    open(full, 'w').write(text.replace(old, new))
    print(f'{NAME}: edited {path}')
