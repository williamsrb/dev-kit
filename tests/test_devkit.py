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

from devkit_cli import appfork, auth, export, instances, manifest, paths, privilege, update  # noqa: E402
from devkit_cli.common import Plan  # noqa: E402
from devkit_cli.errors import DevkitError  # noqa: E402
from devkit_cli.profiles import choose_first_profile, flag_given, load_for_create, materialize  # noqa: E402


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

    def test_run_privileged_invokes_sudo_after_printing(self):
        # CI runs this suite as root. run_privileged refuses uid 0; this test
        # is about print-then-sudo order, so pretend we still need to escalate.
        original_is_root = privilege.is_root
        privilege.is_root = lambda: False
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sudo = root / "sudo"
            marker = root / "order.txt"
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
            saved_path = os.environ.get("PATH", "")
            os.environ["PATH"] = f"{root}{os.pathsep}{saved_path}"
            buf = io.StringIO()
            try:
                with redirect_stdout(buf):
                    rc = privilege.run_privileged(
                        [sys.executable, str(inner)],
                        reason="they write into /usr/lib/devkit.",
                        steps=["rsync stock -> fork"],
                    )
            finally:
                privilege.is_root = original_is_root
                os.environ["PATH"] = saved_path
            self.assertEqual(rc, 0)
            text = buf.getvalue()
            self.assertIn("rsync stock -> fork", text)
            self.assertIn(privilege.ELEVATION_BANNER, text)
            self.assertIn("sudo --", text)
            self.assertLess(text.find(privilege.ELEVATION_BANNER),
                            text.find("sudo --"))
            self.assertEqual(marker.read_text().splitlines(), ["sudo-ran", "inner-ran"])

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
        codex = (REPO / "templates" / "shell" / "codex.sh").read_text()
        self.assertIn('exec "${PROFILE_CODEX_CLI}" "$@"', codex)
        agent = (REPO / "templates" / "shell" / "cursor-agent.sh").read_text()
        self.assertIn('"${PROFILE_CURSOR_AGENT}" "$@"', agent)

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

    def test_desktop_launch_prepends_profile_bin(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            bin_dir = home / ".agents-profiles" / "dummy" / "bin"
            bin_dir.mkdir(parents=True)
            saved = os.environ.get("PATH", "")
            os.environ["PATH"] = "/usr/bin"
            try:
                auth.prepend_profile_bin(home, "dummy")
                self.assertEqual(os.environ["PATH"].split(os.pathsep)[0], str(bin_dir))
                self.assertIn("/usr/bin", os.environ["PATH"])
            finally:
                os.environ["PATH"] = saved


class AuthDispatcherTests(unittest.TestCase):
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
    """Per-profile Electron forks follow the Claude Personal recipe:
    rsync stock, patch identity, never write the stock tree, survive via
    apt + dpkg hooks (Cursor's dual hook; Personal is apt-only)."""

    def _asar(self, path: Path, desktop: str) -> None:
        blob = (json.dumps({"name": "app", "desktopName": desktop,
                            "productName": "Claude"}) + "\n").encode()
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
            appfork.patch_asar_desktop_name(
                path, "Claude-dummy.desktop", dry_run=False)
            self.assertEqual(appfork.asar_desktop_name(path), "Claude-dummy.desktop")

    def test_asar_dry_run_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "app.asar"
            self._asar(path, "chatgpt.desktop")
            before = path.read_bytes()
            appfork.patch_asar_desktop_name(
                path, "Codex-dummy.desktop", dry_run=True)
            self.assertEqual(path.read_bytes(), before)

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

    def test_refuses_to_rsync_onto_stock_or_personal(self):
        spec = appfork.VENDORS["claude"]
        with self.assertRaises(RuntimeError) as caught:
            appfork.rsync_stock(spec, spec.stock_lib, dry_run=True)
        self.assertIn("stock", str(caught.exception))
        with self.assertRaises(RuntimeError) as caught:
            appfork.rsync_stock(spec, appfork.PERSONAL_LIB, dry_run=True)
        self.assertIn("Personal", str(caught.exception))

    def test_cheap_gate_skips_when_version_and_desktop_name_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            stock = Path(tmp) / "stock"
            dest = Path(tmp) / "fork"
            for tree in (stock, dest):
                tree.mkdir()
                (tree / "version").write_text("42.0.0\n", encoding="utf-8")
                self._asar(tree / "resources" / "app.asar", "Claude-dummy.desktop")
            spec = appfork.Vendor(
                name="claude", package="claude-desktop", stock_lib=stock,
                binary="claude-desktop",
                stock_desktop_name="com.anthropic.Claude.desktop",
                asar_rel="resources/app.asar",
            )
            with self.assertRaises(appfork.Skip) as caught:
                appfork.cheap_gates(spec, dest, "dummy")
            self.assertIn("already at 42.0.0", str(caught.exception))

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
            self.assertNotIn("99-cursor-recolor", apt)
            self.assertNotIn("99-claude-personal-sync", apt)

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
