"""Build the expected web/tests/dec1177-empty-sigils.spec.ts for the DEC-1201 N1 and N2 follow-up.

Input: main's file (72d4ebd). Output: expected/dec1177-empty-sigils.spec.ts.
N1: the reviewer's guard case, verbatim, after the Compare case (the file's last case).
N2: the reviewer's header text, with "The two DEC-1199 cases" ruled to "The DEC-1199 cases"
(N1 adds a third DEC-1199 case that also reads the computed `::before` only).
Each old span must occur exactly once.
"""
import pathlib, sys

kit = pathlib.Path(__file__).parent
src = (kit / "main-72d4ebd.spec.ts").read_text()

OLD_HEADER = """// Every case but the third reads Chromium's own accessibility tree (CDP), not
// the name that Playwright computes: the text of a ::before is in Chromium's
// tree only. The third reads the stylesheet that the page loads.
"""
NEW_HEADER = """// Each DEC-1177 case but the stylesheet case reads Chromium's own accessibility
// tree (CDP), not the name that Playwright computes: the text of a ::before is in
// Chromium's tree only. The stylesheet case reads the stylesheet that the page
// loads. The DEC-1199 cases read the computed `::before` only.
"""
OLD_TAIL = """  expect(await spokenText(page, message)).toEqual(['NO DECKS LOADED.']);
  await expectOneMark(page, message, '◇');
});
"""
GUARD = """
// A box with no `.gv1-rune` span keeps the ◇ of `.gv1-empty::before`, its only mark (DEC-1199).
// No deck in the repository has an empty `winConditions`, so the route empties it.
test('the deck page with no win conditions keeps the ◇ of its empty state (DEC-1199)', async ({ page }) => {
  await page.route('**/commanders/eternal-agony/deck.json', async (route) => {
    const response = await route.fetch();
    await route.fulfill({ response, json: { ...(await response.json()), winConditions: [] } });
  });
  await page.goto('/deck/eternal-agony');
  const message = "No documented win conditions in this deck's dossier yet.";
  const empty = page.locator('.gv1-empty').filter({ hasText: message });
  await expect(empty).toHaveCount(1);
  await expect(empty.locator('.gv1-rune')).toHaveCount(0);
  expect(await beforeGlyph(page, message)).toMatch(/^"◇"/);
});
"""
for old in (OLD_HEADER, OLD_TAIL):
    n = src.count(old)
    if n != 1:
        sys.exit(f"old span found {n} times: {old[:60]!r}")
if not src.endswith(OLD_TAIL):
    sys.exit("the Compare case is not the file's last case")
out = src.replace(OLD_HEADER, NEW_HEADER) + GUARD
# The guard's body must equal the reviewer's scratch case byte for byte.
guard_src = (kit / "reviewer" / "guard.spec.ts").read_text()
body = guard_src[guard_src.index("// A box with no"):]
assert GUARD.lstrip("\n") == body, "guard text differs from the reviewer's scratch case"
(kit / "expected").mkdir(exist_ok=True)
(kit / "expected" / "dec1177-empty-sigils.spec.ts").write_text(out)
print("wrote expected; lines", out.count("\n"))
