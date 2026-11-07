# Rebuilding the conference program

The program is built from `conference-program.md` using Python 3.8 or newer
and Google Chrome, Chromium, or Microsoft Edge. No Python packages are needed.

From this directory, run:

```sh
python3 build_pdf.py
```

This replaces `conference-program.pdf` after a successful build. If the browser
is not detected, provide its executable path, for example on macOS:

```sh
python3 build_pdf.py --chrome "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
```

Alternatively, set `CHROME_PATH` to the browser executable. To choose another
source or destination, or save the intermediate HTML alongside the PDF:

```sh
python3 build_pdf.py --md conference-program.md --out conference-program-new.pdf --html-only
```

Relative paths are resolved from this directory. The output directory must
already exist. `--html-only` also creates the PDF; it keeps the HTML for
inspection. Run `python3 build_pdf.py --help` for all options.

## Editing

- Edit `conference-program.md` for the meeting title, date, location,
  schedule, posters, and dinner details. The script supports the headings,
  paragraphs, simple emphasis, and pipe tables used in that file; it is not a
  general-purpose Markdown renderer.
- Edit `style/theme.css` for colors and fonts, and `style/program.css` for
  layout and print styling.
- The image paths, footer acknowledgment, header label, and forced day page
  break are configured near the top of `build_pdf.py`. Keep
  `conference_logo.png`, `restaurant_location.png`, and the four referenced
  files in `logos/` available when building.

Review the PDF after substantive edits: content length, installed fonts, and
browser version can affect pagination. The generated HTML embeds the styles and
images, so it can also be opened independently in a browser.
