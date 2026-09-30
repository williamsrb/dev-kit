---
id: how-to-self-ignore-a-sidecar-extract-tree
when_skills: [run-plan, plan-implementation]
inputs: [a git checkout that must stay read-only]
outputs: [<source>/.extract/<run-id>/ ignored without editing source .gitignore]
stop_if: [editing source .gitignore or .git/info/exclude]
read: whole
prose: caveman-lite
---

# Self-ignore a sidecar extract tree

Default extract output is `<source>/.extract/<run-id>/`. The kit must not
edit the source `.gitignore` or `.git/`. `git check-ignore .extract/` often
matches nothing in a legacy repo.

## Procedure

1. Write `<source>/.extract/.gitignore` with a single pattern: `*`.
2. Keep run artifacts under `.extract/<run-id>/`, not at the source root.
3. `promote` (later slice) is the only copy into the source tree.
4. In tests: copy the fixture to a temp dir, `git init` + commit, run
   `--apply`, then assert `git status --porcelain` is empty. Do not let the
   sidecar land in the kit tree.

## Pitfalls

- Putting `.extract/` only in the *kit* `.gitignore` does not protect a
  *source* checkout the operator points `--source` at.
- `*` inside `.extract/.gitignore` also ignores that gitignore file. Git
  still reads it when walking the directory; status stays clean.
- Dry-run must not create `.extract/` at all. `--apply` is the first write.
