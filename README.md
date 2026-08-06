# Picasso — your personal design-inspiration library

*Version 1.7.0 (`picasso --version`) — the "delight" release*

Drop screenshots into a folder, run one command, and Picasso turns them into a
beautiful, searchable design gallery — every screenshot analyzed by a vision
model for its style, components, palette, and ideas. Browse it like a museum:
hover to focus, click to enter the viewing room, filter by design vocabulary.

![Picasso](docs/screenshot.png)

## How it works

1. **You point Picasso at your screenshots folder** — during setup you paste any path
   (e.g. `~/Desktop/shots`); your images stay where they are, nothing is copied
2. **You run** `picasso update`
3. **Picasso scans only the new ones** — content-hash dedup means re-runs are instant,
   renames keep their analysis, and replaced files are detected and re-analyzed
4. **A vision model writes the library** — `data/library.json` with a full curator read per
   screenshot: description, layout structure, hero analysis, components, palette (with hex),
   typography, design-jargon tags, **use cases** ("use for a…"), and creative ideas
5. **Your gallery opens in the browser** — double-click `src/index.html` anytime,
   works fully offline (fonts bundled, no server needed)

## Quick start

```bash
# 1. Get the code
git clone https://github.com/aj-codespy/picasso && cd picasso

# 2. Install the `picasso` command (symlinks into ~/.local/bin)
./install.sh

# 3. One-time setup: pick a provider, paste your API key, pick a model,
#    and paste the path of your screenshots folder
picasso setup

# 4. Point Picasso at your screenshots (any .png / .jpg / .jpeg / .webp):
picasso update
```

The first `picasso` run creates its own Python virtual environment (`.venv`) —
no manual Python setup.

### Windows

```bat
:: 1. Install the `picasso` command (copies picasso.cmd into a PATH folder)
install.bat

:: 2. Open a NEW terminal, then:
picasso setup
picasso update
```

`install.bat` adds the folder to your user PATH via PowerShell (no truncation).
Requires Python 3.9+ from [python.org](https://www.python.org/downloads/) —
the launcher prefers the `py` launcher, so the Microsoft Store alias stub is
not an issue. Everything else is identical to macOS/Linux. The full test suite
runs on Windows too (`python -m unittest tests.test_designlib`).

## Providers

Pick any one at `picasso setup` — the CLI remembers it.

| Provider | Models | Key | Free tier? |
|---|---|---|---|
| **OpenAI** | `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.5`, `gpt-5.5-pro`, `gpt-5.4`, `gpt-5.4-pro`, `gpt-5.4-mini`, `gpt-5.4-nano` | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | paid |
| **Google** | `gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-pro` | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | yes |
| **NVIDIA NIM** | `nemotron-nano-12b-v2-vl` | [build.nvidia.com](https://build.nvidia.com) | yes |
| **OpenRouter** | `google/gemini-2.5-flash:free`, `qwen/qwen2.5-vl-72b-instruct` | [openrouter.ai/keys](https://openrouter.ai/keys) | yes |

- **Google** uses Google's official `google-genai` SDK (installed automatically in the venv).
- **Keys are stored in `~/.designlib/config.json`** (outside the project) — they can
  never leak into a git commit. Environment variables `DESIGNLIB_PROVIDER`,
  `DESIGNLIB_API_KEY`, `DESIGNLIB_MODEL` override it.
- **Your screenshots folder is also saved in that config** — paste any path during
  `picasso setup` (e.g. `~/Desktop/shots`) and your images are used in place, no
  copying into the project. `update` mirrors them into `src/screenshots/`
  (hardlink first, copy fallback) so the offline gallery can still find them.
- Your screenshots are sent **only** to the provider you chose.

## Commands

```bash
picasso setup      # choose provider, enter API key, pick model + screenshots folder (one time)
picasso update     # analyze NEW screenshots, refresh the gallery
picasso seed       # load a bundled sample collection to explore before analyzing your own
picasso inspire    # just open the gallery page
```

`picasso seed` is opt-in and privacy-safe. Launching it loads 20 sample works
(analysis metadata only — titles, tags, palette, ideas) so you can see how a
curated Picasso gallery looks before you've analyzed anything. The samples'
artwork is never bundled: works show a quiet "artwork stays yours" placeholder
until you run `picasso update` on your own screenshots. It refuses to overwrite
a library that already has works unless you pass `--force`.

### `picasso update` flags

| Flag | What it does |
|---|---|
| `--force` | re-analyze every image (e.g. after switching to a better model) |
| `--prune` | drop library entries whose image files were deleted |
| `--no-open` | don't open the browser at the end |
| `--screenshots DIR` | scan a different folder (overrides the one saved in setup) |
| `--provider` / `--model` / `--key` | override the saved config for one run |

## The gallery

- **Wall view** — works hang in rows; hovering a work focuses it with a
  cursor-tracked zoom and a soft spotlight (transform-only — zero layout
  shift). Click a work to enter its viewing room via a FLIP blow-up animation.
- **Viewing room** — full-size detail with catalogue number, ink placard,
  description, components, palette swatches, typography, use cases, and ideas.
  Navigate with `←` / `→` or the room nav; close with `Esc`. Deep-link any
  work: `#design-07`.
- **Browse by vocabulary** — every analyzed tag becomes a filter chip with
  counts; **browse by structure** — the component taxonomy (Navigation,
  Content, Interaction, Data, Identity) filters OR-within, AND-across tags
  and search. Every filter combo is a shareable deep link
  (`#tag=clean&facets=Data&q=dashboard`).
- **Search** — debounced instant full-text filter across descriptions and
  tags, with result counts and per-term highlighting. `/` or `Cmd/Ctrl-K`
  focuses search from anywhere.
- **Favorites & notes** — star any work and jot private notes; both persist
  in a user-owned `meta.json` overlay.
- **Marquee** — the tag cloud scrolls by and pauses on hover; the whole
  gallery respects `prefers-reduced-motion`.
- **Motion system** — GSAP (vendored locally, no CDN) powers the spotlight,
  scroll-row hang, FLIP modal, hero word-split entrance, chip cascade, and a
  pinned How-it-works reveal — with a film-grain finish and gallery
  baseboard. Falls back to a fully-static, animated gallery if GSAP is absent
  or reduced motion is on.

## Project layout

```
picasso/
├── designlib.py            # the CLI (stdlib-only; Google SDK optional)
├── picasso                 # launcher (macOS/Linux) — creates .venv on first run
├── picasso.cmd             # launcher (Windows) — same behavior
├── install.sh              # symlinks `picasso` into ~/.local/bin (macOS/Linux)
├── install.bat             # adds `picasso` to user PATH (Windows)
├── src/
│   ├── index.html          # the gallery — self-contained, file:// works
│   ├── screenshots/        # ← gallery mirror (hardlinks of your folder; never committed)
│   ├── data.js             # regenerated from the library
│   └── sync_data.py        # library.json → data.js bridge
├── data/library.json       # the generated library
└── tests/                  # unit tests (no network)
```

## Development

```bash
python3 -m unittest tests.test_designlib -v   # 57 tests, no network
```

## FAQ

**Is it free?** The tool is free. Vision models: NVIDIA NIM and OpenRouter free
tiers work; Google has a free tier; OpenAI is paid. A handful of images costs
nothing on free tiers.

**Is my data private?** Your screenshots never leave your machine except to the
vision provider you explicitly chose. Nothing is uploaded to a Picasso server
(there is none).

**Do I need to re-analyze everything when I add images?** No. Only new or
changed images are analyzed (content-hash dedup). 1,000s of unchanged images
are skipped in seconds.

**Can I use my own model?** The curated lists contain verified-working vision
models per provider. `--force` re-analyzes with a newly chosen model.

## License

[MIT](LICENSE)
