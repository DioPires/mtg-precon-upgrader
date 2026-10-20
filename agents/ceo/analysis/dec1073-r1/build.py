# Build the expected files of fix round 1 (DEC-1073, PR #25) from the head's
# files and the reviewer's text in verdict 3cd4642d on DEC-1087.
import re, sys
seed = open('head-seed.ts').read()
old_tail = "    expect(fromApp).toStrictEqual(seed);\n  });\n});\n"
assert seed.endswith(old_tail), 'seed tail moved'
new_case = (
    "    expect(fromApp).toStrictEqual(seed);\n  });\n\n"
    "  it('holds no joined mana cost: the stub sends card_faces for every // card', () => {\n"
    "    const joined = Object.entries(cardCacheSeed()).filter(([, e]) => (e as { mana_cost: string }).mana_cost.includes(' // '));\n"
    "    expect(joined.map(([key]) => key)).toEqual([]);\n"
    "  });\n});\n"
)
open('expected/web/src/__tests__/data/e2eCardCacheSeed.test.ts', 'w').write(seed[: -len(old_tail)] + new_case)

readme = open('head-README.md').read()
def sub(old, new):
    global readme
    flat = re.sub(r'\s+', ' ', readme)
    assert flat.count(old) == 1, ('not once', old, flat.count(old))
    # Replace on the flattened text, then keep the flat paragraph for the compare.
    readme = flat.replace(old, new)
sub("A card with two halves on one side (adventure, split, room) comes with",
    "A card with two halves on one side (adventure, split, room, prepare) comes with")
sub("68 of the 1,552 names have no row in the price index",
    "68 of the 1,556 names have no row in the price index")
sub("- If two runs start with one port value, at most one of them runs cases, on its own build. The other stops with the same message.",
    "- If two runs with one port value overlap, the run whose server takes the port first runs the cases, on its own build. The other stops with the same message. A run whose server starts after the other run has ended takes the free port and runs its cases on its own build.")
open('expected/README.flat.txt', 'w').write(readme)
print('built')
