"""Render DIR/cheat_sheet.md to DIR/cheat_sheet.pdf (A4) with python-markdown and headless Chrome.

Run from the repo root:
    uv run --with markdown python scripts/prerelease/build_pdf.py --set-dir DIR

This Mac has no pandoc or wkhtmltopdf; Chrome's --print-to-pdf is what works.
Chrome keeps the sheet's Scryfall links as clickable links in the PDF.

The run deletes the old DIR/cheat_sheet.pdf before Chrome starts, so a stale
file can never pass. Chrome 156 can write the whole PDF and then exit with an
error: "Teardown watchdog expired", exit code 2, in some agent runs (4, 5 and
9 November 2026). A --user-data-dir in a temporary folder does not prevent it.
On a non-zero exit the run keeps the PDF only if pdf_complete() accepts the
file: it prints a warning with Chrome's exit code and the last lines of its
stderr, and exits 0. Otherwise it prints the same details and exits 1.
"""

import argparse
import os
import subprocess
import sys
import tempfile

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CSS = """
@page { size: A4; margin: 12mm 11mm; }
body { font-family: -apple-system, Helvetica, Arial, "Apple Color Emoji", sans-serif; font-size: 9.5pt; line-height: 1.3; }
sub { font-size: 7.5pt; color: #444; vertical-align: baseline; }
li { margin: 2pt 0; }
h1 { font-size: 16pt; } h2 { font-size: 12.5pt; margin-top: 14pt; } h3 { font-size: 10.5pt; }
table { border-collapse: collapse; font-size: 8.4pt; width: 100%; }
th, td { border: 1px solid #999; padding: 2px 4px; vertical-align: top; }
th { background: #eee; }
td:nth-child(1), td:nth-child(2) { white-space: nowrap; }
tr { page-break-inside: avoid; }
code { font-size: 8.5pt; }
a { color: #1a4fa0; text-decoration: none; }
"""


# A complete PDF is more than this many bytes; the Star Trek sheet is about 1.2 MB.
MIN_PDF_BYTES = 10_000


def pdf_complete(data: bytes, min_bytes: int = MIN_PDF_BYTES) -> bool:
    """True when `data` is a whole PDF file.

    It is larger than `min_bytes`, starts with "%PDF-" and ends with the
    end-of-file marker "%%EOF" (trailing whitespace allowed).
    """
    return len(data) > min_bytes and data.startswith(b"%PDF-") and data.rstrip().endswith(b"%%EOF")


def stderr_tail(stderr: bytes, lines: int = 10) -> str:
    """The last `lines` lines of Chrome's stderr, for the warning or the error."""
    return "\n".join(stderr.decode("utf-8", "replace").rstrip().splitlines()[-lines:])


def main() -> int:
    import markdown  # Here, so the tests import this module without the package.

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--set-dir", required=True)
    args = ap.parse_args()
    if not os.path.exists(CHROME):
        raise SystemExit(f"Chrome not found at {CHROME}; the PDF needs headless Chrome there")

    # Absolute, because Chrome reads the HTML from a file:// URL.
    set_dir = os.path.abspath(args.set_dir)
    src = os.path.join(set_dir, "cheat_sheet.md")
    pdf_path = os.path.join(set_dir, "cheat_sheet.pdf")
    with open(src, encoding="utf-8") as fh:
        body = markdown.markdown(fh.read(), extensions=["tables", "sane_lists"])
    # No old PDF may pass the check below as if Chrome had written it.
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    # A temporary folder, not DIR: DIR/cheat_sheet.html is build_html.py's page (DEC-1223).
    with tempfile.TemporaryDirectory() as tmp:
        html_path = os.path.join(tmp, "cheat_sheet.html")
        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>")
        done = subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
             f"--print-to-pdf={pdf_path}", f"file://{html_path}"],
            capture_output=True,
        )
    if done.returncode != 0:
        data = b""
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as fh:
                data = fh.read()
        details = (
            f"Chrome exited with code {done.returncode}. The last lines of its stderr:\n"
            f"{stderr_tail(done.stderr)}"
        )
        if not pdf_complete(data):
            print(f"error: {details}\n{pdf_path} is missing or incomplete ({len(data)} bytes).",
                  file=sys.stderr)
            return 1
        print(f"warning: {details}\nThe PDF is complete, so the run keeps it.", file=sys.stderr)
    print(f"wrote {pdf_path} ({os.path.getsize(pdf_path)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
