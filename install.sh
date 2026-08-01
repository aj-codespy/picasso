#!/usr/bin/env bash
# Install the `picasso` command into ~/.local/bin so it works from any directory.
set -euo pipefail
cd "$(dirname "$0")"

TARGET="${PICASSO_BIN:-$HOME/.local/bin}"
mkdir -p "$TARGET"
ln -sf "$PWD/picasso" "$TARGET/picasso"
chmod +x "$PWD/picasso"

case ":$PATH:" in
    *":$TARGET:"*) ;;
    *) echo "NOTE: $TARGET is not on your PATH. Add it with:"
       echo "  export PATH=\"$TARGET:\$PATH\"" ;;
esac

echo "Installed. Try:  picasso inspire"
