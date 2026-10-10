"""Acceptance tests for `devkit project`.

Each case builds a real kit home in a temp home and a throwaway git repo. No
test runs a write command against the real home: devkit commands resolve the
home from the passwd entry, so these call the command functions with the root
guard patched to a temp home.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from devkit_cli import flavors, kithome, manifest, privilege, project
from devkit_cli.common import Plan
from devkit_cli.errors import DevkitError

_MASTER: tempfile.TemporaryDirectory | None = None
MASTER_HOME: Path


def setUpModule() -> None:
    """One installed kit for the whole module. Cases that need to change it copy it."""
    global _MASTER, MASTER_HOME
    _MASTER = tempfile.TemporaryDirectory()
    MASTER_HOME = Path(_MASTER.name) / "home"
    MASTER_HOME.mkdir()
    with mock.patch.dict(os.environ, {"XDG_DATA_HOME": ""}), redirect_stdout(io.StringIO()):
        kithome.ensure_installed(REPO, MASTER_HOME, Plan(True))


def tearDownModule() -> None:
    if _MASTER is not None:
        _MASTER.cleanup()


def run_devkit(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(REPO / "devkit"), *args],
                          capture_output=True, text=True, check=False)


def snapshot(root: Path) -> dict[str, tuple]:
    """Every path under `root` with what a write would change."""
    found = {}
    for base, dirs, files in os.walk(root):
        for name in (*dirs, *files):
            path = Path(base) / name
            stat = os.lstat(path)
            found[str(path.relative_to(root))] = (
                os.readlink(path) if path.is_symlink() else None,
                stat.st_size, stat.st_mtime_ns)
    return found


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ProjectCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.home = MASTER_HOME
        gitconfig = self.tmp / "gitconfig"
        gitconfig.write_text("[user]\n\tname = t\n\temail = t@example.com\n"
                             "[init]\n\tdefaultBranch = main\n")
        patcher = mock.patch.dict(os.environ, {
            "HOME": str(self.tmp), "XDG_CONFIG_HOME": str(self.tmp / ".config"),
            "XDG_DATA_HOME": "", "GIT_CONFIG_GLOBAL": str(gitconfig),
            "GIT_CONFIG_NOSYSTEM": "1"})
        patcher.start()
        self.addCleanup(patcher.stop)
        for name in ("AGENTS_HOME", "DEVKIT_PROFILE"):
            os.environ.pop(name, None)
        self.use_home(MASTER_HOME)

    # -- fixtures
    def use_home(self, home: Path) -> None:
        self.home = home
        patcher = mock.patch.object(
            privilege, "refuse_root",
            lambda *_a, **_k: types.SimpleNamespace(pw_dir=str(home)))
        patcher.start()
        self.addCleanup(patcher.stop)

    @property
    def kit_root(self) -> Path:
        return kithome.current_release(self.home)

    def git(self, repo: Path, *args: str) -> str:
        return subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                              text=True, check=True).stdout

    def make_repo(self, files: dict[str, str] | None = None, name: str = "work") -> Path:
        """A git repo with `files` committed (so they are tracked)."""
        repo = self.tmp / name
        repo.mkdir()
        self.git(repo, "init", "-q")
        for rel, text in (files or {}).items():
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (repo / rel).write_text(text)
        (repo / ".keep").write_text("")
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "-q", "-m", "init")
        return repo

    def config(self, *layers: str, name: str = "project.json") -> Path:
        path = self.tmp / name
        path.write_text(json.dumps({"schema": 1, "layers": list(layers)}))
        return path

    def skills(self, *layers: str) -> tuple[str, ...]:
        return project.resolve_layers(layers, self.kit_root).skills

    def call(self, fn, repo: Path, **kwargs) -> tuple[int, str]:
        kwargs.setdefault("apply", True)
        out = io.StringIO()
        with redirect_stdout(out):
            rc = fn(argparse.Namespace(path=str(repo), **kwargs))
        return rc, out.getvalue()

    def build(self, repo: Path, *layers: str, **kwargs) -> tuple[int, str]:
        kwargs.setdefault("config", str(self.config(*(layers or ("core",)))))
        return self.call(project.cmd_build, repo, **kwargs)

    def status(self, repo: Path, **kwargs) -> tuple[int, str]:
        return self.call(project.cmd_status, repo, **kwargs)

    def clean(self, repo: Path, **kwargs) -> tuple[int, str]:
        return self.call(project.cmd_clean, repo, **kwargs)

    def porcelain(self, repo: Path) -> str:
        return self.git(repo, "status", "--porcelain", "-uall")

    def exclude_text(self, repo: Path) -> str:
        return project.exclude_path(repo).read_text()


class BuildTests(ProjectCase):
    def test_T1_core_skills_are_linked_through_current(self):
        """T1 · US-001, FR-5, FR-6"""
        repo = self.make_repo()
        rc, _ = self.build(repo, "core")
        self.assertEqual(rc, 0)
        skills = self.skills("core")
        self.assertGreater(len(skills), 10)
        prefix = kithome.current_link(self.home) / "core" / "skills"
        for name in skills:
            agents = repo / ".agents" / "skills" / name
            self.assertEqual(os.readlink(agents), str(prefix / name))
            self.assertTrue(agents.is_dir())
            claude = repo / ".claude" / "skills" / name
            self.assertEqual(os.readlink(claude), f"../../.agents/skills/{name}")
            self.assertTrue(claude.is_dir())

    def test_T2_dry_run_writes_nothing(self):
        """T2 · US-001"""
        repo = self.make_repo()
        before = snapshot(repo)
        rc, out = self.build(repo, "core", apply=False)
        self.assertEqual(rc, 0)
        self.assertIn("Dry run", out)
        self.assertIn(".agents/skills/", out)
        self.assertIn("exclude", out)
        self.assertEqual(snapshot(repo), before)

    def test_T3_second_apply_has_nothing_to_do(self):
        """T3 · US-001"""
        repo = self.make_repo()
        self.build(repo, "core")
        rc, out = self.build(repo, "core")
        self.assertEqual(rc, 0)
        self.assertIn("nothing to do", out)

    def test_T4_git_status_stays_clean_and_foreign_exclude_lines_survive(self):
        """T4 · US-003, FR-8"""
        repo = self.make_repo()
        exclude = project.exclude_path(repo)
        exclude.write_text("# mine\n*.log\n")
        self.build(repo, "core")
        self.assertEqual(self.porcelain(repo), "")
        text = self.exclude_text(repo)
        self.assertTrue(text.startswith("# mine\n*.log\n"))
        self.assertIn("# >>> devkit project main >>>", text)
        self.assertIn("/.devkit-project.json", text)
        for name in self.skills("core"):
            self.assertIn(f"/.agents/skills/{name}", text)
            self.assertIn(f"/.claude/skills/{name}", text)

    def test_T5_tracked_paths_are_skipped_with_a_warning(self):
        """T5 · US-003, FR-10"""
        name = self.skills("core")[0]
        files = {f".agents/skills/{name}": "mine\n", "AGENTS.md": "# theirs\n"}
        repo = self.make_repo(files)
        hashes = {rel: sha(repo / rel) for rel in files}
        rc, out = self.build(repo, "core", rules=True)
        self.assertEqual(rc, 0)
        self.assertIn(f"warn  .agents/skills/{name}: tracked", out)
        self.assertIn("warn  AGENTS.md", out)
        self.assertEqual({rel: sha(repo / rel) for rel in files}, hashes)
        self.assertFalse((repo / ".claude" / "skills" / name).exists())
        self.assertFalse((repo / "CLAUDE.md").exists())
        self.assertNotIn(f"/.agents/skills/{name}\n", self.exclude_text(repo))
        self.assertEqual(self.git(repo, "status", "--porcelain", "--untracked-files=no"), "")

    def test_T6_tracked_agents_md_is_never_edited_and_claude_md_not_written(self):
        """T6 · US-003, FR-9"""
        repo = self.make_repo({"AGENTS.md": "# theirs\n", "harness/AGENTS.md": "# ours\n"})
        before = sha(repo / "AGENTS.md")
        _, out = self.build(repo, "core")
        self.assertEqual(sha(repo / "AGENTS.md"), before)
        self.assertFalse((repo / "CLAUDE.md").exists())
        self.assertIn("warn  AGENTS.md", out)

    def test_T6b_a_repo_with_only_claude_md_is_left_alone(self):
        repo = self.make_repo({"CLAUDE.md": "# theirs\n", "harness/AGENTS.md": "# ours\n"})
        self.build(repo, "core")
        self.assertFalse((repo / "AGENTS.md").exists())
        self.assertEqual((repo / "CLAUDE.md").read_text(), "# theirs\n")

    def test_T7_harness_agents_md_becomes_agents_md_and_a_claude_link(self):
        """T7 · US-002, FR-9"""
        repo = self.make_repo({"harness/AGENTS.md": "# Our repo\nUse tabs.\n"})
        self.build(repo, "core")
        agents = repo / "AGENTS.md"
        self.assertTrue(agents.is_file() and not agents.is_symlink())
        self.assertIn("Use tabs.", agents.read_text())
        self.assertIn("devkit project build", agents.read_text())
        self.assertEqual(os.readlink(repo / "CLAUDE.md"), "AGENTS.md")
        text = self.exclude_text(repo)
        self.assertIn("/AGENTS.md\n", text)
        self.assertIn("/CLAUDE.md\n", text)
        self.assertEqual(self.porcelain(repo), "")

    def test_T7b_no_content_means_no_file(self):
        repo = self.make_repo()
        self.build(repo, "core")
        self.assertFalse((repo / "AGENTS.md").exists())
        self.assertFalse(os.path.lexists(repo / "CLAUDE.md"))

    def test_T7c_agents_md_follows_harness_edits_but_not_hand_edits(self):
        repo = self.make_repo({"harness/AGENTS.md": "# one\n"})
        self.build(repo, "core")
        (repo / "harness" / "AGENTS.md").write_text("# two\n")
        self.build(repo, "core")
        self.assertIn("# two", (repo / "AGENTS.md").read_text())
        (repo / "AGENTS.md").write_text("# hand edited\n")
        (repo / "harness" / "AGENTS.md").write_text("# three\n")
        _, out = self.build(repo, "core")
        self.assertEqual((repo / "AGENTS.md").read_text(), "# hand edited\n")
        self.assertIn("warn  AGENTS.md", out)

    def test_T8_rules_embed_the_generator_output_per_layer(self):
        """T8 · FR-9"""
        script = self.kit_root / "core" / "bin" / "generate-agents-md.py"

        def render(*layers: str) -> str:
            argv = [sys.executable, str(script), "--stdout"]
            for layer in layers:
                argv += ["--layer", layer]
            return subprocess.run(argv, capture_output=True, text=True, check=True).stdout

        core_only, with_client = render("core"), render("core", "client")
        self.assertGreater(len(with_client), len(core_only))

        repo = self.make_repo(name="a")
        self.build(repo, "core", rules=True)
        self.assertIn(core_only, (repo / "AGENTS.md").read_text())
        self.assertNotIn(with_client, (repo / "AGENTS.md").read_text())

        repo = self.make_repo(name="b")
        self.build(repo, "client", rules=True)
        self.assertIn(with_client, (repo / "AGENTS.md").read_text())

    def test_T8b_a_rebuild_keeps_the_stamped_rules_choice_until_overridden(self):
        """T8b · FR-9"""
        repo = self.make_repo(files={"harness/AGENTS.md": "Repo notes.\n"})
        self.build(repo, "core", rules=True)
        with_rules = (repo / "AGENTS.md").read_text()

        rc, out = self.build(repo, "core")
        self.assertEqual(rc, 0)
        self.assertEqual((repo / "AGENTS.md").read_text(), with_rules)
        self.assertEqual(self.status(repo, config=str(self.config("core")))[0], 0, out)

        self.build(repo, "core", rules=False)
        self.assertEqual((repo / "AGENTS.md").read_text(),
                         project.GENERATED_HEADER + "\nRepo notes.\n")
        self.assertIs(project.read_stamp(repo)["rules"], False)
        self.build(repo, "core")
        self.assertIs(project.read_stamp(repo)["rules"], False)

    def test_T9_repo_owned_skills_are_relative_unexcluded_and_win(self):
        """T9 · US-004, FR-10"""
        shadow = self.skills("core")[0]
        repo = self.make_repo({
            "harness/skills/own-skill/SKILL.md": "---\nname: own-skill\n---\n",
            f"harness/skills/{shadow}/SKILL.md": f"---\nname: {shadow}\n---\n"})
        _, out = self.build(repo, "core")
        self.assertEqual(os.readlink(repo / ".agents/skills/own-skill"),
                         "../../harness/skills/own-skill")
        self.assertEqual(os.readlink(repo / ".claude/skills/own-skill"),
                         "../../.agents/skills/own-skill")
        self.assertEqual(os.readlink(repo / f".agents/skills/{shadow}"),
                         f"../../harness/skills/{shadow}")
        text = self.exclude_text(repo)
        self.assertNotIn("own-skill", text)
        self.assertNotIn(f"/.agents/skills/{shadow}\n", text)
        self.assertIn(f"warn  .agents/skills/{shadow}", out)
        self.assertIn("wins over the base skill", out)
        # Another base skill is still linked from the kit.
        other = self.skills("core")[1]
        self.assertIn("/core/skills/", os.readlink(repo / f".agents/skills/{other}"))

    def test_T10_two_layers_union_without_duplicates(self):
        """T10 · FR-3"""
        core, both = self.skills("core"), self.skills("core", "enonic")
        self.assertEqual(len(both), len(set(both)))
        self.assertTrue(set(core) < set(both))
        extra = min(set(both) - set(core))
        repo = self.make_repo()
        self.build(repo, "core", "enonic")
        self.assertTrue((repo / ".agents/skills" / extra).is_dir())
        linked = sorted(p.name for p in (repo / ".agents/skills").iterdir())
        self.assertEqual(linked, sorted(both))

    def test_T20_dropping_a_layer_prunes_only_what_the_build_made(self):
        both, core = self.skills("core", "enonic"), self.skills("core")
        extra = min(set(both) - set(core))
        repo = self.make_repo()
        self.build(repo, "core", "enonic")
        foreign = repo / ".agents/skills/foreign"
        foreign.symlink_to("/tmp")
        self.build(repo, "core")
        self.assertFalse(os.path.lexists(repo / ".agents/skills" / extra))
        self.assertFalse(os.path.lexists(repo / ".claude/skills" / extra))
        self.assertTrue(foreign.is_symlink())
        self.assertEqual(self.porcelain(repo).count("foreign"), 1)

    def test_T21_a_linked_guard_dir_is_never_written_through(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        repo = self.make_repo()
        (repo / ".claude").symlink_to(outside)
        _, out = self.build(repo, "core")
        self.assertEqual(list(outside.iterdir()), [])
        self.assertIn("warn  .claude/skills/", out)
        self.assertTrue((repo / ".agents/skills").is_dir())

    def test_T22_foreign_real_directory_is_skipped_with_its_claude_link(self):
        name = self.skills("core")[0]
        repo = self.make_repo()
        (repo / ".agents/skills" / name).mkdir(parents=True)
        (repo / ".agents/skills" / name / "SKILL.md").write_text("mine\n")
        _, out = self.build(repo, "core")
        self.assertIn(f"warn  .agents/skills/{name}", out)
        self.assertEqual((repo / ".agents/skills" / name / "SKILL.md").read_text(), "mine\n")
        self.assertFalse(os.path.lexists(repo / ".claude/skills" / name))


class ErrorTests(ProjectCase):
    def test_T11_bad_input_raises_with_a_fix(self):
        """T11 · FR-2, FR-4, FR-7"""
        repo = self.make_repo()
        with self.assertRaises(DevkitError) as caught:
            self.build(repo, "nope")
        self.assertIn("no flavor or profile type named 'nope'", str(caught.exception))
        self.assertIn("core", caught.exception.fix)

        for text in ("not json", '{"schema": 2, "layers": ["core"]}',
                     '{"schema": 1, "layers": []}', '{"schema": 1, "layers": [3]}',
                     '{"schema": 1}', '{"schema": 1, "layers": ["../core"]}', "[]"):
            with self.subTest(text=text):
                cfg = self.tmp / "bad.json"
                cfg.write_text(text)
                with self.assertRaises(DevkitError):
                    self.build(repo, config=str(cfg))
        with self.assertRaises(DevkitError) as caught:
            self.build(repo, config=str(self.tmp / "missing.json"))
        self.assertIn("init", caught.exception.fix)

        with self.assertRaises(DevkitError) as caught:
            self.build(self.tmp)
        self.assertIn("git work tree", str(caught.exception))

        empty_home = self.tmp / "empty-home"
        empty_home.mkdir()
        self.use_home(empty_home)
        with self.assertRaises(DevkitError) as caught:
            self.build(repo, "core")
        self.assertIn("no installed kit", str(caught.exception))
        self.assertIn("install.py", caught.exception.fix)
        self.assertEqual(snapshot(empty_home), {})

    def test_T11b_a_tracked_stamp_path_refuses_the_build(self):
        repo = self.make_repo({".devkit-project.json": "{}\n"})
        with self.assertRaises(DevkitError):
            self.build(repo, "core")


class StatusTests(ProjectCase):
    def _kit_copy(self) -> Path:
        """A private copy of the kit home, installed as the project's home."""
        home = self.tmp / "home2"
        shutil.copytree(MASTER_HOME, home, symlinks=True)
        self.use_home(home)
        return home

    def _install_next_release(self, home: Path, drop: str | None) -> None:
        """Install and flip to a release that differs by one skill or one file."""
        src = self.tmp / "payload2"
        shutil.copytree(kithome.current_release(home), src, symlinks=True)
        if drop:
            shutil.rmtree(src / "core" / "skills" / drop)
        else:
            (src / "core" / "zz-extra.txt").write_text("x\n")
        files = kithome.payload_files(src)
        digest = kithome.payload_digest(src, files)
        release = kithome.install_release(src, home, files, digest, {"commit": "t"})
        kithome.flip_current(home, release)

    def test_T12_status_reports_drift_and_breakage(self):
        """T12 · US-005, FR-12"""
        repo = self.make_repo()
        self.build(repo, "core")
        rc, out = self.status(repo, config=str(self.tmp / "project.json"))
        self.assertEqual((rc, out.strip().splitlines()[-1]), (0, "ok"))
        self.assertIn("built from kit release", out)

        name = self.skills("core")[0]
        (repo / ".claude/skills" / name).unlink()
        rc, out = self.status(repo, config=str(self.tmp / "project.json"))
        self.assertEqual(rc, 1)
        self.assertIn(f".claude/skills/{name}", out)
        self.build(repo, "core")
        self.assertEqual(self.status(repo, config=str(self.tmp / "project.json"))[0], 0)

        (repo / ".agents/skills" / name).unlink()
        (repo / ".agents/skills" / name).symlink_to(self.tmp / "gone")
        rc, out = self.status(repo, config=str(self.tmp / "project.json"))
        self.assertEqual(rc, 1)
        self.assertIn(f"broken .agents/skills/{name}", out)

    def test_T12b_status_of_an_unbuilt_repo_is_a_failure(self):
        rc, out = self.status(self.make_repo())
        self.assertEqual(rc, 1)
        self.assertIn("not built", out)

    def test_T12c_a_release_with_a_different_skill_set_is_drift(self):
        home = self._kit_copy()
        repo = self.make_repo()
        self.build(repo, "core")
        dropped = self.skills("core")[-1]
        self._install_next_release(home, drop=dropped)
        rc, out = self.status(repo, config=str(self.tmp / "project.json"))
        self.assertEqual(rc, 1)
        self.assertIn(f"prune  .agents/skills/{dropped}", out)

    def test_T12d_a_release_with_the_same_skills_is_informational(self):
        home = self._kit_copy()
        repo = self.make_repo()
        self.build(repo, "core")
        self._install_next_release(home, drop=None)
        rc, out = self.status(repo, config=str(self.tmp / "project.json"))
        self.assertEqual(rc, 0, out)
        self.assertIn("informational", out)

    def test_T13_status_warns_about_a_profile_duplicate(self):
        """T13 · FR-12"""
        repo = self.make_repo()
        self.build(repo, "core")
        name = self.skills("core")[0]
        agents_home = self.tmp / "profile-home"
        (agents_home / "skills" / name).mkdir(parents=True)
        with mock.patch.dict(os.environ, {"AGENTS_HOME": str(agents_home),
                                          "DEVKIT_PROFILE": "enonic"}):
            rc, out = self.status(repo, config=str(self.tmp / "project.json"))
        self.assertEqual(rc, 0)
        self.assertIn(f"warn  skill {name}", out)
        self.assertIn("enonic", out)


class CleanTests(ProjectCase):
    def test_T14_clean_removes_only_what_the_build_made(self):
        """T14 · US-005, FR-14"""
        repo = self.make_repo({
            "harness/AGENTS.md": "# ours\n",
            "harness/skills/own-skill/SKILL.md": "---\nname: own-skill\n---\n"})
        self.build(repo, "core")
        names = self.skills("core")
        changed = names[0]
        (repo / ".claude/skills" / changed).unlink()
        (repo / ".claude/skills" / changed).symlink_to("/tmp")

        before = snapshot(repo)
        rc, out = self.clean(repo, apply=False)
        self.assertEqual((rc, snapshot(repo)), (0, before))
        self.assertIn("Dry run", out)

        rc, out = self.clean(repo)
        self.assertEqual(rc, 0)
        self.assertIn(f"warn  .claude/skills/{changed}", out)
        self.assertEqual(os.readlink(repo / ".claude/skills" / changed), "/tmp")
        for name in names:
            self.assertFalse(os.path.lexists(repo / ".agents/skills" / name))
        self.assertTrue(os.path.lexists(repo / ".agents/skills/own-skill"))
        self.assertTrue(os.path.lexists(repo / ".claude/skills/own-skill"))
        for rel in ("AGENTS.md", "CLAUDE.md", ".devkit-project.json"):
            self.assertFalse(os.path.lexists(repo / rel), rel)
        self.assertNotIn("devkit project", self.exclude_text(repo))
        self.assertEqual((repo / "harness/AGENTS.md").read_text(), "# ours\n")

    def test_T14b_clean_returns_a_plain_repo_to_its_prior_state(self):
        repo = self.make_repo()
        before = {k: v[:2] for k, v in snapshot(repo).items() if not k.startswith(".git/")}
        exclude_before = project.exclude_path(repo).read_text()
        self.build(repo, "core")
        self.clean(repo)
        after = {k: v[:2] for k, v in snapshot(repo).items() if not k.startswith(".git/")}
        self.assertEqual(after, before)
        self.assertEqual(project.exclude_path(repo).read_text(), exclude_before)
        self.assertFalse((repo / ".agents").exists())
        self.assertFalse((repo / ".claude").exists())

    def test_T14c_clean_without_a_stamp_does_nothing(self):
        repo = self.make_repo()
        rc, out = self.clean(repo)
        self.assertEqual(rc, 0)
        self.assertIn("nothing to clean", out)

    def test_T14d_clean_leaves_a_tracked_path_alone(self):
        repo = self.make_repo()
        self.build(repo, "core")
        name = self.skills("core")[0]
        self.git(repo, "add", "-f", f".claude/skills/{name}")
        self.git(repo, "commit", "-q", "-m", "track one")
        _, out = self.clean(repo)
        self.assertIn(f"warn  .claude/skills/{name}: tracked", out)
        self.assertTrue((repo / ".claude/skills" / name).is_symlink())


class WorktreeTests(ProjectCase):
    def test_T19_linked_worktrees_keep_separate_exclude_blocks(self):
        """T19 · FR-8"""
        repo = self.make_repo()
        wt = self.tmp / "wt"
        self.git(repo, "worktree", "add", "-q", str(wt), "-b", "feature")
        self.build(repo, "core")
        self.build(wt, "core")
        text = self.exclude_text(repo)
        self.assertIn("# >>> devkit project main >>>", text)
        self.assertIn("# >>> devkit project worktree wt >>>", text)
        self.assertEqual(project.exclude_path(wt), project.exclude_path(repo))
        self.assertEqual(self.porcelain(repo), "")
        self.assertEqual(self.porcelain(wt), "")

        self.clean(wt)
        text = self.exclude_text(repo)
        self.assertIn("# >>> devkit project main >>>", text)
        self.assertNotIn("worktree wt", text)
        self.assertEqual(self.porcelain(repo), "")
        self.assertEqual(self.status(repo, config=str(self.tmp / "project.json"))[0], 0)


class HomeSafetyTests(ProjectCase):
    def test_T15_no_command_writes_under_the_home(self):
        """T15 · FR-15"""
        repo = self.make_repo({"harness/AGENTS.md": "# ours\n"})
        before = snapshot(MASTER_HOME)
        self.call(project.cmd_init, repo, layer=["core"], force=False)
        self.build(repo, "core", rules=True)
        self.build(repo, "core", apply=False)
        self.status(repo, config=str(self.tmp / "project.json"))
        self.clean(repo)
        self.assertEqual(snapshot(MASTER_HOME), before)


class InitTests(ProjectCase):
    def test_T16_init_writes_a_valid_config(self):
        """T16 · FR-13"""
        repo = self.make_repo()
        rc, out = self.call(project.cmd_init, repo, layer=["core", "enonic", "core"],
                            force=False, apply=False)
        self.assertEqual(rc, 0)
        self.assertFalse((repo / "harness/project.json").exists())
        self.assertIn("Dry run", out)

        self.call(project.cmd_init, repo, layer=["core", "enonic", "core"], force=False)
        data = json.loads((repo / "harness/project.json").read_text())
        self.assertEqual(data, {"schema": 1, "layers": ["core", "enonic"]})
        self.assertEqual(project.load_config(repo).layers, ("core", "enonic"))

        with self.assertRaises(DevkitError) as caught:
            self.call(project.cmd_init, repo, layer=["core"], force=False)
        self.assertIn("--force", caught.exception.fix)
        self.call(project.cmd_init, repo, layer=["php"], force=True)
        self.assertEqual(project.load_config(repo).layers, ("php",))

    def test_T16b_init_validates_layers_against_the_installed_kit(self):
        repo = self.make_repo()
        with self.assertRaises(DevkitError) as caught:
            self.call(project.cmd_init, repo, layer=["nope"], force=False)
        self.assertIn("core", caught.exception.fix)
        with self.assertRaises(DevkitError):
            self.call(project.cmd_init, repo, layer=None, force=False)
        self.assertFalse((repo / "harness").exists())

    def test_T16c_build_reads_the_config_init_wrote(self):
        repo = self.make_repo()
        self.call(project.cmd_init, repo, layer=["core"], force=False)
        rc, _ = self.call(project.cmd_build, repo, config=None, rules=False)
        self.assertEqual(rc, 0)
        self.assertTrue((repo / ".agents/skills").is_dir())


class ContractTests(ProjectCase):
    def test_T17_help_contract(self):
        """T17 · FR-1"""
        bare, helped = run_devkit("project"), run_devkit("project", "--help")
        self.assertEqual(bare.returncode, 0, bare.stderr)
        self.assertEqual(bare.stdout, helped.stdout)
        for command in ("init", "build", "status", "clean", "flavors"):
            self.assertIn(command, bare.stdout)
        for command in ("init", "build", "clean"):
            self.assertIn("Dry run without --apply", run_devkit("project", command, "-h").stdout)
        bad = run_devkit("project", "build", "--nope")
        self.assertEqual(bad.returncode, 2)
        self.assertIn("usage:", bad.stderr)
        self.assertEqual(run_devkit("project", "--nope").returncode, 2)

    def test_T18_stamp_holds_no_home_path_and_lint_passes(self):
        """T18 · FR-11"""
        repo = self.make_repo()
        self.build(repo, "core", rules=True)
        text = (repo / ".devkit-project.json").read_text()
        stamp = json.loads(text)
        self.assertNotIn(str(self.home), text)
        self.assertNotIn("/home/", text)
        self.assertEqual(stamp["schema"], 1)
        self.assertEqual(stamp["layers"], ["core"])
        self.assertTrue(stamp["rules"] is True)
        self.assertEqual(stamp["release"], kithome.read_stamp(self.kit_root)["release_id"])
        self.assertIn(f".agents/skills/{self.skills('core')[0]}", stamp["entries"])
        existing = [p for p in ("devkit_cli/project.py", "tests/test_project.py",
                                "docs/project.md") if (REPO / p).exists()]
        self.assertEqual(run_devkit("lint-paths", *existing).returncode, 0)


class FlavorTests(ProjectCase):
    XP7_ONLY = frozenset({"develop-xp7-backend", "develop-react4xp-v5",
                          "develop-react4xp-v6", "apply-react4xp-practices"})
    XP8_ONLY = frozenset({"develop-xp8", "develop-react4xp-v7"})

    def repo_flavor(self, repo: Path, name: str, **body) -> Path:
        path = repo / "harness/flavors" / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"name": name, **body}))
        return path

    def refusal(self, repo: Path, *layers: str) -> DevkitError:
        with self.assertRaises(DevkitError) as caught:
            self.build(repo, *layers)
        return caught.exception

    def test_T23_enonic_flavors_split_by_xp_version(self):
        """T23 · US-005"""
        core = set(self.skills("core"))
        base = set(flavors.expand("enonic-base", *self._cat()).skills)
        for layer, own, other in (("enonic-xp8", self.XP8_ONLY, self.XP7_ONLY),
                                  ("enonic-xp7", self.XP7_ONLY, self.XP8_ONLY)):
            with self.subTest(layer=layer):
                repo = self.make_repo(name=layer)
                self.build(repo, layer)
                linked = {p.name for p in (repo / ".agents/skills").iterdir()}
                self.assertEqual(linked, core | base | own)
                self.assertFalse(linked & other)

    def _cat(self):
        return flavors.catalog(self.kit_root)[0], self.kit_root

    def test_T24_repo_flavor_builds_overrides_the_kit_and_drifts(self):
        """T24 · US-002, FR-9"""
        repo = self.make_repo()
        path = self.repo_flavor(repo, "mine", skills=["develop-xp8"])
        cfg = str(self.config("core", "mine", name="flavors.json"))
        rc, _ = self.build(repo, config=cfg)
        self.assertEqual(rc, 0)
        self.assertTrue((repo / ".agents/skills/develop-xp8").is_dir())
        self.assertEqual(self.status(repo, config=cfg)[0], 0)
        path.write_text(json.dumps({"name": "mine", "skills": ["develop-xp7-backend"]}))
        self.assertEqual(self.status(repo, config=cfg)[0], 1)
        rc, _ = self.call(project.cmd_init, repo, layer=["mine", "enonic-xp8"], force=False)
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads((repo / "harness/project.json").read_text())["layers"],
                         ["mine", "enonic-xp8"])

        self.repo_flavor(repo, "enonic-xp8", skills=["develop-xp8"])
        rc, out = self.build(repo, "enonic-xp8")
        self.assertIn("warn", out)
        self.assertIn("overrides the kit flavor", out)
        self.assertEqual(
            {p.name for p in (repo / ".agents/skills").iterdir()}, {"develop-xp8"})

    def test_T25_bad_flavors_are_refused_with_flavor_file_and_fix(self):
        """T25 · US-004"""
        cases = {
            "unknown-skill": {"skills": ["no-such-skill"]},
            "unknown-include": {"includes": ["no-such-layer"]},
            "unknown-key": {"skils": []},
            "bad-skill-name": {"skills": ["../x"]},
            "bad-exclude": {"exclude": ["develop-xp8"]},
            "loop-a": {"includes": ["loop-b"]},
        }
        for name, body in cases.items():
            with self.subTest(name=name):
                repo = self.make_repo(name=f"r-{name}")
                self.repo_flavor(repo, name, **body)
                if name == "loop-a":
                    self.repo_flavor(repo, "loop-b", includes=["loop-a"])
                err = self.refusal(repo, name)
                self.assertIn(name, str(err))
                self.assertIn(f"{name}.json", str(err))
                self.assertTrue(err.fix)
        repo = self.make_repo(name="r-rename")
        (repo / "harness/flavors").mkdir(parents=True)
        (repo / "harness/flavors/one.json").write_text('{"name": "two"}')
        err = self.refusal(repo, "one")
        self.assertIn("one.json", str(err))
        self.assertTrue(err.fix)
        repo = self.make_repo(name="r-profile")
        self.repo_flavor(repo, "enonic", skills=[])
        err = self.refusal(repo, "enonic")
        self.assertIn("profile type", str(err))
        self.assertIn("rename", err.fix)

    def test_T26_exclude_removes_and_a_later_layer_adds_back(self):
        """T26"""
        repo = self.make_repo()
        self.repo_flavor(repo, "lean", includes=["enonic-xp8"], exclude=["develop-react4xp-v7"])
        cat, _ = flavors.catalog(self.kit_root, repo)
        self.assertNotIn("develop-react4xp-v7", flavors.expand("lean", cat, self.kit_root).skills)
        resolved = project.resolve_layers(("lean",), self.kit_root, repo)
        self.assertNotIn("develop-react4xp-v7", resolved.skills)
        back = project.resolve_layers(("lean", "enonic-xp8"), self.kit_root, repo)
        self.assertIn("develop-react4xp-v7", back.skills)

    def test_T27_flavors_command_is_read_only(self):
        """T27 · FR-7"""
        repo = self.make_repo()
        self.repo_flavor(repo, "mine", skills=["develop-xp8"])
        before, repo_before = snapshot(MASTER_HOME), snapshot(repo)
        rc, out = self.call(project.cmd_flavors, repo, name=None)
        self.assertEqual(rc, 0)
        for name in ("enonic-xp7", "enonic-xp8", "mine", "core", "enonic"):
            self.assertIn(name, out)
        rc, out = self.call(project.cmd_flavors, repo, name="enonic-xp8")
        self.assertIn("develop-react4xp-v7", out)
        self.assertNotIn("develop-react4xp-v6", out)
        with self.assertRaises(DevkitError) as caught:
            self.call(project.cmd_flavors, repo, name="nope")
        self.assertIn("core", caught.exception.fix)
        outside = self.tmp / "not-a-repo"
        outside.mkdir()
        self.assertEqual(self.call(project.cmd_flavors, outside, name=None)[0], 0)
        self.assertEqual(snapshot(MASTER_HOME), before)
        self.assertEqual(snapshot(repo), repo_before)

    def test_T28_every_kit_flavor_is_valid(self):
        """T28"""
        cat, _ = flavors.catalog(REPO)
        self.assertTrue(cat)
        types = set(flavors.profile_types(REPO))
        for name, flavor in cat.items():
            with self.subTest(flavor=name):
                self.assertEqual(flavor.path.stem, name)
                self.assertNotIn(name, types)
                flavors.expand(name, cat, REPO)

    def test_T29_xp_flavors_cover_the_enonic_profile(self):
        """T29 · FR-10"""
        cat, _ = flavors.catalog(REPO)
        union = (set(flavors.expand("enonic-xp7", cat, REPO).skills)
                 | set(flavors.expand("enonic-xp8", cat, REPO).skills))
        enonic = set(flavors.expand("enonic", cat, REPO).skills)
        self.assertEqual(
            union, enonic,
            "enonic-xp7 and enonic-xp8 must together equal the enonic profile: "
            "classify the new skill into enonic-base, enonic-xp7 or enonic-xp8")

    def test_T30_profile_type_layers_resolve_as_before(self):
        """T30 · FR-6"""
        legacy: list[str] = []
        for layer in ("core", "enonic", "client"):
            for entry in manifest.load(layer, kit_root=self.kit_root).get("skills", []):
                leaf = manifest.layer_leaf(entry)
                if leaf and leaf not in legacy and (self.kit_root / "core/skills" / leaf).exists():
                    legacy.append(leaf)
        self.assertEqual(list(self.skills("core", "enonic", "client")), legacy)
        repo = self.make_repo()
        self.build(repo, "core", "enonic")
        stamp = json.loads((repo / ".devkit-project.json").read_text())
        self.assertEqual(sorted(stamp), ["agents_md", "agents_md_sha256", "entries",
                                         "layers", "release", "rules", "schema"])

    def test_T31_the_installed_kit_carries_flavors(self):
        """T31 · FR-1"""
        self.assertTrue((self.kit_root / "flavors/enonic-xp8.json").is_file())


class ProfileUnchangedTests(unittest.TestCase):
    def test_the_leaf_rule_is_shared_with_profile_projection(self):
        """US-006: the extracted helper keeps the rule `_link_layer` always had."""
        for entry, leaf in (("plain", "plain"), ("dir/**", "dir"), ("dir/", "dir"),
                            ("a/b/c.md", "a"), ("x**", "x")):
            self.assertEqual(manifest.layer_leaf(entry), leaf)


if __name__ == "__main__":
    unittest.main()
