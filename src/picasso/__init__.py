"""Picasso — a searchable design-inspiration library (CLI + static gallery).

Gallery: picasso inspire
CLI:     picasso seed | analyze | update | resync | --version
"""

from .designlib import main, VERSION

__all__ = ["main", "VERSION"]
__version__ = VERSION
