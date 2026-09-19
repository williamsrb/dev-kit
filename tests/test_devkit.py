"""Acceptance tests for devkit.

Each test names the requirement it covers so a failure points at the
requirement, not just the code.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from devkit_cli import export, instances, manifest, paths, privilege, update  # noqa: E402
from devkit_cli.common import Plan  # noqa: E402
from devkit_cli.errors import DevkitError  # noqa: E402
from devkit_cli.profiles import materialize  # noqa: E402


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

    GROUPS = ["profile", "update", "origin", "docs"]

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

    def test_bad_flag_does_not_slip_through_the_help_branch(self):
        self.assertEqual(run("--nope").returncode, 2)


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
    def test_export_is_in_sync(self):
        self.assertEqual(run("export", "--check").returncode, 0)

    def test_core_is_present_and_populated(self):
        """What CI can check without the source: the committed export exists."""
        core = REPO / "core"
        self.assertTrue(core.is_dir(), "core/ is missing; run devkit export --apply")
        self.assertGreater(len(list((core / "skills").iterdir())), 20)

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

    def test_hue_is_stable_and_distinct_per_profile(self):
        a = instances.profile_colors({"name": "alpha"})
        b = instances.profile_colors({"name": "beta"})
        self.assertEqual(a, instances.profile_colors({"name": "alpha"}))
        self.assertNotEqual(a, b)

    def test_declared_color_wins_over_the_derived_hue(self):
        declared = {"name": "x", "color": {"light": "#ffcc00", "dark": "#6a0dad"}}
        self.assertEqual(instances.profile_colors(declared), ("#ffcc00", "#6a0dad"))


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

    def test_uid_zero_is_refused(self):
        with self.assertRaises(DevkitError):
            privilege.resolve_target_user("root")

    def test_unknown_user_is_named(self):
        with self.assertRaises(DevkitError) as caught:
            privilege.resolve_target_user("definitely-not-a-user")
        self.assertIn("definitely-not-a-user", str(caught.exception))


class RenderingTests(unittest.TestCase):
    def test_no_unrendered_token_survives(self):
        profile = manifest.load("enonic")
        tokens = instances.render_tokens(profile, "codex", Path("/home/example"))
        for template in (REPO / "templates").rglob("*"):
            if not template.is_file():
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

    def test_apt_does_not_flag_third_party(self):
        self.assertNotIn("thirdparty", self._plan("apt", "debian"))

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

            staging, home_fn = update.STAGING_ROOT, Path.home
            update.STAGING_ROOT = Path(tmp) / "staged"
            Path.home = staticmethod(lambda: home)
            try:
                with redirect_stdout(io.StringIO()):
                    rc = update.cmd_apply(argparse.Namespace(profile="core", apply=True))
            finally:
                update.STAGING_ROOT, Path.home = staging, home_fn

            wrapper = (home / ".local" / "bin" / "claude-core").read_text()
            provenance = json.loads(
                (home / ".agents-profiles" / "core" / "claude"
                 / instances.PROVENANCE_NAME).read_text())

        self.assertEqual(rc, 0)
        self.assertIn(self.MARKER.strip(), wrapper)
        self.assertEqual(provenance["source_commit"], commit)
        self.assertEqual(provenance["history"][-1]["to"], commit)


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


if __name__ == "__main__":
    unittest.main()
