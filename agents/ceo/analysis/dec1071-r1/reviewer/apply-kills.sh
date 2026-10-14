#!/bin/sh
# DEC-1103 review: put the proposed kill cases into the web/ tree given as $1.
set -e
W="$1"
cp /tmp/dec1071-review/kills/dec1071-moxfield-check.spec.ts "$W/tests/"
# Unit case on the DNS flag text.
perl -0pi -e 's/import \{ isMoxfieldHost, isScryfallHost \} from/import { BLOCK_SCRYFALL_DNS, isMoxfieldHost, isScryfallHost } from/' "$W/src/__tests__/data/e2eGuardHosts.test.ts"
perl -0pi -e 'BEGIN { local $/; open F, "/tmp/dec1071-review/kills/unit-dns-case.ts"; $c = <F>; close F } s/\n\}\);\n\z/$c\});\n/' "$W/src/__tests__/data/e2eGuardHosts.test.ts"
# dec181: the read saw the final priced count.
perl -0pi -e 's/(      if \(await pageOverflows\(page\)\) overflows\.push\(\x27shopping\x27\);\n)/$1      \/\/ The read above needs the final priced count. The seed gives it at first\n      \/\/ paint, so the count does not move when the lookups end (DEC-1071).\n      const priced = page.locator(\x27.gv1-shop-summary .gv1-shop-stat\x27, { hasText: \x27EST. COST\x27 }).locator(\x27span\x27).nth(2);\n      const atRead = await priced.textContent();\n      await page.waitForLoadState(\x27networkidle\x27);\n      expect(await priced.textContent(), \x27the Shopping read saw the final priced count\x27).toBe(atRead);\n/' "$W/tests/dec181-qa.spec.ts"
# dec184: the summary counts every priced row.
perl -0pi -e 's/import \{ test, type Page \} from \x27\.\/support\/test\x27;/import { expect, test, type Page } from \x27.\/support\/test\x27;/' "$W/tests/dec184-visual-qa.spec.ts"
perl -0pi -e 's/(      await checkOverflow\(page, \x27shopping\x27, w\);\n)/$1      \/\/ The shot and the audits need every price in: the summary counts each\n      \/\/ row that shows a price (DEC-1071).\n      const counts = await page.evaluate(() => {\n        const rows = document.querySelectorAll(\x27.gv1-shop-row .gv1-shop-row-price .gv1-rune\x27).length;\n        const stat = [...document.querySelectorAll(\x27.gv1-shop-summary .gv1-shop-stat\x27)].find((s) => s.textContent?.includes(\x27EST. COST\x27));\n        const text = stat?.querySelectorAll(\x27span\x27)[2]?.textContent ?? \x27\x27;\n        const m = \/(\\d+)\\\/\\d+ priced\/.exec(text);\n        return { rows, summary: m ? Number(m[1]) : \/all priced\/.test(text) ? rows : -1 };\n      });\n      expect(counts.summary, \x27the Shopping summary counts every row that shows a price\x27).toBe(counts.rows);\n/' "$W/tests/dec184-visual-qa.spec.ts"
# IN-2: the message names the refusal that the route gives.
perl -0pi -e 's/(  await expect\(page\.locator\(\x27\.gv1-lab-url-msg\x27\)\)\.toBeVisible\(\{ timeout: 15000 \}\);\n)/$1  await expect(page.locator(\x27.gv1-lab-url-msg\x27)).toContainText(\x27moxfield returned HTTP 403\x27);\n/' "$W/tests/combo-lab.spec.ts"
