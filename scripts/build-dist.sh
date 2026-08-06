#!/usr/bin/env bash
# build-dist.sh — regenerate the self-contained dist/ gallery bundle.
# Run from the repo root. Safe to re-run: rebuilds dist/ from scratch.
set -euo pipefail
cd "$(dirname "$0")/.."

rm -rf dist
mkdir -p dist/vendor dist/fonts dist/screenshots

cp src/index.html dist/
cp src/data.js dist/
cp src/vendor/*.js dist/vendor/ 2>/dev/null || true
cp src/vendor/LICENSE dist/vendor/ 2>/dev/null || true
cp src/fonts/*.woff2 dist/fonts/
cp src/screenshots/*.png dist/screenshots/ 2>/dev/null || true
cp src/screenshots/*.jpg dist/screenshots/ 2>/dev/null || true
cp src/screenshots/*.jpeg dist/screenshots/ 2>/dev/null || true
cp src/screenshots/*.webp dist/screenshots/ 2>/dev/null || true

# deploy note (keeps privacy guidance with the bundle)
if [ -f scripts/README-DEPLOY.md ]; then
  cp scripts/README-DEPLOY.md dist/README-DEPLOY.md
fi

echo "dist/ rebuilt: $(find dist -type f | wc -l | tr -d ' ') files, $(du -sh dist | cut -f1)"
