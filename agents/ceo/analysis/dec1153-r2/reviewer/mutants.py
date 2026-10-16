#!/usr/bin/env python3
"""DEC-1153 mutant runner. Applies one mutant at a time to the tree, runs the
relevant vitest files, records the failing cases, and restores the file with
`git checkout`. Run from wt-dec1170-mut/web. Writes /tmp/dec1170-review/mutants.jsonl (DEC-1170 copy)."""
import json
import os
import subprocess
import sys

WEB = os.getcwd()
OUT = '/tmp/dec1170-review/mutants.jsonl'
FILES = [
    'src/__tests__/data',
    'src/__tests__/components/Shopping.test.tsx',
    'src/__tests__/dec1149',
    'src/__tests__/components/dec1149',
]
CC = 'src/data/cardCache.ts'
LIM = 'src/data/scryfallLimiter.ts'
LD = 'src/data/loader.ts'

MUTANTS = [
    # Part C: cardCache.ts takeBatch
    ('C1', CC, 'if (!identifier) {', 'if (false) {'),
    ('C2', CC, """      if (!identifier) {
        queue.splice(queue.indexOf(wanted), 1);
        queued.delete(wanted.key);""", """      if (!identifier) {
        queued.delete(wanted.key);"""),
    ('C3', CC, """        queue.splice(queue.indexOf(wanted), 1);
        queued.delete(wanted.key);
        settleName(wanted, null, true, 200, now());""", """        queue.splice(queue.indexOf(wanted), 1);
        settleName(wanted, null, true, 200, now());"""),
    ('C4', CC, '        settleName(wanted, null, true, 200, now());\n', ''),
    ('C5', CC, 'settleName(wanted, null, true, 200, now());', 'settleName(wanted, null, false, 200, now());'),
    ('C6', CC, """        settleName(wanted, null, true, 200, now());
        continue;""", """        settleName(wanted, null, true, 200, now());"""),
    # cardCache.ts settle()/settleName (rewritten lines)
    ('C7', CC, 'answer ? cardFor(cards, wanted.name) : null, answer !== null, status, t)',
     'answer ? cardFor(cards, wanted.name) : null, true, status, t)'),
    ('C8', CC, 'settleName(wanted, answer ? cardFor(cards, wanted.name) : null,', 'settleName(wanted, null,'),
    ('C9', CC, '    if (wanted.lookup) settleLookup(wanted, card, answered, status, t);', '    if (false) settleLookup(wanted, card, answered, status, t);'),
    ('C10', CC, '    if (wanted.price) settlePrice(wanted, card, t);', '    if (true) settlePrice(wanted, card, t);'),
    ('C11', CC, '    if (wanted.pictures) settlePictures(wanted, card, t);', '    if (true) settlePictures(wanted, card, t);'),
    # cardCache.ts pump: the settle callback
    ('C12', CC, "{ settle: ({ response }) => settle(taken.batch, response) },", '{},'),
    # Part B: scryfallLimiter.ts
    ('L1', LIM, 'await settledOrAfter(settling, deadline - monotonic());', 'await settledOrAfter(settling, REQUEST_TIMEOUT_MS);'),
    ('L2', LIM, 'if (!job.settle) return finish(job, { sent });', 'if (true) return finish(job, { sent });'),
    ('L3', LIM, 'const settling = (async () => job.settle!(sent))();', 'const settling = Promise.resolve();'),
    ('L4', LIM, '(error) => finish(job, { error }));', '() => finish(job, { sent }));'),
    ('L5', LIM, 'settling.then(() => finish(job, { sent }),', 'settling.then(() => finish(job, { sent: null }),'),
    ('L6', LIM, 'await settledOrAfter(settling, deadline - monotonic());', 'void settledOrAfter(settling, deadline - monotonic());'),
    ('L7', LIM, '      timer = setTimeout(resolve, ms);\n', ''),
    ('L8', LIM, 'work.then(() => resolve(), () => resolve());', 'work.then(() => resolve());'),
    ('L9', LIM, '}).finally(() => clearTimeout(timer));', '});'),
    ('L10', LIM, '        settle: options.settle,\n', ''),
    ('L12', LIM, 'const sent = { url: request.url, response };', "const sent = { url: '', response };"),
    ('L11', LIM, 'const deadline = monotonic() + REQUEST_TIMEOUT_MS;', 'const deadline = monotonic() + 2 * REQUEST_TIMEOUT_MS;'),
    # Part A: loader.ts
    ('D1', LD, '      if (pricesAsOf !== undefined) env.pricesAsOf = pricesAsOf;\n', ''),
    ('D2', LD, "if (typeof stored?.pricesAsOf === 'string' && stored.payload &&", 'if (stored && stored.payload &&'),
    ('D3', LD, "if (typeof stored?.pricesAsOf === 'string' && stored.payload &&", "if (typeof stored?.pricesAsOf === 'string' &&"),
    ('D4', LD, 'Object.keys(stored.payload).length > 0) {', 'Object.keys(stored.payload).length >= 0) {'),
    ('D5', LD, '        memCardMetadata = stored.payload;\n', ''),
    ('D6', LD, '        memCardMetadataMeta = { prices_as_of: stored.pricesAsOf };\n', ''),
    ('D7', LD, 'seedCards(stored.payload, stored.pricesAsOf);', 'seedCards(stored.payload, undefined);'),
    ('D8', LD, '        return stored.payload;\n', ''),
    ('D9', LD, "fetchJson<RawCardMetadataMeta>('/data/card-metadata.meta.json').catch(() => null),",
     "fetchJson<RawCardMetadataMeta>('/data/card-metadata.meta.json'),"),
    ('D10', LD, '      memCardMetadataMeta = meta;\n', ''),
    ('D11', LD, "if (typeof meta?.prices_as_of === 'string') writePersisted('card-metadata', data, meta.prices_as_of);",
     "writePersisted('card-metadata', data, meta?.prices_as_of);"),
    ('D12', LD, """    try {
      await loadCardMetadata();
    } catch {
      return null;
    }
    return memCardMetadataMeta;""", """    await loadCardMetadata();
    return memCardMetadataMeta;"""),
    ('D13', LD, """    try {
      await loadCardMetadata();
    } catch {
      return null;
    }
    return memCardMetadataMeta;""", """    return memCardMetadataMeta;"""),
    ('D14', LD, """    memCardMetadata = null;
    memCardMetadataMeta = null;""", """    memCardMetadata = null;"""),
    ('D15', LD, 'return readEnvelope<T>(key)?.payload ?? null;', 'return (readEnvelope<T>(key) as T | null) ?? null;'),
    ('D16', LD, '      return env;\n    } catch {', '      return { ...env, pricesAsOf: undefined };\n    } catch {'),
]

MUTANTS += [
    # DEC-1170 reviewer's own mutants (U-*). loader.ts
    ('U-D1', LD, "if (typeof meta?.prices_as_of === 'string') writePersisted(", "if (meta?.prices_as_of) writePersisted("),
    ('U-D2', LD, "if (typeof stored?.pricesAsOf === 'string' && stored.payload &&", "if (stored?.pricesAsOf && stored.payload &&"),
    ('U-D6', LD, 'if (pricesAsOf !== undefined) env.pricesAsOf = pricesAsOf;', 'if (pricesAsOf) env.pricesAsOf = pricesAsOf;'),
    ('U-D7', LD, 'if (pricesAsOf !== undefined) env.pricesAsOf = pricesAsOf;', 'if (true) env.pricesAsOf = pricesAsOf;'),
    ('U-D10', LD, 'Object.keys(stored.payload).length > 0) {', 'Object.keys(stored.payload).length > 1) {'),
    ('U-D11', LD, "        fetchJson<RawCardMetadata>('/data/card-metadata.json'),\n", "        fetchJson<RawCardMetadata>('/data/card-metadata.json').catch(() => null),\n"),
    ('U-D12', LD, "writePersisted('card-metadata', data, meta.prices_as_of);", "writePersisted('card-metadata', data);"),
    ('U-D13', LD, """    } catch {
      return null;
    }
    return memCardMetadataMeta;""", """    } catch {
      return memCardMetadataMeta;
    }
    return memCardMetadataMeta;"""),
    ('U-D15', LD, "        memCardMetadataMeta = { prices_as_of: stored.pricesAsOf };\n", "        memCardMetadataMeta = { prices_as_of: OLD_PLACEHOLDER };\n".replace('OLD_PLACEHOLDER', "'2000-01-01T00:00:00Z'")),
    # scryfallLimiter.ts
    ('U-L1', LIM, """    const deadline = monotonic() + REQUEST_TIMEOUT_MS;
    inFlight += 1;
    const { response, error, timedOut } = await fetchWithTimeout(fetchImpl, request, job.signal);""", """    inFlight += 1;
    const { response, error, timedOut } = await fetchWithTimeout(fetchImpl, request, job.signal);
    const deadline = monotonic() + REQUEST_TIMEOUT_MS;"""),
    ('U-L2', LIM, 'const deadline = monotonic() + REQUEST_TIMEOUT_MS;', 'const deadline = monotonic() + REQUEST_TIMEOUT_MS + 1;'),
    ('U-L3', LIM, 'const deadline = monotonic() + REQUEST_TIMEOUT_MS;', 'const deadline = monotonic() + REQUEST_TIMEOUT_MS - 1;'),
    ('U-L4', LIM, 'const settling = (async () => job.settle!(sent))();', 'const settling = Promise.resolve(job.settle!(sent));'),
    ('U-L5', LIM, 'settling.then(() => finish(job, { sent }), (error) => finish(job, { error }));',
     'finish(job, { sent });\n    settling.then(() => undefined, (error) => finish(job, { error }));'),
    ('U-L7', LIM, 'timer = setTimeout(resolve, ms);', 'timer = setTimeout(resolve, 0);'),
    ('U-L20', LIM, """        settle: options.settle,
        done: false,""", """        settle: options.settle,
        done: true,"""),
    ('U-L21', LIM, """        signal: options.signal,
        settle: options.settle,""", """        signal: undefined,
        settle: options.settle,"""),
    ('U-L22', LIM, """        pick,
        request: null,""", """        pick,
        request: { url: COLLECTION_URL },"""),
    # cardCache.ts
    ('U-C1', CC, 'settleName(wanted, null, true, 200, now());', 'settleName(wanted, null, true, 200, 0);'),
    ('U-C2', CC, 'settleName(wanted, null, true, 200, now());', 'settleName(wanted, null, true, 0, now());'),
    ('U-C3', CC, 'answer ? cardFor(cards, wanted.name) : null, answer !== null, status, t);', 'answer ? cardFor(cards, wanted.name) : null, answer !== null, 200, t);'),
    ('U-C6', CC, '    if (wanted.price) settlePrice(wanted, card, t);', '    if (wanted.price) settlePrice(wanted, null, t);'),
    ('U-C7', CC, '    if (wanted.pictures) settlePictures(wanted, card, t);', '    if (wanted.pictures) settlePictures(wanted, null, t);'),
    ('U-C8', CC, '{ settle: ({ response }) => settle(taken.batch, response) },', '{ settle: ({ response }) => void settle(taken.batch, response) },'),
    ('U-C10', CC, 'return batch.length > 0 ? collectionRequest(identifiers) : null;', 'return batch.length >= 0 ? collectionRequest(identifiers) : null;'),
    ('U-C11', CC, '                taken.batch = batch;\n', ''),
]


def run(ident, path, old, new):
    src = open(path).read()
    if src.count(old) != 1:
        return {'id': ident, 'error': f'pattern found {src.count(old)} times'}
    open(path, 'w').write(src.replace(old, new))
    report = f'/tmp/dec1170-review/mut/mut-{ident}.json'
    if os.path.exists(report):
        os.remove(report)
    try:
        proc = subprocess.run(
            ['npx', 'vitest', 'run', *FILES, '--reporter=json', f'--outputFile={report}'],
            capture_output=True, text=True, timeout=120,
        )
        hung = False
    except subprocess.TimeoutExpired:
        hung = True
    finally:
        subprocess.run(['git', 'checkout', '--', path], check=True)
    if hung:
        return {'id': ident, 'file': path, 'killed': True, 'how': 'hang (timeout 120 s)', 'cases': []}
    try:
        data = json.load(open(report))
    except Exception:
        return {'id': ident, 'file': path, 'killed': proc.returncode != 0, 'how': 'no report', 'tail': proc.stdout[-800:] + proc.stderr[-800:]}
    failed = []
    for f in data.get('testResults', []):
        for a in f.get('assertionResults', []):
            if a.get('status') == 'failed':
                failed.append(a.get('fullName'))
        if f.get('status') == 'failed' and not f.get('assertionResults'):
            failed.append(f"{f.get('name')}: {f.get('message', '')[:200]}")
    return {'id': ident, 'file': path, 'killed': len(failed) > 0, 'failed': len(failed), 'cases': failed[:6]}


only = set(sys.argv[1:])
with open(OUT, 'a') as out:
    for ident, path, old, new in MUTANTS:
        if only and ident not in only:
            continue
        res = run(ident, path, old, new)
        out.write(json.dumps(res) + '\n')
        out.flush()
        print(json.dumps(res)[:400], flush=True)
