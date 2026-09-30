---
id: how-to-apply-skill-portfolio-redesign
when_skills: [~/.agents/skills]
read: section
prose: caveman-lite
---

# How to apply skill-portfolio redesign phases

## Prerequisites

- Backup under `~/.agents/skills-backup-*/` (never `rm` skills — `mv` to displaced).
- Plan path: `~/.agents/plans/skill-portfolio-redesign.md` (legacy single file; new work uses `agentctl plan init --output ~/.agents/plans/<TASK-ID>`).

## Procedure

1. Phase 1 — write routing How-To under `~/.agents/kb/implementation/`.
2. Phase 2 — evolve `qa-validation` modes; displace `task-review` real dir; symlink `task-review` → `qa-validation`; copy Codex script + review template into `qa-validation/`.
3. Phase 3 — extend `run-plan` execution rules for implementation / evidence / validation delegation.
4. Phase 4 — merged into `lint-and-draft-commit-message` (lazy python / PHP / Enonic / generic stacks). Routing How-To names the one skill.
5. Phase 5 — move bulky upgrader “What changes” into `references/xp7-to-xp8-changes.md`.
6. Skip Phase 6–7 until user decides worklogs archive and audit date.

## Pitfalls

- Aliases are description/metadata only — do not recreate `review-task` / `impl-validate` directories.
- Do not recreate `lint-and-draft-enonic-commit-message` / `lint-and-draft-generic-commit-message` directories. Those names are aliases on the merged skill.
