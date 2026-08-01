#!/usr/bin/env python3
"""Sync data/library.json -> src/data.js so index.html works via file:// (no server needed)."""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(ROOT, "data", "library.json")
OUT_PATH = os.path.join(ROOT, "src", "data.js")

def main():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    designs = data.get("designs", [])
    # Normalize: each entry must have file/description/tags/components/palette/ideas
    normalized = []
    for d in designs:
        entry = {
            "file": d.get("path", d.get("file", "")).replace("screenshots/", ""),
            "description": d.get("analysis", {}).get("description", d.get("description", "")),
            "tags": d.get("analysis", {}).get("tags", d.get("tags", [])),
            "components": d.get("analysis", {}).get("components", d.get("components", [])),
            "palette": d.get("analysis", {}).get("palette", d.get("palette", "")),
            "ideas": d.get("analysis", {}).get("ideas", d.get("ideas", [])),
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
