"""Acceptance tests for devkit.

Each test names the requirement it covers so a failure points at the
requirement, not just the code.
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
import pwd
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import ClassVar
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from devkit_cli import (
    appfork,
    auth,
    cli_link,
    export,
    globalignore,
    instances,
    kithome,
    kitsource,
    manifest,
    paths,
    privilege,
    profiles,
    scrub,
    session_sync,
    update,
)
from devkit_cli.common import Plan, write_json
from devkit_cli.errors import DevkitError
from devkit_cli.profiles import (
    choose_first_profile,
    flag_given,
    load_for_create,
    materialize,
)
from devkit_cli.uninstaller import DEST_NAME, SCRIPT, ensure, write_uninstaller


def _kit_lineage() -> str:
    from devkit_cli.profiles import _kit_metadata
    return _kit_metadata()["lineage_id"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(REPO / "devkit"), *args],
                          capture_output=True, text=True, check=False)


def export_source() -> Path | None:
    """The harness this kit exports from, when it is present.

    It is absent anywhere that is not a maintainer's machine — CI, a container,
    a teammate's checkout. Tests that need it skip rather than fail, because
    "the source is not here" is not a defect in the kit.
    """
    allowlist = json.loads((REPO / "export-allowlist.json").read_text())
    try:
        return Path(export.resolve_source(None, allowlist))
    except DevkitError:
        return None


NEEDS_SOURCE = unittest.skipIf(export_source() is None,
                               "export source not present (not a maintainer machine)")


class HelpContractTests(unittest.TestCase):
    """'devkit' and 'devkit --help' must produce identical stdout and exit 0;
    the same for every group. An unknown subcommand must write usage to stderr
    and exit 2."""

    GROUPS: ClassVar[list[str]] = ["profile", "update", "origin", "docs"]

    def test_bare_equals_help(self):
        bare, helped = run(), run("--help")
        self.assertEqual(bare.returncode, 0)
        self.assertEqual(helped.returncode, 0)
        self.assertEqual(bare.stdout, helped.stdout)

    def test_every_group_bare_equals_help(self):
        for group in self.GROUPS:
            with self.subTest(group=group):
                bare, helped = run(group), run(group, "--help")
                self.assertEqual(bare.returncode, 0, bare.stderr)
                self.assertEqual(bare.stdout, helped.stdout)

    def test_unknown_subcommand_is_usage_on_stderr_exit_2(self):
        result = run("bogus")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("usage:", result.stderr)

    def test_profile_auth_bare_equals_help(self):
        bare, helped = run("profile", "auth"), run("profile", "auth", "--help")
        self.assertEqual(bare.returncode, 0, bare.stderr)
        self.assertEqual(bare.stdout, helped.stdout)


class PathContractTests(unittest.TestCase):
    """'Grep every installed artifact for a literal ${HOME} or ~/ in a
    non-expanding context; must be zero.'"""

    def test_repo_is_clean(self):
        self.assertEqual(run("lint-paths").returncode, 0)

    def test_container_paths_are_not_flagged_as_home_paths(self):
        contract = json.loads((REPO / "path-contract.json").read_text())
        rule = next(r for r in contract["rules"] if r["id"] == "literal-home")
        pattern = re.compile(rule["pattern"])
        self.assertIsNone(pattern.search("cp /enonic-xp/home/deploy/app.jar ."))
        self.assertIsNone(pattern.search("-e JAVA_HOME=/home/builder/.enonic/x"))
        self.assertIsNotNone(pattern.search("/home/someone/.agents/skills"))

    def test_tilde_in_a_markdown_link_is_an_error(self):
        contract = json.loads((REPO / "path-contract.json").read_text())
        rule = next(r for r in contract["rules"] if r["id"] == "tilde-in-markdown-link")
        self.assertIsNotNone(re.compile(rule["pattern"]).search("see [guide](~/.agents/x.md)"))


class ExportBoundaryTests(unittest.TestCase):
    def test_hard_excludes_are_anchored_not_substring(self):
        """An unanchored `graft/` also matches skills/graft/, which silently
        dropped a real skill."""
        hard = ["graft/", "tests/", "**/__pycache__/"]
        self.assertTrue(export._excluded("graft/index.json", hard))
        self.assertFalse(export._excluded("skills/graft/SKILL.md", hard))
        self.assertTrue(export._excluded("skills/x/__pycache__/a.pyc", hard))

    @NEEDS_SOURCE
    def test_every_skill_on_disk_is_classified(self):
        allowlist = json.loads((REPO / "export-allowlist.json").read_text())
        block = allowlist["skills"]
        listed = set(block["core"]) | set(block["enonic"]) | (set(block["excluded"]) - {"_comment"})
        source = export_source()
        on_disk = {p.name for p in (source / "skills").iterdir() if p.is_dir()}
        self.assertEqual(on_disk - listed, set(), "unclassified skills would ship or vanish silently")

    @NEEDS_SOURCE
    def test_every_bin_on_disk_is_classified(self):
        allowlist = json.loads((REPO / "export-allowlist.json").read_text())
        block = allowlist["bin"]
        listed = set(block["core"]) | (set(block.get("excluded") or {}) - {"_comment"})
        source = export_source()
        rules = scrub.load(source)
        on_disk = {
            p.name for p in (source / "bin").iterdir()
            if p.name != "__pycache__" and (p.is_file() or p.is_dir())
            # what the private scrub rules drop is classified by those rules
            and not (rules is not None and rules.dropped(f"bin/{p.name}"))
        }
        self.assertEqual(on_disk - listed, set(), "unclassified bin entries would ship or vanish silently")

    @NEEDS_SOURCE
    def test_every_mcp_on_disk_is_classified(self):
        allowlist = json.loads((REPO / "export-allowlist.json").read_text())
        block = allowlist["mcp"]
        listed = {e.split("/")[0] for e in block["core"]}
        listed |= set(block.get("excluded") or {}) - {"_comment"}
        source = export_source()
        on_disk = {
            p.name for p in (source / "mcp").iterdir()
            if p.name != "__pycache__"
        }
        self.assertEqual(on_disk - listed, set(), "unclassified mcp entries would ship or vanish silently")

    @NEEDS_SOURCE
    def test_every_vendor_on_disk_is_classified(self):
        allowlist = json.loads((REPO / "export-allowlist.json").read_text())
        block = allowlist.get("vendor") or {}
        listed = set(block.get("core") or []) | (set(block.get("excluded") or {}) - {"_comment"})
        source = export_source()
        root = source / "vendor"
        if not root.is_dir():
            return
        on_disk = {p.name for p in root.iterdir() if p.name != "__pycache__"}
        self.assertEqual(on_disk - listed, set(), "unclassified vendor trees would ship or vanish silently")

    def test_benchmark_monthly_fetches_are_hard_excluded(self):
        allowlist = json.loads((REPO / "export-allowlist.json").read_text())
        hard = allowlist["hard_excludes"]
        self.assertTrue(export._excluded("benchmarks/2026-10/aa.yaml", hard))
        self.assertTrue(export._excluded("benchmarks/2026-10-deepswe.yaml", hard))
        self.assertFalse(export._excluded("benchmarks/harness.yaml", hard))

    def test_skills_vendor_layer_excludes_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            for rel in ("skills-vendor/claude/graphify/SKILL.md",
                        "skills-vendor/claude/orchestrate/SKILL.md"):
                (source / rel).parent.mkdir(parents=True)
                (source / rel).write_text("x")
            allowlist = {"skills_vendor": {"core": ["claude"],
                                           "core_excludes": ["claude/graphify/**"]}}
            chosen = export.selected_files(source, allowlist, {"core"})
        self.assertEqual(set(chosen), {"skills-vendor/claude/orchestrate/SKILL.md"})

    @NEEDS_SOURCE
    def test_every_bin_vendor_on_disk_is_classified(self):
        self._assert_top_level_classified("bin_vendor", "bin-vendor", ("core",))

    @NEEDS_SOURCE
    def test_every_benchmark_on_disk_is_classified(self):
        allowlist = json.loads((REPO / "export-allowlist.json").read_text())
        hard = allowlist["hard_excludes"]
        listed = set(allowlist["benchmarks"]["core"])
        root = export_source() / "benchmarks"
        if not root.is_dir():
            return
        on_disk = {p.name for p in root.iterdir()
                   if not export._excluded(f"benchmarks/{p.name}", hard)}
        self.assertEqual(on_disk - listed, set(),
                         "unclassified benchmark inputs would ship or vanish silently")

    @NEEDS_SOURCE
    def test_every_rules_on_disk_is_classified(self):
        self._assert_top_level_classified(
            "rules", "rules", ("core", "enonic", "client"),
        )

    @NEEDS_SOURCE
    def test_every_hooks_on_disk_is_classified(self):
        self._assert_top_level_classified("hooks", "hooks", ("core",))

    @NEEDS_SOURCE
    def test_every_config_on_disk_is_classified(self):
        self._assert_top_level_classified("config", "config", ("core",))

    @NEEDS_SOURCE
    def test_every_skills_vendor_on_disk_is_classified(self):
        self._assert_top_level_classified(
            "skills_vendor", "skills-vendor", ("core", "files"),
        )

    @NEEDS_SOURCE
    def test_every_kb_on_disk_is_classified(self):
        self._assert_top_level_classified(
            "kb", "kb", ("core", "enonic", "client"),
        )

    def _assert_top_level_classified(
        self, section: str, rel: str, layers: tuple[str, ...],
    ) -> None:
        allowlist = json.loads((REPO / "export-allowlist.json").read_text())
        block = allowlist.get(section) or {}
        listed: set[str] = set()
        for layer in layers:
            for entry in block.get(layer) or []:
                listed.add(str(entry).split("/")[0].rstrip("/"))
        for key in block.get("excluded") or {}:
            if key == "_comment":
                continue
            listed.add(str(key).split("/")[0].rstrip("/"))
        source = export_source()
        root = source / rel
        if not root.is_dir():
            return
        on_disk = {
            p.name for p in root.iterdir()
            if p.name != "__pycache__" and not p.name.startswith(".")
        }
        self.assertEqual(
            on_disk - listed,
            set(),
            f"unclassified {rel} entries would ship or vanish silently",
        )

    @NEEDS_SOURCE
    def test_export_is_in_sync(self):
        self.assertEqual(run("export", "--check").returncode, 0)

    def test_core_is_present_and_populated(self):
        """What CI can check without the source: the committed export exists."""
        core = REPO / "core"
        self.assertTrue(core.is_dir(), "core/ is missing; run devkit export --apply")
        self.assertGreater(len(list((core / "skills").iterdir())), 20)

    def test_agentctl_group_modules_are_exported(self):
        """Listing only the entrypoint after a split exports a broken CLI."""
        entry = (REPO / "core" / "bin" / "agentctl").read_text(encoding="utf-8")
        needed = sorted(set(re.findall(r"^(?:import|from) (agentctl_\w+)", entry, re.MULTILINE)))
        self.assertTrue(needed, "agentctl must import agentctl_* group modules")
        allowlist = json.loads((REPO / "export-allowlist.json").read_text())
        listed = set(allowlist["bin"]["core"])
        missing_allow = [f"{name}.py" for name in needed if f"{name}.py" not in listed]
        missing_core = [
            name for name in needed
            if not (REPO / "core" / "bin" / f"{name}.py").is_file()
        ]
        self.assertEqual(missing_allow, [])
        self.assertEqual(missing_core, [])

    def test_agentctl_entrypoint_imports(self):
        result = subprocess.run(
            [sys.executable, str(REPO / "core" / "bin" / "agentctl"), "--help"],
            capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_no_client_identifier_in_a_core_skill(self):
        allowlist = json.loads((REPO / "export-allowlist.json").read_text())
        offenders = []
        for skill in allowlist["skills"]["core"]:
            root = REPO / "core" / "skills" / skill
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix not in {".md", ".py", ".json", ".sh"}:
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue
                if "acme-group" in text or "k8s.example.com" in text:
                    offenders.append(str(path.relative_to(REPO)))
        self.assertEqual(offenders, [], "core skills must not name a client")


class ProfileCompositionTests(unittest.TestCase):
    def test_extends_composes_layers(self):
        core, enonic = manifest.load("core"), manifest.load("enonic")
        self.assertTrue(set(core["skills"]).issubset(set(enonic["skills"])))
        self.assertGreater(len(enonic["skills"]), len(core["skills"]))

    def test_instances_are_overridden_not_appended(self):
        """A profile declaring two vendors means exactly those two."""
        php = manifest.load("php")
        self.assertEqual([i["vendor"] for i in php["instances"]], ["claude", "codex"])

    def test_inheritance_loop_is_named(self):
        """A loop must be reported by name, not hit the recursion limit."""
        with tempfile.TemporaryDirectory() as tmp:
            kit = Path(tmp)
            (kit / "profiles").mkdir()
            (kit / "export-allowlist.json").write_text("{}", encoding="utf-8")
            for name, parent in (("a", "b"), ("b", "a")):
                (kit / "profiles" / f"{name}.json").write_text(
                    json.dumps({"name": name, "extends": parent}), encoding="utf-8")
            with self.assertRaises(DevkitError) as caught:
                manifest.load("a", kit_root=kit)
            self.assertIn("loops", str(caught.exception))
            self.assertIn("a -> b", str(caught.exception))

    def test_palette_fallback_is_stable_and_distinct(self):
        a = instances.profile_colors({"name": "alpha"})
        b = instances.profile_colors({"name": "beta"})
        self.assertEqual(a, instances.profile_colors({"name": "alpha"}))
        self.assertIn(a[0], instances.PROFILE_PALETTE)
        self.assertIn(b[0], instances.PROFILE_PALETTE)
        # Distinct names usually land on distinct slots; if they collide the
        # create-time assigner still enforces uniqueness against provenance.
        self.assertEqual(len(instances.PROFILE_PALETTE), 16)

    def test_declared_color_wins_over_the_derived_hue(self):
        declared = {"name": "x", "color": {"light": "#ffcc00", "dark": "#6a0dad"}}
        self.assertEqual(instances.profile_colors(declared), ("#ffcc00", "#6a0dad"))

    def test_assign_color_refuses_duplicates_and_accepts_custom(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            root = home / ".agents-profiles" / "taken" / "claude"
            root.mkdir(parents=True)
            write_json = __import__("devkit_cli.common", fromlist=["write_json"]).write_json
            write_json(root / instances.PROVENANCE_NAME, {
                "profile": "taken", "vendor": "claude", "color": "#FF453A",
            })
            with self.assertRaises(DevkitError) as caught:
                instances.assign_profile_color(
                    {"name": "other"}, home, explicit="#ff453a")
            self.assertIn("already used", str(caught.exception))
            pair = instances.assign_profile_color(
                {"name": "other"}, home, explicit="#ABCDEF")
            self.assertEqual(pair["light"], "#abcdef")
            self.assertNotEqual(pair["dark"], pair["light"])

    def test_assign_color_picks_free_palette_when_unset(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            first = instances.assign_profile_color({"name": "a"}, home)
            again = instances.assign_profile_color({"name": "a"}, home)
            self.assertEqual(first, again)
            self.assertIn(first["light"], instances.PROFILE_PALETTE)
            # Claim the rest of the palette via fake provenance so the next
            # create must avoid first["light"].
            used = {first["light"]}
            for i, color in enumerate(instances.PROFILE_PALETTE):
                if color in used:
                    continue
                root = home / ".agents-profiles" / f"p{i}" / "claude"
                root.mkdir(parents=True)
                (root / instances.PROVENANCE_NAME).write_text(
                    json.dumps({"profile": f"p{i}", "vendor": "claude",
                                "color": color}),
                    encoding="utf-8")
                used.add(color)
            # Only first["light"] remains free among the palette... actually we
            # claimed all except we started with first which isn't in provenance.
            # Put first into provenance too, forcing an off-palette draw.
            root = home / ".agents-profiles" / "claimed" / "claude"
            root.mkdir(parents=True)
            (root / instances.PROVENANCE_NAME).write_text(
                json.dumps({"profile": "claimed", "vendor": "claude",
                            "color": first["light"]}),
                encoding="utf-8")
            overflow = instances.assign_profile_color({"name": "overflow"}, home)
            self.assertNotIn(overflow["light"], used)

    def test_provenance_color_keeps_type_dark_when_light_matches(self):
        profile = {"name": "enonic", "color": {"light": "#ffcc00", "dark": "#6a0dad"}}
        instances.apply_provenance_color(profile, {"color": "#FFCC00"})
        self.assertEqual(profile["color"], {"light": "#ffcc00", "dark": "#6a0dad"})
        instances.apply_provenance_color(profile, {"color": "#ff453a"})
        self.assertEqual(profile["color"]["light"], "#ff453a")
        self.assertNotEqual(profile["color"]["dark"], "#6a0dad")

    def test_graft_mcp_is_skipped_and_not_a_profile_default(self):
        catalog = json.loads((REPO / "core" / "mcp" / "catalog.json").read_text())
        self.assertIn("graft", catalog["skip"])
        for name in ("slack-workspace-leanon", "playwright", "browser-control"):
            self.assertIn(name, catalog["parked"], name)
        expected = {
            "core": ["context7", "serena"],
            "php": ["context7", "serena"],
            "extract": ["serena"],
            "enonic": ["context7", "serena", "gitlab"],
            "client": ["context7", "serena", "gitlab", "atlassian-rovo-preview"],
        }
        for name, names in expected.items():
            profile = manifest.load(name)
            self.assertEqual(profile.get("mcp", []), names, name)
            for parked in (*catalog["parked"], *catalog["skip"]):
                self.assertNotIn(parked, profile.get("mcp", []),
                                 f"{name} must not enable parked {parked} MCP by default")

    def test_materialize_writes_live_mcp_and_skips_parked(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            materialize(load_for_create("dummy", "enonic"),
                        ["cursor", "claude", "codex"],
                        home, Plan(apply=True), force=True)
            live = ["context7", "gitlab", "serena"]
            cursor = json.loads(
                (home / ".agents-profiles/dummy/cursor/mcp.json").read_text())
            self.assertEqual(sorted(cursor["mcpServers"]), live)
            claude = json.loads(
                (home / ".agents-profiles/dummy/claude/.claude.json").read_text())
            self.assertEqual(sorted(claude["mcpServers"]), live)
            toml = (home / ".agents-profiles/dummy/codex/config.toml").read_text()
            for name in live:
                self.assertIn(f"[mcp_servers.{name}]", toml)
            for parked in ("graft", "playwright", "slack-workspace-leanon",
                           "browser-control"):
                self.assertNotIn(parked, cursor["mcpServers"])
                self.assertNotIn(parked, claude["mcpServers"])
                self.assertNotIn(f"[mcp_servers.{parked}]", toml)

    def test_profile_mcp_commands_use_the_profile_agents_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            materialize(load_for_create("dummy", "enonic"),
                        ["cursor", "claude", "codex"],
                        home, Plan(apply=True), force=True)
            wanted = str(home / ".agents-profiles/dummy/agents/bin/serena-mcp")
            base = home / ".agents-profiles/dummy"
            cursor = json.loads((base / "cursor/mcp.json").read_text())
            claude = json.loads((base / "claude/.claude.json").read_text())
            self.assertEqual(cursor["mcpServers"]["serena"]["command"], wanted)
            self.assertEqual(claude["mcpServers"]["serena"]["command"], wanted)
            toml = (base / "codex/config.toml").read_text()
            self.assertIn(f'command = "{wanted}"', toml)
            self.assertNotIn(f"{home}/.agents/", toml)

    def test_adopt_refuses_a_directory_discovery_cannot_see(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            stock = home / ".claude"
            inside = home / ".agents-profiles" / "mine" / "claude"
            stock.mkdir()
            inside.mkdir(parents=True)
            user = argparse.Namespace(pw_dir=str(home))
            with mock.patch.object(privilege, "refuse_root", lambda *_a: user), \
                    redirect_stdout(io.StringIO()):
                adopt = lambda d: profiles.cmd_adopt(argparse.Namespace(
                    name="mine", type="core", vendor="claude", config_dir=str(d),
                    apply=True))
                with self.assertRaises(DevkitError):
                    adopt(stock)
                self.assertFalse((stock / instances.PROVENANCE_NAME).exists())
                self.assertEqual(adopt(inside), 0)
            self.assertEqual([row[:2] for row in instances.discover_instances(home)],
                             [("mine", "claude")])

    def test_client_profile_supplies_the_real_overlay(self):
        """'core/ ships only the .example.json, and the client profile supplies the real file.'"""
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            config = home / ".agents-profiles/acme/agents/config"
            config.parent.mkdir(parents=True)
            config.symlink_to(REPO / "core" / "config")  # how older syncs left it
            profile = load_for_create("acme", "client")
            with redirect_stdout(io.StringIO()):
                materialize(profile, ["claude"], home, Plan(apply=True), force=True)
            self.assertFalse(config.is_symlink())
            self.assertEqual(json.loads((config / "client-overlay.json").read_text()),
                             profile["client_overlay"])
            self.assertTrue((config / "client-overlay.example.json").is_symlink())
            with redirect_stdout(io.StringIO()):
                materialize(load_for_create("plain", "core"), ["claude"], home,
                            Plan(apply=True), force=True)
            self.assertTrue((home / ".agents-profiles/plain/agents/config").is_symlink())

    def test_sync_keeps_an_overlay_the_operator_edited(self):
        """The profile writes placeholders once; the operator's real hosts survive a sync."""
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            profile = load_for_create("acme", "client")
            with redirect_stdout(io.StringIO()):
                materialize(profile, ["claude"], home, Plan(apply=True), force=True)
            overlay = home / ".agents-profiles/acme/agents/config/client-overlay.json"
            overlay.write_text('{"git_host": "git.corp.test"}\n', encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                materialize(profile, ["claude"], home, Plan(apply=True), force=False)
            self.assertEqual(json.loads(overlay.read_text()), {"git_host": "git.corp.test"})
            with redirect_stdout(io.StringIO()):
                materialize(profile, ["claude"], home, Plan(apply=True), force=True)
            self.assertEqual(json.loads(overlay.read_text()), profile["client_overlay"])

    def test_sync_keeps_claude_state_outside_mcp_servers(self):
        """.claude.json also holds login state and trust flags, which sync must not erase."""
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            profile = load_for_create("dummy", "enonic")
            materialize(profile, ["claude"], home, Plan(apply=True), force=True)
            path = home / ".agents-profiles/dummy/claude/.claude.json"
            data = json.loads(path.read_text())
            data["oauthAccount"] = {"emailAddress": "someone@example.com"}
            data["projects"] = {"/work": {"hasTrustDialogAccepted": True}}
            path.write_text(json.dumps(data, indent=2) + "\n")
            materialize(profile, ["claude"], home, Plan(apply=True), force=True)
            after = json.loads(path.read_text())
            self.assertEqual(after["oauthAccount"], data["oauthAccount"])
            self.assertEqual(after["projects"], data["projects"])
            self.assertEqual(sorted(after["mcpServers"]), sorted(data["mcpServers"]))

    def test_sync_keeps_spawned_playwright_mcp(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            materialize(load_for_create("dummy", "enonic"), ["cursor", "claude", "codex"],
                        home, Plan(apply=True), force=True)
            spec = {"url": "http://localhost:8939/mcp"}
            cursor_path = home / ".agents-profiles/dummy/cursor/mcp.json"
            data = json.loads(cursor_path.read_text())
            data["mcpServers"]["playwright-JOT-101"] = spec
            cursor_path.write_text(json.dumps(data, indent=2) + "\n")
            claude_path = home / ".agents-profiles/dummy/claude/.claude.json"
            cdata = json.loads(claude_path.read_text())
            cdata["mcpServers"]["playwright-JOT-101"] = {"type": "http", **spec}
            claude_path.write_text(json.dumps(cdata, indent=2) + "\n")
            toml_path = home / ".agents-profiles/dummy/codex/config.toml"
            toml_path.write_text(
                toml_path.read_text()
                + '\n[mcp_servers.playwright-JOT-101]\nurl = "http://localhost:8939/mcp"\n')
            materialize(load_for_create("dummy", "enonic"), ["cursor", "claude", "codex"],
                        home, Plan(apply=True), force=True)
            self.assertEqual(
                json.loads(cursor_path.read_text())["mcpServers"]["playwright-JOT-101"],
                spec)
            self.assertIn("playwright-JOT-101",
                          json.loads(claude_path.read_text())["mcpServers"])
            self.assertIn("[mcp_servers.playwright-JOT-101]", toml_path.read_text())


def _load_playwright():
    import importlib.util
    path = REPO / "core" / "mcp" / "playwright.py"
    spec = importlib.util.spec_from_file_location("devkit_playwright", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class PlaywrightProfileEnableTests(unittest.TestCase):
    """spawn --enable must write playwright-<id> into profile MCP files,
    not only the stock ~/.cursor ~/.claude ~/.codex configs."""

    def _instance(self, home: Path, name: str, vendor: str) -> Path:
        config = home / ".agents-profiles" / name / vendor
        config.mkdir(parents=True)
        (config / ".devkit-profile.json").write_text(
            json.dumps({"profile": name, "vendor": vendor}), encoding="utf-8")
        return config

    def test_enable_on_profiles_writes_all_three_vendors(self):
        pw = _load_playwright()
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cursor = self._instance(home, "dummy", "cursor")
            (cursor / "mcp.json").write_text(
                json.dumps({"mcpServers": {"context7": {"url": "https://x"}}}) + "\n")
            claude = self._instance(home, "dummy", "claude")
            (claude / ".claude.json").write_text(
                json.dumps({"mcpServers": {}}) + "\n")
            codex = self._instance(home, "dummy", "codex")
            (codex / "config.toml").write_text("model = \"x\"\n")
            url = "http://localhost:8942/mcp"
            with mock.patch.dict(os.environ):
                os.environ.pop("DEVKIT_PROFILE", None)
                pw.enable_on_profiles(home, "playwright-JOT-101", url,
                                      ["cursor", "claude", "codex"], dry_run=False)
                cursor_mcp = json.loads((cursor / "mcp.json").read_text())["mcpServers"]
                self.assertEqual(cursor_mcp["playwright-JOT-101"], {"url": url})
                self.assertEqual(cursor_mcp["context7"]["url"], "https://x")
                claude_mcp = json.loads((claude / ".claude.json").read_text())["mcpServers"]
                self.assertEqual(claude_mcp["playwright-JOT-101"]["url"], url)
                toml = (codex / "config.toml").read_text()
                self.assertIn("[mcp_servers.playwright-JOT-101]", toml)
                self.assertIn(url, toml)
                pw.disable_on_profiles(home, "playwright-JOT-101",
                                       ["cursor", "claude", "codex"], dry_run=False)
                self.assertNotIn("playwright-JOT-101",
                                 json.loads((cursor / "mcp.json").read_text())["mcpServers"])
                self.assertNotIn("playwright-JOT-101",
                                 json.loads((claude / ".claude.json").read_text())["mcpServers"])
                self.assertNotIn("[mcp_servers.playwright-JOT-101]",
                                 (codex / "config.toml").read_text())

    def test_devkit_profile_hides_sibling_mcp(self):
        pw = _load_playwright()
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            dummy = self._instance(home, "dummy", "cursor")
            (dummy / "mcp.json").write_text(json.dumps({"mcpServers": {}}) + "\n")
            other = self._instance(home, "php", "cursor")
            (other / "mcp.json").write_text(json.dumps({"mcpServers": {}}) + "\n")
            saved = os.environ.get("DEVKIT_PROFILE")
            os.environ["DEVKIT_PROFILE"] = "dummy"
            try:
                pw.enable_on_profiles(
                    home, "playwright-JOT-101", "http://localhost:8943/mcp",
                    ["cursor"], dry_run=False)
            finally:
                if saved is None:
                    os.environ.pop("DEVKIT_PROFILE", None)
                else:
                    os.environ["DEVKIT_PROFILE"] = saved
            self.assertIn(
                "playwright-JOT-101",
                json.loads((dummy / "mcp.json").read_text())["mcpServers"])
            self.assertNotIn(
                "playwright-JOT-101",
                json.loads((other / "mcp.json").read_text())["mcpServers"])


class AgentsHomeTests(unittest.TestCase):
    """agentctl must honor AGENTS_HOME; Path.home()/.agents is the fallback."""

    def test_agents_home_env_overrides_dot_agents(self):
        sys.path.insert(0, str(REPO / "core" / "bin"))
        import agentctl_jira
        saved = os.environ.get("AGENTS_HOME")
        os.environ["AGENTS_HOME"] = "/tmp/profile-agents"
        try:
            self.assertEqual(agentctl_jira.agents_home(), Path("/tmp/profile-agents"))
        finally:
            if saved is None:
                os.environ.pop("AGENTS_HOME", None)
            else:
                os.environ["AGENTS_HOME"] = saved


class ProfileIsolationTests(unittest.TestCase):
    """A profile must not load sibling skills, a full core/ tree, or shared
    Playwright storage state."""

    ENONIC_ONLY = "apply-react4xp-practices"

    def test_php_profile_does_not_see_enonic_skills_or_full_core(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            materialize(load_for_create("phpbox", "php"), ["claude"], home,
                        Plan(apply=True), force=True)
            materialize(load_for_create("xpbox", "enonic"), ["claude"], home,
                        Plan(apply=True), force=True)
            php_skills = home / ".agents-profiles" / "phpbox" / "agents" / "skills"
            xp_skills = home / ".agents-profiles" / "xpbox" / "agents" / "skills"
            self.assertTrue((xp_skills / self.ENONIC_ONLY).exists(),
                            "enonic profile should project XP skills")
            self.assertFalse((php_skills / self.ENONIC_ONLY).exists(),
                             "php profile must not project enonic skills")
            php_vendor = home / ".agents-profiles" / "phpbox" / "claude" / "skills"
            self.assertFalse((php_vendor / self.ENONIC_ONLY).exists())
            php_root = home / ".agents-profiles" / "phpbox"
            self.assertFalse((php_root / "core").exists(),
                             "full core/ symlink leaks every exported skill")
            self.assertTrue((php_root / "hooks").is_dir())
            settings = json.loads(
                (home / ".agents-profiles" / "phpbox" / "claude" / "settings.json")
                .read_text())
            extra = settings["permissions"]["additionalDirectories"]
            self.assertNotIn(str(php_root), extra)
            self.assertIn(str(php_root / "agents"), extra)

    def test_auth_does_not_share_storage_state_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            host_auth = home / ".agents" / ".auth"
            host_auth.mkdir(parents=True)
            (host_auth / "user.json").write_text('{"cookies":[]}\n')
            (host_auth / "jira-api-token.yaml").write_text("token: x\n")
            materialize(load_for_create("dummy", "core"), ["claude"], home,
                        Plan(apply=True), force=True)
            dest = home / ".agents-profiles" / "dummy" / "agents" / ".auth"
            self.assertTrue(dest.is_dir())
            self.assertFalse(dest.is_symlink())
            self.assertFalse((dest / "user.json").exists())
            token = dest / "jira-api-token.yaml"
            self.assertTrue(token.is_symlink())
            self.assertEqual(token.resolve(), (host_auth / "jira-api-token.yaml").resolve())


class PrivilegeTests(unittest.TestCase):
    """'install.py run as root without --user must exit 2 and name the target
    user'; 'Resolution to a /root home, or to uid 0, must be refused.'"""

    def test_root_without_user_is_refused_and_names_the_fix(self):
        original = privilege.is_root
        privilege.is_root = lambda: True
        saved = os.environ.pop("SUDO_USER", None)
        try:
            with self.assertRaises(DevkitError) as caught:
                privilege.refuse_root(None)
            self.assertIn("--user", caught.exception.fix)
        finally:
            privilege.is_root = original
            if saved:
                os.environ["SUDO_USER"] = saved

    def test_root_with_user_writes_as_that_account(self):
        """'Every created path is then owned by that account.'"""
        entry = pwd.getpwuid(os.getuid())
        calls = []
        with mock.patch.object(privilege, "is_root", lambda: True), \
                mock.patch.dict(os.environ, {}), \
                mock.patch("os.setgroups", lambda g: calls.append(("groups",))), \
                mock.patch("os.setresgid", lambda *a: calls.append(("gid", *a))), \
                mock.patch("os.setresuid", lambda *a: calls.append(("uid", *a))):
            self.assertEqual(privilege.refuse_root(entry.pw_name), entry)
            self.assertEqual(os.environ["HOME"], entry.pw_dir)
        self.assertEqual(calls, [("groups",), ("gid", entry.pw_gid, entry.pw_gid, 0),
                                 ("uid", entry.pw_uid, entry.pw_uid, 0)])

    def test_regain_root_needs_a_saved_root_uid(self):
        with mock.patch("os.getresuid", lambda: (1000, 1000, 1000)), \
                mock.patch("os.geteuid", lambda: 1000):
            self.assertFalse(privilege.regain_root())
        calls = []
        with mock.patch("os.getresuid", lambda: (1000, 1000, 0)), \
                mock.patch("os.geteuid", lambda: 1000), \
                mock.patch("os.setresuid", lambda *a: calls.append(a)), \
                mock.patch("os.setresgid", lambda *a: None), \
                mock.patch("os.setgroups", lambda g: None):
            self.assertTrue(privilege.regain_root())
        self.assertEqual(calls, [(0, 0, 0)])

    def test_uid_zero_is_refused(self):
        with self.assertRaises(DevkitError):
            privilege.resolve_target_user("root")

    def test_unknown_user_is_named(self):
        with self.assertRaises(DevkitError) as caught:
            privilege.resolve_target_user("definitely-not-a-user")
        self.assertIn("definitely-not-a-user", str(caught.exception))

    def test_elevation_prints_the_plan_before_sudo(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            privilege.explain_elevation(
                "they install packages into the system.",
                ["sudo apt-get update", "sudo apt-get install -y python3"])
        text = buf.getvalue()
        self.assertIn("These steps need administrator privileges", text)
        self.assertIn("sudo apt-get update", text)
        self.assertIn(privilege.ELEVATION_BANNER, text)
        self.assertLess(text.find("sudo apt-get update"),
                        text.find(privilege.ELEVATION_BANNER))

    def _run_privileged_with(self, path_dir: Path, *, interactive: bool):
        # CI runs this suite as root. run_privileged refuses uid 0; this test
        # is about print-then-elevate order, so pretend we still need to escalate.
        original_is_root = privilege.is_root
        original_interactive = privilege.shell_is_interactive
        privilege.is_root = lambda: False
        privilege.shell_is_interactive = lambda: interactive
        saved_path = os.environ.get("PATH", "")
        os.environ["PATH"] = str(path_dir)
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                rc = privilege.run_privileged(
                    [sys.executable, str(path_dir / "inner.py")],
                    reason="they write into /usr/lib/devkit.",
                    steps=["rsync stock -> fork"],
                )
        finally:
            privilege.is_root = original_is_root
            privilege.shell_is_interactive = original_interactive
            os.environ["PATH"] = saved_path
        return rc, buf.getvalue()

    def test_run_privileged_invokes_sudo_after_printing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / "order.txt"
            sudo = root / "sudo"
            sudo.write_text(
                "#!/bin/sh\n"
                f"echo sudo-ran >> '{marker}'\n"
                "if [ \"$1\" = -- ]; then shift; fi\n"
                "exec \"$@\"\n",
                encoding="utf-8")
            sudo.chmod(0o755)
            inner = root / "inner.py"
            inner.write_text(
                f"open({str(marker)!r}, 'a').write('inner-ran\\n')\n",
                encoding="utf-8")
            rc, text = self._run_privileged_with(root, interactive=True)
            self.assertEqual(rc, 0)
            self.assertIn("rsync stock -> fork", text)
            self.assertIn(privilege.ELEVATION_BANNER, text)
            self.assertIn("sudo --", text)
            self.assertLess(text.find(privilege.ELEVATION_BANNER),
                            text.find("sudo --"))
            self.assertEqual(marker.read_text().splitlines(), ["sudo-ran", "inner-ran"])

    def test_run_privileged_uses_pkexec_when_not_a_tty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / "order.txt"
            pkexec = root / "pkexec"
            pkexec.write_text(
                "#!/bin/sh\n"
                f"echo pkexec-ran >> '{marker}'\n"
                "exec \"$@\"\n",
                encoding="utf-8")
            pkexec.chmod(0o755)
            inner = root / "inner.py"
            inner.write_text(
                f"open({str(marker)!r}, 'a').write('inner-ran\\n')\n",
                encoding="utf-8")
            rc, text = self._run_privileged_with(root, interactive=False)
            self.assertEqual(rc, 0)
            self.assertIn("pkexec", text)
            self.assertNotIn("sudo --", text)
            self.assertIn("Non-interactive shell", text)
            self.assertLess(text.find(privilege.ELEVATION_BANNER),
                            text.find("pkexec"))
            self.assertEqual(marker.read_text().splitlines(), ["pkexec-ran", "inner-ran"])

    def test_run_privileged_uses_sudo_askpass_without_pkexec(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / "order.txt"
            sudo = root / "sudo"
            sudo.write_text(
                "#!/bin/sh\n"
                f"echo sudo-A-ran >> '{marker}'\n"
                "while [ \"$1\" = -A ] || [ \"$1\" = -- ]; do shift; done\n"
                "exec \"$@\"\n",
                encoding="utf-8")
            sudo.chmod(0o755)
            inner = root / "inner.py"
            inner.write_text(
                f"open({str(marker)!r}, 'a').write('inner-ran\\n')\n",
                encoding="utf-8")
            rc, text = self._run_privileged_with(root, interactive=False)
            self.assertEqual(rc, 0)
            self.assertIn("sudo -A --", text)
            self.assertEqual(marker.read_text().splitlines(), ["sudo-A-ran", "inner-ran"])

    def test_bootstrap_elevate_uses_pkexec_when_not_a_tty(self):
        src = (REPO / "bootstrap.sh").read_text(encoding="utf-8")
        start = src.index("interactive_shell()")
        end = src.index("\n# ---------------------------------------------------------------- family")
        funcs = src[start:end]
        bash = shutil.which("bash")
        self.assertIsNotNone(bash)

        def run(path_dir: Path) -> subprocess.CompletedProcess[str]:
            script = (
                "say() { printf '%s\\n' \"$*\"; }\n"
                f"{funcs}\n"
                "APPLY=1\n"
                "ELEVATION_ANNOUNCED=1\n"
                "ELEVATION_ASKED=0\n"
                "elevate /bin/true\n"
            )
            env = os.environ.copy()
            env["PATH"] = str(path_dir)
            return subprocess.run(
                [bash, "-c", script],
                stdin=subprocess.DEVNULL, capture_output=True, text=True,
                check=False, env=env)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pkexec = root / "pkexec"
            pkexec.write_text("#!/bin/sh\necho pkexec-ran \"$@\"\n", encoding="utf-8")
            pkexec.chmod(0o755)
            result = run(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Non-interactive shell", result.stdout)
            self.assertIn("+ pkexec /bin/true", result.stdout)
            self.assertIn("pkexec-ran /bin/true", result.stdout)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sudo = root / "sudo"
            sudo.write_text("#!/bin/sh\necho sudo-ran \"$@\"\n", encoding="utf-8")
            sudo.chmod(0o755)
            result = run(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("+ sudo -A -- /bin/true", result.stdout)
            self.assertIn("sudo-ran -A -- /bin/true", result.stdout)

    def test_noninteractive_shell_has_no_tty_on_stdin_or_stdout(self):
        # Same check elevate() uses: a line prints only when that fd is a tty.
        script = (
            "if [ -t 0 ] ; then echo stdin; fi\n"
            "if [ -t 1 ] ; then echo stdout; fi\n"
        )
        cmd = subprocess.run(
            ["bash", "-c", script],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False)
        self.assertEqual(cmd.stdout, "")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO)
        probe = subprocess.run(
            [sys.executable, "-c",
             ("from devkit_cli.privilege import shell_is_interactive\n"
              "print('yes' if shell_is_interactive() else 'no')")],
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            check=False, env=env)
        self.assertEqual(probe.stdout.strip(), "no", probe.stderr)

    def test_bootstrap_dry_run_labels_root_commands(self):
        result = subprocess.run(
            ["bash", str(REPO / "bootstrap.sh"), "--profile", "core"],
            capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("would run (as root): sudo", result.stdout)
        self.assertNotIn(privilege.ELEVATION_BANNER, result.stdout)


class RenderingTests(unittest.TestCase):
    def test_no_unrendered_token_survives(self):
        profile = manifest.load("enonic")
        tokens = instances.render_tokens(profile, "codex", Path("/home/example"))
        for template in (REPO / "templates").rglob("*"):
            if not template.is_file() or template.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".ico"}:
                continue
            rendered = instances.render(template.read_text(encoding="utf-8"), tokens)
            # Only real tokens count. A comment saying "${PROFILE_*} is rendered
            # by install.py" is documentation, not an unrendered token.
            leftovers = re.findall(r"\$\{PROFILE_[A-Z_]+\}", rendered)
            self.assertEqual(leftovers, [], f"{template.name} has unrendered tokens")

    def test_rendering_is_home_relative_not_hardcoded(self):
        profile = manifest.load("core")
        tokens = instances.render_tokens(profile, "claude", Path("/home/someone-else"))
        self.assertTrue(tokens["PROFILE_CONFIG_DIR"].startswith("/home/someone-else/"))


class DocsGateTests(unittest.TestCase):
    """'devkit docs generate --check must produce no diff on a clean tree, and
    must fail after a CLI change that did not regenerate.' 'Every file under
    docs/ must be reachable from README.md.'"""

    def test_docs_are_up_to_date(self):
        self.assertEqual(run("docs", "generate", "--check").returncode, 0)

    def test_every_doc_is_reachable_from_the_readme(self):
        from devkit_cli import docsgen
        self.assertEqual(docsgen.unreachable_docs(), [])

    def test_an_orphan_doc_fails_the_gate(self):
        orphan = REPO / "docs" / "_orphan-test.md"
        orphan.write_text("# orphan\n", encoding="utf-8")
        try:
            self.assertEqual(run("docs", "generate", "--check").returncode, 1)
        finally:
            orphan.unlink()


class IgnoredPathTests(unittest.TestCase):
    """'The gate reads tracked source, not local state.'

    agentctl writes scan JSON into .security-local/, and trivy embeds commit
    messages in it. Without the ignore entry a routine scan fails lint-paths
    over a path nobody wrote.
    """

    def test_local_state_is_not_scanned(self):
        contract = json.loads((REPO / "path-contract.json").read_text())
        planted = REPO / ".security-local" / "lint-fixture.json"
        planted.parent.mkdir(exist_ok=True)
        planted.write_text('{"note": "~/.local/bin"}\n', encoding="utf-8")
        try:
            self.assertEqual(paths.scan([REPO], contract), [])
        finally:
            planted.unlink()


class InlineCodeTests(unittest.TestCase):
    def test_a_link_inside_backticks_is_not_a_link(self):
        """A document explaining the ~ rule must be able to quote it."""
        contract = json.loads((REPO / "path-contract.json").read_text())
        found = paths.scan([REPO / "docs" / "paths.md"], contract)
        self.assertEqual([v.rule["id"] for v in found], [])


class BootstrapPlanTests(unittest.TestCase):
    def test_every_manager_yields_a_plan(self):
        for mgr in ("apt", "dnf", "pacman"):
            with self.subTest(manager=mgr):
                result = subprocess.run(
                    [sys.executable, str(REPO / "devkit_cli" / "bootstrap_plan.py"),
                     "--profile", "core", "--manager", mgr],
                    capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                kinds = {line.split("\t")[0] for line in result.stdout.splitlines()}
                self.assertTrue({"pkg", "npm", "uv", "binary"}.issubset(kinds))

    def _plan(self, manager: str, family: str | None = None) -> str:
        args = ["--profile", "core", "--manager", manager]
        if family:
            args += ["--family", family]
        return subprocess.run(
            [sys.executable, str(REPO / "devkit_cli" / "bootstrap_plan.py"), *args],
            capture_output=True, text=True, check=True).stdout

    def test_rhel_flags_the_third_party_packages(self):
        """A declined third-party repo must be a skip, never a hard failure,
        which means the plan has to name which packages need one, and which repo."""
        plan = self._plan("dnf", "rhel")
        self.assertIn("thirdparty\tffmpeg\trpmfusion", plan)
        self.assertIn("thirdparty\tripgrep\tepel", plan)

    def test_fedora_flags_nothing_although_it_also_uses_dnf(self):
        """EPEL is Fedora's packages backported to RHEL. On Fedora they are in
        base, and epel-release does not exist — so needs_repo cannot key on the
        package manager."""
        plan = self._plan("dnf", "fedora")
        self.assertNotIn("thirdparty", plan)
        self.assertIn("pkg\tripgrep", plan)

    def test_uv_python_pin_is_its_own_field(self):
        plan = self._plan("apt", "debian").splitlines()
        self.assertIn("uv\tserena-agent\t3.13", plan)
        self.assertIn("uv\truff", plan)

    def test_apt_does_not_flag_third_party(self):
        self.assertNotIn("thirdparty", self._plan("apt", "debian"))

    def test_declined_third_party_is_a_skip_not_a_missing(self):
        """Rocky CI runs --third-party no; verify must not fail on EPEL packages."""
        from unittest import mock

        from devkit_cli import bootstrap_plan, manifest
        profile = manifest.load("core")
        skippable = bootstrap_plan.third_party_binaries(profile, "dnf", "rhel")
        self.assertTrue({"rg", "shellcheck", "ffmpeg", "convert"} <= skippable)
        self.assertNotIn("jq", skippable)

        with mock.patch("devkit_cli.bootstrap_plan.shutil.which", return_value=None), \
             mock.patch("devkit_cli.bootstrap_plan._alternate", return_value=None):
            self.assertEqual(
                bootstrap_plan.verify(profile, manager="dnf", family="rhel"), 1)
            self.assertEqual(
                bootstrap_plan.verify(
                    profile, manager="dnf", family="rhel",
                    third_party_declined=True),
                1)

        with mock.patch("devkit_cli.bootstrap_plan.shutil.which",
                        side_effect=lambda b: f"/usr/bin/{b}"), \
             mock.patch("devkit_cli.bootstrap_plan._alternate", return_value=None):
            self.assertEqual(
                bootstrap_plan.verify(
                    profile, manager="dnf", family="rhel",
                    third_party_declined=True),
                0)

        def which_no_epel(binary: str):
            if binary in skippable:
                return None
            return f"/usr/bin/{binary}"

        with mock.patch("devkit_cli.bootstrap_plan.shutil.which",
                        side_effect=which_no_epel), \
             mock.patch("devkit_cli.bootstrap_plan._alternate", return_value=None):
            self.assertEqual(
                bootstrap_plan.verify(
                    profile, manager="dnf", family="rhel",
                    third_party_declined=True),
                0)
            self.assertEqual(
                bootstrap_plan.verify(profile, manager="dnf", family="rhel"), 1)

    def test_a_manager_without_a_package_uses_the_declared_fallback(self):
        """ocrmypdf is absent from EPEL and AUR-only on Arch, and nothing here
        may require the AUR."""
        for manager, family in (("dnf", "rhel"), ("pacman", "arch")):
            with self.subTest(manager=manager):
                plan = self._plan(manager, family)
                self.assertIn("uv\tocrmypdf", plan)
                self.assertNotIn("pkg\tocrmypdf", plan)


class ModeTests(unittest.TestCase):
    """'Under umask 077 and umask 022, resulting modes must be identical.'"""

    def _install(self, umask: int, home: Path) -> list[str]:
        previous = os.umask(umask)
        try:
            materialize(manifest.load("core"), ["claude"], home, Plan(apply=True), force=True)
        finally:
            os.umask(previous)
        return sorted(f"{path.stat().st_mode & 0o777:o} {path.relative_to(home)}"
                      for path in home.rglob("*") if not path.is_symlink())

    def test_modes_do_not_inherit_the_umask(self):
        with tempfile.TemporaryDirectory() as tmp:
            strict = self._install(0o077, Path(tmp) / "strict")
            loose = self._install(0o022, Path(tmp) / "loose")
        self.assertEqual(strict, loose)
        self.assertIn("755 .local/bin/claude-core", strict)


class UpdateApplyTests(unittest.TestCase):
    """'update apply completes with the network down, from staged content.'

    apply used to re-materialize from the local checkout while stamping the
    staged commit into provenance, so the instance recorded a commit it had
    never been built from.
    """

    MARKER = "# staged-payload marker\n"

    def _stage(self, root: Path, commit: str) -> Path:
        payload = root / commit
        payload.mkdir(parents=True)
        for item in ("profiles", "templates", "devkit.yaml", "export-allowlist.json"):
            source = REPO / item
            if source.is_dir():
                shutil.copytree(source, payload / item)
            else:
                shutil.copy2(source, payload / item)
        (payload / "core" / "skills").mkdir(parents=True)
        catalog = REPO / "core" / "mcp" / "catalog.json"
        if catalog.is_file():
            mcp_dir = payload / "core" / "mcp"
            mcp_dir.mkdir(parents=True)
            shutil.copy2(catalog, mcp_dir / "catalog.json")
        wrapper = payload / "templates" / "shell" / "claude.sh"
        wrapper.write_text(wrapper.read_text() + self.MARKER, encoding="utf-8")
        (payload / ".devkit-staged.json").write_text(json.dumps({
            "commit": commit,
            "lineage_id": _kit_lineage(),
            "upstream": "unused", "fetched_at": "20260101T000000Z"}), encoding="utf-8")
        return payload

    def test_apply_installs_the_staged_payload(self):
        commit = "d" * 40
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            self._stage(Path(tmp) / "staged", commit)
            materialize(manifest.load("core"), ["claude"], home, Plan(apply=True), force=True)

            # The root guard is PrivilegeTests' subject, not this one's, and CI
            # runs as root — where it would refuse before apply does anything.
            staging, home_fn = update.STAGING_ROOT, Path.home
            guard = privilege.refuse_root
            update.STAGING_ROOT = Path(tmp) / "staged"
            Path.home = staticmethod(lambda: home)
            privilege.refuse_root = lambda *_a, **_kw: None
            try:
                with redirect_stdout(io.StringIO()):
                    rc = update.cmd_apply(argparse.Namespace(profile="core", apply=True))
            finally:
                update.STAGING_ROOT, Path.home = staging, home_fn
                privilege.refuse_root = guard

            wrapper = (home / ".local" / "bin" / "claude-core").read_text()
            provenance = json.loads(
                (home / ".agents-profiles" / "core" / "claude"
                 / instances.PROVENANCE_NAME).read_text())

        self.assertEqual(rc, 0)
        self.assertIn(self.MARKER.strip(), wrapper)
        self.assertEqual(provenance["source_commit"], commit)
        self.assertEqual(provenance["history"][-1]["to"], commit)


class InstanceNamingTests(unittest.TestCase):
    def test_create_binds_a_free_form_name_to_a_type(self):
        profile = load_for_create("dummy", "enonic")
        self.assertEqual(profile["name"], "dummy")
        self.assertEqual(profile["type"], "enonic")
        self.assertEqual([i["vendor"] for i in profile["instances"]],
                         ["claude", "codex", "cursor"])

    def test_create_without_type_keeps_name_equals_type(self):
        profile = load_for_create("php", None)
        self.assertEqual(profile["name"], "php")
        self.assertEqual(profile["type"], "php")

    def test_unknown_name_without_type_is_named(self):
        with self.assertRaises(DevkitError) as caught:
            load_for_create("dummy", None)
        self.assertIn("--type", str(caught.exception.fix))

    def test_duplicate_name_is_refused_even_with_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            profile = load_for_create("dummy", "enonic")
            materialize(profile, ["codex"], home, Plan(apply=True), force=True)
            with self.assertRaises(DevkitError) as caught:
                from devkit_cli.profiles import _refuse_duplicate
                _refuse_duplicate(home, "dummy")
            self.assertIn("already exists", str(caught.exception))

    def test_slash_in_the_name_is_refused(self):
        with self.assertRaises(DevkitError):
            instances.validate_instance_name("enonic/dummy")

    def test_provenance_records_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            profile = load_for_create("dummy", "enonic")
            materialize(profile, ["codex"], home, Plan(apply=True), force=True)
            prov = instances.read_provenance(
                home / ".agents-profiles" / "dummy" / "codex")
            self.assertEqual(prov["profile"], "dummy")
            self.assertEqual(prov["type"], "enonic")
            found = instances.discover_instances(home)
            self.assertEqual([(n, v) for n, v, _d, _p in found], [("dummy", "codex")])

    def test_missing_type_in_provenance_infers_name_equals_type(self):
        self.assertEqual(instances.instance_type({}, "enonic"), "enonic")
        self.assertEqual(instances.instance_type({"type": "php"}, "dummy"), "php")


class FirstProfileOfferTests(unittest.TestCase):
    def test_unattended_uses_type_as_the_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            chosen = choose_first_profile(Path(tmp), "enonic", offer=False)
        self.assertEqual(chosen, ("enonic", "enonic"))

    def test_unattended_honours_an_explicit_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            chosen = choose_first_profile(Path(tmp), "enonic", name="dummy", offer=False)
        self.assertEqual(chosen, ("dummy", "enonic"))

    def test_offer_declined_returns_none(self):
        answers = iter(["n"])
        with tempfile.TemporaryDirectory() as tmp:
            chosen = choose_first_profile(
                Path(tmp), "core", offer=True,
                input_fn=lambda _p: next(answers), print_fn=lambda *_a: None)
        self.assertIsNone(chosen)

    def test_offer_accepts_free_form_name_and_type(self):
        answers = iter(["y", "enonic", "dummy"])
        with tempfile.TemporaryDirectory() as tmp:
            chosen = choose_first_profile(
                Path(tmp), "core", offer=True,
                input_fn=lambda _p: next(answers), print_fn=lambda *_a: None)
        self.assertEqual(chosen, ("dummy", "enonic"))

    def test_offer_defaults_name_to_the_type(self):
        answers = iter(["", "php", ""])
        with tempfile.TemporaryDirectory() as tmp:
            chosen = choose_first_profile(
                Path(tmp), "core", offer=True,
                input_fn=lambda _p: next(answers), print_fn=lambda *_a: None)
        self.assertEqual(chosen, ("php", "php"))

    def test_flag_given_ignores_argparse_defaults(self):
        self.assertFalse(flag_given("--profile", ["--apply"]))
        self.assertTrue(flag_given("--profile", ["--profile", "enonic"]))
        self.assertTrue(flag_given("--name", ["--name=dummy"]))


class InstallVerifyTests(unittest.TestCase):
    """'--verify' must check the instance --name names, not the type's directory."""

    @staticmethod
    def _verify(name: str, type_name: str, home: Path) -> int:
        spec = importlib.util.spec_from_file_location("install_script", REPO / "install.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with redirect_stdout(io.StringIO()):
            return module.verify(load_for_create(name, type_name), home)

    def test_named_instance_is_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            materialize(load_for_create("dummy", "enonic"), ["claude"],
                        home, Plan(apply=True), force=True)
            self.assertEqual(self._verify("dummy", "enonic", home), 0)
            self.assertEqual(self._verify("enonic", "enonic", home), 1)

    def test_missing_instance_is_a_problem(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._verify("nosuch", "enonic", Path(tmp)), 1)


class CodexDesktopTests(unittest.TestCase):
    def test_codex_desktop_sets_both_isolation_vars(self):
        profile = load_for_create("dummy", "enonic")
        tokens = instances.render_tokens(profile, "codex", Path("/home/example"))
        rendered = instances.render(
            (REPO / "templates" / "desktop" / "codex.desktop").read_text(), tokens)
        self.assertIn("CODEX_HOME=/home/example/.agents-profiles/dummy/codex", rendered)
        self.assertIn("CODEX_ELECTRON_USER_DATA_PATH=/home/example/.config/Codex-dummy",
                      rendered)
        self.assertIn("Name=Codex · dummy", rendered)
        self.assertIn("/usr/lib/devkit/codex-dummy/codex-launcher", rendered)
        self.assertIn("StartupWMClass=Codex-dummy", rendered)
        self.assertIn("Keywords=AI;Chat;Assistant;ChatGPT;Codex;LLM;", rendered)
        self.assertNotIn("x-scheme-handler/", rendered)
        self.assertNotIn("[Desktop Action", rendered)

    def test_cursor_desktop_new_empty_window_keeps_profile_dirs(self):
        profile = load_for_create("dummy", "enonic")
        tokens = instances.render_tokens(profile, "cursor", Path("/home/example"))
        rendered = instances.render(
            (REPO / "templates" / "desktop" / "cursor.desktop").read_text(), tokens)
        self.assertIn("Actions=new-empty-window;", rendered)
        self.assertIn("[Desktop Action new-empty-window]", rendered)
        self.assertIn("--new-window", rendered)
        self.assertEqual(rendered.count(
            "--user-data-dir=/home/example/.agents-profiles/dummy/cursor"), 2)
        self.assertNotIn("x-scheme-handler/", rendered)

    def test_profile_desktops_do_not_claim_vendor_schemes(self):
        tokens = instances.render_tokens(manifest.load("enonic"), "claude",
                                         Path("/home/example"))
        for name in ("claude.desktop", "cursor.desktop", "codex.desktop"):
            text = instances.render(
                (REPO / "templates" / "desktop" / name).read_text(), tokens)
            self.assertNotIn("x-scheme-handler/", text, name)

    def test_php_still_has_no_cursor_instance(self):
        php = manifest.load("php")
        self.assertEqual([i["vendor"] for i in php["instances"]], ["claude", "codex"])
        self.assertTrue(all(i["kind"] == "cli+desktop" for i in php["instances"]))


class ProfileCliPathTests(unittest.TestCase):
    def test_wrappers_exec_the_stock_cli_token(self):
        claude = (REPO / "templates" / "shell" / "claude.sh").read_text()
        self.assertIn('exec "${PROFILE_CLAUDE_CLI}" "$@"', claude)
        self.assertNotIn("exec claude ", claude)
        self.assertIn('AGENTS_HOME="${PROFILE_AGENTS_HOME}"', claude)
        self.assertIn('PATH="${PROFILE_BIN_DIR}:${PATH}"', claude)
        self.assertIn('DEVKIT_PROFILE="${PROFILE_NAME}"', claude)
        codex = (REPO / "templates" / "shell" / "codex.sh").read_text()
        self.assertIn('exec "${PROFILE_CODEX_CLI}" "$@"', codex)
        self.assertIn('AGENTS_HOME="${PROFILE_AGENTS_HOME}"', codex)
        for name in ("claude.sh", "codex.sh", "cursor-agent.sh", "profile-tool.sh"):
            text = (REPO / "templates" / "shell" / name).read_text()
            with self.subTest(template=name):
                self.assertIn("export GRAFT_NO_GITIGNORE GRAFT_NO_IGNORE", text)
        agent = (REPO / "templates" / "shell" / "cursor-agent.sh").read_text()
        self.assertIn('"${PROFILE_CURSOR_AGENT}" "$@"', agent)
        self.assertIn('AGENTS_HOME="${PROFILE_AGENTS_HOME}"', agent)
        # XDG stays unexported; profile identity is exported.
        self.assertIn('XDG_CONFIG_HOME="${PROFILE_XDG_CONFIG_DIR}"', agent)
        self.assertNotIn("export XDG_CONFIG_HOME", agent)

    def test_public_wrapper_is_not_a_stock_name(self):
        layout = instances.paths_for("dummy", "claude", Path("/home/example"))
        self.assertEqual(layout["wrapper"].name, "claude-dummy")
        self.assertEqual(layout["bin_dir"] / "claude",
                         Path("/home/example/.agents-profiles/dummy/bin/claude"))

    def test_profile_bin_links_unprefixed_name_to_the_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            materialize(load_for_create("dummy", "enonic"), ["claude"], home,
                        Plan(apply=True), force=True)
            wrapper = home / ".local" / "bin" / "claude-dummy"
            link = home / ".agents-profiles" / "dummy" / "bin" / "claude"
            self.assertTrue(wrapper.is_file())
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(), wrapper.resolve())
            text = wrapper.read_text()
            self.assertIn("exec ", text)
            self.assertNotIn("exec claude ", text)
            self.assertIn("AGENTS_HOME=", text)
            agentctl = home / ".agents-profiles" / "dummy" / "bin" / "agentctl"
            self.assertTrue(agentctl.is_file())
            tool = agentctl.read_text()
            self.assertIn('AGENTS_HOME=', tool)
            self.assertIn("/agents/bin/", tool)
            self.assertNotIn("/core/bin/", tool)
            agents = home / ".agents-profiles" / "dummy" / "agents"
            self.assertTrue(agents.is_dir())
            self.assertTrue((agents / "bin").is_symlink())
            self.assertTrue((agents / "plans").is_dir())
            self.assertFalse((home / ".agents-profiles" / "dummy" / "core").exists())

    def test_resolve_stock_cli_skips_devkit_wrappers_and_keeps_the_shim(self):
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp)
            stock = bin_dir / "claude"
            stock.write_text("#!/bin/sh\n# vendor shim\n", encoding="utf-8")
            stock.chmod(0o755)
            wrapper = bin_dir / "claude-dummy"
            wrapper.write_text("#!/bin/sh\n# Generated by devkit\nexec /tmp/claude\n",
                               encoding="utf-8")
            saved = os.environ.get("PATH")
            os.environ["PATH"] = f"{bin_dir}{os.pathsep}{saved or ''}"
            try:
                self.assertEqual(instances.resolve_stock_cli("claude"), str(stock))
            finally:
                if saved is None:
                    del os.environ["PATH"]
                else:
                    os.environ["PATH"] = saved

    def test_desktop_launch_binds_profile_env_and_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            bin_dir = home / ".agents-profiles" / "dummy" / "bin"
            bin_dir.mkdir(parents=True)
            saved = {key: os.environ.get(key) for key in
                     ("PATH", "DEVKIT_PROFILE", "DEVKIT_PROFILE_HOME", "AGENTS_HOME",
                      "GRAFT_NO_GITIGNORE", "GRAFT_NO_IGNORE")}
            os.environ["PATH"] = "/usr/bin"
            for key in ("DEVKIT_PROFILE", "DEVKIT_PROFILE_HOME", "AGENTS_HOME"):
                os.environ.pop(key, None)
            try:
                auth.bind_profile_env(home, "dummy")
                self.assertEqual(os.environ["PATH"].split(os.pathsep)[0], str(bin_dir))
                self.assertIn("/usr/bin", os.environ["PATH"])
                self.assertEqual(os.environ["DEVKIT_PROFILE"], "dummy")
                self.assertEqual(os.environ["DEVKIT_PROFILE_HOME"],
                                 str(home / ".agents-profiles" / "dummy"))
                self.assertEqual(os.environ["AGENTS_HOME"],
                                 str(home / ".agents-profiles" / "dummy" / "agents"))
                self.assertEqual(os.environ["GRAFT_NO_GITIGNORE"], "1")
                self.assertEqual(os.environ["GRAFT_NO_IGNORE"], "1")
            finally:
                for key, value in saved.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value


class AuthDispatcherTests(unittest.TestCase):
    def test_dry_run_creates_nothing_in_the_home(self):
        """'Every one of these is a dry run without --apply.'"""
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            plan = Plan(apply=False)
            with redirect_stdout(io.StringIO()):
                materialize(load_for_create("dummy", "enonic"), None, home, plan, False)
                ensure(home, plan)
                globalignore.ensure(home, plan)
                cli_link.ensure(home, plan)
            self.assertTrue(plan.actions)
            self.assertEqual(list(home.iterdir()), [])

    def test_pending_marker_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            profile = load_for_create("dummy", "enonic")
            materialize(profile, ["codex"], home, Plan(apply=True), force=True)
            auth.write_pending(home, "dummy", "codex")
            name, vendor = auth.resolve_target("codex://callback", home, running=[])
            self.assertEqual((name, vendor), ("dummy", "codex"))

    def test_one_running_instance_is_enough_without_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            profile = load_for_create("dummy", "enonic")
            materialize(profile, ["codex"], home, Plan(apply=True), force=True)
            name, vendor = auth.resolve_target(
                "codex://callback", home, running=["dummy"])
            self.assertEqual((name, vendor), ("dummy", "codex"))

    def test_ambiguous_running_instances_refuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            for name in ("alpha", "beta"):
                materialize(load_for_create(name, "enonic"), ["codex"], home,
                            Plan(apply=True), force=True)
            with self.assertRaises(DevkitError) as caught:
                auth.resolve_target("codex://callback", home, running=["alpha", "beta"])
            self.assertIn("ambiguous", str(caught.exception))

    def test_update_discovers_a_free_form_instance(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            materialize(load_for_create("dummy", "enonic"), ["codex"], home,
                        Plan(apply=True), force=True)
            original = Path.home
            Path.home = staticmethod(lambda: home)
            try:
                found = update._installed_instances(None)
            finally:
                Path.home = original
            self.assertEqual([(n, v) for n, v, _d, _p in found], [("dummy", "codex")])
            self.assertEqual(found[0][3]["type"], "enonic")


class AppForkTests(unittest.TestCase):
    """Per-profile Electron forks rsync stock, patch identity, never write
    the stock tree, and survive via apt and dpkg hooks."""

    def _asar(self, path: Path, desktop: str, version: str = "1.0.0") -> None:
        blob = (json.dumps({"name": "app", "desktopName": desktop,
                            "productName": "Claude", "version": version}) + "\n").encode()
        header = {
            "files": {
                "package.json": {
                    "offset": "0",
                    "size": len(blob),
                    "integrity": appfork.integrity_for(blob, 4194304),
                }
            }
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        appfork.write_asar(path, header, blob, 0o644)

    def test_asar_patch_changes_desktop_name_and_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "app.asar"
            self._asar(path, "com.anthropic.Claude.desktop")
            appfork.patch_asar_package(
                path, {"desktopName": "Claude-dummy.desktop"}, dry_run=False)
            self.assertEqual(appfork.asar_desktop_name(path), "Claude-dummy.desktop")

    def test_asar_dry_run_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "app.asar"
            self._asar(path, "chatgpt.desktop")
            before = path.read_bytes()
            appfork.patch_asar_package(
                path, {"desktopName": "Codex-dummy.desktop"}, dry_run=True)
            self.assertEqual(path.read_bytes(), before)

    def test_asar_identity_follows_the_profile_slug(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stock = root / "stock"
            stock.mkdir()
            spec = appfork.Vendor(
                name="claude", package="claude-desktop", stock_lib=stock,
                binary="claude-desktop",
                stock_desktop_name="com.anthropic.Claude.desktop",
                asar_rel="resources/app.asar",
            )
            for profile in ("enonic", "php"):
                dest = root / f"claude-{profile}"
                self._asar(dest / "resources" / "app.asar",
                           "com.anthropic.Claude.desktop")
                appfork.patch_identity(spec, dest, profile, dry_run=False)
                self.assertEqual(
                    appfork.asar_desktop_name(dest / "resources" / "app.asar"),
                    f"Claude-{profile}.desktop",
                )

    def test_cursor_unpacked_identity_patches_desktop_name_and_nameshort(self):
        with tempfile.TemporaryDirectory() as tmp:
            stock = Path(tmp) / "stock"
            dest = Path(tmp) / "forks" / "cursor-dummy"
            app_dir = dest / "resources" / "app"
            app_dir.mkdir(parents=True)
            (app_dir / "package.json").write_text(
                json.dumps({"name": "Cursor", "desktopName": "cursor.desktop",
                            "version": "1.0.0"}) + "\n",
                encoding="utf-8")
            (app_dir / "product.json").write_text(
                json.dumps({"nameShort": "Cursor",
                            "linuxIconName": "co.anysphere.cursor"}) + "\n",
                encoding="utf-8")
            spec = appfork.Vendor(
                name="cursor", package="cursor", stock_lib=stock,
                binary="cursor", stock_desktop_name="cursor.desktop",
                package_json_rel="resources/app/package.json",
                product_json_rel="resources/app/product.json",
                version_rel=None,
            )
            lines = appfork.patch_identity(spec, dest, "dummy", dry_run=False)
            pkg = json.loads((app_dir / "package.json").read_text())
            product = json.loads((app_dir / "product.json").read_text())
            self.assertEqual(pkg["desktopName"], "Cursor-dummy.desktop")
            self.assertEqual(product["nameShort"], "Cursor-dummy")
            self.assertTrue(any("desktopName=Cursor-dummy.desktop" in line for line in lines))

    def test_refuses_to_rsync_onto_stock(self):
        spec = appfork.VENDORS["claude"]
        with self.assertRaises(RuntimeError) as caught:
            appfork.rsync_stock(spec, spec.stock_lib, dry_run=True)
        self.assertIn("stock", str(caught.exception))

    def _claude_spec(self, stock: Path) -> appfork.Vendor:
        return appfork.Vendor(
            name="claude", package="claude-desktop", stock_lib=stock,
            binary="claude-desktop",
            stock_desktop_name="com.anthropic.Claude.desktop",
            asar_rel="resources/app.asar",
        )

    def test_cheap_gate_skips_when_version_and_desktop_name_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            stock = Path(tmp) / "stock"
            dest = Path(tmp) / "fork"
            for tree in (stock, dest):
                tree.mkdir()
                (tree / "version").write_text("42.0.0\n", encoding="utf-8")
                self._asar(tree / "resources" / "app.asar", "Claude-dummy.desktop", "2.5.0")
            with self.assertRaises(appfork.Skip) as caught:
                appfork.cheap_gates(self._claude_spec(stock), dest, "dummy")
            self.assertIn("already at 2.5.0", str(caught.exception))

    def test_cheap_gate_rebuilds_when_only_the_app_version_moved(self):
        # The `version` file is Electron's and does not change between app
        # releases; a gate on it alone left forks stale across upgrades.
        with tempfile.TemporaryDirectory() as tmp:
            stock = Path(tmp) / "stock"
            dest = Path(tmp) / "fork"
            for tree, app in ((stock, "2.6.0"), (dest, "2.5.0")):
                tree.mkdir()
                (tree / "version").write_text("42.0.0\n", encoding="utf-8")
                self._asar(tree / "resources" / "app.asar", "Claude-dummy.desktop", app)
            appfork.cheap_gates(self._claude_spec(stock), dest, "dummy")

    def test_install_hook_writes_apt_and_dpkg_snippets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = appfork.Env(
                fork_root=root / "forks",
                worker=root / "usr" / "local" / "bin" / "sync-devkit-profile-apps.py",
                apt_conf=root / "etc" / "apt" / "apt.conf.d" / "99-devkit-profile-apps",
                dpkg_conf=root / "etc" / "dpkg" / "dpkg.cfg.d" / "60devkit-profile-apps",
                apparmor_dir=root / "etc" / "apparmor.d",
                home_root=root / "home",
                log_path=root / "var" / "log" / "devkit-profile-apps.log",
            )
            appfork.install_hook(env, dry_run=False)
            apt = env.apt_conf.read_text()
            dpkg = env.dpkg_conf.read_text()
            self.assertIn("DPkg::Post-Invoke", apt)
            self.assertIn("/usr/local/bin/sync-devkit-profile-apps.py", apt)
            self.assertIn("|| true", apt)
            self.assertIn("post-invoke", dpkg)
            self.assertIn("does not run for bare dpkg", dpkg)
            self.assertTrue(env.worker.is_file())
            # apt execs the worker directly; without a shebang sh runs it.
            ran = subprocess.run(
                [str(env.worker), "--help"], capture_output=True, text=True, cwd=root,
                check=False)
            self.assertEqual(ran.returncode, 0, ran.stderr)
            self.assertIn("usage:", ran.stdout)
            self.assertTrue((env.fork_root / appfork.EMBLEM_NAME).is_file())
            self.assertNotIn("99-cursor-recolor", apt)

    def test_desktop_tokens_point_at_the_fork_not_stock(self):
        tokens = instances.render_tokens(
            load_for_create("dummy", "enonic"), "claude", Path("/home/example"))
        self.assertEqual(tokens["PROFILE_GUI_BIN"],
                         "/usr/lib/devkit/claude-dummy/claude-desktop")
        self.assertEqual(tokens["PROFILE_WM_CLASS"], "Claude-dummy")
        rendered = instances.render(
            (REPO / "templates" / "desktop" / "claude.desktop").read_text(), tokens)
        self.assertIn("/usr/lib/devkit/claude-dummy/claude-desktop", rendered)
        self.assertNotIn("/usr/bin/claude-desktop", rendered)
        self.assertIn("SingleMainWindow=true", rendered)
        self.assertIn("Actions=NewChat;NewCode;", rendered)
        self.assertIn("[Desktop Action NewChat]", rendered)
        self.assertIn("[Desktop Action NewCode]", rendered)
        self.assertIn("claude://claude.ai/new", rendered)
        self.assertIn("claude://code/new", rendered)
        self.assertEqual(rendered.count("CLAUDE_CONFIG_DIR=/home/example/.agents-profiles/dummy/claude"), 3)
        self.assertEqual(rendered.count("--user-data-dir=/home/example/.config/Claude-dummy"), 3)


class WirePathTests(unittest.TestCase):
    """'On a box with both .bash_profile and .profile, --wire-path must write to
    .bash_profile.' bootstrap.sh prepends ~/.local/bin to its own PATH so it can
    see what it installs, which made this check read the PATH it had just
    fixed up and skip the report entirely."""

    @unittest.skipUnless(any(shutil.which(m) for m in ("apt-get", "dnf", "pacman")),
                         "no supported package manager to detect")
    def test_wire_path_targets_bash_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            for name in (".bash_profile", ".profile"):
                (home / name).touch()
            # Drop only ~/.local/bin from the real PATH. Hard-coding one keeps
            # bootstrap.sh from finding python3 wherever the image puts it, and
            # it exits before the check under test.
            without_local_bin = ":".join(
                entry for entry in os.environ["PATH"].split(":")
                if entry and not entry.rstrip("/").endswith("/.local/bin"))
            result = subprocess.run(
                ["bash", str(REPO / "bootstrap.sh"), "--wire-path"],
                capture_output=True, text=True, check=False,
                env={"HOME": str(home), "PATH": without_local_bin, "LANG": "C"})
        self.assertIn("is not on your PATH", result.stdout)
        self.assertIn(".bash_profile", result.stdout)
        self.assertNotIn(str(home / ".profile"), result.stdout)


_ROOT_ARTIFACTS = (
    Path("/usr/lib/devkit"),
    Path("/usr/local/bin/sync-devkit-profile-apps.py"),
    Path("/etc/apt/apt.conf.d/99-devkit-profile-apps"),
    Path("/etc/dpkg/dpkg.cfg.d/60devkit-profile-apps"),
    Path("/var/log/devkit-profile-apps.log"),
)


def _host_has_root_artifacts() -> bool:
    if any(path.exists() for path in _ROOT_ARTIFACTS):
        return True
    apparmor = Path("/etc/apparmor.d")
    return apparmor.is_dir() and any(apparmor.glob("devkit-*"))


def _run_uninstall(home: Path, *args: str, script: Path | None = None) -> subprocess.CompletedProcess:
    if "--apply" in args and _host_has_root_artifacts():
        raise unittest.SkipTest("host has root devkit files; --apply would ask sudo")
    if script is None:
        script = home / ".generated-uninstaller.sh"
        write_uninstaller(script)
    env = os.environ.copy()
    env["HOME"] = str(home)
    # git reads --global config from $XDG_CONFIG_HOME too; an inherited one would
    # point the ignore-block strip at the real machine's file.
    env["XDG_CONFIG_HOME"] = str(home / ".config")
    return subprocess.run(
        ["bash", str(script), *args],
        capture_output=True, text=True, check=False, env=env)


class UninstallTests(unittest.TestCase):
    """devkit-uninstall.sh is a detached shell command. The PATH copy deletes itself."""

    def test_failed_root_removal_keeps_the_elevate_status(self):
        self.assertNotIn("if ! elevate", SCRIPT)
        self.assertIn('elevate "${ROOTS[@]}" && rc=0 || rc=$?', SCRIPT)

    def test_script_does_not_call_devkit(self):
        self.assertFalse((REPO / "devkit-uninstall.sh").exists())
        self.assertNotIn("devkit_cli", SCRIPT)
        self.assertNotIn("python3", SCRIPT)

    def test_nothing_installed_exits_0(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = _run_uninstall(Path(tmp))
        self.assertEqual(result.returncode, 0, result.stderr)
        if _host_has_root_artifacts():
            self.assertIn("root  ", result.stdout)
        else:
            self.assertIn("nothing to remove", result.stdout)

    def test_removes_profile_state_and_leaves_the_host_harness(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            profile = home / ".agents-profiles" / "dummy" / "claude"
            profile.mkdir(parents=True)
            (profile / ".devkit-profile.json").write_text("{}\n", encoding="utf-8")
            bindir = home / ".local" / "bin"
            bindir.mkdir(parents=True)
            wrapper = bindir / "claude-dummy"
            wrapper.write_text("# Generated by devkit\n", encoding="utf-8")
            stock = bindir / "claude"
            stock.symlink_to("/usr/bin/true")
            installed = bindir / "devkit-uninstall.sh"
            write_uninstaller(installed)
            harness = home / ".agents" / "skills"
            harness.mkdir(parents=True)
            (harness / "keep.md").write_text("keep\n", encoding="utf-8")
            desktop = home / ".local" / "share" / "applications" / "Claude-dummy.desktop"
            desktop.parent.mkdir(parents=True)
            desktop.write_text(
                "# Generated by devkit\n"
                "Icon=claude-dummy\n"
                "Exec=env --user-data-dir=" + str(home / ".config" / "Claude-dummy") + "\n",
                encoding="utf-8",
            )
            icon = home / ".local" / "share" / "icons" / "hicolor" / "512x512" / "apps" / "claude-dummy.png"
            icon.parent.mkdir(parents=True)
            icon.write_bytes(b"png")
            icon48 = home / ".local" / "share" / "icons" / "hicolor" / "48x48" / "apps" / "claude-dummy.png"
            icon48.parent.mkdir(parents=True)
            icon48.write_bytes(b"png")
            data = home / ".config" / "Claude-dummy"
            data.mkdir(parents=True)
            shell = home / ".bashrc"
            shell.write_text(
                "export KEEP=1\n"
                "\n# Added by devkit bootstrap.sh\n"
                'export PATH="$HOME/.local/bin:$PATH"\n',
                encoding="utf-8",
            )
            dry = _run_uninstall(home, script=installed)
            self.assertEqual(dry.returncode, 0, dry.stderr)
            self.assertTrue(installed.is_file())
            self.assertTrue(profile.is_dir())
            result = _run_uninstall(home, "--apply", script=installed)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(installed.exists())
            self.assertFalse((REPO / "devkit-uninstall.sh").exists())
            self.assertFalse((home / ".agents-profiles").exists())
            self.assertFalse(wrapper.exists())
            self.assertFalse(desktop.exists())
            self.assertFalse(icon.exists())
            self.assertFalse(icon48.exists())
            self.assertFalse(data.exists())
            self.assertTrue(stock.is_symlink())
            self.assertEqual((harness / "keep.md").read_text(encoding="utf-8"), "keep\n")
            self.assertEqual(shell.read_text(encoding="utf-8"), "export KEEP=1\n")

    def test_orphan_desktop_removes_icon_and_user_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            desktop = home / ".local" / "share" / "applications" / "Claude-old.desktop"
            desktop.parent.mkdir(parents=True)
            desktop.write_text(
                "# Generated by devkit\n"
                "Icon=claude-old\n"
                "Exec=env --user-data-dir=" + str(home / ".config" / "Claude-old") + "\n",
                encoding="utf-8",
            )
            icon = home / ".local" / "share" / "icons" / "hicolor" / "512x512" / "apps" / "claude-old.png"
            icon.parent.mkdir(parents=True)
            icon.write_bytes(b"png")
            data = home / ".config" / "Claude-old"
            data.mkdir(parents=True)
            result = _run_uninstall(home, "--apply")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(desktop.exists())
            self.assertFalse(icon.exists())
            self.assertFalse(data.exists())

    def test_copy_outside_local_bin_is_not_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".agents-profiles" / "dummy").mkdir(parents=True)
            result = _run_uninstall(home, "--apply")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((home / ".generated-uninstaller.sh").is_file())
        self.assertFalse((REPO / "devkit-uninstall.sh").exists())

    def test_devkit_has_no_uninstall_command(self):
        result = run("uninstall")
        self.assertEqual(result.returncode, 2)

    def test_root_only_refuses_without_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = _run_uninstall(Path(tmp), "--root-only", "/etc/passwd")
        self.assertEqual(result.returncode, 2)
        self.assertIn("root", result.stderr)


class LauncherIconTests(unittest.TestCase):
    def _launcher(self, badged: bool) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            stock = home / "claude-desktop.png"
            stock.write_bytes(b"png")
            profile = load_for_create("dummy", "enonic")
            layout = instances.paths_for("dummy", "claude", home)
            tokens = instances.render_tokens(profile, "claude", home)
            with mock.patch.object(instances, "first_existing", lambda _c: "/usr/bin/claude"), \
                    mock.patch("devkit_cli.profiles._find_vendor_icon", lambda _v: stock), \
                    mock.patch.object(instances, "install_launcher_icons",
                                      lambda *_a: badged), \
                    redirect_stdout(io.StringIO()):
                profiles._write_desktop(Plan(True), "claude", profile, layout, tokens,
                                        True, REPO)
            return layout["desktop"].read_text()

    def test_launcher_names_the_badged_icon(self):
        self.assertIn("\nIcon=claude-dummy\n", self._launcher(badged=True))

    def test_failed_badge_falls_back_to_the_stock_icon(self):
        """'If Magick or the emblem is missing the launcher falls back to the stock icon.'"""
        self.assertIn("\nIcon=claude-desktop\n", self._launcher(badged=False))

    @unittest.skipUnless(
        instances.imagemagick() and instances.profile_emblem(),
        "needs ImageMagick and the profile emblem",
    )
    def test_install_launcher_icons_writes_matching_pixel_sizes(self):
        binary = instances.imagemagick()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "stock.png"
            subprocess.run(
                [*binary, "-size", "64x64", "xc:#ff0000", str(source)],
                check=True, capture_output=True,
            )
            dest = instances.paths_for("dummy", "claude", Path(tmp))["icon"]
            self.assertTrue(
                instances.install_launcher_icons(source, dest, "#2563EB"))
            root = dest.parent.parent.parent
            for size in instances.ICON_THEME_SIZES:
                path = root / f"{size}x{size}" / "apps" / dest.name
                self.assertTrue(path.is_file(), path)
                probe = subprocess.run(
                    [*binary, str(path), "-format", "%w", "info:"],
                    capture_output=True, text=True, check=True,
                )
                self.assertEqual(probe.stdout.strip(), str(size), path)

    @unittest.skipUnless(
        instances.imagemagick() and instances.profile_emblem(),
        "needs ImageMagick and the profile emblem",
    )
    def test_full_bleed_icon_is_shrunk_before_badging(self):
        binary = instances.imagemagick()
        emblem = instances.profile_emblem()

        def draw(path, shape):
            subprocess.run(
                [*binary, "-size", "100x100", "xc:none", "-fill", "#ff0000",
                 "-draw", shape, str(path)],
                check=True, capture_output=True,
            )

        def alpha(path, x, y):
            out = subprocess.run(
                [*binary, str(path), "-format", f"%[fx:p{{{x},{y}}}.a]", "info:"],
                capture_output=True, text=True, check=True,
            )
            return float(out.stdout)

        # Full-bleed art shrunk to 84% leaves (95, 95) transparent; art that
        # already has a margin reaches (90, 90) unless it is shrunk too.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            full, margin, out = tmp / "full.png", tmp / "margin.png", tmp / "out.png"
            draw(full, "roundrectangle 0,0 99,99 12,12")
            draw(margin, "rectangle 8,8 91,91")
            badge_with = {
                "recolor_icon": lambda src: instances.recolor_icon(
                    src, out, "#2563EB"),
                "_badge_icon": lambda src: appfork._badge_icon(
                    binary, src, out, "#2563EB", emblem) is None,
            }
            for name, badge in badge_with.items():
                self.assertTrue(badge(full), name)
                self.assertEqual(alpha(out, 95, 95), 0.0, f"{name} full")
                self.assertTrue(badge(margin), name)
                self.assertEqual(alpha(out, 90, 90), 1.0, f"{name} margin")

            stock = tmp / "stock"
            (stock / "resources").mkdir(parents=True)
            for name in ("icon.png", "TrayIcon.png"):
                shutil.copy(full, stock / "resources" / name)
            spec = appfork.Vendor(
                name="claude", package="claude-desktop", stock_lib=stock,
                binary="claude-desktop",
                stock_desktop_name="com.anthropic.Claude.desktop",
                icon_globs=("resources/icon.png", "resources/TrayIcon*.png"),
            )
            fork_root = tmp / "root"
            fork_root.mkdir()
            shutil.copy(emblem, fork_root / appfork.EMBLEM_NAME)
            dest = tmp / "fork"
            appfork.recolor_tree_icons(
                spec, dest, "#2563EB", dry_run=False, fork_root=fork_root)
            self.assertEqual(alpha(dest / "resources" / "icon.png", 95, 95), 0.0)
            self.assertEqual(alpha(dest / "resources" / "TrayIcon.png", 95, 95), 1.0)

    @unittest.skipUnless(
        shutil.which("gtk-update-icon-cache")
        or shutil.which("gtk4-update-icon-cache"),
        "gtk-update-icon-cache not on PATH",
    )
    def test_refresh_hicolor_cache_indexes_new_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            icon = (home / ".local" / "share" / "icons" / "hicolor"
                    / "48x48" / "apps" / "codex-dummy.png")
            icon.parent.mkdir(parents=True)
            icon.write_bytes(b"\x89PNG\r\n\x1a\n")
            self.assertTrue(instances.refresh_hicolor_cache(home))
            cache = home / ".local" / "share" / "icons" / "hicolor" / "icon-theme.cache"
            self.assertTrue(cache.is_file())
            self.assertIn(b"codex-dummy", cache.read_bytes())


class UninstallerIsAlwaysWrittenTests(unittest.TestCase):
    """'Every command that creates a profile leaves a way to undo it.'"""

    def test_ensure_records_then_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            dry = Plan(False)
            ensure(home, dry)
            self.assertEqual(len(dry.actions), 1)
            self.assertFalse((home / ".local" / "bin" / DEST_NAME).exists())

            wet = Plan(True)
            ensure(home, wet)
            dest = home / ".local" / "bin" / DEST_NAME
            self.assertTrue(dest.is_file())
            self.assertTrue(os.access(dest, os.X_OK))

    def test_ensure_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            ensure(home, Plan(True))
            again = Plan(True)
            ensure(home, again)
            self.assertEqual(again.actions, [])

    def test_ensure_rewrites_a_stale_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            dest = home / ".local" / "bin" / DEST_NAME
            dest.parent.mkdir(parents=True)
            dest.write_text("# an older devkit wrote this\n", encoding="utf-8")
            plan = Plan(True)
            ensure(home, plan)
            self.assertEqual(len(plan.actions), 1)
            self.assertIn("FORK_ROOT", dest.read_text(encoding="utf-8"))

    def test_every_profile_writing_command_calls_ensure(self):
        """A create or sync path that forgets this leaves nothing to undo it."""
        body = (REPO / "devkit_cli" / "profiles.py").read_text(encoding="utf-8")
        self.assertIn("uninstaller.ensure(home, plan)",
                      (REPO / "install.py").read_text(encoding="utf-8"))
        self.assertEqual(body.count("uninstaller.ensure(home, plan)"), 2,
                         "cmd_create and cmd_sync must both call ensure")

    def _doctor(self, home: Path) -> str:
        saved = os.environ.get("HOME")
        os.environ["HOME"] = str(home)
        try:
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                profiles.cmd_doctor(argparse.Namespace(profile=None))
            return buffer.getvalue()
        finally:
            if saved is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = saved

    def test_doctor_reports_an_installed_machine_with_no_uninstaller(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            materialize(load_for_create("dummy", "core"), ["claude"], home,
                        Plan(apply=True), force=True)
            self.assertIn(f"{DEST_NAME}: missing", self._doctor(home))
            ensure(home, Plan(True))
            self.assertNotIn(f"{DEST_NAME}: missing", self._doctor(home))

    def test_doctor_is_quiet_when_nothing_is_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertNotIn(DEST_NAME, self._doctor(Path(tmp)))


@unittest.skipUnless(shutil.which("git"), "reads core.excludesFile through git")
class GlobalIgnoreTests(unittest.TestCase):
    """The kit's ignore patterns live in the global git ignore, not in each repo."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        self._saved = {key: os.environ.get(key) for key in ("HOME", "XDG_CONFIG_HOME")}
        os.environ["HOME"] = str(self.home)
        os.environ["XDG_CONFIG_HOME"] = str(self.home / ".config")

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._tmp.cleanup()

    def _set_excludes(self, value: str) -> None:
        (self.home / ".gitconfig").write_text(
            f"[core]\n\texcludesFile = {value}\n", encoding="utf-8")

    def test_default_file_gets_the_block_once(self):
        dry = Plan(False)
        globalignore.ensure(self.home, dry)
        default = self.home / ".config" / "git" / "ignore"
        self.assertEqual(len(dry.actions), 1)
        self.assertFalse(default.exists())
        globalignore.ensure(self.home, Plan(True))
        text = default.read_text(encoding="utf-8")
        self.assertIn(globalignore.BEGIN, text)
        self.assertLess(text.index("\ngraft\n"), text.index("!**/skills/graft\n"))
        again = Plan(True)
        globalignore.ensure(self.home, again)
        self.assertEqual(again.actions, [])

    def test_configured_excludes_file_is_used_and_kept(self):
        self._set_excludes("~/.gitignore_global")
        target = self.home / ".gitignore_global"
        target.write_text("*.log", encoding="utf-8")
        globalignore.ensure(self.home, Plan(True))
        text = target.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("*.log\n\n" + globalignore.BEGIN))
        self.assertFalse((self.home / ".config" / "git" / "ignore").exists())

    def test_patterns_already_present_write_nothing(self):
        self._set_excludes("~/.gitignore_global")
        target = self.home / ".gitignore_global"
        target.write_text("\n".join(globalignore.PATTERNS) + "\n", encoding="utf-8")
        plan = Plan(True)
        globalignore.ensure(self.home, plan)
        self.assertEqual(plan.actions, [])
        self.assertNotIn(globalignore.BEGIN, target.read_text(encoding="utf-8"))

    def test_uninstall_strips_only_the_block(self):
        self._set_excludes("~/.gitignore_global")
        target = self.home / ".gitignore_global"
        target.write_text("*.log\n", encoding="utf-8")
        globalignore.ensure(self.home, Plan(True))
        result = _run_uninstall(self.home, "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(target.read_text(encoding="utf-8"), "*.log\n")

    def test_uninstall_keeps_a_block_without_its_end_line(self):
        self._set_excludes("~/.gitignore_global")
        target = self.home / ".gitignore_global"
        text = f"{globalignore.BEGIN}\ngraft\n*.log\n"
        target.write_text(text, encoding="utf-8")
        result = _run_uninstall(self.home, "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(target.read_text(encoding="utf-8"), text)

    def test_uninstaller_markers_match(self):
        self.assertIn(f"IGNORE_BEGIN='{globalignore.BEGIN}'", SCRIPT)
        self.assertIn(f"IGNORE_END='{globalignore.END}'", SCRIPT)

    def test_every_profile_writing_command_calls_ensure(self):
        body = (REPO / "devkit_cli" / "profiles.py").read_text(encoding="utf-8")
        self.assertIn("globalignore.ensure(home, plan)",
                      (REPO / "install.py").read_text(encoding="utf-8"))
        self.assertEqual(body.count("globalignore.ensure(home, plan)"), 2)


class CliLinkTests(unittest.TestCase):
    def test_links_devkit_onto_path_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            dry = Plan(False)
            cli_link.ensure(home, dry)
            self.assertEqual(len(dry.actions), 1)
            self.assertFalse((home / ".local" / "bin" / "devkit").exists())
            cli_link.ensure(home, Plan(True))
            link = home / ".local" / "bin" / "devkit"
            self.assertEqual(os.readlink(link),
                             str(kithome.current_link(home) / "devkit.py"))
            again = Plan(True)
            cli_link.ensure(home, again)
            self.assertEqual(again.actions, [])

    def test_foreign_file_is_left_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            link = home / ".local" / "bin" / "devkit"
            link.parent.mkdir(parents=True)
            link.write_text("mine", encoding="utf-8")
            plan = Plan(True)
            cli_link.ensure(home, plan)
            self.assertEqual(plan.actions, [])
            self.assertEqual(link.read_text(encoding="utf-8"), "mine")

    def test_every_profile_writing_command_calls_ensure(self):
        body = (REPO / "devkit_cli" / "profiles.py").read_text(encoding="utf-8")
        self.assertIn("cli_link.ensure(home, plan)",
                      (REPO / "install.py").read_text(encoding="utf-8"))
        self.assertEqual(body.count("cli_link.ensure(home, plan)"), 2)

    def test_a_link_into_a_checkout_is_relinked(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            link = home / ".local" / "bin" / "devkit"
            link.parent.mkdir(parents=True)
            link.symlink_to(Path(tmp) / "old-checkout" / "devkit.py")
            plan = Plan(True)
            cli_link.ensure(home, plan)
            self.assertEqual(len(plan.actions), 1)
            self.assertEqual(os.readlink(link),
                             str(kithome.current_link(home) / "devkit.py"))

    def test_uninstaller_removes_the_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cli_link.ensure(home, Plan(True))
            result = _run_uninstall(home, "--apply")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((home / ".local" / "bin" / "devkit").is_symlink())


class SessionSyncTests(unittest.TestCase):
    ORG = ("acct", "org")
    quiet = staticmethod(lambda *args, **kwargs: [])

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)
        for name in ("one", "two"):
            config = self.home / ".agents-profiles" / name / "claude"
            config.mkdir(parents=True)
            (config / ".devkit-profile.json").write_text(
                json.dumps({"profile": name, "vendor": "claude"}), encoding="utf-8")

    def _desktop(self, name, org=ORG):
        base = self.home / ".config" / ("Claude" if name == "stock" else f"Claude-{name}")
        folder = base / "claude-code-sessions" / org[0] / org[1]
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def _code(self, name):
        return self.home / (".claude" if name == "stock"
                            else f".agents-profiles/{name}/claude") / "projects"

    def _write(self, path, text, mtime):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        os.utime(path, (mtime, mtime))

    def _sync(self, source, target, apply=True, **kwargs):
        plan = Plan(apply)
        session_sync.sync_sessions(self.home, source, target, plan,
                                   find_running=self.quiet, find_holders=self.quiet, **kwargs)
        return plan

    def test_code_copies_new_and_newer_and_never_deletes_or_downgrades(self):
        self._write(self._code("one") / "p" / "a.jsonl", "one-a", 200)
        self._write(self._code("one") / "p" / "b.jsonl", "one-b-old", 100)
        self._write(self._code("one") / "p" / "c.jsonl", "one-c", 300)
        self._write(self._code("two") / "p" / "b.jsonl", "two-b-new", 150)
        self._write(self._code("two") / "p" / "c.jsonl", "two-c-old", 50)
        self._write(self._code("two") / "p" / "only.jsonl", "two-only", 10)
        plan = self._sync("one", "two")
        target = self._code("two") / "p"
        self.assertEqual((target / "a.jsonl").read_text(), "one-a")
        self.assertEqual((target / "b.jsonl").read_text(), "two-b-new")
        self.assertEqual((target / "c.jsonl").read_text(), "one-c")
        self.assertEqual((target / "only.jsonl").read_text(), "two-only")
        self.assertEqual(len(plan.actions), 1)
        self.assertIn("1 new, 1 newer, 1 unchanged", plan.actions[0])
        again = self._sync("one", "two")
        self.assertEqual(again.actions, [])
        self.assertEqual(list(target.glob("*.devkit-partial")), [])

    def test_dry_run_writes_nothing(self):
        self._write(self._code("one") / "p" / "a.jsonl", "x", 200)
        plan = self._sync("one", "two", apply=False)
        self.assertEqual(len(plan.actions), 1)
        self.assertFalse(self._code("two").exists())

    def test_desktop_chats_flatten_into_the_targets_org_only(self):
        self._write(self._desktop("stock", ("accA", "org1")) / "local_1.json", "s1", 100)
        self._write(self._desktop("stock", ("accA", "org2")) / "local_2.json", "s2", 100)
        self._write(self._desktop("stock", ("accA", "org2")) / "local_1.json", "s1-newer", 200)
        self._write(self._desktop("stock", ("accA", "org2")) / "scheduled-tasks.json", "t", 100)
        mine = self._desktop("one", ("accB", "orgB"))
        self._write(mine / "local_9.json", "mine", 100)
        self._sync("stock", "one")
        self.assertEqual(sorted(p.name for p in mine.glob("*.json")),
                         ["local_1.json", "local_2.json", "local_9.json"])
        self.assertEqual((mine / "local_1.json").read_text(), "s1-newer")
        sessions = mine.parent.parent
        self.assertEqual([p.name for p in sessions.iterdir()], ["accB"])
        self.assertEqual([p.name for p in sessions.glob("*/*")], ["orgB"])

    def test_desktop_target_without_an_org_folder_is_refused(self):
        self._write(self._desktop("one") / "local_1.json", "x", 100)
        (self.home / ".config" / "Claude-two").mkdir(parents=True)
        with self.assertRaises(DevkitError) as raised:
            self._sync("one", "two")
        self.assertIn("signed-in organization", str(raised.exception))

    def test_only_limits_the_trees(self):
        self._write(self._code("one") / "p" / "a.jsonl", "x", 100)
        self._write(self._desktop("one") / "local_1.json", "y", 100)
        self._desktop("two")
        self._sync("one", "two", only="code")
        self.assertTrue((self._code("two") / "p" / "a.jsonl").is_file())
        self.assertFalse((self._desktop("two") / "local_1.json").exists())

    def test_running_target_blocks_apply_but_not_a_dry_run(self):
        self._write(self._code("one") / "p" / "a.jsonl", "x", 100)
        busy = lambda *args, **kwargs: [("Desktop", "4242")]
        with self.assertRaises(DevkitError) as raised:
            session_sync.sync_sessions(self.home, "one", "two", Plan(True), find_running=busy)
        self.assertIn("4242", str(raised.exception))
        self.assertFalse(self._code("two").exists())
        session_sync.sync_sessions(self.home, "one", "two", Plan(False), find_running=busy)

    def test_indexeddb_is_replaced_and_the_old_one_kept_only_when_asked(self):
        for name, text in (("one", "from-one"), ("two", "from-two")):
            db = self._desktop(name).parents[2] / "IndexedDB"
            db.mkdir()
            (db / "CURRENT").write_text(text, encoding="utf-8")
        self._write(self._code("one") / "p" / "a.jsonl", "x", 100)
        two_db = self._desktop("two").parents[2] / "IndexedDB"
        self._sync("one", "two")
        self.assertEqual((two_db / "CURRENT").read_text(), "from-two")
        self._sync("one", "two", indexeddb=True)
        self.assertEqual((two_db / "CURRENT").read_text(), "from-one")
        backups = list(two_db.parent.glob("IndexedDB.devkit-backup-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / "CURRENT").read_text(), "from-two")

    def test_refuses_same_unknown_and_empty(self):
        with self.assertRaises(DevkitError):
            self._sync("one", "one")
        with self.assertRaises(DevkitError) as raised:
            self._sync("nope", "one")
        self.assertIn("stock", raised.exception.fix)
        with self.assertRaises(DevkitError):
            self._sync("one", "two")

    def test_stock_names_the_unprefixed_install(self):
        self._write(self._code("stock") / "p" / "a.jsonl", "x", 100)
        self._sync("stock", "one")
        self.assertTrue((self._code("one") / "p" / "a.jsonl").is_file())

    def _fake_proc(self, procs):
        root = self.home / "proc"
        for pid, comm, args, env in procs:
            entry = root / str(pid)
            entry.mkdir(parents=True)
            (entry / "comm").write_text(comm + "\n")
            (entry / "cmdline").write_bytes(args.encode())
            (entry / "environ").write_bytes(env.encode())
        return root

    def test_running_matches_the_right_instance_only(self):
        one = session_sync.resolve_side("one", self.home)
        two = session_sync.resolve_side("two", self.home)
        stock = session_sync.resolve_side("stock", self.home)
        root = self._fake_proc([
            (11, "claude-desktop", f"/x/claude-desktop\0--user-data-dir={one.desktop}\0", ""),
            (12, "claude-desktop", "/x/claude-desktop --type=zygote --no-zygote-sandbox", ""),
            (13, "claude", "claude", f"A=b\0CLAUDE_CONFIG_DIR={two.code}\0"),
            (14, "bash", "bash", f"CLAUDE_CONFIG_DIR={one.code}\0"),
            (15, "claude-desktop", "/opt/Claude/claude-desktop", ""),
            (16, "claude", "claude", "A=b\0"),
        ])
        self.assertEqual(session_sync.running(one, True, True, root), [("Desktop", "11")])
        self.assertEqual(session_sync.running(two, True, True, root), [("Code", "13")])
        self.assertCountEqual(session_sync.running(stock, True, True, root),
                              [("Desktop", "15"), ("Code", "16")])
        self.assertEqual(session_sync.running(stock, False, False, root), [])

    def _agent_dir(self, name, vendor):
        if name == "stock":
            return self.home / {"codex": ".codex", "cursor": ".config/Cursor"}[vendor]
        config = self.home / ".agents-profiles" / name / vendor
        config.mkdir(parents=True, exist_ok=True)
        (config / ".devkit-profile.json").write_text(
            json.dumps({"profile": name, "vendor": vendor}), encoding="utf-8")
        return config

    def _codex(self, name, threads, db=True):
        home = self._agent_dir(name, "codex")
        home.mkdir(parents=True, exist_ok=True)
        if db:
            con = sqlite3.connect(home / "state_5.sqlite")
            con.execute("create table threads (id text primary key, rollout_path text not null,"
                        " cwd text not null, title text not null, updated_at integer not null,"
                        " updated_at_ms integer, project_id text)")
            for thread_id, updated, mtime in threads:
                rollout = home / "sessions" / "2026" / f"rollout-{thread_id}.jsonl"
                self._write(rollout, f"body-{name}-{thread_id}", mtime)
                con.execute("insert into threads values (?,?,?,?,?,?,?)",
                            (thread_id, str(rollout), "/w", f"t-{thread_id}", updated,
                             updated * 1000, "proj-" + name))
            con.commit()
            con.close()
        for thread_id, _u, _m in threads:
            with (home / "session_index.jsonl").open("a", encoding="utf-8") as index:
                index.write(json.dumps({"id": thread_id, "thread_name": f"t-{thread_id}"}) + "\n")
        return home

    def _threads(self, home):
        con = sqlite3.connect(home / "state_5.sqlite")
        try:
            return {r[0]: r[1:] for r in con.execute(
                "select id, rollout_path, updated_at, project_id from threads")}
        finally:
            con.close()

    def test_codex_copies_rollouts_adds_threads_and_bumps_newer(self):
        src = self._codex("one", [("a", 100, 100), ("b", 300, 300), ("c", 50, 50)])
        dst = self._codex("two", [("b", 200, 200), ("c", 50, 50)])
        plan = self._sync("one", "two", agents="codex")
        self.assertEqual(len(plan.actions), 3)
        rows = self._threads(dst)
        self.assertEqual(sorted(rows), ["a", "b", "c"])
        self.assertEqual(rows["a"][0], str(dst / "sessions" / "2026" / "rollout-a.jsonl"))
        self.assertIsNone(rows["a"][2])
        self.assertEqual(rows["b"][1], 300)
        self.assertEqual((dst / "sessions" / "2026" / "rollout-a.jsonl").read_text(), "body-one-a")
        self.assertEqual((dst / "sessions" / "2026" / "rollout-b.jsonl").read_text(), "body-one-b")
        ids = [json.loads(line)["id"] for line in (dst / "session_index.jsonl").read_text().splitlines()]
        self.assertEqual(sorted(ids), ["a", "b", "c"])
        self.assertEqual(len(list(dst.glob("state_5.sqlite.devkit-backup-*"))), 1)
        self.assertEqual(self._sync("one", "two", agents="codex").actions, [])
        self.assertEqual(len(self._threads(src)), 3)

    def test_codex_without_a_target_database_copies_files_only(self):
        self._codex("one", [("a", 100, 100)])
        dst = self._codex("two", [], db=False)
        self._sync("one", "two", agents="codex")
        self.assertTrue((dst / "sessions" / "2026" / "rollout-a.jsonl").is_file())
        self.assertFalse((dst / "state_5.sqlite").exists())

    def test_codex_refuses_a_target_schema_it_cannot_fill(self):
        self._codex("one", [("a", 100, 100)])
        dst = self._codex("two", [])
        con = sqlite3.connect(dst / "state_5.sqlite")
        con.execute("alter table threads add column cli_version text not null default ''")
        con.execute("create table other (x integer not null)")
        con.execute("drop table threads")
        con.execute("create table threads (id text primary key, rollout_path text not null,"
                    " updated_at integer not null, brand_new text not null)")
        con.commit()
        con.close()
        with self.assertRaises(DevkitError) as raised:
            self._sync("one", "two", agents="codex")
        self.assertIn("brand_new", str(raised.exception))
        self.assertFalse((dst / "sessions").exists())

    def _cursor(self, name, chats, extra=()):
        db = self._agent_dir(name, "cursor") / "User" / "globalStorage" / "state.vscdb"
        db.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(db)
        con.execute("create table cursorDiskKV (key text unique on conflict replace, value blob)")
        con.execute("create table composerHeaders (composerId text primary key, workspaceId text,"
                    " lastUpdatedAt integer, value text)")
        for composer_id, updated in chats:
            con.execute("insert into composerHeaders values (?,?,?,?)",
                        (composer_id, "ws", updated, f"{name}-head-{composer_id}"))
            for key in (f"composerData:{composer_id}", f"bubbleId:{composer_id}:b1",
                        f"bubbleId:{composer_id}:b2", f"checkpointId:{composer_id}:c1"):
                con.execute("insert into cursorDiskKV values (?,?)", (key, f"{name}-{key}"))
        for key in extra:
            con.execute("insert into cursorDiskKV values (?,?)", (key, f"{name}-{key}"))
        con.commit()
        con.close()
        return db

    def _kv(self, db):
        con = sqlite3.connect(db)
        try:
            return dict(con.execute("select key, value from cursorDiskKV"))
        finally:
            con.close()

    def test_cursor_copies_new_and_newer_chats_family_by_family(self):
        self._cursor("one", [("aaa", 100), ("aaab", 100), ("old", 10), ("up", 300)],
                     extra=["agentKv:blob:xyz", "composerData:aaaZ"])
        dst = self._cursor("two", [("old", 20), ("up", 200)], extra=["composerData:mine"])
        plan = self._sync("one", "two", agents="cursor")
        self.assertEqual(len(plan.actions), 1)
        self.assertIn("2 new, 1 newer, 1 unchanged", plan.actions[0])
        kv = self._kv(dst)
        self.assertEqual(kv["bubbleId:aaa:b2"], "one-bubbleId:aaa:b2")
        self.assertEqual(kv["composerData:aaab"], "one-composerData:aaab")
        self.assertEqual(kv["checkpointId:up:c1"], "one-checkpointId:up:c1")
        self.assertEqual(kv["composerData:mine"], "two-composerData:mine")
        self.assertEqual(kv["composerData:old"], "two-composerData:old")
        self.assertNotIn("agentKv:blob:xyz", kv)
        self.assertNotIn("composerData:aaaZ", kv)
        con = sqlite3.connect(dst)
        heads = dict(con.execute("select composerId, value from composerHeaders"))
        con.close()
        self.assertEqual(heads["up"], "one-head-up")
        self.assertEqual(heads["old"], "two-head-old")
        self.assertEqual(len(list(dst.parent.glob("state.vscdb.devkit-backup-*"))), 1)
        self.assertEqual(self._sync("one", "two", agents="cursor").actions, [])

    def test_cursor_refuses_a_target_that_never_started(self):
        self._cursor("one", [("aaa", 100)])
        self._agent_dir("two", "cursor")
        with self.assertRaises(DevkitError) as raised:
            self._sync("one", "two", agents="cursor")
        self.assertIn("launch the target Cursor", raised.exception.fix)

    def test_an_unusable_database_is_reported_not_a_traceback(self):
        self._cursor("one", [("aaa", 100)])
        db = self._cursor("two", [])
        con = sqlite3.connect(db)
        con.execute("drop table composerHeaders")
        con.commit()
        con.close()
        with self.assertRaises(DevkitError) as raised:
            self._sync("one", "two", agents="cursor")
        self.assertIn("session database", str(raised.exception))

    def test_agents_are_chosen_by_name_and_all_means_what_both_sides_have(self):
        self._write(self._code("one") / "p" / "a.jsonl", "x", 100)
        self._codex("one", [("a", 100, 100)])
        self._codex("two", [])
        plan = self._sync("one", "two", agents="claude,codex")
        self.assertEqual(len(plan.actions), 4)
        again = self._sync("one", "two", agents="all")
        self.assertEqual(again.actions, [])
        for bad, text in (("nope", "unknown agent"), ("cursor", "no cursor instance")):
            with self.assertRaises(DevkitError) as raised:
                self._sync("one", "two", agents=bad)
            self.assertIn(text, str(raised.exception))
        with self.assertRaises(DevkitError):
            self._sync("one", "two", agents="codex", only="code")

    def test_holders_finds_a_process_with_a_file_open_under_a_root(self):
        from devkit_cli.sessions import common
        root = self.home / "fakeproc"
        for pid, link in ((21, f"{self.home}/data/state.db"), (22, f"{self.home}/data-other/x"),
                          (23, "/etc/passwd")):
            fds = root / str(pid) / "fd"
            fds.mkdir(parents=True)
            (fds / "3").symlink_to(link)
            (root / str(pid) / "comm").write_text("app\n")
        found = common.holders("Cursor", [self.home / "data"], root)
        self.assertEqual(found, [("Cursor", "21")])

    def test_cli_help_exits_zero(self):
        result = run("profile", "session-sync", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--source", result.stdout)


class GlobalIgnoreWithoutGitTests(unittest.TestCase):
    def test_no_git_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            saved = os.environ.get("PATH")
            os.environ["PATH"] = str(home)
            try:
                plan = Plan(True)
                globalignore.ensure(home, plan)
            finally:
                os.environ["PATH"] = saved or ""
            self.assertEqual(plan.actions, [])
            self.assertFalse((home / ".config").exists())


class UninstallDocTests(unittest.TestCase):
    """'docs/install.md lists what devkit-uninstall.sh actually removes.'

    The uninstall list is prose, so nothing else catches a path added to the
    script and never documented.
    """

    DOC = REPO / "docs" / "install.md"

    def _uninstall_section(self) -> str:
        text = self.DOC.read_text(encoding="utf-8")
        start = text.index("## Uninstalling")
        end = text.find("\n## ", start + 1)
        return text[start:] if end == -1 else text[start:end]

    def test_every_root_owned_target_is_documented(self):
        section = self._uninstall_section()
        for name in ("FORK_ROOT", "WORKER", "APT_CONF", "DPKG_CONF", "LOG_PATH",
                     "APPARMOR_DIR"):
            declared = re.search(rf"^{name}=(\S+)$", SCRIPT, re.MULTILINE)
            with self.subTest(constant=name):
                self.assertIsNotNone(declared, f"{name} is no longer declared")
                self.assertIn(declared.group(1), section,
                              f"{name} is removed but not documented")

    def test_the_kit_home_is_documented(self):
        self.assertIn(".local/share/devkit", self._uninstall_section())
        self.assertIn("releases/*/.devkit-install.json", SCRIPT)

    def test_every_literal_home_target_is_documented(self):
        section = self._uninstall_section()
        literals = set(re.findall(r'remove_(?:file|dir) "\$HOME/([^"$]+)"', SCRIPT))
        self.assertTrue(literals, "the script stopped naming home paths literally")
        for rel in sorted(literals):
            with self.subTest(path=rel):
                self.assertIn(rel, section,
                              f"$HOME/{rel} is removed but not documented")


# ---------------------------------------------------------------- standalone

LINEAGE = "a" * 40
GIT_ENV = {"GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                            text=True, check=True, env={**os.environ, **GIT_ENV})
    return result.stdout.strip()


def _put(root: Path, rel: str, text: str = "x\n", mode: int = 0o644) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(mode)
    return path


def _mini_kit(root: Path, lineage: str = LINEAGE, skill: str = "one\n") -> Path:
    """A tiny tree with the payload shape, plus files the payload must skip."""
    for rel, mode in (("devkit.py", 0o755), ("devkit", 0o755),
                      ("devkit_cli/__init__.py", 0o644), ("core/bin/agentctl.py", 0o755),
                      ("templates/a.txt", 0o644), ("profiles/core.json", 0o644),
                      ("export-allowlist.json", 0o644), ("path-contract.json", 0o644)):
        _put(root, rel, "#!/usr/bin/env python3\n" if mode == 0o755 else "{}\n", mode)
    _put(root, "core/skills/s/SKILL.md", skill)
    _put(root, "devkit.yaml", f"lineage_id: {lineage}\nfork_id: t\nupstream: null\n")
    (root / "core/bin/agentctl").symlink_to("agentctl.py")
    for noise in ("docs/a.md", "tests/t.py", "scripts/s.sh", "bootstrap.sh", "install.py",
                  "graft/INDEX.md", ".gitleaks.toml", "devkit_cli/__pycache__/x.pyc",
                  ".git/HEAD"):
        _put(root, noise)
    return root


def _git_kit(root: Path) -> str:
    """A git checkout of the mini kit whose devkit.yaml names its root commit."""
    _mini_kit(root, lineage="pending")
    _put(root, ".gitignore", "core/ignored.txt\n__pycache__/\n")
    shutil.rmtree(root / ".git")
    for rel in ("docs", "tests", "scripts", "graft", "bootstrap.sh", "install.py",
                ".gitleaks.toml"):
        target = root / rel
        shutil.rmtree(target) if target.is_dir() else target.unlink()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "root")
    lineage = _git(root, "rev-parse", "HEAD")
    _put(root, "devkit.yaml", f"lineage_id: {lineage}\nfork_id: t\nupstream: null\n")
    _git(root, "commit", "-q", "-am", "record lineage")
    return lineage


class KitHomeTests(unittest.TestCase):
    """'The installed kit is a copy: immutable releases and a current link.'"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.kit = _mini_kit(self.tmp / "kit")
        pinned = mock.patch.dict(os.environ, {"XDG_DATA_HOME": str(self.tmp / "elsewhere")})
        pinned.start()
        self.addCleanup(pinned.stop)

    def _install(self, src: Path | None = None) -> Plan:
        plan = Plan(True)
        kithome.ensure_installed(src or self.kit, self.home, plan)
        return plan

    def _releases(self) -> list[str]:
        return sorted(p.name for p in kithome.releases_dir(self.home).iterdir())

    def test_payload_excludes_what_a_release_does_not_need(self):
        files = kithome.payload_files(self.kit)
        for skipped in ("docs", "tests", "scripts", "graft", "bootstrap.sh", "install.py",
                        ".gitleaks.toml", "__pycache__", ".git"):
            with self.subTest(skipped=skipped):
                self.assertFalse([f for f in files if skipped in f.split("/")
                                  or f.startswith(skipped)], files)
        self.assertIn("core/skills/s/SKILL.md", files)
        self.assertIn("core/bin/agentctl", files)

    def test_release_keeps_exec_bits_and_relative_symlinks(self):
        self._install()
        release = kithome.current_release(self.home)
        self.assertTrue(os.access(release / "devkit.py", os.X_OK))
        self.assertFalse(os.access(release / "templates" / "a.txt", os.X_OK))
        link = release / "core" / "bin" / "agentctl"
        self.assertTrue(link.is_symlink())
        self.assertEqual(os.readlink(link), "agentctl.py")
        self.assertTrue(link.exists())
        stamp = kithome.read_stamp(release)
        self.assertEqual(stamp["release_id"], release.name)
        self.assertEqual(stamp["payload_digest"][:12], release.name)
        self.assertEqual(stamp["lineage_id"], LINEAGE)
        self.assertFalse((release / "docs").exists())

    def test_an_absolute_or_escaping_symlink_is_refused(self):
        for target in (str(self.tmp / "outside"), "../../../outside", "../../docs/a.md"):
            with self.subTest(target=target):
                kit = _mini_kit(self.tmp / f"kit-{abs(hash(target))}")
                (kit / "core/bin/bad").symlink_to(target)
                with self.assertRaises(DevkitError):
                    self._install(kit)
        self.assertFalse(kithome.releases_dir(self.home).exists()
                         and any(kithome.releases_dir(self.home).iterdir()))

    def test_digest_is_stable_and_the_same_payload_installs_once(self):
        files = kithome.payload_files(self.kit)
        self.assertEqual(kithome.payload_digest(self.kit, files),
                         kithome.payload_digest(self.kit, files))
        first = self._install()
        again = self._install()
        self.assertTrue(first.actions)
        self.assertEqual(again.actions, [])
        self.assertEqual(len(self._releases()), 1)

    def test_digest_ignores_umask_but_not_content_or_exec_bit(self):
        files = kithome.payload_files(self.kit)
        base = kithome.payload_digest(self.kit, files)
        (self.kit / "templates/a.txt").chmod(0o600)
        self.assertEqual(kithome.payload_digest(self.kit, files), base)
        (self.kit / "templates/a.txt").chmod(0o755)
        self.assertNotEqual(kithome.payload_digest(self.kit, files), base)

    def test_flip_current_never_exposes_a_missing_link(self):
        import threading
        self._install()
        first = kithome.current_release(self.home)
        _put(self.kit, "core/skills/s/SKILL.md", "two\n")
        self._install()
        second = kithome.current_release(self.home)
        self.assertNotEqual(first, second)
        stop, bad = threading.Event(), []

        def flipper():
            while not stop.is_set():
                for release in (first, second):
                    kithome.flip_current(self.home, release)

        thread = threading.Thread(target=flipper)
        thread.start()
        try:
            link = kithome.current_link(self.home)
            for _ in range(3000):
                try:
                    if not (os.readlink(link) and (link / "devkit.py").exists()):
                        bad.append("dangling")
                except OSError as exc:
                    bad.append(str(exc))
        finally:
            stop.set()
            thread.join()
        self.assertEqual(bad, [])

    def test_prune_keeps_current_and_the_previous_release(self):
        for text in ("one\n", "two\n", "three\n", "four\n"):
            _put(self.kit, "core/skills/s/SKILL.md", text)
            self._install()
            self.assertLessEqual(len(self._releases()), 2)
        current = kithome.current_release(self.home)
        self.assertEqual(len(self._releases()), 2)
        self.assertEqual(kithome.previous_release(self.home).name != current.name, True)
        self.assertIn("three", (kithome.previous_release(self.home)
                                / "core/skills/s/SKILL.md").read_text())

    def test_running_from_current_copies_nothing(self):
        self._install()
        plan = Plan(True)
        root = kithome.ensure_installed(kithome.current_release(self.home), self.home, plan)
        self.assertEqual(plan.actions, [])
        self.assertEqual(root, kithome.current_link(self.home))

    def test_dry_run_installs_nothing_and_reads_the_source(self):
        plan = Plan(False)
        root = kithome.ensure_installed(self.kit, self.home, plan)
        self.assertEqual(root, self.kit)
        self.assertTrue(plan.actions)
        self.assertFalse(kithome.kit_home(self.home).exists())

    def test_xdg_data_home_counts_only_under_the_home(self):
        with mock.patch.dict(os.environ, {"XDG_DATA_HOME": str(self.home / "data")}):
            self.assertEqual(kithome.kit_home(self.home), self.home / "data" / "devkit")
        with mock.patch.dict(os.environ, {"XDG_DATA_HOME": "/somewhere/else"}):
            self.assertEqual(kithome.kit_home(self.home),
                             self.home / ".local" / "share" / "devkit")

    def test_kit_commit_reads_the_stamp_before_git(self):
        self._install()
        release = kithome.current_release(self.home)
        stamp = release / ".devkit-install.json"
        data = json.loads(stamp.read_text())
        data.update(commit="c" * 40, dirty=True)
        stamp.write_text(json.dumps(data))
        self.assertEqual(instances.kit_commit(release), "c" * 40 + "-dirty")
        self.assertEqual(instances.kit_commit(self.tmp / "nowhere"), "unknown")

    def test_dry_run_lists_every_projection_through_current(self):
        profile = load_for_create("dummy", "core")
        dry_home = self.tmp / "dry"
        real_home = self.tmp / "real"
        dry_home.mkdir()
        real_home.mkdir()
        dry, real = Plan(False), Plan(True)
        with redirect_stdout(io.StringIO()):
            materialize(profile, ["claude"], dry_home, dry, force=True)
            materialize(profile, ["claude"], real_home, real, force=True)
        # Only links into the kit: in dry run `claude/hooks` waits for a directory
        # the apply run creates first, which is unrelated to where links point.
        def links(plan: Plan, home: Path) -> list[str]:
            return sorted(a.replace(str(home), "~") for a in plan.actions
                          if a.startswith("link") and "/current/core/" in a)

        self.assertGreater(len(links(dry, dry_home)), 10)
        self.assertEqual(links(dry, dry_home), links(real, real_home))
        self.assertFalse([a for a in dry.actions if str(REPO) in a])
        self.assertFalse(kithome.kit_home(dry_home).exists())


class KitSourceTests(unittest.TestCase):
    """'The upgrade source is a local directory or a git URL; lineage is checked.'"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.staging = self.tmp / "staging"
        self.repo = self.tmp / "repo"
        self.lineage = _git_kit(self.repo)
        self.kit = {"lineage_id": self.lineage}

    def _stage(self, source, ref: str = "HEAD") -> Path:
        with redirect_stdout(io.StringIO()):
            return kitsource.stage(str(source), ref, self.kit, self.staging, "20260101T000000000000Z")

    def test_directory_with_git_reads_the_working_tree(self):
        _put(self.repo, "core/untracked.txt", "u\n")
        _put(self.repo, "core/ignored.txt", "i\n")
        clean = kitsource.inspect_directory(self.repo, self.kit)
        self.assertIn("core/untracked.txt", clean["files"])
        self.assertNotIn("core/ignored.txt", clean["files"])
        self.assertTrue(clean["dirty"], "an untracked payload file differs from HEAD")
        (self.repo / "core/untracked.txt").unlink()
        self.assertFalse(kitsource.inspect_directory(self.repo, self.kit)["dirty"])
        _put(self.repo, "core/skills/s/SKILL.md", "edited\n")
        edited = kitsource.inspect_directory(self.repo, self.kit)
        self.assertTrue(edited["dirty"])
        self.assertTrue(edited["lineage_verified"])
        staged = self._stage(self.repo)
        marker = kitsource.read_marker(staged)
        self.assertTrue(marker["dirty"])
        self.assertEqual(marker["commit"], _git(self.repo, "rev-parse", "HEAD"))
        self.assertEqual((staged / "core/skills/s/SKILL.md").read_text(), "edited\n")
        self.assertFalse((staged / ".git").exists())

    def test_directory_without_git_is_read_by_walking(self):
        plain = self.tmp / "plain"
        shutil.copytree(self.repo, plain, symlinks=True)
        shutil.rmtree(plain / ".git")
        out = io.StringIO()
        with redirect_stdout(out):
            staged = kitsource.stage_directory(plain, self.kit, self.staging, "s1")
        marker = kitsource.read_marker(staged)
        self.assertFalse(marker["dirty"])
        self.assertEqual(marker["commit"], "unknown")
        self.assertFalse(marker["lineage_verified"])
        self.assertIn("unverified by history", out.getvalue())
        self.assertTrue((staged / "core/bin/agentctl").is_symlink())

    def test_git_remote_with_a_ref(self):
        _git(self.repo, "tag", "v1")
        first = _git(self.repo, "rev-parse", "HEAD")
        _put(self.repo, "core/skills/s/SKILL.md", "later\n")
        _git(self.repo, "commit", "-q", "-am", "later")
        bare = self.tmp / "remote.git"
        _git(self.tmp, "clone", "-q", "--bare", str(self.repo), str(bare))
        staged = self._stage(f"file://{bare}", ref="v1")
        marker = kitsource.read_marker(staged)
        self.assertEqual(marker["commit"], first)
        self.assertEqual(marker["lineage_id"], self.lineage)
        self.assertEqual(marker["source"], f"file://{bare}")
        self.assertEqual((staged / "core/skills/s/SKILL.md").read_text(), "one\n")
        head = self._stage(f"file://{bare}")
        self.assertEqual((head / "core/skills/s/SKILL.md").read_text(), "later\n")
        with self.assertRaises(DevkitError):
            self._stage(f"file://{bare}", ref="no-such-ref")

    def test_foreign_lineage_is_refused_for_git_and_for_a_plain_directory(self):
        other = {"lineage_id": "b" * 40}
        bare = self.tmp / "remote.git"
        _git(self.tmp, "clone", "-q", "--bare", str(self.repo), str(bare))
        plain = self.tmp / "plain"
        shutil.copytree(self.repo, plain, symlinks=True)
        shutil.rmtree(plain / ".git")
        for source in (self.repo, f"file://{bare}", plain):
            with self.subTest(source=str(source)), redirect_stdout(io.StringIO()):
                with self.assertRaises(DevkitError) as caught:
                    kitsource.stage(str(source), "HEAD", other, self.staging, "s2")
                self.assertIn("lineage mismatch", str(caught.exception))
        self.assertFalse(self.staging.exists() and any(
            p.name != "fetch-s2" and p.is_dir() for p in self.staging.iterdir()),
            "a refused source must leave nothing staged")

    def test_a_directory_that_is_not_a_kit_is_refused(self):
        with self.assertRaises(DevkitError):
            kitsource.inspect_directory(self.tmp / "missing", self.kit)
        (self.tmp / "empty").mkdir()
        with self.assertRaises(DevkitError):
            kitsource.inspect_directory(self.tmp / "empty", self.kit)

    def test_source_resolution_order(self):
        home = self.tmp / "home"
        home.mkdir()
        meta = {"upstream": "https://example.com/kit.git"}
        with mock.patch("devkit_cli.profiles._kit_metadata", return_value=meta):
            self.assertEqual(kitsource.resolve_source("/x", home), "/x")
            self.assertEqual(kitsource.resolve_source(None, home),
                             "https://example.com/kit.git")
            with redirect_stdout(io.StringIO()):
                kithome.ensure_installed(self.repo, home, Plan(True))
            self.assertEqual(kitsource.resolve_source(None, home), str(self.repo.resolve()))
            self.assertEqual(kitsource.resolve_source("/y", home), "/y")
        shutil.rmtree(kithome.kit_home(home))
        with mock.patch("devkit_cli.profiles._kit_metadata", return_value={}):
            with self.assertRaises(DevkitError) as caught:
                kitsource.resolve_source(None, home)
            self.assertIn("--from", caught.exception.fix)


class _HomePatched(unittest.TestCase):
    """A temp home that `Path.home()`, the staging cache and the root guard see."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.checkout = self.tmp / "checkout"
        kithome.copy_payload(REPO, self.checkout, kithome.payload_files(REPO))
        for patcher in (
                mock.patch.dict(os.environ, {"HOME": str(self.home),
                                             "XDG_CONFIG_HOME": str(self.home / ".config"),
                                             "XDG_DATA_HOME": ""}),
                mock.patch.object(Path, "home", staticmethod(lambda: self.home)),
                mock.patch.object(update, "STAGING_ROOT", self.tmp / "staged"),
                mock.patch.object(privilege, "refuse_root", lambda *_a, **_k: None)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def _profile(self, kit: Path | None = None) -> dict:
        kit = kit or self.checkout
        return instances.bind_instance(manifest.load("core", kit_root=kit), "core", "core")

    def _install(self, kit: Path | None = None) -> None:
        kit = kit or self.checkout
        with redirect_stdout(io.StringIO()):
            materialize(self._profile(kit), ["claude"], self.home, Plan(True),
                        force=True, kit_root=kit)
            ensure(self.home, Plan(True))
            cli_link.ensure(self.home, Plan(True))

    def _env(self) -> dict:
        return {**os.environ, "HOME": str(self.home),
                "XDG_CONFIG_HOME": str(self.home / ".config")}

    def _core_skill(self, kit: Path) -> Path:
        """A skill the core profile projects, so an edit to it is visible."""
        return kit / "core" / "skills" / self._profile(kit)["skills"][0]

    def _apply(self, source: Path | str | None, apply: bool = True) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            rc = update.cmd_apply(argparse.Namespace(
                profile="core", apply=apply, from_source=str(source) if source else None,
                ref=None))
        return rc, out.getvalue()

    def _projections(self) -> dict[str, str]:
        found = {}
        for base in (self.home / ".agents-profiles", self.home / ".local" / "bin"):
            for root, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs if not d.endswith("-data")]
                for name in (*dirs, *files):
                    path = Path(root) / name
                    if path.is_symlink():
                        found[str(path)] = os.readlink(path)
        return found


class StandaloneInstallTests(_HomePatched):
    """'Delete the checkout, keep working.'"""

    def test_nothing_under_home_names_the_checkout(self):
        self._install()
        needle = str(self.checkout).encode()
        links = self._projections()
        self.assertGreater(len(links), 50)
        for path, target in links.items():
            self.assertNotIn(str(self.checkout), target, path)
        scanned = 0
        for root, dirs, files in os.walk(self.home):
            for name in files:
                path = Path(root) / name
                if path.is_symlink() or name == ".devkit-install.json":
                    continue  # the stamp records the upgrade source, which is not a runtime reference
                scanned += 1
                self.assertNotIn(needle, path.read_bytes(), str(path))
        self.assertGreater(scanned, 100)

    def test_everything_still_runs_after_the_checkout_is_deleted(self):
        self._install()
        shutil.rmtree(self.checkout)
        for path, target in self._projections().items():
            self.assertTrue(Path(path).exists(), f"{path} -> {target} dangles")

        devkit = self.home / ".local" / "bin" / "devkit"
        for args in (("profile", "list"), ("doctor",)):
            result = subprocess.run([str(devkit), *args], capture_output=True, text=True,
                                    env=self._env(), check=False)
            with self.subTest(command=args):
                self.assertNotIn("Traceback", result.stderr)
                self.assertNotIn("legacy:", result.stdout)
        listed = subprocess.run([str(devkit), "profile", "list"], capture_output=True,
                                text=True, env=self._env(), check=False)
        self.assertEqual(listed.returncode, 0, listed.stderr)

        tool = subprocess.run([str(self.home / ".agents-profiles/core/bin/agentctl"), "--help"],
                              capture_output=True, text=True, env=self._env(), check=False)
        self.assertEqual(tool.returncode, 0, tool.stderr)
        hook = self.home / ".agents-profiles/core/claude/hooks/deny-git-push.sh"
        ran = subprocess.run(["bash", str(hook)], input='{"command": "git push"}',
                             capture_output=True, text=True, env=self._env(), check=False)
        self.assertIn('"deny"', ran.stdout, ran.stderr)

        bash = subprocess.run(["bash", "-n", str(self.home / ".local/bin/claude-core")],
                              capture_output=True, text=True, check=False)
        self.assertEqual(bash.returncode, 0, bash.stderr)
        launch = (self.home / ".local/bin/devkit-auth-launch").read_text()
        python_path = re.search(r'^PYTHONPATH="([^"]+)"', launch, re.MULTILINE).group(1)
        self.assertEqual(python_path, str(kithome.current_link(self.home)))
        imported = subprocess.run(
            [sys.executable, "-c", "import devkit_cli.auth"], capture_output=True, text=True,
            env={**self._env(), "PYTHONPATH": python_path}, check=False)
        self.assertEqual(imported.returncode, 0, imported.stderr)

    def test_maintainer_commands_refuse_from_an_installed_release(self):
        self._install()
        devkit = self.home / ".local" / "bin" / "devkit"
        for command in (("export", "--check"), ("docs", "generate", "--check"), ("lint-paths",)):
            result = subprocess.run([str(devkit), *command], capture_output=True, text=True,
                                    env=self._env(), check=False)
            with self.subTest(command=command):
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("needs a checkout", result.stderr)
                self.assertIn("run it from your checkout", result.stderr)
        explicit = subprocess.run([str(devkit), "lint-paths", str(self.checkout)],
                                  capture_output=True, text=True, env=self._env(), check=False)
        self.assertNotIn("needs a checkout", explicit.stderr)

    def test_repeated_sync_from_an_edited_checkout_keeps_two_releases(self):
        skill = self._core_skill(self.checkout) / "SKILL.md"
        for run in range(3):
            skill.write_text(skill.read_text() + f"\nedit {run}\n")
            self._install()
        releases = kithome.releases_dir(self.home)
        self.assertEqual(len(list(releases.iterdir())), 2)
        self.assertIn("edit 2", (kithome.current_link(self.home) / "core/skills"
                                 / skill.parent.name / "SKILL.md").read_text())

    def test_provenance_records_the_installed_commit(self):
        self._install()
        prov = instances.read_provenance(self.home / ".agents-profiles/core/claude")
        stamp = kithome.read_stamp(kithome.current_release(self.home))
        self.assertEqual(prov["source_commit"], instances.kit_commit(
            kithome.current_release(self.home)))
        self.assertEqual(stamp["source"], str(self.checkout.resolve()))


class StandaloneUpgradeTests(_HomePatched):
    """'update apply installs a release, flips current, and rolls back on failure.'"""

    def setUp(self):
        super().setUp()
        self._install()
        self.first = kithome.current_release(self.home)
        self.skill = self._core_skill(self.checkout).name

    def _variant(self, name: str, text: str) -> Path:
        copy = self.tmp / name
        kithome.copy_payload(self.checkout, copy, kithome.payload_files(self.checkout))
        _put(copy, f"core/skills/{self.skill}/SKILL.md", text)
        return copy

    def _visible_skill(self) -> str:
        return (self.home / ".agents-profiles/core/agents/skills" / self.skill
                / "SKILL.md").read_text()

    def test_apply_from_a_directory_moves_current_and_leaves_links_alone(self):
        before = self._projections()
        rc, out = self._apply(self._variant("second", "second release\n"))
        self.assertEqual(rc, 0, out)
        second = kithome.current_release(self.home)
        self.assertNotEqual(second, self.first)
        self.assertEqual(self._projections(), before)
        self.assertEqual(self._visible_skill(), "second release\n")
        self.assertTrue(self.first.is_dir(), "the previous release is kept for rollback")

        self._apply(self._variant("third", "third release\n"))
        self.assertEqual(self._visible_skill(), "third release\n")
        remaining = {p.name for p in kithome.releases_dir(self.home).iterdir()}
        self.assertEqual(remaining, {second.name, kithome.current_release(self.home).name})
        self.assertNotIn(self.first.name, remaining)
        prov = instances.read_provenance(self.home / ".agents-profiles/core/claude")
        self.assertEqual(prov["history"][-1]["to"], prov["source_commit"])

    def test_apply_keeps_the_colour_chosen_at_create(self):
        config_dir = self.home / ".agents-profiles/core/claude"
        prov = instances.read_provenance(config_dir)
        chosen = "#2563eb"
        self.assertNotEqual(prov["color"], chosen)
        write_json(config_dir / instances.PROVENANCE_NAME, {**prov, "color": chosen})
        rc, out = self._apply(self._variant("second", "second release\n"))
        self.assertEqual(rc, 0, out)
        self.assertEqual(instances.read_provenance(config_dir)["color"], chosen)

    def test_apply_of_an_identical_payload_installs_nothing(self):
        rc, out = self._apply(self.checkout)
        self.assertEqual(rc, 0)
        self.assertIn("up to date", out)
        self.assertEqual(kithome.current_release(self.home), self.first)
        self.assertEqual(len(list(kithome.releases_dir(self.home).iterdir())), 1)

    def test_dry_run_apply_writes_nothing_to_the_kit_home(self):
        rc, out = self._apply(self._variant("second", "second release\n"), apply=False)
        self.assertEqual(rc, 0)
        self.assertIn("Dry run", out)
        self.assertEqual(kithome.current_release(self.home), self.first)
        self.assertEqual(len(list(kithome.releases_dir(self.home).iterdir())), 1)
        staged = self.tmp / "staged"
        self.assertFalse(staged.exists() and any(staged.iterdir()),
                         "a dry run must not stage a payload a later bare apply installs")

    def test_a_failure_after_the_flip_restores_current_and_the_instance(self):
        config = self.home / ".agents-profiles/core/claude"
        before = instances.read_provenance(config)
        wrapper = (self.home / ".local/bin/claude-core").read_text()
        source = self._variant("second", "second release\n")
        with mock.patch("devkit_cli.profiles.materialize", side_effect=RuntimeError("boom")), \
                self.assertRaises(DevkitError) as caught:
            self._apply(source)
        self.assertIn("rolled back", str(caught.exception))
        self.assertEqual(kithome.current_release(self.home), self.first)
        self.assertEqual(self._visible_skill(),
                         (self.checkout / "core/skills" / self.skill / "SKILL.md").read_text())
        self.assertEqual(instances.read_provenance(config), before)
        self.assertEqual((self.home / ".local/bin/claude-core").read_text(), wrapper)
        self.assertFalse(list(config.parent.glob("claude.devkit-backup-*")))

    def test_a_foreign_lineage_is_refused_before_anything_is_installed(self):
        foreign = self._variant("foreign", "foreign\n")
        yaml = foreign / "devkit.yaml"
        yaml.write_text(re.sub(r"lineage_id: \w+", "lineage_id: " + "f" * 40,
                               yaml.read_text()))
        with self.assertRaises(DevkitError) as caught:
            self._apply(foreign)
        self.assertIn("lineage mismatch", str(caught.exception))
        self.assertEqual(kithome.current_release(self.home), self.first)
        self.assertEqual(len(list(kithome.releases_dir(self.home).iterdir())), 1)

    def test_apply_from_a_git_remote(self):
        remote = self.tmp / "remote-src"
        shutil.copytree(self.checkout, remote, symlinks=True)
        _put(remote, f"core/skills/{self.skill}/SKILL.md", "from the remote\n")
        _git(remote, "init", "-q", "-b", "main")
        _git(remote, "add", "-A")
        _git(remote, "commit", "-q", "-m", "root")
        root = _git(remote, "rev-parse", "HEAD")
        # This kit's real lineage is its own root commit, which no test history
        # can share: name the test history's root in the kit, the remote and
        # the installed instance instead.
        yaml = remote / "devkit.yaml"
        yaml.write_text(re.sub(r"lineage_id: \w+", f"lineage_id: {root}", yaml.read_text()))
        _git(remote, "commit", "-q", "-am", "record lineage")
        path = self.home / ".agents-profiles/core/claude" / instances.PROVENANCE_NAME
        prov = json.loads(path.read_text())
        prov["lineage_id"] = root
        path.write_text(json.dumps(prov))
        kit = {**profiles._kit_metadata(), "lineage_id": root}
        with mock.patch.object(update, "_kit", return_value=kit):
            rc, out = self._apply(f"file://{remote}")
        self.assertEqual(rc, 0, out)
        self.assertEqual(self._visible_skill(), "from the remote\n")
        stamp = kithome.read_stamp(kithome.current_release(self.home))
        self.assertEqual(stamp["source"], f"file://{remote}")
        self.assertEqual(stamp["commit"], _git(remote, "rev-parse", "HEAD"))
        self.assertFalse(stamp["dirty"])


class UninstallKitHomeTests(unittest.TestCase):
    """'devkit-uninstall.sh removes the kit home, only when it holds release stamps.'"""

    def _kit(self, home: Path, stamped: bool) -> Path:
        release = home / ".local" / "share" / "devkit" / "releases" / "abc123abc123"
        release.mkdir(parents=True)
        (release / ("devkit.py")).write_text("x")
        if stamped:
            (release / ".devkit-install.json").write_text("{}")
        (release.parent.parent / "current").symlink_to("releases/abc123abc123")
        return release.parent.parent

    def test_dry_run_names_a_stamped_kit_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            kit = self._kit(home, stamped=True)
            result = _run_uninstall(home)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"dir   {kit}", result.stdout)
            self.assertTrue(kit.is_dir(), "a dry run removes nothing")

    def test_apply_removes_it_and_leaves_an_unstamped_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            kit = self._kit(home, stamped=True)
            result = _run_uninstall(home, "--apply")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(kit.exists())
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            kit = self._kit(home, stamped=False)
            result = _run_uninstall(home)
            self.assertNotIn(str(kit), result.stdout)
            self.assertTrue(kit.is_dir())

    def test_apply_removes_the_update_staging_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            staged = home / ".cache" / "devkit" / "staged" / "dir-abc123abc123"
            staged.mkdir(parents=True)
            (staged / ".devkit-staged.json").write_text("{}")
            self.assertIn(f"dir   {home / '.cache/devkit'}", _run_uninstall(home).stdout)
            result = _run_uninstall(home, "--apply")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((home / ".cache" / "devkit").exists())
            self.assertTrue((home / ".cache").is_dir())

    def test_script_stays_static(self):
        self.assertNotIn("python3", SCRIPT)
        self.assertNotIn("devkit_cli", SCRIPT)


class LegacyDoctorTests(_HomePatched):
    """'doctor lists profiles still linked into a checkout and names the fix.'"""

    def _doctor(self) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            rc = profiles.cmd_doctor(argparse.Namespace(profile=None))
        return rc, out.getvalue()

    def _make_legacy(self) -> None:
        self._install()
        agents = self.home / ".agents-profiles/core/agents"
        for layer in ("skills", "kb"):
            for link in list((agents / layer).iterdir()):
                if not link.is_symlink():  # a nested projection dir, e.g. kb/offline-reference
                    continue
                link.unlink()
                link.symlink_to(self.checkout / "core" / layer / link.name)
        (agents / "bin").unlink()
        (agents / "bin").symlink_to(self.checkout / "core" / "bin")
        devkit = self.home / ".local" / "bin" / "devkit"
        devkit.unlink()
        devkit.symlink_to(self.checkout / "devkit.py")

    def test_a_checkout_linked_profile_is_reported_with_the_fixing_command(self):
        self._make_legacy()
        rc, out = self._doctor()
        self.assertEqual(rc, 1)
        self.assertIn("legacy: core:", out)
        self.assertIn("devkit profile sync core --apply", out)
        self.assertIn("legacy: ~/.local/bin/devkit", out)

    def test_sync_makes_it_standalone_and_doctor_clean_of_legacy(self):
        self._make_legacy()
        self._install()
        _rc, out = self._doctor()
        self.assertNotIn("legacy:", out)
        self.assertEqual(os.readlink(self.home / ".local/bin/devkit"),
                         str(kithome.current_link(self.home) / "devkit.py"))
        for path, target in self._projections().items():
            self.assertNotIn(str(self.checkout), target, path)

    def test_update_check_lists_legacy_installs(self):
        self._make_legacy()
        out = io.StringIO()
        with redirect_stdout(out):
            update.cmd_check(argparse.Namespace(profile=None, from_source=None, ref=None))
        self.assertIn("legacy: core", out.getvalue())
        self.assertIn("devkit profile sync core --apply", out.getvalue())

    def test_update_check_against_a_directory_source(self):
        self._install()
        newer = self.tmp / "newer"
        kithome.copy_payload(self.checkout, newer, kithome.payload_files(self.checkout))
        _put(newer, f"core/skills/{self._core_skill(self.checkout).name}/SKILL.md", "new\n")
        for source, word in ((self.checkout, "up to date"), (newer, "update available")):
            out = io.StringIO()
            with self.subTest(source=source.name), redirect_stdout(out):
                update.cmd_check(argparse.Namespace(
                    profile=None, from_source=str(source), ref=None))
            self.assertIn(f": {word}", out.getvalue().splitlines()[0])


class HeadlessTests(unittest.TestCase):
    """Headless installs leave no GUI artifacts and stay headless across sync/update."""

    def setUp(self):
        self._env = mock.patch.dict(os.environ)
        self._env.start()
        os.environ.pop(instances.HEADLESS_ENV, None)
        self.addCleanup(self._env.stop)

    def _user(self, home: Path):
        return mock.patch.object(
            privilege, "refuse_root",
            lambda *_a, **_kw: argparse.Namespace(pw_dir=str(home), pw_name="tester"))

    def _materialize(self, home: Path, headless: bool, name: str = "dummy") -> dict:
        stock = home / "claude-desktop.png"
        stock.write_bytes(b"png")
        profile = load_for_create(name, "enonic")
        instances.apply_headless(profile, headless, home)
        with mock.patch.object(instances, "first_existing", lambda _c: "/usr/bin/claude"), \
                mock.patch("devkit_cli.profiles._find_vendor_icon", lambda _v: stock), \
                mock.patch.object(instances, "install_launcher_icons") as badge, \
                mock.patch.object(instances, "refresh_hicolor_cache") as cache, \
                mock.patch.object(instances, "imagemagick") as magick, \
                redirect_stdout(io.StringIO()):
            materialize(profile, ["claude"], home, Plan(apply=True), force=True)
        self.badge_calls = (badge.called, cache.called, magick.called)
        return instances.read_provenance(
            instances.paths_for(name, "claude", home)["config_dir"])

    def test_headless_materialize_writes_no_gui_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            prov = self._materialize(home, True)
            self.assertFalse((home / ".local" / "share" / "applications").exists())
            self.assertFalse((home / ".local" / "share" / "icons").exists())
            auth_paths = instances.auth_paths(home)
            self.assertFalse(auth_paths["launch"].exists())
            self.assertFalse(auth_paths["dispatch"].exists())
        self.assertIs(prov["headless"], True)
        self.assertNotIn("color", prov)
        self.assertNotIn("appfork", prov)
        self.assertEqual(self.badge_calls, (False, False, False))

    def test_desktop_materialize_still_writes_launcher(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            prov = self._materialize(home, False)
            self.assertTrue(instances.paths_for("dummy", "claude", home)["desktop"].is_file())
            self.assertTrue(instances.auth_paths(home)["launch"].is_file())
        self.assertIn("color", prov)
        self.assertIn("appfork", prov)
        self.assertNotIn("headless", prov)

    def test_extract_profile_shape(self):
        profile = manifest.load("extract")
        self.assertEqual(profile["lineage"], ["extract"])
        for skill in profile["skills"]:
            self.assertTrue((REPO / "core" / "skills" / skill).is_dir(), skill)
        for entry in profile["kb"]:
            leaf = manifest.layer_leaf(entry)
            self.assertTrue((REPO / "core" / "kb" / leaf).is_dir(), entry)
        provided = [name for dep in profile["deps"] for name in dep["provides"]]
        self.assertEqual(
            provided,
            ["git", "python3", "cc", "make", "node", "npm", "graft", "serena",
             "graphify", "playwright-cli", "7z"])
        for dep in profile["deps"]:
            if set(dep["provides"]) & {"graft", "serena", "graphify", "node"}:
                self.assertTrue(
                    dep.get("version") or "@" in dep.get("package", "")
                    or "==" in dep.get("package", ""), dep["provides"])

    def test_extract_headless_materialize(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            profile = load_for_create("x", "extract")
            instances.apply_headless(profile, True, home)
            with mock.patch.object(instances, "first_existing", lambda _c: "/usr/bin/vendor"), \
                    mock.patch.object(instances, "install_launcher_icons"), \
                    mock.patch.object(instances, "refresh_hicolor_cache"), \
                    mock.patch.object(instances, "imagemagick"), \
                    redirect_stdout(io.StringIO()):
                materialize(profile, ["claude", "codex", "cursor"], home,
                            Plan(apply=True), force=True)
            bindir = home / ".local" / "bin"
            for vendor in ("claude", "codex", "cursor"):
                self.assertTrue((bindir / f"{vendor}-x").exists(), vendor)
            claude = instances.paths_for("x", "claude", home)["config_dir"]
            self.assertTrue((claude / "skills" / "graft").is_symlink())
            self.assertFalse((home / ".local" / "share" / "applications").exists())
            servers = json.loads((claude / ".claude.json").read_text())["mcpServers"]
            self.assertEqual(list(servers), ["serena"])

    def test_apply_headless_precedence(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self._materialize(home, True)

            def resolved(flag):
                profile = load_for_create("dummy", "enonic")
                instances.apply_headless(profile, flag, home)
                return profile["headless"]

            self.assertTrue(resolved(None))
            os.environ[instances.HEADLESS_ENV] = "0"
            self.assertFalse(resolved(None))
            self.assertTrue(resolved(True))
            os.environ[instances.HEADLESS_ENV] = "1"
            self.assertFalse(resolved(False))
            os.environ[instances.HEADLESS_ENV] = "maybe"
            self.assertTrue(resolved(None))

    def test_finish_appforks_skips_escalation_when_headless(self):
        profile = load_for_create("dummy", "enonic")
        profile["headless"] = True
        with mock.patch.object(profiles, "escalate_appforks") as escalate:
            profiles.finish_appforks(Path("/nonexistent"), profile, "tester")
        escalate.assert_not_called()

    def test_discover_desktop_instances_skips_headless(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self._materialize(home, True, name="quiet")
            self._materialize(home, False, name="loud")
            names = [row[0] for row in appfork.discover_desktop_instances(home)]
            self.assertEqual(names, ["loud"])

    def test_sync_homes_on_headless_only_home_never_syncs(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self._materialize(home, True)
            out = io.StringIO()
            with mock.patch.object(appfork, "sync_one") as sync_one, redirect_stdout(out):
                appfork.sync_homes([home], appfork.Env(), dry_run=True)
            sync_one.assert_not_called()
            self.assertIn("no desktop profile instances found", out.getvalue())

    def test_apps_sync_is_a_noop_under_env(self):
        os.environ[instances.HEADLESS_ENV] = "1"
        for apply in (False, True):
            args = argparse.Namespace(apply=apply, install_hook=True, icons_only=True,
                                      user=None, profile=None, vendor=None)
            with mock.patch.object(privilege, "run_privileged") as run, \
                    redirect_stdout(io.StringIO()) as out:
                rc = profiles.cmd_apps_sync(args)
            self.assertEqual(rc, 0)
            run.assert_not_called()
            self.assertIn("skip: headless devkit", out.getvalue())

    def test_create_headless_has_no_color_and_refuses_color_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            base = {"name": "dummy", "type": "enonic", "vendor": ["claude"],
                    "apply": True, "force": False, "headless": True, "color": None}
            with self._user(home), mock.patch.object(instances, "first_existing", lambda _c: None), \
                    mock.patch.object(instances, "assign_profile_color") as assign, \
                    mock.patch.object(profiles, "finish_appforks"), \
                    redirect_stdout(io.StringIO()):
                with self.assertRaises(DevkitError):
                    profiles.cmd_create(argparse.Namespace(**{**base, "color": "#112233"}))
                self.assertEqual(profiles.cmd_create(argparse.Namespace(**base)), 0)
            assign.assert_not_called()
            prov = instances.read_provenance(
                instances.paths_for("dummy", "claude", home)["config_dir"])
            self.assertIs(prov["headless"], True)
            self.assertNotIn("color", prov)
            out = io.StringIO()
            with mock.patch.object(Path, "home", staticmethod(lambda: home)), \
                    redirect_stdout(out):
                profiles.cmd_show(argparse.Namespace(name="dummy"))
            shown = json.loads(out.getvalue())
        self.assertNotIn("colors", shown)
        self.assertIs(shown["headless"], True)

    def test_sync_keeps_headless_and_no_headless_switches_to_color(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self._materialize(home, True)
            config = instances.paths_for("dummy", "claude", home)["config_dir"]

            def sync(**kw):
                with self._user(home), \
                        mock.patch.object(instances, "first_existing", lambda _c: None), \
                        mock.patch.object(profiles, "finish_appforks"), \
                        redirect_stdout(io.StringIO()):
                    profiles.cmd_sync(argparse.Namespace(name="dummy", apply=True, **kw))
                return instances.read_provenance(config)

            kept = sync(headless=None)
            self.assertIs(kept["headless"], True)
            self.assertNotIn("color", kept)
            flipped = sync(headless=False)
        self.assertNotIn("headless", flipped)
        self.assertRegex(flipped["color"], r"^#[0-9A-Fa-f]{6}$")

    def test_update_apply_keeps_headless(self):
        helper = UpdateApplyTests()
        commit = "e" * 40
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            helper._stage(Path(tmp) / "staged", commit)
            profile = load_for_create("core", "core")
            instances.apply_headless(profile, True, home)
            materialize(profile, ["claude"], home, Plan(apply=True), force=True)
            staging, home_fn = update.STAGING_ROOT, Path.home
            update.STAGING_ROOT = Path(tmp) / "staged"
            Path.home = staticmethod(lambda: home)
            try:
                with self._user(home), redirect_stdout(io.StringIO()):
                    rc = update.cmd_apply(argparse.Namespace(profile="core", apply=True))
            finally:
                update.STAGING_ROOT, Path.home = staging, home_fn
            prov = instances.read_provenance(
                instances.paths_for("core", "claude", home)["config_dir"])
            self.assertFalse(instances.auth_paths(home)["launch"].exists())
        self.assertEqual(rc, 0)
        self.assertIs(prov["headless"], True)
        self.assertNotIn("color", prov)

    def test_doctor_skips_auth_lines_for_all_headless_home(self):
        want = "x-scheme-handler/claude (want devkit)"
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self._materialize(home, True, name="quiet")

            def doctor() -> str:
                out = io.StringIO()
                with mock.patch.object(Path, "home", staticmethod(lambda: home)), \
                        mock.patch.object(auth, "doctor_lines", lambda _h: [want]), \
                        mock.patch.object(instances, "kit_commit",
                                          lambda *_a: prov_commit), \
                        redirect_stdout(out):
                    profiles.cmd_doctor(argparse.Namespace(profile=None))
                return out.getvalue()

            prov_commit = instances.read_provenance(
                instances.paths_for("quiet", "claude", home)["config_dir"])["source_commit"]
            self.assertNotIn(want, doctor())
            self._materialize(home, False, name="loud")
            self.assertIn(want, doctor())


if __name__ == "__main__":
    unittest.main()
