import json, sys, re, os, collections
hits = [l.strip() for l in open(sys.argv[1]) if l.strip()]
out = []
for f in hits:
    agent = f.split('/')[-2][:8]; run = os.path.basename(f)[:8]
    if run == '61218405': continue
    buf = []; ts = None
    for line in open(f, errors='replace'):
        try: rec = json.loads(line)
        except Exception: continue
        ts = ts or rec.get('ts')
        if rec.get('stream') == 'stdout': buf.append(rec.get('chunk', ''))
    for sl in ''.join(buf).split('\n'):
        sl = sl.strip()
        if not sl.startswith('{"type":"assistant"'): continue
        try: ev = json.loads(sl)
        except Exception: continue
        for c in ev.get('message', {}).get('content', []) or []:
            if c.get('type') != 'tool_use' or c.get('name') != 'Bash': continue
            cmd = c['input'].get('command', '')
            # drop heredoc bodies
            body = re.sub(r"<<-?\s*'?(\w+)'?\n.*?\n\1\b", '<<HEREDOC', cmd, flags=re.S)
            for ln in body.split('\n'):
                if re.search(r'\bcurl\b[^|;]*?(https?://)?api\.scryfall\.com', ln) and 'PAPERCLIP_API_URL' not in ln:
                    loop = bool(re.search(r'\bfor\b|\bwhile\b|xargs', body))
                    out.append((ts[:10], agent, run, loop, ln.strip()[:170]))
uniq = sorted(set(out))
ag = collections.Counter(r[1] for r in uniq); rn = collections.defaultdict(set)
for r in uniq: rn[r[1]].add(r[2])
print('curl lines', len(uniq), 'runs', len({r[2] for r in uniq}))
for a, n in ag.most_common(): print(' ', a, 'lines', n, 'runs', len(rn[a]))
print('since 2026-09-17:', len([r for r in uniq if r[0] >= '2026-09-17']), 'lines in', len({r[2] for r in uniq if r[0] >= '2026-09-17'}), 'runs')
print('in a loop:', sum(r[3] for r in uniq))
for r in uniq: print(r)
