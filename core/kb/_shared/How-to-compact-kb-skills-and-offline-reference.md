---
id: how-to-compact-kb-skills-and-offline-reference
when_skills: []
inputs: [~/.agents/kb, ~/.agents/skills]
outputs: [smaller loaded-token path; llm-index.md]
stop_if: [rewriting skill name, fenced templates, or vendor API signatures]
read: whole
prose: caveman-lite
---

# Compact KB, skills, and offline-reference

Canonical tree is `~/.agents`. Harness homes (`~/.cursor`, `~/.claude`, `~/.codex`, `~/.claude_personal`) consume it via skill link-farms and `kb` → `~/.agents/kb`. Edit here only. Do not copy files into vendor folders.

Prose register: caveman-lite (`How-to-author-ai-howtos.md`). Stock Caveman full/ultra is forbidden.

The win is **loaded tokens per task**, not corpus size. Slices and indexes can grow byte count while a typical run opens a chooser instead of a 3–13k tutorial.

## Already done (2026-08-15) — do not redo

| Pass | What landed |
|------|-------------|
| Owned KB | Frontmatter + caveman-lite on hot-path How-tos; Context budget lives in `How-to-resolve-task-context.md`; XP-test JUnit/Jest split; worklog README then slack **or** jira; enonic-cli `commands.md` is section-read |
| Offline-reference | Sphinx/Godot chrome stripped; catalog `llm-index.md` is v2 chooser + nested folder indexes |
| Skills | Routing, not a corpus rewrite. `run-plan` uses testing/implementation `llm-index.md`. `apply-react4xp-practices` load table only. Descriptions lost install-provenance suffixes only |

Do **not** re-run `compact_owned_kb.py` `main()`. It splits worklog and adds frontmatter to files that lack `---`. A second run is messy even when it skips files that already have frontmatter.

## Guardrails (hard)

1. **Skill `name:`** — never change. One skill is one directory. `metadata.aliases` and `metadata.recommendedRole` are pipe-appended onto `description`; do not create alias directories.
2. **Templates** — never compact. Includes `templates.md`, `*template*`, `template/` trees, `assets/review-artifact-template.md`, `render-diff-patch/template.html`, fenced markdown templates inside `write-and-validate.md`.
3. **Skill `description:`** — compact only when trigger phrases stay intact. Do **not** run regex that stops at the first `.` (it turns `git.example.com/...` into `similar.example.com/...` leftover). `compact_skills.py` must **not** rewrite descriptions (provenance strip is disabled on purpose).
4. **Fenced code, tables, API signatures, issue keys, paths, commands** — exact. Never stylistically compress fences.
5. **Offline-reference API pages** — not How-tos. Do not rewrite `lib-content.md` / Godot class files into Procedure/Pitfalls. Compact chrome only. After a vendor **sync** script, chrome comes back — re-run `compact_offline_reference.py`, then regenerate that catalog’s index.
6. **`playwright-cli`** — vendor symlink into `node_modules`. Do not edit.
7. **Git** — leave files unstaged. No `git add` / `git reset` / `git push`.

## Scripts

All under `~/.agents/kb/_shared/scripts/`.

| Script | Safe to re-run? | Effect |
|--------|-----------------|--------|
| `compact_owned_kb.py` `main()` | **No** | Split + frontmatter (already applied) |
| `compact_owned_kb.write_llm_index(bucket)` | **Yes** | Rebuild owned `kb/<bucket>/llm-index.md` plus nested folder indexes |
| `llm_index.py` | **Yes** | Rebuild every owned + offline-reference v2 index |
| `compact_offline_reference.py` | Yes after a docs sync | Chrome strip + per-catalog v2 index. Idempotent on already-stripped pages |
| `compact_skills.py` | Yes for blank-line / standalone `Adapted from [url].` lines | Skips templates, scripts, `playwright-cli`. Does **not** rewrite `name` or `description` |

Regenerate all indexes:

```bash
python3 ~/.agents/kb/_shared/scripts/llm_index.py
```

Owned buckets only: `compact_owned_kb.write_llm_index(bucket)` still works (delegates to `llm_index.write_bucket_indexes`).

## Procedure (future run)

1. Read this file and `How-to-author-ai-howtos.md`. Open the canvas only if you need the last measured numbers: `~/.cursor/projects/home-leanon-agents/canvases/kb-compaction-plan.canvas.tsx`.
2. Inventory unique skill directories (`SKILL.md` under `~/.agents/skills`, skip alias-bound links — there should be none). Count tokens as `len(text)//4`. Report **loaded-first-file** deltas, not only corpus totals.
3. Owned How-tos: hand-edit leftover tutorial voice. Keep operational constraints (exclusions, deslop, evidence parent paths). New How-tos get frontmatter + caveman-lite from the start. Then `write_llm_index` for touched buckets.
4. Offline-reference: after `sync-*-docs.py` / Godot generators, run `compact_offline_reference.py`. Do not LLM-rewrite API catalogs. Fat pages (`lib-content.md`, Godot `class_*.md`) stay `read: section` via the index token column — refuse a whole-file read when tokens are thousands.
5. Skills: hand-compact workflow prose (duplicate Context-budget lists, “read every How-to”, See-X-for-best-practices lists). Point at KB How-tos / `llm-index.md` instead of inlining. Skip `name`, templates, and `playwright-cli`. Description edits are manual and must keep every trigger phrase plus the ` | recommendedRole:` / ` | aliases:` suffix.
6. Sanity: grep `similar.example.com` / `\[git\](https://git)` / missing `^name:` on unique `SKILL.md`. Confirm `run-plan` and `plan-task-evidence` still say llm-index, not “list every How-to”.
7. Update the canvas numbers if this run changed loaded-path tokens.

## What is still large on purpose

| Item | Why it stays |
|------|----------------|
| `kb/offline-reference/**` ~820k | Vendor API. Routing, not rewrite |
| `apply-react4xp-practices/references/*.md` ~12k | Binding conventions + XML examples |
| `plan-task-evidence/templates.md` | Load-bearing evidence/Jira template |
| `plan-implementation/references/write-and-validate.md` fenced template | Plan file shape |
| `enonic-cli/commands.md`, xp8 change catalogs | Open one `###` / one catalog |
| One-off project How-tos (NTF/AS/acme) | Operational evidence constraints |

## Pitfalls

- Re-running owned `main()` can re-split worklog or skip files that already have YAML and leave bodies un-lited. Prefer targeted edits + `write_llm_index`.
- Description regex that uses `[^\n.]+` after `from` eats `git.example.com`. If a description ends with `.example.com/group/enonic-skills.` or a body link became `[git](https://git)`, restore the full URL and the original trigger sentence.
- `write_llm_index` in `compact_owned_kb.py` used to skip `How-to-author-ai-howtos.md`, which left `kb/_shared/llm-index.md` empty. Index every owned `*.md` except `llm-index.md` itself.
- Hot-path QA files missed the ~3.0k target on purpose so Blocker / deslop / user-scope exclusions stayed intact. Do not fragment those.
- `when_skills` is not a loader. The index `skills` column keeps only canonical skill directory names (aliases resolved). Globs, URLs, and source paths are dropped. Do not rewrite How-to frontmatter just to clean it; the indexer ignores junk entries.
- Do not open a bucket `llm-index.md` and then every listed How-to. Folder rows are choosers. Open the matching project/topic index only.

## Sample data

| Item | Path |
|------|------|
| Authoring contract | `kb/_shared/How-to-author-ai-howtos.md` |
| This runbook | `kb/_shared/How-to-compact-kb-skills-and-offline-reference.md` |
| Owned compact helper | `kb/_shared/scripts/compact_owned_kb.py` |
| Index builder | `kb/_shared/scripts/llm_index.py` |
| Offline compact | `kb/_shared/scripts/compact_offline_reference.py` |
| Skills compact | `kb/_shared/scripts/compact_skills.py` |
| Last plan board | `~/.cursor/projects/home-leanon-agents/canvases/kb-compaction-plan.canvas.tsx` |
