import pathlib
d = pathlib.Path('/tmp/dec1088-ceo')
# Unit file: the reviewer's kill line after :444, without its scratch comment.
unit = (d / 'head-unit.tsx').read_text().split('\n')
assert unit[443] == "    expect(button).toHaveAttribute('type', 'button');", unit[443]
assert unit[444] == "    expect(button.tabIndex).not.toBe(-1);", unit[444]
kill_unit = pathlib.Path('/tmp/dec1088/Shopping.test.kill-line.tsx').read_text().split('\n')
assert kill_unit[444] == "    expect(button.className).toBe('gv1-shop-btn'); // DEC-1088 scratch kill line", kill_unit[444]
line = "    expect(button.className).toBe('gv1-shop-btn');"
assert kill_unit[444].startswith(line)
unit.insert(444, line)
(d / 'expected-unit.tsx').write_text('\n'.join(unit))
# Spec: the reviewer's kill case appended at the end, with two changes that
# change no behaviour: the describe title, and the file's own importButton().
spec = (d / 'head-spec.ts').read_text()
assert spec.endswith('}\n')
kill = pathlib.Path('/tmp/dec1088/specs/zz-dec1088-kill.spec.ts').read_text()
start = kill.index("for (const fonts of ['live', 'blocked'] as const) {")
block = kill[start:]
old_title = "test.describe(`fonts ${fonts}`, () => {"
new_title = "test.describe(`DEC-1083 owned-cards import, look (fonts ${fonts})`, () => {"
old_btn = "const button = page.getByRole('button', { name: 'Import owned cards', exact: true });"
new_btn = "const button = importButton(page);"
assert block.count(old_title) == 1 and block.count(old_btn) == 1
block = block.replace(old_title, new_title).replace(old_btn, new_btn)
head_comment = (
    "\n"
    "// The button keeps the look of `.gv1-shop-btn` (DEC-1088 B1). Each value read\n"
    "// here is one that a CSS rule sets, so none depends on the font. The ring\n"
    "// check above does not pin the class: `.gv1-root :focus-visible` gives every\n"
    "// control the same ring.\n"
)
(d / 'expected-spec.ts').write_text(spec + head_comment + block)
print('built')
