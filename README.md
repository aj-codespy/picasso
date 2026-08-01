# Picasso — your personal design-inspiration library

Drop screenshots into a folder, run one command, and Picasso turns them into a
beautiful, searchable design gallery — every screenshot analyzed by a vision
model for its style, components, palette, and ideas. Browse it like a museum:
hover to focus, click to enter the viewing room, filter by design vocabulary.

![Picasso](docs/screenshot.png)

## How it works

1. **You drop screenshots** into `src/screenshots/` (any `.png` / `.jpg` / `.jpeg` / `.webp`)
2. **You run** `picasso update`
3. **Picasso scans only the new ones** — content-hash dedup means re-runs are instant,
   renames keep their analysis, and replaced files are detected and re-analyzed
4. **A vision model writes the library** — `data/library.json` with description,
   tags, components, palette, and ideas per screenshot
5. **Your gallery opens in the browser** — double-click `src/index.html` anytime,
   works fully offline (fonts bundled, no server needed)

## Quick start

```bash
# 1. Get the code
git clone <this-repo-url> && cd picasso

# 2. Install the `picasso` command (symlinks into ~/.local/bin)
./install.sh

# 3. One-time setup: pick a provider, paste your API key, pick a model
picasso setup

# 4. Drop screenshots into src/screenshots/, then:
picasso update
```

The first `picasso` run creates its own Python virtual environment (`.venv`) —
no manual Python setup.

## Providers

Pick any one at `picasso setup` — the CLI remembers it.

| Provider | Models | Key | Free tier? |
|---|---|---|---|
| **OpenAI** | `gpt-4o`, `gpt-4.1`, `gpt-4.1-mini` | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | paid |
| **Google** | `gemini-2.5-flash`, `gemini-2.5-pro` | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | yes |
| **NVIDIA NIM** | `nemotron-nano-12b-v2-vl` | [build.nvidia.com](https://build.nvidia.com) | yes |
| **OpenRouter** | `gemini-2.5-flash:free`, `qwen2.5-vl-72b` | [openrouter.ai/keys](https://openrouter.ai/keys) | yes |

- **Google** uses Google's official `google-genai` SDK (installed automatically in the venv).
- **Keys are stored in `~/.designlib/config.json`** (outside the project) — they can
  never leak into a git commit. Environment variables `DESIGNLIB_PROVIDER`,
  `DESIGNLIB_API_KEY`, `DESIGNLIB_MODEL` override it.
- Your screenshots are sent **only** to the provider you chose.

## Commands

```bash
picasso setup      # choose provider, enter API key, pick model (one time)
picasso update     # analyze NEW screenshots, refresh the gallery
picasso inspire    # just open the gallery page
```

### `picasso update` flags

| Flag | What it does |
|---|---|
| `--force` | re-analyze every image (e.g. after switching to a better model) |
| `--prune` | drop library entries whose image files were deleted |
| `--no-open` | don't open the browser at the end |
| `--screenshots DIR` | scan a different folder |
| `--provider` / `--model` / `--key` | override the saved config for one run |

## The gallery

- **Wall view** — works in flex rows; hovering a work grows it to ~5/8 of its
  row while its neighbors recede (nothing dims). Click opens the viewing room.
- **Catalogue view** — list with full descriptions.
- **Browse by vocabulary** — every analyzed tag becomes a filter chip with counts.
- **Search** — instant full-text filter across descriptions and tags.
- **Marquee** — the tag cloud scrolls by; pauses on hover; respects
  `prefers-reduced-motion`.

## Project layout

```
picasso/
├── designlib.py            # the CLI (stdlib-only; Google SDK optional)
├── picasso                 # launcher — creates .venv on first run
├── install.sh              # symlinks `picasso` into ~/.local/bin
├── src/
│   ├── index.html          # the gallery — self-contained, file:// works
│   ├── screenshots/        # ← drop your screenshots here (never committed)
│   ├── data.js             # regenerated from the library
│   └── sync_data.py        # library.json → data.js bridge
├── data/library.json       # the generated library
└── tests/                  # unit tests (no network)
```

## Development

```bash
python3 -m unittest tests.test_designlib -v   # 14 tests, no network
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
