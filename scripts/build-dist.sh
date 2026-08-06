#!/usr/bin/env bash
# build-dist.sh — regenerate the self-contained dist/ gallery bundle.
# Run from the repo root. Safe to re-run: rebuilds dist/ from scratch.
set -euo pipefail
cd "$(dirname "$0")/.."

rm -rf dist
mkdir -p dist/vendor dist/fonts dist/screenshots

cp src/picasso/index.html dist/
cp src/picasso/data.js dist/
cp src/picasso/vendor/*.js dist/vendor/ 2>/dev/null || true
cp src/picasso/vendor/LICENSE dist/vendor/ 2>/dev/null || true
cp src/picasso/fonts/*.woff2 dist/fonts/
cp src/picasso/screenshots/*.png dist/screenshots/ 2>/dev/null || true
cp src/picasso/screenshots/*.jpg dist/screenshots/ 2>/dev/null || true
cp src/picasso/screenshots/*.jpeg dist/screenshots/ 2>/dev/null || true
cp src/picasso/screenshots/*.webp dist/screenshots/ 2>/dev/null || true

# deploy note (keeps privacy guidance with the bundle)
if [ -f scripts/README-DEPLOY.md ]; then
  cp scripts/README-DEPLOY.md dist/README-DEPLOY.md
fi

echo "dist/ rebuilt: $(find dist -type f | wc -l | tr -d ' ') files, $(du -sh dist | cut -f1)"
