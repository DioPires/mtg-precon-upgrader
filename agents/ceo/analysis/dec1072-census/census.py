import json, sys, re, os, collections
hits = [l.strip() for l in open(sys.argv[1]) if l.strip()]
pat = re.compile(r'curl\b[^\n|;&]*api\.scryfall\.com|api\.scryfall\.com[^\n]*\|\s*curl')
rows = []
for f in hits:
    agent = f.split('/')[-2]; run = os.path.basename(f)[:8]
    buf = []
    first_ts = None
    for line in open(f, errors='replace'):
        try: rec = json.loads(line)
        except Exception: continue
        first_ts = first_ts or rec.get('ts')
        if rec.get('stream') == 'stdout': buf.append(rec.get('chunk', ''))
    text = ''.join(buf)
    for sl in text.split('\n'):
        sl = sl.strip()
        if not sl.startswith('{'): continue
        try: ev = json.loads(sl)
        except Exception: continue
        if ev.get('type') != 'assistant': continue
        for c in ev.get('message', {}).get('content', []) or []:
            if c.get('type') == 'tool_use' and c.get('name') == 'Bash':
                cmd = c.get('input', {}).get('command', '')
                if 'api.scryfall.com' in cmd and re.search(r'\bcurl\b', cmd):
                    n = len(re.findall(r'\bcurl\b', cmd))
                    loops = bool(re.search(r'\bfor\b|\bwhile\b|xargs', cmd))
                    rows.append((first_ts, agent[:8], run, n, loops, cmd[:160].replace('\n', ' ')))
by_agent = collections.Counter(); runs = collections.defaultdict(set)
for r in rows:
    by_agent[r[1]] += 1; runs[r[1]].add(r[2])
print('commands', len(rows), 'runs', sum(len(v) for v in runs.values()))
for a, n in by_agent.most_common(): print(a, 'commands', n, 'runs', len(runs[a]))
print('with a loop', sum(1 for r in rows if r[4]))
dates = sorted(r[0] for r in rows if r[0]); print('first', dates[:1], 'last', dates[-1:])
json.dump(rows, open('/tmp/dec1072-census/rows.json', 'w'), indent=0)
for r in sorted(rows)[-8:]: print(r)
