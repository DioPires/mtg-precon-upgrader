"""DEC-1151 mutant runner for PR #61 at e882c60.

Each mutant replaces one exact string (it must occur once) in one source file,
runs the mutant's unit file with vitest, writes the log, and restores the file
with `git checkout`. Before each mutant, `git status --porcelain` must print
nothing. Usage: python3 mutants.py [ID ...] (no ID runs every mutant).
"""

import json
import re
import subprocess
import sys
from pathlib import Path

TREE = Path('/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/wt-dec1142-review')
WEB = TREE / 'web'
LOGS = Path('/Users/dpires/.paperclip/instances/default/workspaces/6ba3ac88-12e8-41a7-834f-98e3d92dae78/dec1142-review-logs/mutants')

NOUN = 'web/src/lib/cardNoun.ts'
SHOP = 'web/src/components/organisms/Shopping.tsx'
ENG = 'web/src/components/organisms/Engine.tsx'
LAB = 'web/src/routes/ComboLab.tsx'
REP = 'web/src/lib/spellbookReport.ts'

T_NOUN = 'src/__tests__/lib/cardNoun.test.ts'
T_SHOP = 'src/__tests__/components/Shopping.test.tsx'
T_ENG = 'src/__tests__/components/Engine.test.tsx'
T_LAB = 'src/__tests__/routes/ComboLab.test.tsx'
T_REP = 'src/__tests__/lib/spellbookReport.test.ts'

RET = "return count === 1 ? 'card' : 'cards';"
L743 = '· {buy.length} unique · {buyTotal} {cardNoun(buyTotal)}</span>'
L789 = '· {own.length} unique · {ownTotal} {cardNoun(ownTotal)}</span>'
L108 = '{cur.count} {cardNoun(cur.count)} · hover for full frame</div>'
L288 = '`Loaded ${deck.cardNames.length} ${cardNoun(deck.cardNames.length)} from ${deck.site}${'
L153 = 'lines.push(`Analyzed ${report.cardsAnalyzed} of ${report.cardsTotal} ${cardNoun(report.cardsTotal)}.`);'
L309 = 'out.push(`_Analyzed ${report.cardsAnalyzed} of ${report.cardsTotal} ${cardNoun(report.cardsTotal)}._`);'

# (id, file, old, new, unit file, note)
M = [
    # cardNoun.ts:3 (the helper)
    ('H1', NOUN, RET, "return count <= 1 ? 'card' : 'cards';", T_NOUN, 'rule 3'),
    ('H2', NOUN, RET, "return count < 2 ? 'card' : 'cards';", T_NOUN, 'rule 3'),
    ('H3', NOUN, RET, "return count > 1 ? 'cards' : 'card';", T_NOUN, 'rule 3'),
    ('H4', NOUN, RET, "return Math.abs(count) === 1 ? 'card' : 'cards';", T_NOUN, 'rule 3'),
    ('H5', NOUN, RET, "return count === 1 ? 'cards' : 'card';", T_NOUN, 'brief'),
    ('H6', NOUN, RET, "return count !== 1 ? 'card' : 'cards';", T_NOUN, 'operator'),
    ('H7', NOUN, RET, "return count >= 1 ? 'card' : 'cards';", T_NOUN, 'operator'),
    ('H8', NOUN, RET, "return count < 1 ? 'card' : 'cards';", T_NOUN, 'operator'),
    ('H9', NOUN, RET, "return count > 1 ? 'card' : 'cards';", T_NOUN, 'operator'),
    ('H10', NOUN, RET, "return count === 0 ? 'card' : 'cards';", T_NOUN, 'literal'),
    ('H11', NOUN, RET, "return count === 2 ? 'card' : 'cards';", T_NOUN, 'literal'),
    ('H12', NOUN, RET, "return true ? 'card' : 'cards';", T_NOUN, 'conditional'),
    ('H13', NOUN, RET, "return false ? 'card' : 'cards';", T_NOUN, 'conditional'),
    ('H14', NOUN, RET, "return count === 1 ? '' : 'cards';", T_NOUN, 'string'),
    ('H15', NOUN, RET, "return count === 1 ? 'card' : '';", T_NOUN, 'string'),
    ('H16', NOUN, RET, "return count === 1 ? 'card' : 'card';", T_NOUN, 'string'),
    ('H17', NOUN, RET, "return count == 1 ? 'card' : 'cards';", T_NOUN, 'equivalent on number'),
    ('H18', NOUN, RET, "return Math.round(count) === 1 ? 'card' : 'cards';", T_NOUN, 'rounding'),
    ('H19', NOUN, RET, "return Math.ceil(count) === 1 ? 'card' : 'cards';", T_NOUN, 'rounding'),
    ('H20', NOUN, RET, "return Math.floor(count) === 1 ? 'card' : 'cards';", T_NOUN, 'rounding'),
    ('H21', NOUN, RET, "return Math.trunc(count) === 1 ? 'card' : 'cards';", T_NOUN, 'rounding'),
    ('H22', NOUN, RET, "return !(count < 1 || count > 1) ? 'card' : 'cards';", T_NOUN, 'NaN'),
    ('H23', NOUN, RET, "return count * count === 1 ? 'card' : 'cards';", T_NOUN, 'sign'),
    ('H24', NOUN, 'export function cardNoun', 'function cardNoun', T_NOUN, 'export'),
    # Shopping.tsx:743 (Need to buy)
    ('S1', SHOP, L743, '· {buy.length} unique · {buyTotal} cards</span>', T_SHOP, 'old text'),
    ('S2', SHOP, L743, '· {buy.length} unique · {buyTotal} {cardNoun(buy.length)}</span>', T_SHOP, 'noun reads buy.length'),
    ('S3', SHOP, L743, '· {buy.length} unique · {buyTotal} {cardNoun(ownTotal)}</span>', T_SHOP, 'noun reads ownTotal'),
    ('S4', SHOP, L743, '· {buy.length} unique · {buyTotal} {cardNoun(own.length)}</span>', T_SHOP, 'noun reads own.length'),
    ('S5', SHOP, L743, '· {buy.length} unique · {ownTotal} {cardNoun(buyTotal)}</span>', T_SHOP, 'count reads ownTotal'),
    ('S6', SHOP, L743, '· {buy.length} unique · {ownTotal} {cardNoun(ownTotal)}</span>', T_SHOP, 'count and noun read ownTotal'),
    ('S7', SHOP, L743, '· {buy.length} unique · {buy.length} {cardNoun(buyTotal)}</span>', T_SHOP, 'count reads buy.length'),
    ('S8', SHOP, L743, '· {buyTotal} unique · {buyTotal} {cardNoun(buyTotal)}</span>', T_SHOP, 'unique reads buyTotal'),
    ('S9', SHOP, L743, '· {own.length} unique · {buyTotal} {cardNoun(buyTotal)}</span>', T_SHOP, 'unique reads own.length'),
    ('S10', SHOP, L743, '· {buy.length} unique · {buyTotal}{cardNoun(buyTotal)}</span>', T_SHOP, 'space dropped'),
    # Shopping.tsx:789 (Already own)
    ('S11', SHOP, L789, '· {own.length} unique · {ownTotal} cards</span>', T_SHOP, 'old text'),
    ('S12', SHOP, L789, '· {own.length} unique · {ownTotal} {cardNoun(own.length)}</span>', T_SHOP, 'noun reads own.length'),
    ('S13', SHOP, L789, '· {own.length} unique · {ownTotal} {cardNoun(buyTotal)}</span>', T_SHOP, 'noun reads buyTotal'),
    ('S14', SHOP, L789, '· {own.length} unique · {ownTotal} {cardNoun(buy.length)}</span>', T_SHOP, 'noun reads buy.length'),
    ('S15', SHOP, L789, '· {own.length} unique · {buyTotal} {cardNoun(ownTotal)}</span>', T_SHOP, 'count reads buyTotal'),
    ('S16', SHOP, L789, '· {own.length} unique · {buyTotal} {cardNoun(buyTotal)}</span>', T_SHOP, 'count and noun read buyTotal'),
    ('S17', SHOP, L789, '· {own.length} unique · {own.length} {cardNoun(ownTotal)}</span>', T_SHOP, 'count reads own.length'),
    ('S18', SHOP, L789, '· {ownTotal} unique · {ownTotal} {cardNoun(ownTotal)}</span>', T_SHOP, 'unique reads ownTotal'),
    ('S19', SHOP, L789, '· {buy.length} unique · {ownTotal} {cardNoun(ownTotal)}</span>', T_SHOP, 'unique reads buy.length'),
    # Engine.tsx:108
    ('E1', ENG, L108, '{cur.count} cards · hover for full frame</div>', T_ENG, 'old text'),
    ('E2', ENG, L108, '{cur.count} {cardNoun(cur.cards.length)} · hover for full frame</div>', T_ENG, 'rule 4'),
    ('E3', ENG, L108, '{cur.count} {cardNoun(totalCards)} · hover for full frame</div>', T_ENG, 'noun reads totalCards'),
    ('E4', ENG, L108, '{cur.count} {cardNoun(engine.length)} · hover for full frame</div>', T_ENG, 'noun reads engine.length'),
    ('E5', ENG, L108, '{cur.cards.length} {cardNoun(cur.count)} · hover for full frame</div>', T_ENG, 'count reads cur.cards.length'),
    ('E6', ENG, L108, '{totalCards} {cardNoun(cur.count)} · hover for full frame</div>', T_ENG, 'count reads totalCards'),
    ('E7', ENG, L108, '{cur.count} {cardNoun(cur.count)} · hover for frame</div>', T_ENG, 'text'),
    ('E8', ENG, L108, '{cur.count}{cardNoun(cur.count)} · hover for full frame</div>', T_ENG, 'space dropped'),
    # ComboLab.tsx:288
    ('C1', LAB, L288, '`Loaded ${deck.cardNames.length} cards from ${deck.site}${', T_LAB, 'old text'),
    ('C2', LAB, L288, '`Loaded ${deck.cardNames.length} ${cardNoun(deck.commanderNames.length)} from ${deck.site}${', T_LAB, 'noun reads commanderNames'),
    ('C3', LAB, L288, '`Loaded ${deck.cardNames.length} ${cardNoun(deck.unresolved.length)} from ${deck.site}${', T_LAB, 'noun reads unresolved'),
    ('C4', LAB, L288, '`Loaded ${deck.cardNames.length} ${cardNoun(deck.cardNames.length + deck.commanderNames.length)} from ${deck.site}${', T_LAB, 'noun reads cards + commanders'),
    ('C5', LAB, L288, '`Loaded ${deck.commanderNames.length} ${cardNoun(deck.cardNames.length)} from ${deck.site}${', T_LAB, 'count reads commanderNames'),
    ('C6', LAB, L288, '`Loaded ${deck.cardNames.length} ${cardNoun(deck.cardNames.length)} from ${deck.name}${', T_LAB, 'site reads name'),
    ('C7', LAB, L288, '`Loaded ${deck.cardNames.length} ${cardNoun(deck.cardNames.length)} from${deck.site}${', T_LAB, 'space dropped'),
    # spellbookReport.ts:153 (plain text)
    ('R1', REP, L153, 'lines.push(`Analyzed ${report.cardsAnalyzed} of ${report.cardsTotal} cards.`);', T_REP, 'old text'),
    ('R2', REP, L153, 'lines.push(`Analyzed ${report.cardsAnalyzed} of ${report.cardsTotal} ${cardNoun(report.cardsAnalyzed)}.`);', T_REP, 'noun reads cardsAnalyzed'),
    ('R3', REP, L153, 'lines.push(`Analyzed ${report.cardsAnalyzed} of ${report.cardsTotal} ${cardNoun(report.cardsTotal - report.cardsAnalyzed)}.`);', T_REP, 'noun reads total - analyzed'),
    ('R4', REP, L153, 'lines.push(`Analyzed ${report.cardsAnalyzed} of ${report.cardsTotal} ${cardNoun(report.unresolved.length)}.`);', T_REP, 'noun reads unresolved'),
    ('R5', REP, L153, 'lines.push(`Analyzed ${report.cardsTotal} of ${report.cardsAnalyzed} ${cardNoun(report.cardsTotal)}.`);', T_REP, 'counts swapped'),
    ('R6', REP, L153, 'lines.push(`Analyzed ${report.cardsAnalyzed} of ${report.cardsTotal} ${cardNoun(report.cardsTotal)}`);', T_REP, 'full stop dropped'),
    ('R7', REP, L153, 'lines.push(`Analyzed ${report.cardsAnalyzed} of ${report.cardsTotal} ${cardNoun(report.cardsTotal)}.`.toUpperCase());', T_REP, 'case'),
    # spellbookReport.ts:309 (Markdown)
    ('R8', REP, L309, 'out.push(`_Analyzed ${report.cardsAnalyzed} of ${report.cardsTotal} cards._`);', T_REP, 'old text'),
    ('R9', REP, L309, 'out.push(`_Analyzed ${report.cardsAnalyzed} of ${report.cardsTotal} ${cardNoun(report.cardsAnalyzed)}._`);', T_REP, 'noun reads cardsAnalyzed'),
    ('R10', REP, L309, 'out.push(`_Analyzed ${report.cardsAnalyzed} of ${report.cardsTotal} ${cardNoun(report.cardsTotal - report.cardsAnalyzed)}._`);', T_REP, 'noun reads total - analyzed'),
    ('R11', REP, L309, 'out.push(`_Analyzed ${report.cardsAnalyzed} of ${report.cardsTotal} ${cardNoun(report.unresolved.length)}._`);', T_REP, 'noun reads unresolved'),
    ('R12', REP, L309, 'out.push(`_Analyzed ${report.cardsTotal} of ${report.cardsAnalyzed} ${cardNoun(report.cardsTotal)}._`);', T_REP, 'counts swapped'),
    ('R13', REP, L309, 'out.push(`Analyzed ${report.cardsAnalyzed} of ${report.cardsTotal} ${cardNoun(report.cardsTotal)}.`);', T_REP, 'emphasis dropped'),
    # Import lines
    ('I1', SHOP, "import { cardNoun } from '../../lib/cardNoun';\n", '', T_SHOP, 'import removed'),
    ('I2', ENG, "import { cardNoun } from '../../lib/cardNoun';\n", '', T_ENG, 'import removed'),
    ('I3', LAB, "import { cardNoun } from '../lib/cardNoun';\n", '', T_LAB, 'import removed'),
    ('I4', REP, "import { cardNoun } from './cardNoun';\n", '', T_REP, 'import removed'),
]

ANSI = re.compile(r'\x1b\[[0-9;]*m')


def sh(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def run(mid, path, old, new, test, note):
    if sh(['git', 'status', '--porcelain'], TREE).stdout.strip():
        raise SystemExit(f'{mid}: tree not clean before the mutant')
    f = TREE / path
    src = f.read_text()
    if src.count(old) != 1:
        raise SystemExit(f'{mid}: the old string occurs {src.count(old)} times in {path}')
    f.write_text(src.replace(old, new))
    try:
        p = sh(['npx', 'vitest', 'run', test], WEB)
    finally:
        sh(['git', 'checkout', '--', path], TREE)
    out = ANSI.sub('', p.stdout + p.stderr)
    log = LOGS / f'{mid}.log'
    log.write_text(f'# {mid} ({note}) {path}\n# old: {old!r}\n# new: {new!r}\n# exit {p.returncode}\n\n{out}')
    m = re.search(r'^\s*Tests\s+(.+)$', out, re.M)
    count = m.group(1).strip() if m else '(no Tests line)'
    verdict = 'survived' if p.returncode == 0 else 'killed'
    clean = not sh(['git', 'status', '--porcelain'], TREE).stdout.strip()
    return {'id': mid, 'file': path, 'note': note, 'count': count, 'verdict': verdict,
            'exit': p.returncode, 'log': str(log), 'clean_after': clean}


def main():
    LOGS.mkdir(parents=True, exist_ok=True)
    want = set(sys.argv[1:])
    res = [run(*m) for m in M if not want or m[0] in want]
    name = 'results.json' if not want else f'results-{"-".join(sorted(want))}.json'
    (LOGS / name).write_text(json.dumps(res, indent=2))
    for r in res:
        print(f"{r['id']:4} {r['verdict']:8} {r['count']:40} clean={r['clean_after']} {r['note']}")


if __name__ == '__main__':
    main()
