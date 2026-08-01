#!/usr/bin/env python3
"""Unit tests for designlib.py — pure logic only, no network calls."""
import base64
import json
import os
import shutil
import sys
import tempfile
import time
import types as pyt
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import designlib as dl


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


if __name__ == "__main__":
    unittest.main()
