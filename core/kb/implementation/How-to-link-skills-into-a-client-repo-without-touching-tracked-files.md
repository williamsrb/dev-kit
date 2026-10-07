---
id: how-to-link-skills-into-a-client-repo-without-touching-tracked-files
when_skills: [run-plan, plan-implementation, validate-impl]
inputs: [devkit/devkit_cli/project.py, devkit/tests/test_project.py]
outputs: [untracked skill links, a managed .git/info/exclude block, a stamp]
stop_if: [running a project command with --apply against the real home or a real client repo as a smoke test]
read: whole
prose: caveman-lite
---

# Link skills into a client repo without touching tracked files

`devkit project build` (see `devkit/docs/project.md`) writes `.agents/skills/<n>`, `.claude/skills/<n>`, optional `AGENTS.md` + `CLAUDE.md` and a stamp, and hides them through `.git/info/exclude`. Rules that carry over to any command that writes generated paths into someone's checkout.

## Procedure

1. One `git ls-files -z -- <paths>` call with `git --literal-pathspecs` for every candidate. A returned path equal to or under the candidate counts as tracked (a tracked real directory shows as its files).
2. Skip, with `warn  <path>: <reason>`, anything tracked, any real file or directory, and any link the build does not own. A tracked link that already has the wanted target is satisfied, not a warning (a committed repo-owned link).
3. Own a link only when it is in the stamp or its target matches the build's pattern (`<kit>/current/core/skills/…`, `../../harness/skills/<n>`, `../../.agents/skills/<n>`, `AGENTS.md`). Prune and clean use the same test.
4. Guard `.agents`, `.agents/skills`, `.claude`, `.claude/skills`: if one is a link or a file, skip everything under it. Do not pass paths beyond it to `ls-files`.
5. Exclude entries: anchored `/path` lines in one block per worktree, `# >>> devkit project <main|worktree NAME> >>>`. `git rev-parse --git-path info/exclude` resolves to the common dir, shared by every linked worktree. Write the block before the links.
6. `AGENTS.md` only when neither it nor `CLAUDE.md` exists (tracked-but-deleted counts). Store its sha256 in the stamp so a later build can tell its own file from a hand edit.
7. Tests: one installed kit per module (`kithome.ensure_installed(REPO, tmp_home, Plan(True))`), a temp git repo per case, `privilege.refuse_root` patched to a namespace with `pw_dir`. Cases that flip `current` work on `shutil.copytree(home, symlinks=True)`.

## Pitfalls

- Base links name `<home>/.local/share/devkit/current`. A test that builds under one home and checks status under another sees every link as a relink. Build under the home you check with.
- The generated `AGENTS.md` from `generate-agents-md.py --stdout` is 606 lines for `core`, 712 with `client`. Keep it behind `--rules`; a profile already projects the rules.
- A scratch config dir with symlinked vendor credentials (to test user-level vs project-level skill precedence) is refused by the auto-mode classifier. Leave precedence "not verified" in the docs, do not work around it.
- Doctor on this machine reports the `personal` profile stale and legacy-linked; that is the profile's install commit, not a project-mode change.
