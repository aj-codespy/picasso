#!/usr/bin/env python3
"""Sync data/library.json -> src/data.js so index.html works via file:// (no server needed)."""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(ROOT, "data", "library.json")
OUT_PATH = os.path.join(ROOT, "src", "data.js")

HEX_RE = re.compile(r"#[0-9a-fA-F]{6}\b")


def normalize_analysis(analysis):
    """Coerce an analysis record into the gallery shape (title + swatch list).

    Mirrors designlib.normalize_analysis so the file:// gallery always gets the
    same shape whether the record came from a fresh `picasso update` or from an
    older library.json that predates the structured palette.
    """
    a = dict(analysis or {})

    if not a.get("title"):
        desc = (a.get("description") or "").strip()
        head = desc.split(".")[0].strip(" ,;:-") if desc else ""
        words = head.split()
        if not words:
            a["title"] = "Untitled work"
        else:
            a["title"] = " ".join(words[:6]).rstrip(",") + "…" if len(words) > 6 else head

    palette = a.get("palette")
    swatches = []
    if isinstance(palette, list):
        for sw in palette:
            if isinstance(sw, dict) and sw.get("hex"):
                m = HEX_RE.search(str(sw["hex"]))
                swatches.append({
                    "hex": m.group(0) if m else str(sw["hex"]),
                    "name": str(sw.get("name", "") or ""),
                    "role": str(sw.get("role", "") or ""),
                })
    elif isinstance(palette, str):
        for hexcode in HEX_RE.findall(palette):
            m = re.search(r"([A-Za-z-]+)\s*" + re.escape(hexcode), palette)
            swatches.append({"hex": hexcode, "name": m.group(1) if m else "", "role": ""})
    # Prefer swatches when hex is present; otherwise keep the prose string so
    # the gallery still shows something (never fabricate hex).
    a["palette"] = swatches if swatches else palette
    return a


def main():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    designs = data.get("designs", [])
    # Normalize: each entry must have file/description/tags/components/palette/ideas
    normalized = []
    for d in designs:
        analysis = normalize_analysis(d.get("analysis"))
        entry = {
            "file": d.get("path", d.get("file", "")).replace("screenshots/", ""),
            "title": analysis.get("title", ""),
            "description": analysis.get("description", d.get("description", "")),
            "layout": analysis.get("layout", ""),
            "hero": analysis.get("hero", ""),
            "typography": analysis.get("typography", ""),
            "tags": analysis.get("tags", d.get("tags", [])),
            "components": analysis.get("components", d.get("components", [])),
            "palette": analysis.get("palette", []),
            "usage": analysis.get("usage", []),
            "ideas": analysis.get("ideas", d.get("ideas", [])),
        }
        if entry["file"]:
            normalized.append(entry)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("// Auto-generated from data/library.json — do not edit by hand.\n")
        f.write("window.DESIGNS = ")
        f.write(json.dumps(normalized, indent=2, ensure_ascii=False))
        f.write(";\n")
    print(f"OK: {len(normalized)} designs -> {OUT_PATH}")


if __name__ == "__main__":
    main()