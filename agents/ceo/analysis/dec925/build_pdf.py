"""Render cheat_sheet.md to cheat_sheet.pdf (A4) with python-markdown and headless Chrome.

Run from the repo root:
    uv run --with markdown python agents/ceo/analysis/dec925/build_pdf.py

This Mac has no pandoc or wkhtmltopdf; Chrome's --print-to-pdf is what works.
"""

import os
import subprocess
import sys

import markdown

HERE = os.path.dirname(os.path.abspath(__file__))
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
"""


def main() -> int:
    src = os.path.join(HERE, "cheat_sheet.md")
    html_path = os.path.join(HERE, "cheat_sheet.html")
    pdf_path = os.path.join(HERE, "cheat_sheet.pdf")
    with open(src, encoding="utf-8") as fh:
        body = markdown.markdown(fh.read(), extensions=["tables", "sane_lists"])
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>")
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={pdf_path}", f"file://{html_path}"],
        check=True, capture_output=True,
    )
    os.remove(html_path)
    print(f"wrote {pdf_path} ({os.path.getsize(pdf_path)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
