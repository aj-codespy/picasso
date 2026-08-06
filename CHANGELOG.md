# Changelog

All notable changes to **Picasso** are documented here. Format: [Keep a Changelog](https://keepachangelog.com/)
— Added / Changed / Fixed, grouped by version. Versions track the `picasso --version` release.

## [1.8.0] — 2026-08-06

### Added
- **Installable Python package** — `picasso` is now a real PyPI package
  (`pip install picasso-design-gallery`). Ships sdist + wheel, a `picasso`
  console entry point, and `python -m picasso`.
- **`pyproject.toml`** — setuptools build config; gallery assets (index.html,
  data.js, fonts, vendored GSAP, seed data) bundled into the wheel.
- **CHANGELOG.md** (this file).

### Changed
- **Source layout** — the CLI + gallery moved into an importable
  `src/picasso/` package. `ROOT` now resolves identically whether ran from a
  repo checkout or an installed site-packages copy; launchers (macOS/Linux
  `picasso`, Windows `picasso.cmd`) run `python -m picasso`.
- Version bumped `1.7.0` → `1.8.0`.

### Security / privacy
- **User screenshots are never shipped in the package.** The wheel bundles
  only the gallery's `screenshots/README.md` placeholder; the real images stay
  on your machine and show as "Artwork stays yours — add your screenshot" in
  the gallery until you run `picasso update`. Verified post-build.

## [1.7.0] — 2026-08-06 — "the delight release"

### Added
- **GSAP motion system** (vendored locally, no CDN) — hall of the spotlight
  transform-only hover, scroll row hang + top progress rule, FLIP modal with
  full a11y contract, hero word-split entrance (font-aware), chip cascade,
  pinned How-it-works reveal, film-grain finish, gallery baseboard.
- **Deep links** — `#design-07` opens a work's room; `#tag=…&facets=…&q=…`
  restores a filtered wall; back/forward + pasted links work.
- **Facet taxonomy** in `sync_data.py` (Navigation / Content / Interaction /
  Data / Identity) + facet filter UI (multi-select OR-within, AND-across).
- **Static-host audit + self-contained `dist/` bundle** — everything local,
  fully offline; `scripts/build-dist.sh` rebuilds it.

### Fixed
- Search: debounce, live result counts ("13 of 20 works"), clear semantics,
  `/` + Cmd/Ctrl+K focus, Esc blur, prev/next walk, event-target guards.

## [1.6.0] — 2026-08-01 — "Trust & Truth"

### Added
- `picasso setup` — provider (OpenAI / Google / NVIDIA NIM / OpenRouter,
  Google via official SDK), API-key prompt, model + screenshots-folder pick.
- `picasso seed` — opt-in bundled sample collection (`--force` to overwrite).
- `picasso update` — content-hash dedup (renames/nothing, replaced files
  re-analyzed), mirror-into-gallery via hardlink-with-copy-fallback.
- **Curator's Room** empty state for a fresh gallery.

### Security
- API keys stored only in `~/.designlib/config.json` (never in the repo);
  screenshots sent only to the chosen provider.

## [1.5.0] — 2026-07-31 — "hardened"

- Windows launcher (`picasso.cmd`), POSIX/macOS launcher symlink resolution,
  `install.bat` / `install.sh`, corrupt-file recovery, pinned dependencies.

## [1.0.0] — 2026-07-27

- Initial gallery skeleton: static `index.html` with flat works grid, search,
  favorites, notes. Single-file `designlib.py` CLI.