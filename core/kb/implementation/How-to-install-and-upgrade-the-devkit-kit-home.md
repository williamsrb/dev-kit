---
id: how-to-install-and-upgrade-the-devkit-kit-home
when_skills: [run-plan, plan-implementation, validate-impl]
inputs: [devkit/devkit_cli/kithome.py, devkit/devkit_cli/kitsource.py, devkit/devkit_cli/update.py, devkit/devkit_cli/migrations.py]
outputs: [~/.local/share/devkit/releases, ~/.local/share/devkit/current]
stop_if: [running a devkit write command against the real home as a smoke test]
read: whole
prose: caveman-lite
---

# Install and upgrade the devkit kit home

devkit copies itself into `~/.local/share/devkit/` (`releases/<id>/` plus `current`). Profiles, `~/.local/bin/devkit` and the auth scripts link through `current`, never into the checkout.

## Procedure

1. Code that writes a path for later use names `kithome.current_link(home)`. `common.REPO_ROOT` resolves symlinks, so under an installed devkit it is a release directory.
2. `materialize` calls `kithome.ensure_installed(src, home, plan)` first. Apply: installs the payload if its digest is new, flips `current`, returns `current`. Dry run: installs nothing, returns `src`, links still print under `current`.
3. Upgrade: `devkit update apply --from <dir|git URL> --apply`. A directory is read as its working tree (payload allowlist only), so uncommitted work installs and is stamped dirty.
4. Existing install: `<checkout>/devkit profile sync <name> --apply`. `devkit doctor` / `update check` list `legacy:` profiles.

5. Hand-off: a tree installs itself. `kithome.run_as_incoming` runs the incoming `devkit.py` (`update stage-tree`, `update inspect-tree`, `update apply --staged`) with `DEVKIT_HANDOFF=1`, so the incoming `PAYLOAD` decides what ships. A tree whose `devkit_cli/update.py` lacks `HANDOFF_PROTOCOL` (read with `ast`) installs through the running code. Never import or exec the incoming tree in the parent.
6. `kithome.install_checked` runs `verify_release` (the release's own `PAYLOAD`, stamp digest, `payload_entries`) before `flip_current`; a bad release is removed and `current` stays.
7. Add a migration: append `Migration(name, needs, run, fix)` to `migrations.REGISTRY`. `needs(home)` is cheap, reads state only and returns reasons (empty = not needed); `run` must be safe to repeat; `fix` is the manual command. Doctor reports it; `update apply` and `profile sync` run it.

## Testing

- Never smoke-test with `./devkit profile create ... --apply`. It resolves the home from `pwd`, not `$HOME`, so a temp `HOME` is ignored and it writes the real profile, then asks root for forks.
- In tests call `materialize(profile, ["claude"], tmp_home, Plan(True), force=True, kit_root=<copy>)` and patch `Path.home` for code that calls it (see `_HomePatched` in `tests/test_devkit.py`).
- `kit_home()` honors `XDG_DATA_HOME` only under the given home, so an inherited value cannot redirect a test.
- Copy the payload with `kithome.copy_payload(REPO, dest, kithome.payload_files(REPO))`; `shutil.copytree` without `symlinks=True` turns the four `core/bin` links into file copies.

- Hand-off runs a real child that sees the temp home only through `HOME`/`XDG_*`. `_HomePatched` sets `DEVKIT_HANDOFF=1` so in-process patches still apply; a hand-off test removes it and passes the staging dir explicitly. Patch `kithome.PAYLOAD` only after building the source variant, or the variant loses the entry.

## Pitfalls

- The install stamp records the upgrade `source` (the checkout path). A "no checkout path under $HOME" scan must skip `.devkit-install.json`.
- A dry run reads the source tree, so existence checks must use the read root and link targets the `current` root.
- Rollback restores every instance backed up in the run and flips `current` back; backups are deleted only after the last instance succeeds.
