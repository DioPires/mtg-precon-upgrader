SHOP = 'src/components/organisms/Shopping.tsx'
PPL = 'src/components/molecules/PricePausedLine.tsx'
CSS = 'src/styles/styles.css'
SHOPT = 'src/__tests__/components/Shopping.test.tsx'
UNIT = ['npx', 'vitest', 'run']
E2E_A = ['npx', 'playwright', 'test', 'tests/dec1154-shop-summary.spec.ts', '--workers', '3']
E2E_B = ['npx', 'playwright', 'test', 'tests/dec1154-shop-live-regions.spec.ts', 'tests/dec1083-shop-import-keyboard.spec.ts',
         'tests/dec942-owned-quota.spec.ts', 'tests/dec1131-card-batches.spec.ts', '--workers', '3']
E2E_ALL = ['npx', 'playwright', 'test', '--workers', '3']

OK_BLOCK = """        <div role="status">
          {importMsg?.ok && (
            <div className="gv1-shop-import-msg gv1-shop-import-ok">
              <span className="gv1-mono-xs">◆</span>
              <span className="gv1-mono-xs">{importMsg.text}</span>
            </div>
          )}
        </div>"""
ERR_BLOCK = """        <div role="alert">
          {importMsg && !importMsg.ok && (
            <div className="gv1-shop-import-msg gv1-shop-import-err">
              <span className="gv1-mono-xs">⚠</span>
              <span className="gv1-mono-xs">{importMsg.text}</span>
            </div>
          )}
        </div>"""
OK_SPAN_SIGIL = '              <span className="gv1-mono-xs">◆</span>\n'
ERR_SPAN_SIGIL = '              <span className="gv1-mono-xs">⚠</span>\n'
OK_TEXT = 'gv1-shop-import-ok">\n              <span className="gv1-mono-xs">◆</span>\n              <span className="gv1-mono-xs">{importMsg.text}</span>'
ERR_TEXT = 'gv1-shop-import-err">\n              <span className="gv1-mono-xs">⚠</span>\n              <span className="gv1-mono-xs">{importMsg.text}</span>'

def one(path, old, new, suites):
    return ([(path, old, new)], suites)

MUTANTS = {
 'BASE': ([], [E2E_B]),
 # Item 2: the merge commit's importStatus() call. The CSV path keeps a quantity of -1.
 'M0': one(SHOP, '        const q = read >= 1 ? read : 1;\n', '        const q = read;\n',
           [['npx', 'vitest', 'run', SHOPT, '-t', 'counts a CSV quantity of -1 as 1']]),
 # Item 8: the import message's words change; every import case must fail.
 'T1': one(SHOP, "+ 'To replace the list, use Clear owned first.',", "+ 'To replace the list, use Clear owned.',", [UNIT]),

 # ---- Shopping.tsx: the status region ----
 'S1a': one(SHOP, '        <div role="status">\n          {importMsg?.ok', '        <div>\n          {importMsg?.ok', [UNIT, E2E_B]),
 'S1b': one(SHOP, '        <div role="status">\n          {importMsg?.ok', '        <div role="alert">\n          {importMsg?.ok', [UNIT, E2E_B]),
 'S1c': one(SHOP, '        <div role="status">\n          {importMsg?.ok', '        <div role="status" hidden={!importMsg?.ok}>\n          {importMsg?.ok', [UNIT, E2E_B]),
 'S1d': one(SHOP, '        <div role="status">\n          {importMsg?.ok', '        <div role="status" key={importMsg?.text}>\n          {importMsg?.ok', [UNIT, E2E_B]),
 'S11a': one(SHOP, OK_BLOCK, """        {importMsg?.ok && (<div role="status">
            <div className="gv1-shop-import-msg gv1-shop-import-ok">
              <span className="gv1-mono-xs">◆</span>
              <span className="gv1-mono-xs">{importMsg.text}</span>
            </div>
        </div>)}""", [UNIT, E2E_B]),
 'S2a': one(SHOP, '          {importMsg?.ok && (', '          {importMsg && (', [UNIT, E2E_B]),
 'S2b': one(SHOP, '          {importMsg?.ok && (', '          {importMsg && !importMsg.ok && (', [UNIT, E2E_B]),
 'S3a': one(SHOP, '<div className="gv1-shop-import-msg gv1-shop-import-ok">', '<div className="gv1-shop-import-ok">', [UNIT, E2E_B]),
 'S3b': one(SHOP, '<div className="gv1-shop-import-msg gv1-shop-import-ok">', '<div className="gv1-shop-import-msg gv1-shop-import-err">', [UNIT, E2E_B]),
 'S4a': one(SHOP, OK_SPAN_SIGIL, '              <span>◆</span>\n', [UNIT, E2E_B]),
 'S4b': one(SHOP, OK_SPAN_SIGIL, '              <span className="gv1-mono-xs">⚠</span>\n', [UNIT, E2E_B]),
 'S5a': one(SHOP, OK_TEXT, OK_TEXT.replace('<span className="gv1-mono-xs">{importMsg.text}', '<span>{importMsg.text}'), [UNIT, E2E_B]),
 'S5b': one(SHOP, OK_TEXT, OK_TEXT.replace('{importMsg.text}', "{''}"), [UNIT, E2E_B]),
 # ---- Shopping.tsx: the alert region ----
 'S6a': one(SHOP, '        <div role="alert">', '        <div role="status">', [UNIT, E2E_B]),
 'S6b': one(SHOP, '        <div role="alert">', '        <div>', [UNIT, E2E_B]),
 'S11b': one(SHOP, ERR_BLOCK, """        {importMsg && !importMsg.ok && (<div role="alert">
            <div className="gv1-shop-import-msg gv1-shop-import-err">
              <span className="gv1-mono-xs">⚠</span>
              <span className="gv1-mono-xs">{importMsg.text}</span>
            </div>
        </div>)}""", [UNIT, E2E_B]),
 # The error put in the status region: the status region holds both blocks, and the alert region stays empty.
 'S6c': ([(SHOP, OK_BLOCK + '\n' + ERR_BLOCK, OK_BLOCK.replace('\n        </div>', '') + '\n' + ERR_BLOCK.split('\n', 1)[1].rsplit('\n', 1)[0] + '\n        </div>\n        <div role="alert">\n        </div>')], [UNIT, E2E_B]),
 'S7a': one(SHOP, '          {importMsg && !importMsg.ok && (', '          {importMsg && (', [UNIT, E2E_B]),
 'S7b': one(SHOP, '          {importMsg && !importMsg.ok && (', '          {!importMsg?.ok && (', [UNIT, E2E_B]),
 'S8a': one(SHOP, '<div className="gv1-shop-import-msg gv1-shop-import-err">', '<div className="gv1-shop-import-err">', [UNIT, E2E_B]),
 'S8b': one(SHOP, '<div className="gv1-shop-import-msg gv1-shop-import-err">', '<div className="gv1-shop-import-msg gv1-shop-import-ok">', [UNIT, E2E_B]),
 'S9a': one(SHOP, ERR_SPAN_SIGIL, '              <span>⚠</span>\n', [UNIT, E2E_B]),
 'S9b': one(SHOP, ERR_SPAN_SIGIL, '              <span className="gv1-mono-xs">◆</span>\n', [UNIT, E2E_B]),
 'S10a': one(SHOP, ERR_TEXT, ERR_TEXT.replace('<span className="gv1-mono-xs">{importMsg.text}', '<span>{importMsg.text}'), [UNIT, E2E_B]),
 'S10b': one(SHOP, ERR_TEXT, ERR_TEXT.replace('{importMsg.text}', "{''}"), [UNIT, E2E_B]),

 # ---- PricePausedLine.tsx ----
 'P1a': one(PPL, '    <div role="status">\n', '    <div>\n', [UNIT, E2E_B]),
 'P1b': one(PPL, '    <div role="status">\n', '    <div role="alert">\n', [UNIT, E2E_B]),
 'P1c': one(PPL, '    <div role="status">\n', '    <div role="status" aria-live="off">\n', [UNIT, E2E_B]),
 'P2a': one(PPL, '{until !== null && waiting && (', '{until !== null && (', [UNIT, E2E_B]),
 'P2b': one(PPL, '{until !== null && waiting && (', '{waiting && (', [UNIT, E2E_B]),
 'P2c': one(PPL, '  return (\n    <div role="status">', '  if (until === null || !waiting) return null;\n  return (\n    <div role="status">', [UNIT, E2E_B]),
 'P3a': one(PPL, '<p className="gv1-mono-xs gv1-shop-paused">', '<p className="gv1-shop-paused">', [UNIT, E2E_B]),
 'P3b': one(PPL, '<p className="gv1-mono-xs gv1-shop-paused">', '<p className="gv1-mono-xs">', [UNIT, E2E_B]),
 'P3c': ([(PPL, '<p className="gv1-mono-xs gv1-shop-paused">', '<div className="gv1-mono-xs gv1-shop-paused">'), (PPL, '        </p>\n', '        </div>\n')], [UNIT, E2E_B]),
 'P4a': one(PPL, '          Price refresh paused.\n', '          Price refresh stopped.\n', [UNIT, E2E_B]),
 'P5a': one(PPL, "{pricesDate ? ` Prices shown are from ${pricesDate}.` : ''}", "{` Prices shown are from ${pricesDate}.`}", [UNIT, E2E_B]),
 'P5b': one(PPL, "{pricesDate ? ` Prices shown are from ${pricesDate}.` : ''}", "{pricesDate ? '' : ''}", [UNIT, E2E_B]),
 'P6a': one(PPL, '{` Next try at ${clockTime(until)}.`}', "{''}", [UNIT, E2E_B]),

 # ---- styles.css ----
 'C1a': one(CSS, '@media (max-width: 480px) {\n  .gv1-shop-summary {', '@media (max-width: 430px) {\n  .gv1-shop-summary {', [E2E_A]),
 'C1b': one(CSS, '@media (max-width: 480px) {\n  .gv1-shop-summary {', '@media (max-width: 600px) {\n  .gv1-shop-summary {', [E2E_A]),
 'C2a': one(CSS, '  .gv1-shop-summary { display: flex; flex-wrap: wrap; }\n', '', [E2E_A]),
 'C2b': one(CSS, '  .gv1-shop-summary { display: flex; flex-wrap: wrap; }\n', '  .gv1-shop-summary { display: flex; flex-wrap: nowrap; }\n', [E2E_A]),
 'C3a': one(CSS, '  .gv1-shop-stat { flex: 1 1 0; }\n', '  .gv1-shop-stat { flex: 1 1 auto; }\n', [E2E_A]),
 'C3b': one(CSS, '  .gv1-shop-stat { flex: 1 1 0; }\n', '  .gv1-shop-stat { flex: 0 1 auto; }\n', [E2E_A]),
 'C4a': one(CSS, '  .gv1-shop-stat .gv1-serif-xl { font-size: 28px; }\n', '', [E2E_A]),
 'C5a': one(CSS, '  .gv1-shop-summary-actions { flex: 1 1 100%; }\n', '', [E2E_A]),
 'C5b': one(CSS, '  .gv1-shop-summary-actions { flex: 1 1 100%; }\n', '  .gv1-shop-summary-actions { flex: 1 1 0; }\n', [E2E_A]),
 'C6a': one(CSS, '  .gv1-shop-summary-actions button { white-space: nowrap; }\n', '', [E2E_A]),
}
# Item 8: the loaded count reads the file, not the list; only a second import differs.
MUTANTS['T2'] = one(SHOP, '      const loadedCards = [...merged.values()].reduce((s, q) => s + q, 0);\n',
                    '      const loadedCards = [...parsed.values()].reduce((s, q) => s + q, 0);\n', [UNIT])
# Item 8: the end-of-stop render comes 60 s late, so the line stays after the stop ends.
MUTANTS['T3'] = one(PPL, 'Math.max(0, until - Date.now()) + 1);', 'Math.max(0, until - Date.now()) + 60_000);',
                    [['npx', 'vitest', 'run', 'src/__tests__/components/PricePausedLine.test.tsx']])
