---
id: how-to-mirror-a-devkit-core-change-into-the-harness
when_skills: [run-plan, validate-impl]
inputs: [devkit checkout, ~/.agents, a kit commit SHA]
outputs: [~/.agents matching core/, green devkit export --check]
stop_if: [git apply --check fails, core/ edit is not in export-allowlist.json]
read: whole
prose: caveman-lite
---

# Mirror a devkit core change into the harness

`devkit export` copies `~/.agents` into the kit's `core/`, one way. When a change lands in `core/` first, the next export overwrites it unless `~/.agents` gets the same change. `core/` mirrors `~/.agents` path for path, so the kit commit applies as a patch.

## Procedure

1. Cut the patch from the kit commit, `core/` only: `git -C <kit> show <sha> --format= -- core/ > /tmp/core.patch`.
2. Dry-run it on the harness: `git -C ~/.agents apply -p2 --check -v /tmp/core.patch`. `-p2` strips `a/core/`.
3. Apply: `git -C ~/.agents apply -p2 /tmp/core.patch`. Leave it unstaged.
4. A patched `rules/agents.d/*` or `*.mdc` body means `rules/AGENTS.md` is stale. Run `python3 ~/.agents/bin/generate-agents-md.py --apply`, then `--check`.
5. Grep `~/.agents` for what the change removed. Files outside the export allowlist still carry it, and the patch never touched them.
6. From the kit, `./devkit export` (dry run) must list only new harness work, then `./devkit export --check` exits 0 after `--apply`.

## Pitfalls

- The allowlist excludes whole files or directories, never lines. Content the kit must not ship has to leave the upstream file. No allowlist entry can filter one mention out of a file the kit needs.
- A red `export --check` or `test_export_is_in_sync` right after a kit-only edit is this drift. Do not run `export --apply` to green it before step 3: that reverts the kit change.
- `--check` failing on a hunk means `~/.agents` diverged since the kit commit. Merge that file by hand. Do not force the patch.
- Someone else's in-flight edit to an exported file shows up in the same dry run. Name it; do not revert it.
