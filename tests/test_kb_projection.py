"""Profile kb projection: a profile exposes exactly the kb paths its layers name.

Uses the real profiles and export-allowlist.json against a fake core/ tree in a
temp dir; nothing touches the real home.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from devkit_cli import manifest, profiles
from devkit_cli.common import Plan
from devkit_cli.errors import DevkitError

KB_FILES = (
    "_shared/a.md",
    "validation/v.md",
    "implementation/How-to-x.md",
    "implementation/enonic-cli/cli.md",
    "implementation/xp7-to-xp8-upgrade/up.md",
    "offline-reference/scripts/fetch.py",
    "offline-reference/xp7/doc.md",
    "offline-reference/xp8/doc.md",
    "calibration/classify-ticket-autonomy/How-to-calibrate-classify-ticket-autonomy.md",
    "calibration/classify-ticket-autonomy/Corpus-precedents-for-classify-ticket-autonomy.md",
    "testing/t.md",
)


class KbProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.core = root / "release" / "core"
        self.link_core = root / "current" / "core"
        for rel in KB_FILES:
            path = self.core / "kb" / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x\n")
        self.link_core.parent.mkdir(parents=True)
        self.link_core.symlink_to(self.core)
        self.config = root / "instance"
        self.config.mkdir()
        self.kb = self.config / "kb"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def sync(self, profile: str, apply: bool = True) -> Plan:
        plan = Plan(apply)
        loaded = manifest.load(profile)
        profiles._link_layer(plan, self.config, "kb", loaded["kb"], self.core,
                             self.link_core, loaded.get("kb_excludes"))
        return plan

    def visible(self) -> set[str]:
        return {str((Path(top) / f).relative_to(self.kb))
                for top, _, files in os.walk(self.kb, followlinks=True) for f in files}

    def assert_core_only(self) -> None:
        seen = self.visible()
        self.assertIn("offline-reference/scripts/fetch.py", seen)
        self.assertIn("implementation/How-to-x.md", seen)
        self.assertIn("calibration/classify-ticket-autonomy/"
                      "How-to-calibrate-classify-ticket-autonomy.md", seen)
        for leaked in ("offline-reference/xp7/doc.md", "implementation/enonic-cli/cli.md",
                       "implementation/xp7-to-xp8-upgrade/up.md", "testing/t.md",
                       ("calibration/classify-ticket-autonomy/"
                        "Corpus-precedents-for-classify-ticket-autonomy.md")):
            self.assertNotIn(leaked, seen)
        self.assertFalse((self.kb / "offline-reference").is_symlink())
        self.assertTrue((self.kb / "offline-reference" / "scripts").is_symlink())
        self.assertTrue((self.kb / "_shared").is_symlink())

    def test_core_profile_excludes_enonic_reference_and_cli(self):
        self.sync("core")
        self.assert_core_only()

    def test_php_gets_cores_kb_only(self):
        self.sync("php")
        self.assert_core_only()

    def test_enonic_profile_adds_the_enonic_paths_back(self):
        self.sync("enonic")
        seen = self.visible()
        for rel in ("offline-reference/scripts/fetch.py", "offline-reference/xp7/doc.md",
                    "offline-reference/xp8/doc.md", "implementation/enonic-cli/cli.md",
                    "implementation/xp7-to-xp8-upgrade/up.md", "implementation/How-to-x.md"):
            self.assertIn(rel, seen)
        self.assertNotIn("testing/t.md", seen)

    def test_resync_is_idempotent(self):
        self.sync("enonic")
        self.assertEqual(self.sync("enonic").actions, [])
        self.assertEqual(self.sync("enonic", apply=False).actions, [])

    def test_old_whole_leaf_symlinks_convert_to_nested_layout(self):
        self.kb.mkdir()
        for leaf in ("offline-reference", "implementation", "calibration", "testing"):
            (self.kb / leaf).symlink_to(self.link_core / "kb" / leaf)
        dry = self.sync("core", apply=False)
        self.assertIn("unlink kb/offline-reference (becomes a directory)", dry.actions)
        self.assertIn("prune  kb/testing", dry.actions)
        self.sync("core")
        self.assert_core_only()
        self.assertEqual(self.sync("core").actions, [])

    def test_narrowing_prunes_links_and_projection_dirs(self):
        self.sync("enonic")
        plan = self.sync("core")
        self.assertIn("prune  kb/offline-reference/xp7", plan.actions)
        self.assert_core_only()
        # extract names implementation/** whole: the nested dir becomes one link,
        # and the projection dirs it no longer names go.
        self.sync("extract")
        self.assertTrue((self.kb / "implementation").is_symlink())
        self.assertFalse((self.kb / "offline-reference").exists())
        self.assertFalse((self.kb / "calibration").exists())

    def test_real_user_directory_is_refused_and_kept(self):
        user = self.kb / "implementation"
        user.mkdir(parents=True)
        (user / "notes.md").write_text("mine\n")
        self.sync("core")  # a real dir as the container of finer links is fine
        self.assertTrue((user / "notes.md").is_file())
        with self.assertRaises(DevkitError):
            self.sync("extract")  # not a projection; a whole link cannot replace it
        self.assertTrue((user / "notes.md").is_file())

    def test_allowlist_ref_carries_layer_excludes(self):
        core = manifest.load("core")
        self.assertIn("implementation/enonic-cli/**", core["kb_excludes"])
        self.assertFalse(any(e.startswith("implementation/enonic-cli") for e in core["kb"]))
        self.assertEqual(manifest.load("php")["kb_excludes"], core["kb_excludes"])
        enonic = manifest.load("enonic")["kb_excludes"]
        self.assertNotIn("implementation/enonic-cli/**", enonic)
        self.assertEqual(manifest.entry_parts("a/b/**"), ("a", "b"))


if __name__ == "__main__":
    unittest.main()
