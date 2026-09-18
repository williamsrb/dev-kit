---
id: how-to-split-plans-into-lazy-loaded-folders
when_skills: [plan-implementation, plan-task-evidence, run-plan, validate-plan]
read: section
prose: caveman-lite
---

# Split plans into lazy-loaded folders

New plans live under `~/.agents/plans/<TASK-ID>/`. `plan.md` is the default entry. Companions load on demand. Unmigrated `{TASK-ID}.md` and `{TASK-ID}-evidence-plan.md` still resolve.

## Prerequisites

`agentctl` on PATH (`~/.agents/bin/agentctl`).

## Procedure

1. Scaffold: `agentctl plan init --kind implementation --issue KEY --output ~/.agents/plans/KEY`
2. Evidence companion: `agentctl plan init --kind evidence --issue KEY --output ~/.agents/plans/KEY` (adds `evidence.md`; does not wipe impl files unless `--force` on `plan.md`)
3. Look up: `agentctl plan resolve KEY` → `{entry, kind, layout, sections:[{name,file,bytes}]}`
4. Evidence lookup: `agentctl plan resolve KEY --kind evidence`
5. Validate: `agentctl plan validate ~/.agents/plans/KEY` (kind inferred) or pass `--kind`
6. Read with `agentctl markdown slice <companion> --sections …`. Do not `Read` the whole folder.

Implementation companions: `plan.md`, `requirements.md`, `tbd.md`, `implicit.md`, `implementation.md`, `validation.md`. Evidence adds `evidence.md`.

Kind comes from `plan resolve`, not from the filename.

## Pitfalls

- `--output FILE.md` still writes a single-file plan. Folder mode is any output path that does not end in `.md`.
- An index row in `plan.md` that names a missing file is a structural error.
- Do not migrate live in-flight single-file plans unless asked. Resolve falls back to them.
