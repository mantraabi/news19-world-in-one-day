# AGENTS.md

## What this repository is

The entry for the make.fun competition `news-image-20261119`: one 1024×1024 PNG that
sums up the world news of Thursday 19 November 2026 — 32 stories, six regions, one
broadsheet-style page.

## How it is built

- `tools/render.py` (Pillow, authoring time only) composes the page at 2048×2048,
  downsamples once with Lanczos, and writes `entry.png`, `preview-300.png` and
  `layout-audit.json`. All story text, labels and illustrations live in that file —
  the six drawings are geometric primitives, not images loaded from disk.
- `entry.png` is committed. It is the artwork; it is not generated during the graded run.
- `main.py` is the graded entrypoint and stays **standard library only**. It validates the
  committed PNG by hand (signature, a 1024×1024 IHDR, CRC32 on every chunk, IEND, and a
  decompressible image stream) and copies those exact bytes to
  `$MAKEFUN_OUTPUT_DIR/entry.png`. Do not add a Pillow import, a network call, or a render
  step to it — the grading image has no third-party packages.

## Rules for changes

- Keep every line on the page faithful to the reporting recorded in `SOURCES.md`. Use the
  numbers as reported, attribute a single-outlet claim to that outlet, and do not add an
  adjective the report does not support.
- Nothing on the page may describe an event that happened before 19 November 2026.
- After any edit to the page, run `python3 tools/render.py` and check that
  `layout-audit.json` reports zero out-of-cell boxes, zero overlaps, zero truncations and
  zero shrunk strings, then look at `preview-300.png`: the lead, the genocide ruling, the
  IPO, the bridge, the tankers and the game launch must all still be readable at 300 px.
- `README.md` and `SOURCES.md` are in English; keep them that way.
