# Applies one DEC-1110 reviewer mutant to the review tree: python3 apply_k.py K<n>|A<n>
# Each entry: (file under web/, old text, new text). The old text must occur once.
import sys
W = '/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/wt-dec1110-review/web/'
L = 'src/data/scryfallLimiter.ts'
C = 'src/data/cardCache.ts'
T = 'tests/support/test.ts'
M = {
  # The brief's seed mutants.
  'K1': (L, "    if (prev && startedAt < prev.until) return;\n", ""),
  'K2': (L, "    if (prev && startedAt >= prev.until) writeStop(null);", "    if (prev) writeStop(null);"),
  'K3': (L, "    if (stop && inFlight > 0) return 'busy';\n", ""),
  'K4': (L, "      return { until: Math.min(stop.until, now() + stop.ms), ms: stop.ms };", "      return { until: stop.until, ms: stop.ms };"),
  'K5': (L, "    return Math.min(last, now());", "    return last;"),
  'K6': (L, "    if (job.signal?.aborted) return finish(job, { error: error ?? abortReason(job.signal) });\n", ""),
  'K7': (L, "          await withLock(async () => {", "          await (async (task: () => Promise<void>) => task())(async () => {"),
  'K8': (L, "      resolveStorage()?.setItem(LAST_START_KEY, String(at));", "      // K8: no stored last start"),
  'K9': ('src/data/cardEntry.ts', "`$${amount.toFixed(2)}`", "`$${amount}`"),
  'K10': (C, "      if (!options.first) return;", "      return;"),
  'K11': (C, "    writePersisted(key, marked);\n", ""),
  'K12': (C, "        if (refreshed?.refreshedAt !== undefined && now() - refreshed.refreshedAt <= TTL_MS) {", "        if (false) {"),
  'K13a': ('src/components/molecules/CardTile.tsx', "              cardCache.imageFailed(card.n);\n", ""),
  'K13b': ('src/components/molecules/GV1CommanderArt.tsx', "              cardCache.imageFailed(name);\n", ""),
  'K13c': ('src/components/global/GV1CardHoverLayer.tsx', "              cardCache.imageFailed(shownName);\n", ""),
  # Variants of K1 and K2 that compile (tsc's noUnusedParameters stops K1 and K2 in the build).
  'K1v': (L, "    if (prev && startedAt < prev.until) return;\n", "    void startedAt;\n"),
  'K2v': (L, "    if (prev && startedAt >= prev.until) writeStop(null);", "    void startedAt;\n    if (prev) writeStop(null);"),
  'K13bv': ('src/components/molecules/GV1CommanderArt.tsx', "              cardCache.imageFailed(name);\n", "              void cardCache;\n"),
  'A1v': ('src/routes/ComboLab.tsx', " onError={() => cardCache.imageFailed(name)} />", " onError={() => void cardCache} />"),
  'A2v': (L, "        if (event.key === STOP_KEY) notifyListeners();\n", "        void event;\n"),
  'A8v': ('src/components/molecules/GV1CommanderArt.tsx', " || (src && src === failedSrc)", " || (src && src === failedSrc && src === '')"),
  # The reviewer's own mutants, on lines that the pull request adds or rewrites.
  'A1': ('src/routes/ComboLab.tsx', " onError={() => cardCache.imageFailed(name)} />", " />"),
  'A2': (L, "        if (event.key === STOP_KEY) notifyListeners();\n", ""),
  'A3': (L, "              if (bucket.jobs.length > 0) void drain(bucket);\n", ""),
  'A4': (C, "    if (seeded.has(item.key) && current?.status === 'loaded') return;\n", ""),
  'A5': (C, "    if (!seeded.has(key)) return;\n", ""),
  'A6': ('src/data/loader.ts', "      seedCards(cached);\n", ""),
  'A7': ('src/data/loader.ts', "      seedCards(metadata);\n", ""),
  'A8': ('src/components/molecules/GV1CommanderArt.tsx', " || (src && src === failedSrc)", ""),
  'A9': ('src/components/global/GV1CardHoverLayer.tsx', "              imgCache[imgSrc] = 'error';\n", ""),
  'A10': ('src/components/molecules/CardTile.tsx', "const hasImg = !!imgSrc && imgSrc !== failedSrc;", "const hasImg = !!imgSrc;"),
  'A11': (L, "        stopInMemoryOnly = true;\n", ""),
  'A12': (C, "    if (item.refresh) return;\n", ""),
  'A13': ('src/lib/pricesDate.ts', "`${date.getUTCDate()} ${MONTHS[date.getUTCMonth()]} ${date.getUTCFullYear()}`", "`${date.getDate()} ${MONTHS[date.getMonth()]} ${date.getFullYear()}`"),
  'A14': ('src/data/cardEntry.ts', "    mana_cost: (meta.mana_cost ?? '').split(' // ')[0],", "    mana_cost: (meta.mana_cost ?? '').split(' // ').pop(),"),
  'A15': (L, "    if (job.signal?.aborted) return finish(job, { error: abortReason(job.signal) });\n    if (job.url === null) {", "    if (job.url === null) {"),
  # The e2e harness.
  'H1': (T, "              if (rateClock === 'real') stamp(context, Date.now());", "              stamp(context, Date.now());"),
  'H2': (T, "        report?.(Date.now())?.catch(() => undefined);", "        void report;"),
  'H3': (T, "      if (peak > RATE_LIMIT) {", "      if (false) {"),
  'H4': (T, "        if (cards === 'none') {\n          await context.route(\n            (url) => url.pathname === '/data/card-metadata.json',",
         "        if (false) {\n          await context.route(\n            (url) => url.pathname === '/data/card-metadata.json',"),
  'H5': (T, "const RATE_LIMIT = 2;", "const RATE_LIMIT = 3;"),
  'H6': (T, "    while (sorted[i] - sorted[j] >= windowMs) j += 1;", "    while (sorted[i] - sorted[j] > windowMs) j += 1;"),
  'H7': (T, "      if (/^https:\\/\\/api\\.scryfall\\.com\\/cards\\/(named|collection)\\?/.test(url)) {", "      if (/^https:\\/\\/api\\.scryfall\\.com\\/cards\\/(named)\\?/.test(url)) {"),
}
name = sys.argv[1]
f, old, new = M[name]
s = open(W + f).read()
assert s.count(old) == 1, (name, s.count(old))
open(W + f, 'w').write(s.replace(old, new))
print(name, 'applied to', f)
