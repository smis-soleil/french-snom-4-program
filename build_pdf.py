#!/usr/bin/env python3
"""Build conference-program.pdf from conference-program.md.

Requirements: Python 3.8+ and Google Chrome / Chromium / Microsoft Edge (no pip packages).

Usage (from this folder):
    python3 build_pdf.py
    python3 build_pdf.py --md conference-program.md --out conference-program.pdf
    python3 build_pdf.py --html-only        # also keep the intermediate HTML for debugging

If the browser is not found automatically, set CHROME_PATH or use --chrome.
Colors are in style/theme.css, layout in style/program.css.
"""
import argparse
import base64
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# ---- Content settings -------------------------------------------------------
LOGOS = [  # shown side by side in the footer of every page
    "logos/logo soleil.png",
    "logos/Logo-RF-ONERA-RVB.jpg",
    "logos/attocube_WITTENSTEIN.jpg",
    "logos/logo AtouM TECH  06 Octobre 2023.jpg",
]
CONFERENCE_LOGO = "conference_logo.png"      # inside the header circle
RESTAURANT_MAP = "restaurant_location.png"   # in the "Conference dinner" section
STYLES = ["style/theme.css", "style/program.css"]
FOOTER_NOTE = (
    "Ce workshop a bénéficié d'une aide de l'État au titre de France 2030 "
    "(PhOM -Graduate School Physique) portant la référence ANR-11-IDEX-0003"
)
HEADER_LABEL = "Conference program"
NEW_PAGE_DAY = "tuesday"  # this day starts on a new page; posters always do
# -----------------------------------------------------------------------------

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
CHROME_NAMES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge"]


def find_chrome(explicit=None):
    for candidate in [explicit, os.environ.get("CHROME_PATH")]:
        if candidate:
            if Path(candidate).exists():
                return candidate
            sys.exit(f"Browser not found: {candidate}")
    for path in CHROME_CANDIDATES:
        if Path(path).exists():
            return path
    for name in CHROME_NAMES:
        found = shutil.which(name)
        if found:
            return found
    sys.exit("Chrome/Chromium/Edge not found. Install it or pass --chrome /path/to/browser.")


def data_uri(relative_path):
    path = ROOT / relative_path
    if not path.exists():
        sys.exit(f"Missing file: {path}")
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def fmt(text):
    text = escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)


def parse_markdown(lines):
    """Split the markdown into headings, tables and paragraphs."""
    blocks, i = [], 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.startswith("#"):
            m = re.match(r"^(#{1,6})\s+(.*)", line)
            blocks.append(("h", len(m.group(1)), m.group(2).strip()))
            i += 1
        elif line.lstrip().startswith("|"):
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"[:\-\s]+", c or " ") for c in row):
                    rows.append(row)
                i += 1
            blocks.append(("table", rows))
        else:
            para = [line.strip()]
            i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].startswith("#") \
                    and not lines[i].lstrip().startswith("|"):
                para.append(lines[i].strip())
                i += 1
            blocks.append(("p", " ".join(para)))
    return blocks


def render_body(blocks):
    body = []
    section = None  # None | "venue" | "posters" | "dinner"
    open_wrapper = False

    def close_section():
        nonlocal section, open_wrapper
        if section == "dinner":
            body.append(f'<figure class="restaurant-map"><img src="{data_uri(RESTAURANT_MAP)}" '
                        f'alt="Map to the restaurant"></figure>')
        if open_wrapper:
            body.append("</section>")
        section, open_wrapper = None, False

    for block in blocks:
        kind = block[0]
        if kind == "h":
            _, level, title = block
            if level == 1 or (level == 2 and title.lower() == "program"):
                continue
            close_section()
            low = title.lower()
            if level == 2 and low == "location":
                section, open_wrapper = "venue", True
                body.append('<section class="venue"><div class="eyebrow">VENUE</div>')
            elif level == 2 and low.startswith(("monday", "tuesday", "wednesday")):
                parts = re.split(r"\s+[—-]\s+", title, maxsplit=1)
                day, subtitle = parts[0], parts[1] if len(parts) > 1 else ""
                cls = "day new-page" if low.startswith(NEW_PAGE_DAY) else "day"
                body.append(f'<section class="{cls}"><h2>{fmt(day)}</h2>'
                            + (f'<div class="day-subtitle">{fmt(subtitle)}</div>' if subtitle else "")
                            + "</section>")
            elif level == 2 and low == "posters":
                section, open_wrapper = "posters", True
                body.append('<section class="poster-section"><h2>Posters</h2>')
            elif level == 2 and low == "conference dinner":
                section, open_wrapper = "dinner", True
                body.append(f'<section class="dinner-section"><h2>{fmt(title)}</h2>')
            else:
                body.append(f"<h2>{fmt(title)}</h2>")
        elif kind == "p":
            text = block[1]
            if section == "venue":
                if text.startswith("**"):
                    body.append(f'<div class="venue-name">{fmt(text.strip("*"))}</div>')
                else:
                    body.append(f'<div class="venue-address">{fmt(text)}</div>')
                    close_section()
            elif section == "dinner":
                rendered = re.sub(r"^(Restaurant|Address):", r"<strong>\1:</strong>", fmt(text))
                body.append(f'<p class="dinner-copy">{rendered}</p>')
            elif re.fullmatch(r"\*\*[^*]+\*\*", text):
                continue  # the date line is used in the header
            else:
                body.append(f"<p>{fmt(text)}</p>")
        else:
            rows = block[1]
            if not rows:
                continue
            if rows[0][0].lower() == "poster":
                rows, section = rows[1:], "posters"
            if section == "posters":
                for row in rows:
                    if len(row) > 1:
                        body.append(f'<article class="poster-card"><span class="poster-number">{fmt(row[0])}</span>'
                                    f'<div class="poster-info">{fmt(row[1])}</div></article>')
                continue
            if len(rows[0]) > 1 and "session" in rows[0][1].lower():
                body.append(f'<div class="session-banner"><span class="session-time">{fmt(rows[0][0])}</span>'
                            f"<strong>{fmt(rows[0][1])}</strong></div>")
                for row in rows[1:]:
                    if len(row) > 1:
                        body.append(f'<article class="talk"><span class="time">{fmt(row[0])}</span>'
                                    f'<span class="description">{fmt(row[1])}</span></article>')
                continue
            for row in rows:
                if len(row) < 2 or row[0].lower() in ("time", "poster"):
                    continue
                classes = ["agenda-item"]
                if re.search(r"\*\*[^*]+\*\*", row[1]):  # bold name = plenary speaker
                    classes.append("plenary")
                if row[1].strip().lower() in ("lunch", "coffee break"):
                    classes.append("break")
                body.append(f'<article class="{" ".join(classes)}"><span class="time">{fmt(row[0])}</span>'
                            f'<span class="description">{fmt(row[1])}</span></article>')
    close_section()
    return body


def build_html(md_path):
    blocks = parse_markdown(md_path.read_text(encoding="utf-8").splitlines())
    title = next(b[2] for b in blocks if b[0] == "h" and b[1] == 1)
    date = next((b[1].strip("*") for b in blocks if b[0] == "p" and re.fullmatch(r"\*\*[^*]+\*\*", b[1])), "")
    css = "\n".join((ROOT / s).read_text(encoding="utf-8") for s in STYLES)
    logos = "".join(f'<img src="{data_uri(p)}" alt="{escape(Path(p).stem)}">' for p in LOGOS)
    footer = (f'<footer class="page-footer"><div class="footer-logos">{logos}</div>'
              f'<div class="footer-note">{escape(FOOTER_NOTE)}</div></footer>')
    hero_logo = f'<div class="hero-logo"><img src="{data_uri(CONFERENCE_LOGO)}" alt="Conference logo"></div>'
    header = (f'<header class="hero">{hero_logo}<div class="brand">{escape(HEADER_LABEL)}</div>'
              f'<h1>{fmt(title)}</h1><div class="date-pill">{fmt(date)}</div></header>')
    # The footer is emitted twice: Chrome otherwise omits a fixed footer on pages created by forced breaks.
    return ('<!doctype html><html><head><meta charset="utf-8">'
            f"<style>{css}</style></head><body>{header}\n" + "\n".join(render_body(blocks)) + footer + footer
            + "</body></html>")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--md", default="conference-program.md", help="source markdown (default: %(default)s)")
    parser.add_argument("--out", default="conference-program.pdf", help="output PDF (default: %(default)s)")
    parser.add_argument("--chrome", help="path to Chrome/Chromium/Edge")
    parser.add_argument("--html-only", action="store_true",
                        help="also save the intermediate HTML next to the PDF")
    args = parser.parse_args()

    md_path = Path(args.md) if Path(args.md).is_absolute() else ROOT / args.md
    out_path = Path(args.out) if Path(args.out).is_absolute() else ROOT / args.out
    chrome = find_chrome(args.chrome)
    html = build_html(md_path)

    if not out_path.parent.is_dir():
        sys.exit(f"Output directory does not exist: {out_path.parent}")

    # Write beside the destination so a failed browser run cannot leave a stale or partial PDF.
    with tempfile.TemporaryDirectory(dir=out_path.parent) as tmp:
        temp_dir = Path(tmp)
        html_path = temp_dir / "program.html"
        pdf_path = temp_dir / "program.pdf"
        html_path.write_text(html, encoding="utf-8")
        if args.html_only:
            shutil.copy(html_path, out_path.with_suffix(".html"))
        cmd = [chrome, "--headless", "--disable-gpu", "--no-first-run",
               "--no-default-browser-check", f"--user-data-dir={temp_dir / 'profile'}",
               "--no-pdf-header-footer", f"--print-to-pdf={pdf_path}", html_path.as_uri()]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
        except OSError as exc:
            sys.exit(f"Could not run browser {chrome}: {exc}")
        if result.returncode != 0:
            sys.exit(f"Browser failed with exit code {result.returncode}.\n{result.stderr}")
        if not pdf_path.is_file() or pdf_path.stat().st_size == 0:
            sys.exit(f"Browser did not create a PDF.\n{result.stderr}")
        pdf_path.replace(out_path)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
