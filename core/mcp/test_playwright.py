#!/usr/bin/env python3
"""Unit tests for mcp/playwright.py config and id helpers (no npx)."""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def load_mod():
    spec = importlib.util.spec_from_file_location("playwright_mcp", HERE / "playwright.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class PlaywrightHelpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_mod()

    def test_sanitize_and_name(self):
        self.assertEqual(self.mod.sanitize_id("TASK-101"), "TASK-101")
        self.assertEqual(self.mod.server_name("TASK-101"), "playwright-TASK-101")
        with self.assertRaises(SystemExit):
            self.mod.sanitize_id("TASK 101")
        with self.assertRaises(SystemExit):
            self.mod.sanitize_id("--help")

    def test_output_dir_default_and_override(self):
        default = self.mod.output_dir_for("TASK-101", None)
        self.assertEqual(default, (self.mod.ROOT / "TASK-101").resolve())
        with tempfile.TemporaryDirectory() as tmp:
            override = self.mod.output_dir_for("TASK-101", tmp)
            self.assertEqual(override, Path(tmp).resolve())

    def test_build_config_headless_isolated(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            cfg = self.mod.build_config(
                output_dir=out,
                storage_state=out / "storage-state.json",
                viewport_size="1440x900",
                port=8931,
            )
        browser = cfg["browser"]
        self.assertTrue(browser["isolated"])
        self.assertTrue(browser["launchOptions"]["headless"])
        self.assertFalse(browser["launchOptions"]["chromiumSandbox"])
        self.assertEqual(
            browser["contextOptions"]["storageState"],
            str(out / "storage-state.json"),
        )
        self.assertEqual(browser["contextOptions"]["viewport"], {"width": 1440, "height": 900})
        self.assertEqual(cfg["outputDir"], str(out))
        self.assertEqual(cfg["capabilities"], self.mod.DEFAULT_CAPS)
        self.assertNotIn("outputDir", cfg["server"])
        self.assertNotIn("capabilities", cfg["server"])
        self.assertEqual(cfg["server"]["port"], 8931)
        self.assertEqual(cfg["server"]["host"], "localhost")
        self.assertNotIn("allowedHosts", cfg["server"])
        self.assertNotIn("extension", cfg)
        self.assertNotIn("sharedBrowserContext", cfg["server"])

    def test_build_config_headed_extension(self):
        cfg = self.mod.build_config(
            output_dir=Path("/tmp/pw"),
            headless=False,
            extension=True,
            no_sandbox=False,
        )
        self.assertFalse(cfg["browser"]["launchOptions"]["headless"])
        self.assertNotIn("chromiumSandbox", cfg["browser"]["launchOptions"])
        self.assertTrue(cfg["extension"])

    def test_merge_overlay(self):
        base = self.mod.build_config(output_dir=Path("/tmp/a"), port=1)
        merged = self.mod.merge_overlay(base, {"server": {"outputMaxSize": 10}, "extra": 1})
        self.assertEqual(merged["server"]["port"], 1)
        self.assertEqual(merged["server"]["outputMaxSize"], 10)
        self.assertEqual(merged["extra"], 1)

    def test_http_spec(self):
        url = "http://localhost:8931/mcp"
        self.assertEqual(self.mod.http_spec(url, "cursor"), {"url": url})
        self.assertEqual(
            self.mod.http_spec(url, "claude"),
            {"type": "http", "url": url},
        )

    def test_mcp_url_coerces_loopback(self):
        self.assertEqual(self.mod.mcp_url("localhost", 8931), "http://localhost:8931/mcp")
        self.assertEqual(self.mod.mcp_url("127.0.0.1", 8931), "http://localhost:8931/mcp")
        self.assertEqual(self.mod.mcp_url("::1", 8932), "http://localhost:8932/mcp")
        self.assertEqual(self.mod.public_host("127.0.0.1"), "localhost")
        self.assertEqual(self.mod.DEFAULT_HOST, "localhost")
        self.assertTrue(
            self.mod.loopback_url_needs_fix(
                {"host": "127.0.0.1", "url": "http://127.0.0.1:8931/mcp"}
            )
        )
        self.assertFalse(
            self.mod.loopback_url_needs_fix(
                {"host": "localhost", "url": "http://localhost:8931/mcp"}
            )
        )

    def test_dead_instance_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            inst = Path(tmp) / "TASK-101"
            inst.mkdir()
            (inst / "instance.json").write_text(
                json.dumps({"id": "TASK-101", "pid": 999999999})
            )
            live = Path(tmp) / "alive"
            live.mkdir()
            (live / "instance.json").write_text(
                json.dumps({"id": "alive", "pid": os.getpid()})
            )
            with patch.object(self.mod, "INSTANCES", Path(tmp)):
                self.assertEqual(self.mod.dead_instance_ids(), ["TASK-101"])

    def test_pick_storage_state_reuses_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            out.mkdir()
            prev = out / "storage-state.json"
            prev.write_text("{}")
            picked = self.mod.pick_storage_state(
                None,
                {"storage_state": str(prev)},
                out,
            )
            self.assertEqual(picked, prev)

    def test_pick_storage_state_copies_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "auth.json"
            src.write_text('{"cookies": []}')
            out = Path(tmp) / "out"
            picked = self.mod.pick_storage_state(str(src), None, out)
            self.assertEqual(picked, out / "storage-state.json")
            self.assertTrue(picked.is_file())

    def test_claude_allow_rules_are_literal_per_instance(self):
        self.assertEqual(
            self.mod.claude_allow_rules("playwright-TASK-101"),
            [
                "mcp__playwright-TASK-101__browser_navigate",
                "mcp__playwright-TASK-101__browser_take_screenshot",
                "mcp__playwright-TASK-101__browser_set_storage_state",
            ],
        )
        self.assertEqual(
            self.mod.claude_allow_rules("playwright-v1.2")[0],
            "mcp__playwright-v1_2__browser_navigate",
        )

    def test_claude_permissions_upsert_and_remove(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text(json.dumps({"model": "haiku", "permissions": {"allow": ["Bash(git *)"]}}))
            self.mod.upsert_claude_permissions(path, "playwright-TASK-101", False)
            self.mod.upsert_claude_permissions(path, "playwright-TASK-101", False)
            self.mod.upsert_claude_permissions(path, "playwright-TASK-102", False)
            data = json.loads(path.read_text())
            self.assertEqual(data["model"], "haiku")
            allow = data["permissions"]["allow"]
            self.assertEqual(len(allow), 7)
            self.assertEqual(allow[0], "Bash(git *)")

            self.mod.remove_claude_permissions(path, "playwright-TASK-101", False)
            allow = json.loads(path.read_text())["permissions"]["allow"]
            self.assertEqual(allow, ["Bash(git *)"] + self.mod.claude_allow_rules("playwright-TASK-102"))

    def test_claude_permissions_leave_invalid_json_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text("{not json")
            self.mod.upsert_claude_permissions(path, "playwright-TASK-101", False)
            self.mod.remove_claude_permissions(path, "playwright-TASK-101", False)
            self.assertEqual(path.read_text(), "{not json")


if __name__ == "__main__":
    unittest.main()
