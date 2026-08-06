#!/usr/bin/env python3
"""Unit tests for designlib.py — pure logic only, no network calls."""
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import types as pyt
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import picasso.designlib as dl
import picasso.sync_data as sync_data


class TestProviderRegistry(unittest.TestCase):
    def test_model_menu_has_all_models(self):
        for spec in dl.PROVIDERS.values():
            self.assertGreaterEqual(len(spec["models"]), 1)

    def test_unique_model_ids(self):
        seen = set()
        for spec in dl.PROVIDERS.values():
            for m in spec["models"]:
                self.assertNotIn(m, seen)
                seen.add(m)


class TestShotsDir(unittest.TestCase):
    def test_flag_wins_over_config(self):
        cfg = {"screenshots_dir": "/tmp/config_dir"}
        self.assertEqual(dl.resolve_shots_dir("/tmp/flag_dir", cfg), Path("/tmp/flag_dir"))

    def test_config_wins_over_default(self):
        cfg = {"screenshots_dir": "/tmp/config_dir"}
        self.assertEqual(dl.resolve_shots_dir(None, cfg), Path("/tmp/config_dir"))

    def test_default_when_nothing_saved(self):
        self.assertEqual(dl.resolve_shots_dir(None, {}), dl.SCREENSHOTS_DIR)

    def test_tilde_expansion(self):
        cfg = {"screenshots_dir": "~/DesignShots"}
        self.assertEqual(dl.resolve_shots_dir(None, cfg), Path.home() / "DesignShots")

    def test_mirror_into_gallery(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shots = root / "shots"
            shots.mkdir()
            gallery = root / "gallery"
            (shots / "a.png").write_bytes(b"aaa")
            (shots / "b.png").write_bytes(b"bbb")
            images = [shots / "a.png", shots / "b.png"]

            old = dl.SCREENSHOTS_DIR
            dl.SCREENSHOTS_DIR = gallery
            try:
                linked, copied = dl.mirror_into_gallery(images, shots)
                self.assertEqual((linked, copied), (2, 0))
                self.assertTrue((gallery / "a.png").exists())
                self.assertTrue((gallery / "b.png").exists())

                # second run: nothing new to mirror
                self.assertEqual(dl.mirror_into_gallery(images, shots), (0, 0))
            finally:
                dl.SCREENSHOTS_DIR = old

    def test_mirror_noop_for_default_folder(self):
        with tempfile.TemporaryDirectory() as td:
            shots = Path(td) / "shots"
            shots.mkdir()
            (shots / "a.png").write_bytes(b"aaa")
            self.assertEqual(dl.mirror_into_gallery([shots / "a.png"], dl.SCREENSHOTS_DIR), (0, 0))


class TestCleanJson(unittest.TestCase):
    def test_bare_json(self):
        out = dl.clean_json('{"description": "hi", "tags": ["clean"]}')
        self.assertEqual(out["tags"], ["clean"])

    def test_fenced_json(self):
        out = dl.clean_json('```json\n{"description": "hi"}\n```')
        self.assertEqual(out["description"], "hi")

    def test_prose_wrap(self):
        out = dl.clean_json('Here you go:\n{"description": "x"}\nHope that helps')
        self.assertEqual(out["description"], "x")

    def test_no_json_raises(self):
        with self.assertRaises(ValueError):
            dl.clean_json("sorry, no json here")

    def test_json_array_with_nested_braces(self):
        out = dl.clean_json('{"description": "a {b} c", "tags": ["x"]}')
        self.assertEqual(out["description"], "a {b} c")


class TestSha256(unittest.TestCase):
    def test_hash_roundtrip(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"hello picasso")
            path = f.name
        try:
            h1 = dl.sha256_file(path)
            self.assertEqual(len(h1), 64)
            with open(path, "rb") as f:
                import hashlib
                self.assertEqual(h1, hashlib.sha256(b"hello picasso").hexdigest())
        finally:
            os.unlink(path)


class TestMime(unittest.TestCase):
    def test_extensions(self):
        self.assertEqual(dl.mime_for("a.png"), "image/png")
        self.assertEqual(dl.mime_for("a.jpg"), "image/jpeg")
        self.assertEqual(dl.mime_for("a.jpeg"), "image/jpeg")
        self.assertEqual(dl.mime_for("a.webp"), "image/webp")
        self.assertEqual(dl.mime_for("a.unknown"), "image/png")


class TestProviders(unittest.TestCase):
    def test_registry_complete(self):
        self.assertEqual(set(dl.PROVIDERS.keys()), {"openai", "google", "nim", "openrouter"})
        for name, spec in dl.PROVIDERS.items():
            self.assertTrue(spec["label"])
            self.assertTrue(spec["models"])
            self.assertTrue(spec["key_hint"])
            self.assertTrue(spec["env_key"])

    def test_all_models_unique(self):
        seen = set()
        for spec in dl.PROVIDERS.values():
            for m in spec["models"]:
                self.assertNotIn(m, seen)
                seen.add(m)


class TestLibraryOps(unittest.TestCase):
    def test_next_design_number(self):
        designs = [{"path": "screenshots/design_01.png"}, {"path": "screenshots/design_02.png"}]
        self.assertEqual(dl.next_design_number(designs), 3)
        designs = []
        self.assertEqual(dl.next_design_number(designs), 1)
        designs = [{"path": "screenshots/design_05.png"}]
        self.assertEqual(dl.next_design_number(designs), 1)


class TestConfigEnv(unittest.TestCase):
    def test_env_overrides(self):
        old = dict(os.environ)
        try:
            # config file first
            with tempfile.TemporaryDirectory() as td:
                cfg_file = Path(td) / "config.json"
                cfg_file.write_text(json.dumps({"provider": "nim", "api_key": "k", "model": "m"}))
                dl.CONFIG_FILE = cfg_file
                os.environ["DESIGNLIB_MODEL"] = "envmodel"
                cfg = dl.load_config()
                self.assertEqual(cfg["provider"], "nim")
                self.assertEqual(cfg["model"], "envmodel")
                self.assertEqual(cfg["api_key"], "k")
        finally:
            os.environ.clear()
            os.environ.update(old)
            dl.CONFIG_FILE = Path.home() / ".designlib" / "config.json"


class TestPromptSchema(unittest.TestCase):
    REQUIRED_KEYS = ["description", "layout", "hero", "components", "palette",
                     "typography", "tags", "usage", "ideas"]

    def test_prompt_specifies_all_keys(self):
        for key in self.REQUIRED_KEYS:
            self.assertIn(f'"{key}"', dl.PROMPT, f"PROMPT missing key: {key}")

    def test_prompt_specifies_key_semantics(self):
        # each key must have an instruction beyond the bare name
        for key in self.REQUIRED_KEYS:
            line = next(l for l in dl.PROMPT.splitlines() if f'"{key}"' in l)
            self.assertGreater(len(line), len(key) + 12, f"key {key} lacks a spec")


class TestNormalizeAnalysis(unittest.TestCase):
    def test_derives_title_from_description_when_missing(self):
        a = dl.normalize_analysis({"description": "A calm SaaS landing page."})
        self.assertEqual(a["title"], "A calm SaaS landing page")

    def test_derives_untitled_for_empty(self):
        self.assertEqual(dl.normalize_analysis({})["title"], "Untitled work")

    def test_truncates_long_description_title(self):
        a = dl.normalize_analysis({
            "description": "A calm SaaS landing page that pairs warm cream surfaces with a burnt-orange accent; editorial spacing gives it a premium, trust-first feel.",
        })
        self.assertLessEqual(len(a["title"].split()), 7)
        self.assertTrue(a["title"].endswith("…"))

    def test_prose_palette_extracts_hex_swatches(self):
        a = dl.normalize_analysis({
            "palette": "warm cream #FAF7F2 base, deep charcoal #131110 text, burnt-orange #F97316 accent",
        })
        hexes = [s["hex"] for s in a["palette"]]
        self.assertEqual(hexes, ["#FAF7F2", "#131110", "#F97316"])
        self.assertTrue(all(s["name"] or s["role"] for s in a["palette"]))

    def test_list_of_dict_swatches_preserved(self):
        a = dl.normalize_analysis({
            "palette": [{"hex": "#F97316", "name": "burnt-orange", "role": "accent"}],
        })
        self.assertEqual(a["palette"][0]["hex"], "#F97316")
        self.assertEqual(a["palette"][0]["role"], "accent")

    def test_prose_palette_without_hex_keeps_prose(self):
        # Never fabricate hex: a prose palette with no hex stays readable text.
        a = dl.normalize_analysis({"palette": "warm cream and charcoal tones"})
        self.assertEqual(a["palette"], "warm cream and charcoal tones")

    def test_malformed_palette_yields_empty_string(self):
        for bad in [None, 42]:
            self.assertEqual(dl.normalize_analysis({"palette": bad})["palette"], "")


class TestPlanUpdates(unittest.TestCase):
    def _make_img(self, td, name, content):
        p = Path(td) / name
        p.write_bytes(content)
        return p

    def test_new_unchanged_renamed_replaced(self):
        with tempfile.TemporaryDirectory() as td:
            a = self._make_img(td, "a.png", b"content-A")
            b = self._make_img(td, "b.png", b"content-B")
            c = self._make_img(td, "c.png", b"content-C")

            designs = [
                {"path": "screenshots/a.png", "sha256": dl.sha256_file(a), "analysis": {"tags": ["a"]}},
            ]

            # rename a.png -> a2.png (same content), keep b.png, add c.png
            a2 = self._make_img(td, "a2.png", b"content-A")
            images = [a2, b, c]

            to_analyze, path_fixes, kept_names = dl.plan_updates(images, designs)

            # c.png is new -> analyze; b.png new -> analyze; a2 renamed -> path fix
            self.assertEqual(sorted(i.name for i, _, _ in to_analyze), ["b.png", "c.png"])
            self.assertEqual(len(path_fixes), 1)
            self.assertEqual(path_fixes[0][0]["path"], "screenshots/a.png")
            self.assertEqual(path_fixes[0][1], "screenshots/a2.png")

    def test_replaced_same_name_detected(self):
        with tempfile.TemporaryDirectory() as td:
            orig = self._make_img(td, "x.png", b"original")
            designs = [
                {"path": "screenshots/x.png", "sha256": dl.sha256_file(orig), "analysis": {}},
            ]
            changed = self._make_img(td, "x.png", b"CHANGED CONTENT")  # overwrite
            to_analyze, path_fixes, kept = dl.plan_updates([changed], designs)
            self.assertEqual(len(to_analyze), 1)  # must re-analyze
            self.assertEqual(path_fixes, [])
            self.assertEqual(kept, [])

    def test_force_reanalyzes_everything(self):
        with tempfile.TemporaryDirectory() as td:
            a = self._make_img(td, "a.png", b"content-A")
            designs = [
                {"path": "screenshots/a.png", "sha256": dl.sha256_file(a), "analysis": {}},
            ]
            to_analyze, path_fixes, kept = dl.plan_updates([a], designs, force=True)
            self.assertEqual(len(to_analyze), 1)
            self.assertEqual(path_fixes, [])
            self.assertEqual(kept, [])


class TestAtomicWrite(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def test_atomic_write_replaces_content(self):
        f = self.dir / "a.json"
        dl.atomic_write(f, '{"x": 1}')
        self.assertEqual(json.loads(f.read_text()), {"x": 1})

    def test_atomic_write_leaves_no_temp(self):
        f = self.dir / "a.json"
        dl.atomic_write(f, '{"x": 1}')
        leftovers = [p.name for p in self.dir.iterdir() if p.name != "a.json"]
        self.assertEqual(leftovers, [])

    def test_atomic_write_preserves_existing_on_failure(self):
        f = self.dir / "a.json"
        dl.atomic_write(f, '{"x": 1}')
        with mock.patch.object(Path, "write_text", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                dl.atomic_write(f, '{"x": 2}')
        self.assertEqual(json.loads(f.read_text()), {"x": 1})  # original intact


class TestAtomicSaves(unittest.TestCase):
    def test_save_library_uses_atomic_write(self):
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(dl, "JSON_FILE", Path(td) / "library.json"):
                with mock.patch.object(dl, "atomic_write") as aw:
                    dl.save_library({"designs": [{"a": 1}]})
                    aw.assert_called_once_with(dl.JSON_FILE, json.dumps({"designs": [{"a": 1}]}, indent=2))

    def test_save_config_uses_atomic_write_and_stays_private(self):
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(dl, "CONFIG_FILE", Path(td) / "config.json"):
                with mock.patch.object(dl, "atomic_write") as aw, \
                     mock.patch.object(dl.os, "chmod") as ch:
                    dl.save_config({"provider": "nim", "api_key": "x"})
                    aw.assert_called_once_with(dl.CONFIG_FILE, json.dumps({"provider": "nim", "api_key": "x"}, indent=2))
                    ch.assert_called_once_with(dl.CONFIG_FILE, 0o600)


class TestCorruptRecovery(unittest.TestCase):
    def test_load_library_corrupt_backs_up_and_warns(self):
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(dl, "JSON_FILE", Path(td) / "library.json"):
                dl.JSON_FILE.write_text("{not json")
                with mock.patch("builtins.print") as pr:
                    out = dl.load_library()
                self.assertEqual(out, {"designs": []})
                self.assertTrue(pr.called)  # warned, not silent
                backups = [p for p in Path(td).iterdir() if ".corrupt-" in p.name]
                self.assertEqual(len(backups), 1)  # corrupt original preserved
                self.assertEqual(backups[0].read_text(), "{not json")

    def test_load_config_corrupt_backs_up_and_warns(self):
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(dl, "CONFIG_FILE", Path(td) / "config.json"):
                dl.CONFIG_FILE.write_text("nope")
                with mock.patch("builtins.print") as pr:
                    out = dl.load_config()
                self.assertEqual(out, {})
                self.assertTrue(pr.called)
                backups = [p for p in Path(td).iterdir() if ".corrupt-" in p.name]
                self.assertEqual(len(backups), 1)

    def test_load_library_valid_file_untouched(self):
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(dl, "JSON_FILE", Path(td) / "library.json"):
                dl.JSON_FILE.write_text('{"designs": [{"path": "screenshots/a.png"}]}')
                out = dl.load_library()
                self.assertEqual(len(out["designs"]), 1)
                self.assertEqual([p.name for p in Path(td).iterdir()], ["library.json"])


class TestGoogleTimeout(unittest.TestCase):
    """The Google SDK call must hit a hard timeout, never hang forever."""

    PIXEL = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )

    def _fake_sdk(self, hang=False, text="ok"):
        google_mod = pyt.ModuleType("google")
        genai_mod = pyt.ModuleType("google.genai")
        types_mod = pyt.ModuleType("google.genai.types")
        types_mod.Part = mock.MagicMock()
        types_mod.Part.from_bytes.return_value = "PART"
        types_mod.GenerateContentConfig = mock.MagicMock()
        client = mock.MagicMock()
        if hang:

            def _hang(*a, **k):
                time.sleep(30)  # simulate a hung network call

            client.models.generate_content.side_effect = _hang
        else:
            resp = mock.MagicMock()
            resp.text = text
            client.models.generate_content.return_value = resp
        genai_mod.Client = mock.MagicMock(return_value=client)
        google_mod.genai = genai_mod
        return {"google": google_mod, "google.genai": genai_mod, "google.genai.types": types_mod}

    def test_google_call_times_out_instead_of_hanging(self):
        with tempfile.TemporaryDirectory() as td:
            img = Path(td) / "p.png"
            img.write_bytes(self.PIXEL)
            with mock.patch.dict(sys.modules, self._fake_sdk(hang=True)):
                start = time.monotonic()
                with self.assertRaises(RuntimeError):
                    dl.google_generate_content("k", "m", str(img), timeout=0.3)
                self.assertLess(time.monotonic() - start, 5)

    def test_google_call_returns_text_on_success(self):
        with tempfile.TemporaryDirectory() as td:
            img = Path(td) / "p.png"
            img.write_bytes(self.PIXEL)
            with mock.patch.dict(sys.modules, self._fake_sdk(text="hello")):
                self.assertEqual(dl.google_generate_content("k", "m", str(img), timeout=5), "hello")


class TestValidateKeyTempFile(unittest.TestCase):
    """validate_key must use a unique temp file per call (concurrent-safe)."""

    def test_concurrent_calls_use_distinct_temp_paths(self):
        seen = []

        def _fake_analyze(provider, api_key, model, image_path):
            seen.append(Path(image_path).name)
            return {"designs": [{"title": "x"}]}

        with tempfile.TemporaryDirectory() as td:
            real_mkstemp = dl.tempfile.mkstemp

            def _mkstemp_here(*a, **k):
                k["dir"] = td
                return real_mkstemp(*a, **k)

            with mock.patch.object(dl, "analyze_image", side_effect=_fake_analyze), \
                 mock.patch.object(dl.tempfile, "mkstemp", side_effect=_mkstemp_here):
                dl.validate_key("nim", "k", "m")
                dl.validate_key("nim", "k", "m")
        self.assertEqual(len(seen), 2)
        self.assertNotEqual(seen[0], seen[1])  # distinct filenames

    def test_temp_file_cleaned_up_after_validation(self):
        with tempfile.TemporaryDirectory() as td:
            real_mkstemp = dl.tempfile.mkstemp

            def _mkstemp_here(*a, **k):
                k["dir"] = td
                return real_mkstemp(*a, **k)

            with mock.patch.object(dl, "analyze_image", return_value={"designs": []}), \
                 mock.patch.object(dl.tempfile, "mkstemp", side_effect=_mkstemp_here):
                dl.validate_key("nim", "k", "m")
            self.assertEqual(list(Path(td).iterdir()), [])  # nothing left behind


class TestGracefulInterrupt(unittest.TestCase):
    """Ctrl-C must exit cleanly (code 130), not dump a traceback."""

    def test_main_handles_keyboard_interrupt(self):
        def _boom(args):
            raise KeyboardInterrupt

        with mock.patch.object(dl, "cmd_update", side_effect=_boom), \
             mock.patch("builtins.print") as pr:
            with self.assertRaises(SystemExit) as ctx:
                dl.main(["update"])
        self.assertEqual(ctx.exception.code, 130)
        joined = " ".join(str(c) for c in pr.call_args_list)
        self.assertIn("Interrupted", joined)
        self.assertNotIn("Traceback", joined)


class TestResyncFailure(unittest.TestCase):
    """resync() must warn and return False on failure — never crash update."""

    # an existing script so resync takes the subprocess path, not the noop branch
    EXISTING = Path("src/picasso/sync_data.py")

    def test_resync_returns_true_on_success(self):
        with mock.patch.object(dl, "SYNC_SCRIPT", self.EXISTING), \
             mock.patch.object(dl.subprocess, "run", return_value=mock.Mock(returncode=0)):
            self.assertTrue(dl.resync())

    def test_resync_warns_and_returns_false_on_failure(self):
        with mock.patch.object(dl, "SYNC_SCRIPT", self.EXISTING), \
             mock.patch.object(dl.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "sync")), \
             mock.patch("builtins.print") as pr:
            self.assertFalse(dl.resync())  # no exception propagates
            joined = " ".join(str(c) for c in pr.call_args_list)
            self.assertIn("WARNING", joined)

    def test_resync_noop_without_script(self):
        with mock.patch.object(dl, "SYNC_SCRIPT", Path("missing.py")), \
             mock.patch.object(dl.subprocess, "run") as run:
            self.assertTrue(dl.resync())
            run.assert_not_called()


class TestVersionFlag(unittest.TestCase):
    """picasso --version prints the version and exits 0."""

    def test_version_flag_prints_version(self):
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as ctx:
                dl.main(["--version"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn(dl.VERSION, buf.getvalue())


class TestSeedCommand(unittest.TestCase):
    """picasso seed copies the committed sample collection into the library.

    Opt-in and privacy-safe: it must refuse to clobber a library that already
    has designs unless --force, and always leave a usable data.js behind.
    """

    def _patched_seed_path(self, td):
        # Write a 2-design seed into the temp dir and point SEED_FILE there.
        seed = {"designs": [
            {"path": "screenshots/design_01.png", "analysis": {"tags": ["clean"], "description": "A."}},
            {"path": "screenshots/design_02.png", "analysis": {"tags": ["bold-typography"], "description": "B."}},
        ]}
        p = Path(td) / "seed.json"
        p.write_text(json.dumps(seed))
        return p

    def test_seed_fills_empty_library_and_resyncs(self):
        with tempfile.TemporaryDirectory() as td:
            seed = self._patched_seed_path(td)
            with mock.patch.object(dl, "SEED_FILE", seed), \
                 mock.patch.object(dl, "JSON_FILE", Path(td) / "library.json"), \
                 mock.patch.object(dl, "resync", return_value=True) as resync, \
                 mock.patch("builtins.print"):
                dl.cmd_seed(type("A", (), {"force": False})())
            lib = json.loads((Path(td) / "library.json").read_text())
            self.assertEqual(len(lib["designs"]), 2)
            resync.assert_called_once()

    def test_seed_refuses_to_clobber_without_force(self):
        with tempfile.TemporaryDirectory() as td:
            seed = self._patched_seed_path(td)
            lib = Path(td) / "library.json"
            lib.write_text(json.dumps({"designs": [{"path": "screenshots/mine.png", "analysis": {}}]}))
            with mock.patch.object(dl, "SEED_FILE", seed), \
                 mock.patch.object(dl, "JSON_FILE", lib), \
                 mock.patch("builtins.print") as pr:
                with self.assertRaises(SystemExit) as ctx:
                    dl.cmd_seed(type("A", (), {"force": False})())
            self.assertEqual(ctx.exception.code, 1)
            # library untouched
            self.assertEqual(len(json.loads(lib.read_text())["designs"]), 1)
            joined = " ".join(str(c) for c in pr.call_args_list)
            self.assertIn("--force", joined)

    def test_seed_force_overwrites_existing(self):
        with tempfile.TemporaryDirectory() as td:
            seed = self._patched_seed_path(td)
            lib = Path(td) / "library.json"
            lib.write_text(json.dumps({"designs": [{"path": "screenshots/mine.png", "analysis": {}}]}))
            with mock.patch.object(dl, "SEED_FILE", seed), \
                 mock.patch.object(dl, "JSON_FILE", lib), \
                 mock.patch.object(dl, "resync", return_value=True), \
                 mock.patch("builtins.print"):
                dl.cmd_seed(type("A", (), {"force": True})())
            lib2 = json.loads(lib.read_text())
            self.assertEqual(len(lib2["designs"]), 2)

    def test_seed_missing_prompts_users_to_run_setup(self):
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "nope.json"
            with mock.patch.object(dl, "SEED_FILE", missing), \
                 mock.patch.object(dl, "JSON_FILE", Path(td) / "library.json"), \
                 mock.patch("builtins.print") as pr:
                with self.assertRaises(SystemExit) as ctx:
                    dl.cmd_seed(type("A", (), {"force": False})())
            self.assertEqual(ctx.exception.code, 1)
            joined = " ".join(str(c) for c in pr.call_args_list)
            self.assertIn("sample", joined.lower())


class TestFacets(unittest.TestCase):
    """B6: the facet taxonomy derived by sync_data.build_facets.

    Structure facets come from each design's REAL `components` list — no
    fabricated tone/mood dimensions (palette is prose in this corpus, so we
    never invent hex-based facets). The map must be total: every component
    token that appears in the corpus lands in exactly one facet.
    """

    def _load_seed_designs(self):
        seed = json.loads(Path(dl.SEED_FILE).read_text(encoding="utf-8"))
        return seed["designs"]

    def test_every_seed_component_maps_to_exactly_one_facet(self):
        designs = self._load_seed_designs()
        seen = set()
        for d in designs:
            for c in d["analysis"].get("components", []):
                seen.add(str(c).strip().lower())
        mapped = set()
        for group in sync_data.COMPONENT_FACETS:
            for c in group["components"]:
                self.assertNotIn(c, mapped, f"component {c!r} mapped twice")
                mapped.add(c)
        missing = seen - mapped
        self.assertEqual(
            missing, set(),
            f"components with no facet: {sorted(missing)}",
        )

    def test_facets_emitted_only_for_present_components(self):
        designs = [
            {"components": d["analysis"].get("components", [])}
            for d in self._load_seed_designs()
        ]
        facets = sync_data.build_facets(designs)
        struct = facets["structure"]
        self.assertEqual(struct["label"], "Structure")
        # Navigation + Content must exist in the real corpus (navbar/hero appear).
        names = {v["facet"] for v in struct["values"]}
        self.assertIn("Navigation", names)
        self.assertIn("Content", names)
        # Every emitted facet has at least one component.
        for v in struct["values"]:
            self.assertTrue(v["components"], f"empty facet {v['facet']!r}")

    def test_empty_corpus_yields_no_phantom_facets(self):
        facets = sync_data.build_facets([])
        self.assertEqual(facets["structure"]["values"], [])

    def test_facets_are_case_normalized(self):
        facets = sync_data.build_facets([{"components": ["NAVBAR", "Hero"]}])
        nav = next(v for v in facets["structure"]["values"] if v["facet"] == "Navigation")
        self.assertIn("navbar", nav["components"])
        self.assertNotIn("NAVBAR", nav["components"])


class TestInstalledLauncher(unittest.TestCase):
    """B1 regression: the installed `picasso` command must resolve the real
    launcher path even when invoked through the symlink created by
    install.sh (or the copy on Windows). Running `picasso --version` from a
    different cwd must find designlib.py next to the REAL launcher, not the
    symlink location. Offline: we pre-create a fake .venv/bin/python marker so
    the launcher skips the pip/google-genai bootstrap."""

    @classmethod
    def setUpClass(cls):
        cls.PICASSO = Path(__file__).resolve().parent.parent / "picasso"

    def _make_venv_marker(self, root):
        """Pretend a venv already exists so the launcher skips pip+network."""
        bin_dir = root / ".venv" / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        link = bin_dir / "python"
        if not link.exists() or os.path.islink(link):
            try:
                link.unlink()
            except FileNotFoundError:
                pass
            os.symlink(sys.executable, link)

    def test_symlinked_launcher_runs_from_other_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            work, workbin = tmp / "work", tmp / "bin"
            work.mkdir()
            workbin.mkdir()

            # A stub package that prints a marker and exits 0. The launcher runs
            # `python -m picasso` with PYTHONPATH=$PWD/src, so the marker lives
            # in src/picasso/__init__.py of the "installed" copy (imported by
            # __main__.py).
            (work / "src" / "picasso").mkdir(parents=True)
            (work / "src" / "picasso" / "__init__.py").write_text(
                "print('DESIGNLIB_FOUND')\n"
            )
            (work / "src" / "picasso" / "__main__.py").write_text(
                "from . import *\n"
            )
            # Install the real launcher into work/, link it into bin/ (the
            # ~/.local/bin equivalent that install.sh creates).
            shutil.copy(self.PICASSO, work / "picasso")
            os.symlink(work / "picasso", workbin / "picasso")

            # Venv marker in BOTH places: the real location (fixed code looks
            # here after resolving the symlink) and the buggy location (old
            # code cds into bin/). Ensures the RED state fails only on the
            # directory resolution, not on venv bootstrap.
            self._make_venv_marker(work)
            self._make_venv_marker(workbin)

            # Invoke through the symlink, cwd NOT the launcher's dir.
            result = subprocess.run(
                ["bash", str(workbin / "picasso"), "--version"],
                cwd=tmp, capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(
                result.returncode, 0,
                f"launcher failed:\nstdout={result.stdout}\nstderr={result.stderr}",
            )
            self.assertIn("DESIGNLIB_FOUND", result.stdout)


if __name__ == "__main__":
    unittest.main()
