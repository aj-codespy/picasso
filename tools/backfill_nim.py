#!/usr/bin/env python3
"""A9 backfill: enrich analysis records for the sample library via NIM vision.

Reads data/library.json, sends each screenshot to NVIDIA NIM, and writes back
real-color hex swatches + the fields the gallery shows empty (layout, hero,
typography, usage) + a short human title. Resume-safe: skips designs that
already have all target fields filled. NEVER commits images.
"""
import base64, json, os, re, sys, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
# The gallery data lives in the picasso package, not beside this tool script.
PKG = os.path.join(os.path.dirname(ROOT), "src", "picasso")
LIB = os.path.join(PKG, "data", "library.json")
SHOTS = os.path.join(PKG, "screenshots")

# Prefer env-injected key; fall back to the real hermes .env so the script
# runs both under CI-style env and on the dev machine.
def get_key():
    k = os.environ.get("NVIDIA_API_KEY")
    if k:
        return k
    env = os.path.expanduser("~/.hermes/.env")
    try:
        for line in open(env):
            if line.startswith("NVIDIA_API_KEY="):
                return line.strip().split("=", 1)[1]
    except OSError:
        pass
    sys.exit("NVIDIA_API_KEY not found (set env or add to ~/.hermes/.env)")

API_KEY = get_key()
MODEL = "nvidia/nemotron-nano-12b-v2-vl"
ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"

PROMPT = """You are analyzing a UI screenshot for a design-inspiration gallery. Return ONLY a JSON object (no markdown fences, no commentary) with EXACTLY these keys:
{
  "title": "short 3-6 word human headline for the design",
  "layout": "one phrase describing the layout e.g. 'sidebar + card grid'",
  "hero": "one phrase describing the hero/primary section",
  "typography": "one phrase on the type treatment e.g. 'bold sans hero on serif body'",
  "palette": [
    {"hex": "#RRGGBB", "name": "background", "role": "background"},
    {"hex": "#RRGGBB", "name": "text", "role": "text"},
    {"hex": "#RRGGBB", "name": "accent", "role": "accent"}
  ],
  "usage": ["one concrete use case this design fits"]
}
Rules:
- palette: 3-5 REAL colors actually seen in the screenshot. hex MUST be a real #RRGGBB code you read from the image (never invent one).
- title: short and human, no leading article filler ('A clean...' is wrong; 'Clean document manager' is right).
- Each palette entry: name is a short role word (background/surface/text/accent), role is one of background|text|accent|surface.
- usage: 1-2 concise use cases.
Keep every value terse."""


def analyze(path):
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}},
        ]}],
        "max_tokens": 900,
        "temperature": 0.2,
    }
    for attempt in range(4):
        req = urllib.request.Request(
            ENDPOINT, data=json.dumps(payload).encode(),
            headers={"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"})
        try:
            resp = urllib.request.urlopen(req, timeout=180)
            text = json.loads(resp.read())["choices"][0]["message"]["content"]
            return text
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503):
                time.sleep(5 * (attempt + 1))
                continue
            raise
        except Exception:
            if attempt == 3:
                raise
            time.sleep(3)
    raise RuntimeError("exhausted retries")


def parse_json(text):
    m = re.search(r"\{.*\}", text, re.S)  # first { to last }
    if not m:
        return None
    s = m.group(0).replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return None


def clean_swatches(palette):
    out = []
    for sw in (palette or []):
        if not isinstance(sw, dict):
            continue
        h = re.search(r"#[0-9a-fA-F]{6}", str(sw.get("hex", "")))
        if not h:
            continue
        out.append({
            "hex": h.group(0),
            "name": str(sw.get("name", "") or "")[:24],
            "role": str(sw.get("role", "") or "")[:20],
        })
    return out


def main():
    lib = json.load(open(LIB, encoding="utf-8"))
    designs = lib["designs"]
    updated = 0
    for i, d in enumerate(designs, 1):
        a = d.get("analysis", {})
        # Resume: skip already-enriched records.
        have = all(a.get(k) for k in ("layout", "hero", "typography", "usage"))
        have_pal = isinstance(a.get("palette"), list) and any(
            isinstance(s, dict) and s.get("hex") for s in a["palette"])
        if have and have_pal and a.get("title"):
            print(f"[{i}/{len(designs)}] SKIP {d['path']} (already enriched)")
            continue
        img = os.path.join(SHOTS, os.path.basename(d["path"]))
        print(f"[{i}/{len(designs)}] NIM {d['path']} ...", flush=True)
        text = analyze(img)
        j = parse_json(text)
        if not j:
            print(f"  !! unparseable response: {text[:160]!r}")
            continue
        # merge only the enriched fields, preserving existing description/tags/etc.
        a["title"] = str(j.get("title") or a.get("title") or "").strip()[:80]
        a["layout"] = str(j.get("layout") or "")[:100]
        a["hero"] = str(j.get("hero") or "")[:100]
        a["typography"] = str(j.get("typography") or "")[:100]
        sw = clean_swatches(j.get("palette"))
        if sw:
            a["palette"] = sw
        a["usage"] = [str(x)[:80] for x in (j.get("usage") or [])][:3]
        json.dump(lib, open(LIB, "w", encoding="utf-8"), indent=2)  # save each success
        updated += 1
        time.sleep(1.2)  # rate-limit
    print(f"\nDONE: updated {updated} of {len(designs)}")


if __name__ == "__main__":
    main()
