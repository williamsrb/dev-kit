---
id: how-to-keep-harness-git-lean
when_skills: [run-plan]
inputs: [~/.agents, ~/.claude, ~/.cursor, ~/.codex]
outputs: [lean .git, ignored bloat on disk]
stop_if: [remote exists and force-push is not authorized]
read: whole
prose: caveman-lite
---

# Keep harness git lean

Four local harness repos (`~/.agents`, `~/.claude`, `~/.cursor`, `~/.codex`) must track skill code, KB, rules, settings, and shared symlinks. They must **not** track backups, session archives, volatile runtime JSON, or heavy optional skill media. Files stay on disk; git only drops the index/history copies.

No remotes today. History rewrite is local-only. If a remote is added later, force-push is required and must be explicit.

## Scope

Untrack + ignore (keep on disk):

| Repo | Ignored bloat |
|------|----------------|
| `~/.codex` | `backups/` (session archives), `history.jsonl`, `installation_id`, `version.json`, `hooks.premigration/`, `skills/.system/`, `vendor_imports/skills-curated-cache.json`, `chrome-native-hosts-v2.json` |
| `~/.agents` | `bin/actionlint`, ppt-master `references/ai-image-comparison/`, `templates/sounds/`, `templates/icons/`, archify `examples/` + `test/`, `skills/render-diff-patch/diff2html-ui.min.js`. Already ignored: `prds/`, `plans/` (files and `{TASK-ID}/` folders), `history/`, `.packages/`, `.auth/`, caches, tmp |
| `~/.claude` | `.claude.json`, `.claude.json.backup`, `claude_settings_backup/`, `agents.premigration/`, `settings.json.premigration`, `settings.json.bak-*`, `history.jsonl`, `remote-settings.json`, `stats-cache.json`, `policy-limits.json` (`backups/` already ignored) |
| `~/.cursor` | `cli-config.json` |

`.claude.json` is disk-only after untrack. Live MCP server config and account metadata live there. Restore is the file on disk, not git. `settings.json` stays tracked.

Untrack a previously committed path with `git rm --cached` (or `-r --cached`); `test -e` immediately. `policy-limits.json`, `stats-cache.json`, and leftover `settings.json.bak-*` stay ignored on `~/.claude`.

Optional skill media is re-fetched with each skill’s `scripts/download_media.py`. Do not `git add` those directories again.

## Prerequisites

- Working tree clean, or stash unrelated dirty files first. `git filter-repo` refreshes the worktree.
- `git remote -v` empty, or operator authorized a force-push.
- `git-filter-repo` on PATH (`~/.local/bin/git-filter-repo`).
- Never `git rm` without `--cached` for these paths. Never `git reset`.

## Procedure

1. Append ignore rules before (or in the same commit as) the untrack. Cursor: the managed `*` / allowlist block stays byte-for-byte. Delete `!cli-config.json` from LOCAL HARNESS BLOCK, then add a later `cli-config.json` deny. Confirm with `git check-ignore -v cli-config.json` that a deny wins, not a `!` un-ignore.
2. `git rm --cached` (file) or `git rm -r --cached` (dir). `test -e` immediately. Stage only `.gitignore` + the cached-rm paths.
3. Rewrite: path file, one path per line, no `#` comments. Then:

```bash
git filter-repo --force --invert-paths --paths-from-file /tmp/untrack-<repo>.txt
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

4. Drop leftover non-commit refs if `git rev-list --objects --all` still lists purged paths. Codex/Cursor checkpoint refs under `refs/codex/turn-diffs/checkpoints/` can point at **trees**, not commits. `git filter-repo` skips them (`Unexpected object of type tree`). Delete with `git update-ref -d <ref>`, then expire + gc again. That is not `git reset`.
5. Verify: path exists on disk, absent from `git ls-files`, ignored (`git check-ignore -v`). Live `~/.agents/plans` and `prds` dirs still present. Sample Tier C paths still tracked.

## Pitfalls

- `git add -A` before ignore rules re-stages session archives and icons. Check `git check-ignore -v` first.
- `git rm` without `--cached` deletes harness data.
- filter-repo rewrites SHAs. After `reflog expire` + `gc --prune=now`, only a pre-rewrite copy can roll back.
- Tree-typed extra refs pin old blobs after a successful-looking filter-repo run. Inspect `git for-each-ref --format='%(objecttype) %(refname)'` before declaring the pack shrunk.
- Cursor `.git/cursor/` is vendor metadata; `git gc` does not remove it. Pack size (`git count-objects -vH`) is the git-history signal, not `du -sh .git` alone.
- Do not untrack skill code, KB, rules, `settings.json`, or shared symlinks.
- Do not split ignore rules per checkout of the same harness. A later `git add` on the other checkout will re-track the file. Keep one body; `git rm --cached` on the checkout that still has it in the index.
