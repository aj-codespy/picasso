#!/usr/bin/env python3
"""
Picasso — a searchable design-inspiration library, generated from your screenshots.

Drop screenshots into src/screenshots/, run `picasso update`, and the CLI:
  1. asks which vision provider to use (OpenAI / Google / NVIDIA NIM / OpenRouter)
  2. saves your API key once to ~/.designlib/config.json (never in the repo)
  3. analyzes only NEW images (content-hash dedup — renames keep analysis)
  4. writes data/library.json, regenerates src/data.js
  5. opens src/index.html in your browser

Commands:
    picasso setup     choose provider, enter API key, pick model + screenshots folder
    picasso update    analyze new screenshots and refresh the gallery
    picasso inspire   just open the gallery page in your browser

The screenshots folder is saved in ~/.designlib/config.json during setup —
paste any folder path (e.g. ~/Desktop/shots); images are used in place and
mirrored into src/screenshots/ so the offline gallery can find them.
"""
import argparse
import base64
import getpass
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

VERSION = "1.0.0"

ROOT = Path(__file__).resolve().parent
SCREENSHOTS_DIR = ROOT / "src" / "screenshots"
JSON_FILE = ROOT / "data" / "library.json"
SYNC_SCRIPT = ROOT / "src" / "sync_data.py"
INDEX_HTML = ROOT / "src" / "index.html"
CONFIG_DIR = Path.home() / ".designlib"
CONFIG_FILE = CONFIG_DIR / "config.json"

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
CHUNK = 1024 * 1024

PROMPT = """You are a design curator building a design inspiration library. Analyze this UI screenshot in detail — the page structure, the hero, the components, and where this design pattern would be used.

Respond with a JSON object with EXACTLY these keys (no other keys):
- "title": a short human-readable title for this work, 3-9 words, no markdown (e.g. "Aurora SaaS Landing Page")
- "description": 1-2 sentences on the overall design style and intent (e.g. "A calm SaaS landing page that pairs warm cream surfaces with a burnt-orange accent; editorial spacing gives it a premium, trust-first feel.")
- "layout": the page structure in one line — nav position, hero treatment, section rhythm (e.g. "Sticky top nav, full-bleed hero, 3-column feature grid, split CTA band, 5-column footer")
- "hero": what the hero section does — headline pattern, subcopy role, CTA structure, visual treatment; use null when there is no hero
- "components": every UI element you can identify (navbar, hero, sidebar, card-grid, pricing-table, testimonial, product-gallery, form, search-bar, stats, logo, CTA-button, chat-widget, dashboard-chart, table, avatar, breadcrumb, modal, carousel, accordion, badge, tooltip, tabs, pagination, footer, ...). List 6-12 items.
- "palette": EXACTLY a JSON array of swatch objects describing the design's colors, each with EXACTLY these keys: "hex" (the 7-character hex like "#F97316"; approximate the closest dominant value if the screenshot doesn't carry it verbatim), "name" (a short human name like "burnt-orange"), "role" (base/fill, text, accent, surface, border, or the element it applies to). List 3-6 swatches covering the dominant colors of the design. (e.g. [{"hex":"#FAF7F2","name":"warm-cream","role":"base"},{"hex":"#F97316","name":"burnt-orange","role":"accent"}])
- "typography": font character — style, weight contrast, size rhythm (e.g. "serif display headlines with sans body; strong weight contrast; generous line-height")
- "tags": 5-8 design jargon tags, chosen from: minimalist, brutalist, premium, editorial, clean, dark-mode, saas, e-commerce, neumorphic, glassmorphism, bold-typography, monochrome, vibrant, playful, corporate, luxury, tech, dashboard, mobile-first, landing-page, portfolio, ai-saas, gradient, flat-design, skeuomorphic, retro, futuristic, material, apple-style, stripe-style, linear-style, notch, sidebar, bento, glass, 3d, illustration-heavy, typographic, spaced-out, dense, airy, warm, cool, earthy, pastel, neon, gold-accent
- "usage": 2-3 concrete contexts where this design could be used, each a short phrase starting with a verb (e.g. "Use for a SaaS landing page that needs to feel trustworthy", "Use as the shell for a B2B dashboard", "Use for an onboarding flow that should feel light")
- "ideas": 2-3 short creative ideas on what this design could inspire

Output ONLY the JSON object. No markdown fences, no commentary."""

# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

PROVIDERS = {
    "openai": {
        "label": "OpenAI (GPT)",
        "url": "https://api.openai.com/v1/chat/completions",
        "env_key": "OPENAI_API_KEY",
        "models": [
            "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna",
            "gpt-5.5", "gpt-5.5-pro",
            "gpt-5.4", "gpt-5.4-pro", "gpt-5.4-mini", "gpt-5.4-nano",
        ],
        "key_hint": "https://platform.openai.com/api-keys",
    },
    "google": {
        "label": "Google (Gemini)",
        "url": None,  # uses the official google-genai SDK
        "env_key": "GEMINI_API_KEY",
        "models": [
            "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite",
            "gemini-3.1-pro",
        ],
        "key_hint": "https://aistudio.google.com/apikey",
    },
    "nim": {
        "label": "NVIDIA NIM",
        "url": "https://integrate.api.nvidia.com/v1/chat/completions",
        "env_key": "NVIDIA_API_KEY",
        "models": ["nvidia/nemotron-nano-12b-v2-vl"],
        "key_hint": "https://build.nvidia.com",
    },
    "openrouter": {
        "label": "OpenRouter",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "env_key": "OPENROUTER_API_KEY",
        "models": ["google/gemini-2.5-flash:free", "qwen/qwen2.5-vl-72b-instruct"],
        "key_hint": "https://openrouter.ai/keys",
    },
}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(CHUNK)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def atomic_write(path, text):
    """Write text to path atomically: temp file in the same dir, then os.replace.

    A crash mid-write can never corrupt the target — the old file survives.
    os.replace is atomic on POSIX and NTFS (same directory, same volume).
    """
    path = Path(path)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def mime_for(path):
    ext = Path(path).suffix.lower()
    return {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(ext, "image/png")


def clean_json(text):
    """Extract the JSON object from an LLM response (fences / prose tolerant)."""
    text = re.sub(r"```(?:json)?\s*|\s*```", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object in response: {text[:200]!r}")
    return json.loads(text[start:end + 1])


def chat_completion(url, api_key, model, image_path, timeout=180):
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:{mime_for(image_path)};base64,{b64}"}},
            ],
        }],
        "max_tokens": 2048,
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=timeout)
    d = json.loads(resp.read())
    return d["choices"][0]["message"]["content"]


def google_generate_content(api_key, model, image_path, timeout=180):
    """Official google-genai SDK call — verbatim pattern from Google's docs.

    The SDK call runs in a daemon thread with a hard timeout so a hung
    connection can never block the CLI forever.
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        sys.exit("Google provider needs the official SDK.\n  Run:  pip install google-genai\n(inside the project venv:  .venv/bin/pip  or  .venv\\Scripts\\pip.exe)")

    with open(image_path, "rb") as f:
        image_bytes = f.read()
    client = genai.Client(api_key=api_key)

    def _call():
        return client.models.generate_content(
            model=model,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_for(image_path)),
                PROMPT,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
                max_output_tokens=1024,
            ),
        )

    result = {}

    def _run():
        try:
            result["ok"] = _call()
        except Exception as e:  # surfaced on the main thread below
            result["err"] = e

    worker = threading.Thread(target=_run, daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        raise RuntimeError(f"Google SDK call timed out after {timeout}s")
    if "err" in result:
        raise result["err"]
    return result["ok"].text


def analyze_image(provider, api_key, model, image_path, retries=3):
    spec = PROVIDERS[provider]
    last_err = None
    for attempt in range(retries):
        try:
            if provider == "google":
                text = google_generate_content(api_key, model, image_path)
            else:
                text = chat_completion(spec["url"], api_key, model, image_path)
            return normalize_analysis(clean_json(text))
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:300]
            last_err = f"HTTP {e.code}: {body}"
            if e.code in (429, 500, 502, 503):
                time.sleep(5 * (attempt + 1))
                continue
            raise
        except Exception as e:
            last_err = str(e)
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"Failed after {retries} retries: {last_err}")


_HEX_RE = re.compile(r"#[0-9a-fA-F]{6}\b")


def normalize_analysis(a):
    """Coerce a raw LLM analysis into the shape the gallery expects.

    Two things the UI depends on that older or lazy models omit:
    - `title`: short human-readable heading. Derive from description when the
      model didn't provide one so the modal never shows a bare "Design N".
    - `palette`: list of {hex,name,role} swatches. If the model returned prose
      (or a list without hexes), extract hex codes so the gallery renders real
      color chips instead of "—".
    """
    a = dict(a or {})

    if not a.get("title"):
        desc = (a.get("description") or "").strip()
        a["title"] = _title_from_description(desc)

    palette = a.get("palette")
    if isinstance(palette, str):
        # Legacy / prose palette: "warm cream #FAF7F2 base, ...". Yield swatches
        # only when real hex codes are present; otherwise keep the prose so the
        # gallery still has something to show (never fabricate hex).
        swatches = _hex_swatches_from_prose(palette)
        a["palette"] = swatches if swatches else palette
    elif isinstance(palette, list):
        clean = []
        for sw in palette:
            if isinstance(sw, str):
                # Model returned bare hex strings — promote to swatch objects.
                m = _HEX_RE.search(sw)
                c = m.group(0) if m else sw
                clean.append({"hex": c, "name": "", "role": ""})
            elif isinstance(sw, dict) and sw.get("hex"):
                m = _HEX_RE.search(str(sw["hex"]))
                clean.append({
                    "hex": m.group(0) if m else str(sw["hex"]),
                    "name": str(sw.get("name", "") or ""),
                    "role": str(sw.get("role", "") or ""),
                })
        a["palette"] = clean
    else:
        a["palette"] = ""

    return a


def _title_from_description(desc):
    """Headline from the first clause of a description, capped to title length."""
    if not desc:
        return "Untitled work"
    head = desc.split(".")[0].strip(" ,;:-")
    words = head.split()
    # Keep the first ~3 meaningful words of the subject, drop filler.
    if len(words) > 6:
        head = " ".join(words[:6]).rstrip(",") + "…"
    return head or "Untitled work"


def _hex_swatches_from_prose(prose):
    swatches = []
    for hexcode in re.findall(r"#[0-9a-fA-F]{6}\b", prose):
        # Grab the word just before the hex as a rough color name when present.
        m = re.search(r"([A-Za-z-]+)\s*" + re.escape(hexcode), prose)
        name = m.group(1) if m else ""
        swatches.append({"hex": hexcode, "name": name, "role": ""})
    if swatches:
        return swatches
    return []


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config():
    cfg = {}
    if CONFIG_FILE.exists():
        try:
            cfg = json.loads(CONFIG_FILE.read_text())
        except Exception:
            _recover_corrupt(CONFIG_FILE)
            cfg = {}
    # env overrides (DESIGNLIB_* or the provider's own key env)
    env_provider = os.environ.get("DESIGNLIB_PROVIDER")
    if env_provider:
        cfg["provider"] = env_provider.lower()
    env_model = os.environ.get("DESIGNLIB_MODEL")
    if env_model:
        cfg["model"] = env_model
    env_key = os.environ.get("DESIGNLIB_API_KEY")
    if env_key:
        cfg["api_key"] = env_key
    return cfg


def _recover_corrupt(path):
    """Back up an unreadable JSON file instead of silently discarding it.

    Renames <path> to <path>.corrupt-<timestamp>, warns the user, and returns
    the backup path (or None if the file couldn't be moved).
    """
    path = Path(path)
    backup = path.with_name(f"{path.name}.corrupt-{int(time.time())}")
    try:
        os.replace(path, backup)
        print(f"WARNING: {path} was unreadable — backed up to {backup} and starting fresh.")
        return backup
    except OSError:
        print(f"WARNING: {path} was unreadable and could not be backed up — starting fresh.")
        return None


def save_config(cfg):
    CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    atomic_write(CONFIG_FILE, json.dumps(cfg, indent=2))
    os.chmod(CONFIG_FILE, 0o600)


def key_from_env(provider):
    """Fall back to the provider's own well-known env var, if set."""
    spec = PROVIDERS.get(provider, {})
    return os.environ.get(spec.get("env_key", "")) or None


def pick_provider():
    print("Which vision provider should analyze your screenshots?")
    names = list(PROVIDERS.keys())
    for i, name in enumerate(names, 1):
        spec = PROVIDERS[name]
        print(f"  {i}. {spec['label']}")
    choice = input(f"Pick 1-{len(names)}: ").strip()
    try:
        return names[int(choice) - 1]
    except (ValueError, IndexError):
        sys.exit("Invalid choice.")


def pick_model(provider):
    models = PROVIDERS[provider]["models"]
    if len(models) == 1:
        print(f"  Using model: {models[0]}")
        return models[0]
    print("  Pick a model:")
    for i, m in enumerate(models, 1):
        print(f"    {i}. {m}")
    choice = input(f"  Pick 1-{len(models)}: ").strip()
    try:
        return models[int(choice) - 1]
    except (ValueError, IndexError):
        sys.exit("Invalid model choice.")


def resolve_shots_dir(flag, cfg):
    """Screenshots folder, in precedence order: --screenshots flag > saved config > default."""
    if flag:
        return Path(flag).expanduser()
    saved = cfg.get("screenshots_dir")
    if saved:
        return Path(saved).expanduser()
    return SCREENSHOTS_DIR


def pick_screenshots_dir():
    """Ask where the user's screenshots live — paste a path or press Enter for the default.

    The folder is used as-is (no copying into the project); update() mirrors
    images into src/screenshots/ so the file:// gallery still finds them.
    """
    print("\n  Screenshots folder — where your image files already live.")
    print(f"    Paste a folder path (e.g. ~/Desktop/shots), or press Enter for:\n    {SCREENSHOTS_DIR}")
    choice = input("  Folder: ").strip()
    if not choice:
        return SCREENSHOTS_DIR
    path = Path(choice).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    if not path.exists():
        print(f"    {path} doesn't exist yet — creating it.")
        path.mkdir(parents=True, exist_ok=True)
    elif not path.is_dir():
        sys.exit(f"Not a folder: {path}")
    return path


def mirror_into_gallery(images, shots_dir):
    """Make images from an external folder visible to the file:// gallery.

    index.html loads images relative to src/, so every analyzed image must
    exist under src/screenshots/. Hardlink first (no disk copy on the same
    volume), fall back to a copy. Skips files that are already there with
    identical content. No-op when the chosen folder IS the default.

    Returns (n_linked, n_copied).
    """
    if shots_dir.resolve() == SCREENSHOTS_DIR.resolve():
        return 0, 0
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    linked = copied = 0
    for img in images:
        dest = SCREENSHOTS_DIR / img.name
        if dest.exists() and sha256_file(dest) == sha256_file(img):
            continue
        if dest.exists():
            dest.unlink()
        try:
            os.link(img, dest)
            linked += 1
        except OSError:
            shutil.copy2(img, dest)
            copied += 1
    return linked, copied


def validate_key(provider, api_key, model):
    """Live-test the key with a 1x1 PNG before saving it."""
    pixel = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    # unique temp file per call — concurrent runs never collide
    fd, tmp_name = tempfile.mkstemp(suffix=".png", prefix="picasso_1x1_")
    os.close(fd)
    tmp = Path(tmp_name)
    tmp.write_bytes(pixel)
    try:
        analyze_image(provider, api_key, model, str(tmp))
        return True
    except Exception as e:
        print(f"  Key/model check failed: {e}")
        return False
    finally:
        tmp.unlink(missing_ok=True)


def cmd_setup(args):
    cfg = load_config()
    print("Picasso setup — one time, saved to ~/.designlib/config.json\n")
    provider = args.provider or pick_provider()
    spec = PROVIDERS[provider]

    api_key = cfg.get("api_key") or key_from_env(provider)
    if not api_key or args.key:
        api_key = args.key
    if not api_key:
        print(f"  Get an API key: {spec['key_hint']}")
        api_key = getpass.getpass(f"  Paste your {spec['label']} API key: ").strip()

    model = args.model or cfg.get("model") or pick_model(provider)

    if not args.skip_check:
        print("  Verifying key with a tiny test image ...")
        if not validate_key(provider, api_key, model):
            sys.exit("Key or model not working — please check and re-run setup.")

    shots_dir = args.screenshots and Path(args.screenshots).expanduser() or pick_screenshots_dir()
    if not shots_dir.is_dir():
        sys.exit(f"Not a folder: {shots_dir}")

    save_config({"provider": provider, "api_key": api_key, "model": model,
                 "screenshots_dir": str(shots_dir)})
    print(f"\nSaved. Provider: {provider} | Model: {model}")
    print(f"Screenshots folder: {shots_dir}")
    print("Put your screenshots there (png/jpg/jpeg/webp) and run:  picasso update")


# ---------------------------------------------------------------------------
# Library
# ---------------------------------------------------------------------------

def load_library():
    if JSON_FILE.exists():
        try:
            return json.loads(JSON_FILE.read_text())
        except Exception:
            _recover_corrupt(JSON_FILE)
            return {"designs": []}
    return {"designs": []}


def save_library(data):
    JSON_FILE.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(JSON_FILE, json.dumps(data, indent=2))


def next_design_number(designs):
    nums = set()
    for d in designs:
        m = re.match(r"(?:screenshots/)?design_(\d+)\.png$", d.get("path", ""))
        if m:
            nums.add(int(m.group(1)))
    n = 1
    while n in nums:
        n += 1
    return n


def resync():
    """Refresh src/data.js from library.json. Returns True on success.

    A sync failure only warns — library.json is the source of truth and the
    refresh can be retried later; it must never abort an update run.
    """
    if not SYNC_SCRIPT.exists():
        return True
    try:
        subprocess.run([sys.executable, str(SYNC_SCRIPT)], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"  WARNING: gallery data refresh failed (rc={e.returncode}) — "
              f"library.json is safe; re-run update to retry.")
        return False


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

def plan_updates(images, designs, force=False):
    """Decide which images need analysis.

    Returns (to_analyze, path_fixes, kept_names):
      to_analyze  — list of images whose content isn't in the library yet
      path_fixes  — list of (entry, new_rel_path) for renamed-but-unchanged files
      kept_names  — display names of images skipped as already-analyzed
    """
    by_hash = {d.get("sha256"): d for d in designs if d.get("sha256")}
    by_path = {d.get("path", "").replace("screenshots/", ""): d for d in designs}
    to_analyze, path_fixes, kept_names = [], [], []

    for img in images:
        rel = f"screenshots/{img.name}"
        digest = sha256_file(img)

        existing = by_hash.get(digest)
        if existing and not force:
            if existing["path"] != rel:
                path_fixes.append((existing, rel))
            else:
                kept_names.append(img.name)
            continue

        if not force:
            prev = by_path.get(img.name)
            if prev and prev.get("sha256") == digest:
                kept_names.append(img.name)
                continue

        to_analyze.append((img, digest, existing))

    return to_analyze, path_fixes, kept_names


def cmd_update(args):
    cfg = load_config()
    provider = args.provider or cfg.get("provider")
    model = args.model or cfg.get("model")
    api_key = args.key or cfg.get("api_key") or (key_from_env(provider) if provider else None)

    if not provider or not api_key or not model:
        print("Not configured yet. Run:  picasso setup")
        sys.exit(1)
    if provider not in PROVIDERS:
        sys.exit(f"Unknown provider: {provider}")

    shots_dir = resolve_shots_dir(args.screenshots, cfg)
    if not shots_dir.exists():
        print(f"Screenshots folder not found: {shots_dir}")
        print("Run:  picasso setup   # to choose the folder, or pass --screenshots DIR")
        sys.exit(1)
    images = sorted(
        [p for p in shots_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    )
    if not images:
        print(f"No images found in {shots_dir}")
        print("Put your screenshots there (png/jpg/jpeg/webp), then re-run:  picasso update")
        sys.exit(1)

    data = load_library()
    designs = data["designs"]

    if args.prune:
        known = {img.name for img in images}
        before = len(designs)
        designs = [d for d in designs if d.get("path", "").replace("screenshots/", "") in known]
        print(f"Pruned {before - len(designs)} entry(s) whose image files are gone.")

    to_analyze, path_fixes, kept_names = plan_updates(images, designs, force=args.force)

    for entry, new_rel in path_fixes:
        print(f"  {Path(new_rel).name}: renamed — keeping existing analysis")
        entry["path"] = new_rel

    total = len(images)
    kept = len(kept_names) + len(path_fixes)
    for name in kept_names:
        print(f"[{kept_names.index(name) + 1}/{total}] {name}  (already in library)")

    new_count = 0
    for idx, (img, digest, existing) in enumerate(to_analyze, 1):
        rel = f"screenshots/{img.name}"
        print(f"[{kept + idx}/{total}] {img.name}  analyzing via {provider}/{model} ...", flush=True)
        try:
            analysis = analyze_image(provider, api_key, model, str(img))
        except Exception as e:
            print(f"    FAIL: {e}")
            sys.exit(1)

        if existing and args.force:
            existing["analysis"] = analysis
            existing["sha256"] = digest
        else:
            designs.append({"path": rel, "sha256": digest, "analysis": analysis})
        new_count += 1
        print(f"    OK  tags={analysis.get('tags', [])}")
        save_library({"designs": designs})
        time.sleep(1.5)  # free-tier rate limiting

    data["designs"] = designs
    save_library(data)

    linked, copied = mirror_into_gallery(images, shots_dir)
    if linked or copied:
        print(f"  Mirrored {linked + copied} image(s) into src/screenshots/ for the gallery "
              f"({linked} hardlinked, {copied} copied).")

    resync()
    print(f"\nDone: {new_count} analyzed, {kept} kept. Library now has {len(designs)} designs.")
    if not args.no_open:
        open_gallery()


def open_gallery():
    if not INDEX_HTML.exists():
        sys.exit(f"Gallery not found: {INDEX_HTML}")
    url = INDEX_HTML.resolve().as_uri()
    print(f"Opening {url}")
    webbrowser.open(url)


def cmd_inspire(args):
    open_gallery()


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="picasso",
        description="Generate a searchable design-inspiration library from your screenshots.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    sub = parser.add_subparsers(dest="command")

    p_setup = sub.add_parser("setup", help="choose provider, enter API key, pick model + screenshots folder")
    p_setup.add_argument("--provider", choices=list(PROVIDERS.keys()))
    p_setup.add_argument("--key")
    p_setup.add_argument("--model")
    p_setup.add_argument("--screenshots", help="screenshots folder (interactive if omitted)")
    p_setup.add_argument("--skip-check", action="store_true", help="skip the live key test")
    p_setup.set_defaults(fn=cmd_setup)

    p_update = sub.add_parser("update", help="analyze new screenshots and refresh the gallery")
    p_update.add_argument("--provider", choices=list(PROVIDERS.keys()))
    p_update.add_argument("--key")
    p_update.add_argument("--model")
    p_update.add_argument("--screenshots", help="override the screenshots folder")
    p_update.add_argument("--force", action="store_true", help="re-analyze every image")
    p_update.add_argument("--prune", action="store_true", help="drop entries whose files are gone")
    p_update.add_argument("--no-open", action="store_true", help="don't open the gallery at the end")
    p_update.set_defaults(fn=cmd_update)

    p_inspire = sub.add_parser("inspire", help="open the gallery page in your browser")
    p_inspire.set_defaults(fn=cmd_inspire)

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        print("\nQuick start:\n  picasso setup    # provider + API key + model (once)\n  picasso update   # analyze new screenshots\n  picasso inspire  # open the gallery")
        sys.exit(0)

    try:
        args.fn(args)
    except KeyboardInterrupt:
        print("\nInterrupted. Library saved so far — re-run update to continue.")
        sys.exit(130)


if __name__ == "__main__":
    main()
