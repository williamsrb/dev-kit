"""Acceptance tests for the export scrub and the names the kit must not track.

The scrub rules name what must stay out of core/, so they live with the export
source and never in this repository. These tests use dummy names; the last class
is the repository-wide gate, and it builds its patterns from fragments so this
file does not contain what it forbids.
"""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from devkit_cli import export, scrub
from devkit_cli.errors import DevkitError

RULES = {
    "drop_paths": [r"^(?:core/)?kb/projects/"],
    "path_rewrites": [[r"(^|/)lib/acme/", r"\1lib/app/"]],
    "no_rewrite_paths": [r"^vendored/"],
    "rewrites": [
        [r"Acme Corp", "the client"],
        [r"^.*acme-secret.*\n", ""],
        [r"acme", "example", r"\.md$"],
    ],
    "forbidden": [
        {"pattern": "acme"},
        {"pattern": "widgets", "exempt": r"^vendored/"},
    ],
}


class ScrubRulesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = scrub.Rules(RULES)

    def test_rewrites_run_in_order_over_whole_lines(self):
        text = "Acme Corp ships\nthe acme-secret line\nkept\n"
        self.assertEqual(self.rules.text(text, "a.txt"), "the client ships\nkept\n")

    def test_a_rule_with_a_path_only_fires_there(self):
        self.assertEqual(self.rules.text("acme", "notes.md"), "example")
        self.assertEqual(self.rules.text("acme", "notes.txt"), "acme")

    def test_vendored_text_is_copied_untouched(self):
        self.assertEqual(self.rules.text("Acme Corp", "vendored/x.md"), "Acme Corp")

    def test_drops_and_renames_apply_to_paths(self):
        self.assertTrue(self.rules.dropped("kb/projects/a.md"))
        self.assertTrue(self.rules.dropped("core/kb/projects/a.md"))
        self.assertFalse(self.rules.dropped("kb/other/a.md"))
        self.assertEqual(self.rules.rename("src/lib/acme/x.ts"), "src/lib/app/x.ts")

    def test_what_survives_is_reported_with_its_line(self):
        found = self.rules.leaks("fine\nthe ACME team\n", "docs/a.md")
        self.assertEqual([line for line, _ in found], [2])

    def test_a_forbidden_name_in_a_path_is_reported_as_line_zero(self):
        self.assertEqual(self.rules.leaks("", "docs/acme.md"), [(0, "docs/acme.md")])

    def test_an_exempt_path_is_not_scanned_for_that_pattern(self):
        self.assertEqual(self.rules.leaks("widgets", "vendored/a.js"), [])
        self.assertTrue(self.rules.leaks("widgets", "docs/a.js"))

    def test_no_rules_file_means_no_scrub(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(scrub.load(Path(tmp)))

    def test_a_broken_rules_file_stops_the_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / scrub.RULES_PATH
            path.parent.mkdir(parents=True)
            for broken in ("{not json", json.dumps({"rewrites": [["(unclosed", "x"]]})):
                path.write_text(broken, encoding="utf-8")
                with self.assertRaises(DevkitError):
                    scrub.load(Path(tmp))


class ExportScrubTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = scrub.Rules(RULES)

    def test_scrubbed_paths_drop_and_rename(self):
        chosen = {"kb/projects/a.md": Path("a"), "lib/acme/x.ts": Path("x"), "kb/b.md": Path("b")}
        files = export.scrubbed_paths(chosen, self.rules)
        self.assertEqual(sorted(files), ["kb/b.md", "lib/app/x.ts"])
        self.assertEqual(files["lib/app/x.ts"][0], "lib/acme/x.ts")

    def test_two_sources_may_not_collapse_into_one_path(self):
        chosen = {"lib/acme/x.ts": Path("x"), "lib/app/x.ts": Path("y")}
        with self.assertRaises(DevkitError):
            export.scrubbed_paths(chosen, self.rules)

    def test_without_rules_the_paths_are_unchanged(self):
        chosen = {"kb/projects/a.md": Path("a")}
        self.assertEqual(list(export.scrubbed_paths(chosen, None)), ["kb/projects/a.md"])

    def test_any_text_file_is_scrubbed_not_only_known_suffixes(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "x.ts"
            src.write_text("import 'Acme Corp'\n", encoding="utf-8")
            self.assertEqual(export._render(src, "x.ts", self.rules), b"import 'the client'\n")
            self.assertEqual(export._render(src, "x.ts", None), b"import 'Acme Corp'\n")

    def test_binary_files_are_copied_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "x.bin"
            src.write_bytes(b"\xff\xfeAcme Corp")
            self.assertEqual(export._render(src, "x.bin", self.rules), b"\xff\xfeAcme Corp")

    def test_leaks_name_the_file_and_line(self):
        rendered = {"a.md": b"ok\nacme here\n", "b.md": b"clean\n"}
        found = export.scrub_leaks(self.rules, rendered)
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].startswith("a.md:2:"))
        self.assertEqual(export.scrub_leaks(None, rendered), [])

    def _run(self, kit: Path, source: Path, *, check: bool = False, apply: bool = False) -> int:
        args = argparse.Namespace(source=str(source), check=check, apply=apply, no_scan=True)
        with mock.patch.object(export, "repo_file", lambda name: kit / name), \
                mock.patch.object(export, "require_checkout", lambda command: None), \
                redirect_stdout(io.StringIO()):
            return export.cmd_export(args)

    def _kit(self, tmp: str, body: str, rules: dict | None = RULES) -> tuple[Path, Path]:
        kit, source = Path(tmp) / "kit", Path(tmp) / "src"
        (source / "skills/demo").mkdir(parents=True)
        (source / "skills/demo/SKILL.md").write_text(body, encoding="utf-8")
        (source / "skills/demo/lib/acme").mkdir(parents=True)
        (source / "skills/demo/lib/acme/x.ts").write_text("// Acme Corp\n", encoding="utf-8")
        if rules is not None:
            (source / scrub.RULES_PATH).parent.mkdir()
            (source / scrub.RULES_PATH).write_text(json.dumps(rules), encoding="utf-8")
        kit.mkdir()
        (kit / "export-allowlist.json").write_text(
            json.dumps({"source": str(source), "target": "core", "skills": {"core": ["demo"]}}),
            encoding="utf-8")
        return kit, source

    def test_export_writes_the_scrubbed_tree_and_check_agrees(self):
        with tempfile.TemporaryDirectory() as tmp:
            kit, source = self._kit(tmp, "Acme Corp rules\n")
            self.assertEqual(self._run(kit, source, apply=True), 0)
            core = kit / "core/skills/demo"
            self.assertEqual((core / "SKILL.md").read_text(encoding="utf-8"), "the client rules\n")
            self.assertEqual((core / "lib/app/x.ts").read_text(encoding="utf-8"), "// the client\n")
            self.assertFalse((core / "lib/acme").exists())
            self.assertEqual(self._run(kit, source, check=True), 0)

    def test_a_name_the_rules_miss_fails_the_export_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            kit, source = self._kit(tmp, "the acme team\n", rules={**RULES, "rewrites": []})
            with self.assertRaises(DevkitError) as caught:
                self._run(kit, source, apply=True)
            self.assertIn("forbid", str(caught.exception))
            self.assertFalse((kit / "core").exists())
            with self.assertRaises(DevkitError):
                self._run(kit, source, check=True)

    def test_without_a_rules_file_the_export_copies_as_before(self):
        with tempfile.TemporaryDirectory() as tmp:
            kit, source = self._kit(tmp, "Acme Corp rules\n", rules=None)
            self.assertEqual(self._run(kit, source, apply=True), 0)
            self.assertEqual((kit / "core/skills/demo/SKILL.md").read_text(encoding="utf-8"),
                             "Acme Corp rules\n")


class NoUntrackedNamesTests(unittest.TestCase):
    """Names the operator does not own must not be tracked anywhere in this repo."""

    # Fragments, so this file does not hold what it forbids.
    FIRST = "9" "9x"
    SECOND = "see" "ds"
    # Vendored third-party code uses the second word in its ordinary sense.
    SECOND_EXEMPT = ("core/skills-vendor/", "core/skills/archify/assets/")

    def _tracked(self) -> list[str]:
        try:
            out = subprocess.run(["git", "ls-files", "-z"], cwd=REPO, capture_output=True,
                                 check=True).stdout
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("not a git checkout")
        return [p for p in out.decode("utf-8").split("\0") if p]

    def test_no_tracked_path_or_file_names_them(self):
        offenders = []
        for rel in self._tracked():
            lowered = rel.lower()
            exempt = rel.startswith(self.SECOND_EXEMPT)
            if self.FIRST in lowered or (self.SECOND in lowered and not exempt):
                offenders.append(rel)
                continue
            path = REPO / rel
            if path.is_symlink() or not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8").lower()
            except (UnicodeDecodeError, OSError):
                continue
            if self.FIRST in text or (self.SECOND in text and not exempt):
                offenders.append(rel)
        self.assertEqual(offenders, [], "tracked files carry names the kit must not track")


if __name__ == "__main__":
    unittest.main()
