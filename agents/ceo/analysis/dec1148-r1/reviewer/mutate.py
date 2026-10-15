# Apply one named mutant to DeckSelector.tsx. Each pair must match exactly once.
import sys, pathlib
F = pathlib.Path(sys.argv[2])
src = F.read_text()
FOCUS = "trackRef.current?.querySelector<HTMLElement>('.gv1-active')?.focus({ preventScroll: true });"
BRANCH = "    if (next === activeIdx) focusActive();\n    else keyTarget.current = next;\n"
EFFECT_IF = "    if (keyTarget.current === activeIdx) focusActive();\n"
CLEAR = "    keyTarget.current = null;\n  }, [activeIdx, focusActive]);"
M = {
 'S1': [(FOCUS, "trackRef.current?.querySelector<HTMLElement>('.gv1-active');")],
 'S2': [(BRANCH, "    if (e.key === 'ArrowRight') {\n      if (next === activeIdx) focusActive();\n      else keyTarget.current = next;\n    }\n")],
 'S3': [(BRANCH, "    trackRef.current\n      ?.querySelectorAll<HTMLElement>('.gv1-sel-pill')\n      [ordered.findIndex((d) => d.idx === next)]?.focus({ preventScroll: true });\n"),
        (EFFECT_IF, "")],
 'M4': [(CLEAR, "  }, [activeIdx, focusActive]);")],
 'M5': [(FOCUS, "trackRef.current?.querySelector<HTMLElement>('.gv1-active')?.focus();")],
 'M6': [(FOCUS, "trackRef.current?.querySelector<HTMLElement>('.gv1-sel-pill')?.focus({ preventScroll: true });")],
 'M7': [("    if (next === activeIdx) focusActive();\n", "    if (next !== activeIdx) focusActive();\n")],
 'M8': [(BRANCH, "    keyTarget.current = next;\n")],
 # Own mutants on the added lines.
 'M9': [(EFFECT_IF, "    if (keyTarget.current !== null) focusActive();\n")],
 'M10': [(EFFECT_IF, "    focusActive();\n")],
 'M11': [("const keyTarget = useRef<number | null>(null);", "const keyTarget = useRef<number | null>(activeIdx);")],
 'M12': [(CLEAR, "    keyTarget.current = null;\n  }, [focusActive]);")],
 'M13': [("    else keyTarget.current = next;\n", "    else keyTarget.current = activeIdx;\n")],
 'M14': [("    if (next === activeIdx) focusActive();\n", "    if (next === activeIdx) {}\n")],
 'M15': [(FOCUS, "document.querySelector<HTMLElement>('.gv1-active')?.focus({ preventScroll: true });")],
 'M16': [(EFFECT_IF + "    keyTarget.current = null;\n", "    if (keyTarget.current === activeIdx) {\n      focusActive();\n      keyTarget.current = null;\n    }\n")],
 'M17': [("    onSelect(next);\n  };", "  };"), ("    const next = scribed[nextIx].idx;\n", "    const next = scribed[nextIx].idx;\n    onSelect(next);\n")],
 'M18': [("    onSelect(next);\n  };", "    if (next !== activeIdx) onSelect(next);\n  };")],
 'M19': [("    onSelect(next);\n  };", "    onSelect(scribed[curIx < 0 ? 0 : curIx].idx);\n  };")],
 'M20': [("    onSelect(next);\n  };", "  };")],
 'M21': [("    if (next === activeIdx) focusActive();\n", "    if (next === activeIdx) focusActive();\n    keyTarget.current = next;\n"), ("    else keyTarget.current = next;\n", "")],
}
for a, b in M[sys.argv[1]]:
    n = src.count(a)
    assert n == 1, (sys.argv[1], n, a)
    src = src.replace(a, b)
F.write_text(src)
