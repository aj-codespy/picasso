"""Allow `python -m picasso` (and pip console scripts)."""

import sys

from .designlib import main

if __name__ == "__main__":
    sys.exit(main())
