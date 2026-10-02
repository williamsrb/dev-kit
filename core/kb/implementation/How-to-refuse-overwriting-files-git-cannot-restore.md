---
id: how-to-refuse-overwriting-files-git-cannot-restore
when_skills: [run-plan, plan-implementation]
inputs: [a CLI that copies files into a user checkout]
outputs: [a pre-write guard with a --force bypass]
stop_if: []
read: whole
prose: caveman-lite
---

# Refuse to overwrite files git cannot restore

Scope: any command that writes into someone's checkout on the first call (no
dry run), e.g. `extractkit promote`. Reference implementation:
`extract-kit/extractkit_cli/promote.py` (`_blocked`, `_porcelain_codes`).

## Rule

Existing destination blocks when git cannot bring it back:

- staged or unstaged change → `modified`
- untracked → `untracked`
- ignored → `ignored`
- source not in a work tree, or no `git` on PATH →
  `not in a git work tree`

Tracked + clean → overwrite (`git checkout -- f` restores it). Missing →
write. Any block → write nothing, list every blocked path, exit 1, fix =
same argv + `--force`.

## Procedure

1. Build the full copy list first. Check before the first write.
2. `git -C <source> rev-parse --show-toplevel`. Failure → every existing
   dest is `not in a git work tree`.
3. One call over existing dests, paths relative to the toplevel:

   ```bash
   git -C <top> status --porcelain=v1 -z --ignored=matching \
     --untracked-files=all -- <rel>...
   ```

4. Parse `-z` entries: `XY path`. `??` untracked, `!!` ignored, else
   modified. `R`/`C` entries carry an extra NUL-separated original path;
   skip it.
5. No entry for a dest → tracked and clean.

## Pitfalls

- Without `--untracked-files=all`, a file inside an untracked dir shows
  only as `?? dir/`. Also match entries ending in `/` as a prefix
  (ignored dirs still collapse).
- Resolve dest paths before `relative_to(toplevel)`: `/tmp` symlinks and
  `rev-parse` returns the real path.
- Partial writes (skip only blocked files) leave a half-promoted tree.
  Refuse the whole batch.
- `.bak` copies litter the checkout. The bypass is `--force`, not
  backups.
