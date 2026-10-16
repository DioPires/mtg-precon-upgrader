import json
DS = "src/components/organisms/DeckSelector.tsx"
E2E = ("PLAYWRIGHT_BROWSERS_PATH=$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright "
       "GRIMOIRE_E2E_PORT=14849 npx playwright test tests/dec1146-selector-back-focus.spec.ts 2>&1 "
       "| grep -v DeprecationWarning | grep -v trace-deprecation")
LEFT = "const left = !before.isConnected && (!now || now === document.body);"
OLD = "const onOldPill = !!now && !!track?.contains(now) && !now.classList.contains('gv1-active');"
m = [
 {"name": "R1", "file": DS, "edits": [[LEFT, "const left = !before.isConnected;"]]},
 {"name": "R2", "file": DS, "edits": [[LEFT, "const left = !!before && (!now || now === document.body);"]]},
 {"name": "R3", "file": DS, "edits": [[OLD, "const onOldPill = !!now && !!track?.contains(now);"]]},
 {"name": "R4", "file": DS, "edits": [["!!track?.contains(now) &&", "!!track && true &&"]]},
 {"name": "R5", "file": DS, "edits": [["    focusBefore.current = null;\n", ""]]},
 {"name": "R6", "file": DS, "edits": [["    renderedIdx.current = activeIdx;\n", ""]]},
 {"name": "R7", "file": DS, "edits": [["    else if (before && strayed(", "    if (before && strayed("]]},
 {"name": "R11", "file": DS, "edits": [["if (renderedIdx.current !== activeIdx) {", "if (renderedIdx.current !== activeIdx || true) {"]]},
 {"name": "R12", "file": DS, "edits": [["focusBefore.current = document.activeElement;", "focusBefore.current = document.body;"]]},
 {"name": "R13", "file": DS, "edits": [["(!now || now === document.body)", "now === document.body"]]},
 {"name": "R14", "file": DS, "edits": [["else if (before && strayed(before, trackRef.current)) focusActive();",
   "else if (before && strayed(before, trackRef.current)) trackRef.current?.querySelector<HTMLElement>('.gv1-active')?.focus();"]]},
 {"name": "R16", "file": DS, "edits": [["  const now = document.activeElement;\n", "  const now = before as Element | null;\n"]]},
 {"name": "R8", "file": "src/routes/DeckGuide.tsx", "cmd": E2E,
  "edits": [["<DeckSelector decks={stubs} activeIdx={deck.idx}", "<DeckSelector key={deck.slug} decks={stubs} activeIdx={deck.idx}"]]},
 {"name": "R9", "file": "src/routes/DeckGuide.tsx", "cmd": E2E,
  "edits": [["if (next && next.idx !== deck.idx) navigate(`/deck/", "if (next && next.idx === deck.idx) navigate(`/deck/"]]},
 {"name": "R10", "file": "src/routes/Scrying.tsx", "cmd": E2E,
  "edits": [["if (next && next.idx !== deck.idx) navigate(`/scrying/", "if (next && next.idx === deck.idx) navigate(`/scrying/"]]},
 {"name": "R17", "file": "src/routes/DeckGuide.tsx", "cmd": E2E,
  "edits": [["if (next && next.idx !== deck.idx) navigate(`/deck/${next.slug}`);", "if (next!.idx !== deck.idx) navigate(`/deck/${next!.slug}`);"]]},
 {"name": "R18", "file": "src/routes/Scrying.tsx", "cmd": E2E,
  "edits": [["if (next && next.idx !== deck.idx) navigate(`/scrying/${next.slug}`);", "if (next!.idx !== deck.idx) navigate(`/scrying/${next!.slug}`);"]]},
]
json.dump(m, open("/tmp/dec1146-review/own/own-mutants.json", "w"), indent=1)
print(len(m), "mutants")
