# Picasso — static gallery bundle (v1.7-delight)

This folder is the complete, self-contained gallery. No build step — it runs
as pure static files (Google Fonts / GSAP are bundled locally; fully offline).

## Deploy (drag-drop)

- **Vercel** — app.vercel.com → *Add New* → *Project* → *Import* → drop this
  folder; Framework: *Other*. Or `vercel` from inside this folder.
- **Netlify** — app.netlify.com → *Add new site* → *Deploy manually* → drop
  this folder.
- **GitHub Pages** — push `dist/` contents to a `gh-pages` branch.

No build command, no output directory override needed.

## Note on privacy

This bundle **contains your own screenshots** (`screenshots/*.png`). Deploying
it publishes them to the host you choose. The git repo deliberately ignores
screenshots (see `.gitignore`) — this folder is a local mirror for you to
deploy or share at your discretion. Rebuild it anytime (from the repo root):

```bash
./scripts/build-dist.sh   # regenerate dist/ from src/
```

(Or recreate manually: copy `src/index.html`, `src/data.js`,
`src/vendor/`, `src/fonts/`, and `src/screenshots/` into `dist/`.)

## Deep links work out of the box

- `#design-07` opens that work's room.
- `#tag=clean&facets=Data&q=dashboard` restores a filtered wall.
- Back/forward and pasted links all work (hashchange-driven).