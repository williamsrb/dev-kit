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

Canonical tree is `~/.agents`. Harness homes (`~/.cursor`, `~/.claude`, `~/.codex`, `~/.agents-profiles/<profile>/<vendor>`) consume it via skill link-farms and `kb` → `~/.agents/kb`. Edit here only. Do not copy files into vendor folders.

Prose register: caveman-lite (`How-to-author-ai-howtos.md`). Stock Caveman full/ultra is forbidden.

The win is **loaded tokens per task**, not corpus size. Slices and indexes can grow byte count while a typical run opens a chooser instead of a 3–13k tutorial.

## Already done (2026-08-15) — do not redo

| Pass | What landed |
|------|-------------|
| Owned KB | Frontmatter + caveman-lite on hot-path How-tos; Context budget lives in `How-to-resolve-task-context.md`; persistent evidence How-to (no disposable-content tree); XP-test JUnit/Jest split; worklog README then slack **or** jira; enonic-cli `commands.md` is section-read |
| Offline-reference | Sphinx/Godot chrome and wrapper sentences stripped; each catalog `llm-index.md` is `path<TAB>tokens<TAB>keywords` |
| Skills | Routing, not a corpus rewrite. `run-plan` uses testing/implementation `llm-index.md`. `apply-react4xp-practices` load table only. Descriptions lost install-provenance suffixes only |
| Lazy-load split (2026-09-28) | Fat `SKILL.md` routers (`graphify`, `humanize-text`, `plan-task-evidence`, `run-plan`). Catalog How-tos split by family (`enonic-cli/*.md`, `xp7-to-xp8-upgrade/changes-*.md`, `schemes-*.md`). `agentctl` groups extracted to siblings + `agentctl_common.py`. Sequential QA How-tos and autonomy criteria left whole |
| Lint merge (2026-09-30) | `lint-and-draft-commit-message` router + `references/{python,php,enonic,generic}.md`. Old enonic/generic skill dirs removed; names kept as aliases |
| Caveman-lite pilots (2026-10-21), task closed | Plan `~/.agents/plans/optimize-token-markdown-caveman/`. Pilot 1 (`response-formatting.mdc`, `plan-implementation/SKILL.md`, `plan-task-evidence/references/draft-and-evaluate.md`): prose 5,080 → 5,047 (0.6%). Pilot 2 (`plan-task-evidence/SKILL.md`, `run-plan/SKILL.md`, two untagged How-tos: `testing/client/How-to-reach-client-review-admin.md`, `validation/How-to-verify-structured-data-with-the-rich-results-test.md`): prose 12,438 → 12,281 after register rewrite (1.3%) → 12,191 after say-it-once (0.7% more; 2.0% total). Bar was 10%. Both pilots' edits were reverted; only the guard and baseline scripts stayed |
| `markdown-compression` pilot 3 (2026-10-21), task closed | Same 4 files as pilot 2, levers from `skills/markdown-compression/references/lossy-techniques.md` applied in order, whole-file tokens 14,662 → 13,857: within-file dedupe −5.3% (5.9–7.2% on the large `SKILL.md`, 2.5–3.7% on How-tos), prose-to-table **+0.8%** (headers and pipes cost more than terse prose), illustrative-example triage −0.2%, implied-knowledge deletion −0.8%; total −5.5%. The guard passed all stages with 100 duplicate/example waivers, all confirmed by the reviewer. The reviewer agent still found 1 LOSS (a merged `run-plan` step made Constraints/Non-Goals reading optional) and 10 RISKs (rules moved away from the step that uses them, a scope widened by a merge). Edits were not applied |

Do **not** re-run `compact_owned_kb.py` `main()`. It splits worklog and adds frontmatter to files that lack `---`. A second run is messy even when it skips files that already have frontmatter.

Do **not** start another prose-register pass (caveman-lite rewrite or say-it-once dedupe) over rules, skills or How-tos. The 2026-10-21 pilots showed the owned prose is already near caveman-lite: with every negation, limiter and number kept, a rewrite only drops filler. Say-it-once is capped because most repeated rules (Jira posting, screenshot consistency, comment backup) are `client` layer and cannot own a pointer, and a pointer is often as long as the sentence it replaces. To cut always-on tokens, change what loads (remove, merge or lazy-load a rule); that is a content decision for the operator, not compaction.

Within-file dedupe is the only lever that reached about 5%, and only on large `SKILL.md` files. It rewrites rules, so the guard is not enough: every file also needs an independent reviewer agent comparing original and result, plus a fix round. Do not convert terse prose to tables for size; it grows the file.

## Guardrails (hard)

1. **Skill `name:`** — never change. Unique skills are one inode with alias directories; edit one `SKILL.md`, aliases follow.
2. **Templates** — never compact. Includes `templates.md`, `*template*`, `template/` trees, `assets/review-artifact-template.md`, `render-diff-patch/template.html`, fenced markdown templates inside `write-and-validate.md`.
3. **Skill `description:`** — compact only when trigger phrases stay intact. Do **not** run regex that stops at the first `.` (it turns `git.example.com/...` into `similar.example.com/...` leftover). `compact_skills.py` must **not** rewrite descriptions (provenance strip is disabled on purpose).
4. **Fenced code, tables, API signatures, issue keys, paths, commands** — exact. Never stylistically compress fences.
5. **Offline-reference API pages** — not How-tos. Do not rewrite `lib-content.md` / Godot class files into Procedure/Pitfalls. Compact chrome only. After a vendor **sync** script, chrome comes back — re-run `compact_offline_reference.py`, then regenerate that catalog’s index.
6. **`playwright-cli`** — vendor symlink into `node_modules`. Do not edit.
7. **Git** — leave files unstaged. No `git add` / `git reset` / `git push`.

## Scripts

All under `~/.agents/kb/_shared/scripts/`.

The four scripts that write (`compact_owned_kb.py`, `compact_offline_reference.py`, `compact_skills.py`, `llm_index.py`) take `--apply`. Bare invocation and `--help` print the script doc and exit 0, so probing one never rewrites the KB (`apply_gate.py`). Do not pass `--apply` to `compact_owned_kb.py`.

| Script | Safe to re-run? | Effect |
|--------|-----------------|--------|
| `compact_owned_kb.py` `main()` | **No** | Split + frontmatter (already applied) |
| `llm_index.write_bucket_indexes(root)` | **Yes** | Rebuild v2 `llm-index.md` for one owned bucket or offline catalog |
| `compact_owned_kb.write_llm_index(bucket)` | No for new work | v1 columns. Do not use after 2026-09 |
| `compact_offline_reference.py` | Yes after a docs sync | Chrome strip + per-catalog index. Idempotent on already-stripped pages |
| `compact_skills.py` | Yes for blank-line / standalone `Adapted from [url].` lines | Skips templates, scripts, `playwright-cli`. Does **not** rewrite `name` or `description` |
| `compaction_baseline.py` | Yes | Writes in-scope pre-images and `baseline.json` (tokens per file split into prose, code, table, frontmatter) to `--out`. Run before any rewrite |
| `compaction_guard.py` | Yes | Compares files with their pre-images; fails on a lost fence, inline code, URL, link target, number, path, issue key, referenced heading, frontmatter item, or negation/limiter word. `--waivers` declares removed items: `owner` (a `rules/` source now carries it), `reason: duplicate` + `kept` (text still in the file), or `reason: example` + `note`. It cannot detect a weakened rule; pair it with a reviewer. Tests: `tests/test_compaction_guard.py` |

Regenerate owned indexes only. Call `write_bucket_indexes` per existing bucket. Do **not** call `write_owned_indexes()` from a tool that takes `--root`: it hardcodes `KB = Path("${HOME}/.agents/kb")` and walks `calibration`.

```bash
python3 - <<'PY'
from pathlib import Path
import importlib.util
spec = importlib.util.spec_from_file_location(
    "i", "${HOME}/.agents/kb/_shared/scripts/llm_index.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
root = Path("${HOME}/.agents/kb")
for name in ["_shared", "implementation", "testing", "validation", "worklog"]:
    bucket = root / name
    if bucket.is_dir():
        mod.write_bucket_indexes(bucket)
PY
```

## Procedure (future run)

1. Read this file and `How-to-author-ai-howtos.md`. Open the canvas only if you need the last measured numbers: `~/.cursor/projects/home-leanon-agents/canvases/kb-compaction-plan.canvas.tsx`.
2. Inventory with unique inodes for skills (`stat().st_ino` on `SKILL.md`). Count tokens as `len(text)//4`. Report **loaded-first-file** deltas, not only corpus totals.
3. Owned How-tos: hand-edit leftover tutorial voice. Keep operational constraints (exclusions, deslop, disposable parent paths). New How-tos get frontmatter + caveman-lite from the start. Then `write_llm_index` for touched buckets.
4. Offline-reference: after `sync-*-docs.py` / Godot generators, run `compact_offline_reference.py`. Do not LLM-rewrite API catalogs. Fat pages (`lib-content.md`, Godot `class_*.md`) stay `read: section` via the index token column — refuse a whole-file read when tokens are thousands.
5. Skills: hand-compact workflow prose (duplicate Context-budget lists, “read every How-to”, See-X-for-best-practices lists). Point at KB How-tos / `llm-index.md` instead of inlining. Skip `name`, templates, and `playwright-cli`. Description edits are manual and must keep every trigger phrase.
6. Sanity: grep `similar.example.com` / `\[git\](https://git)` / missing `^name:` on unique `SKILL.md`. Confirm disposable slices still linked from the index table. Confirm `run-plan` and `plan-task-evidence` still say llm-index, not “list every How-to”.
7. Update the canvas numbers if this run changed loaded-path tokens.

## What is still large on purpose

| Item | Why it stays |
|------|----------------|
| `kb/offline-reference/**` ~820k | Vendor API. Routing, not rewrite |
| `apply-react4xp-practices/references/*.md` ~12k | Binding conventions + XML examples |
| `plan-task-evidence/templates.md` | Load-bearing evidence/Jira template |
| `plan-implementation/references/write-and-validate.md` fenced template | Plan file shape |
| `enonic-cli/commands.md`, xp8 change catalogs | Chooser + one family file (`project.md`, `changes-build-files.md`, …) |
| One-off project How-tos (client/AS/acme) | Operational evidence constraints |

## Pitfalls

- Re-running owned `main()` can re-split disposable/worklog or skip files that already have YAML and leave bodies un-lited. Prefer targeted edits + `write_llm_index`.
- Description regex that uses `[^\n.]+` after `from` eats `git.example.com`. If a description ends with `.example.com/group/enonic-skills.` or a body link became `[git](https://git)`, restore the full URL and the original trigger sentence.
- `write_llm_index` in `compact_owned_kb.py` used to skip `How-to-author-ai-howtos.md`, which left `kb/_shared/llm-index.md` empty. Index every owned `*.md` except `llm-index.md` itself.
- Hot-path QA files missed the ~3.0k target on purpose so Blocker / deslop / user-scope exclusions stayed intact. Do not fragment those.
- Skills that must **not** grow a KB read: `find-skills`, `tesseract-cli`, `diff-image`, `render-diff-patch`, `dsnote`, `read-figma`, `write-analyst-message`, `apply-react4xp-practices` (How stays in skill references).

## Sample data

| Item | Path |
|------|------|
| Authoring contract | `kb/_shared/How-to-author-ai-howtos.md` |
| This runbook | `kb/_shared/How-to-compact-kb-skills-and-offline-reference.md` |
| Owned compact helper | `kb/_shared/scripts/compact_owned_kb.py` |
| Offline compact | `kb/_shared/scripts/compact_offline_reference.py` |
| Skills compact | `kb/_shared/scripts/compact_skills.py` |
| Last plan board | `~/.cursor/projects/home-leanon-agents/canvases/kb-compaction-plan.canvas.tsx` |
