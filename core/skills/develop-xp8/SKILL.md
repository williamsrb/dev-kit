---
name: develop-xp8
description: "Enonic XP 8 offline docs (platform, CMS, code kit). Use for XP 8 APIs, CMS, frontend integration, or when XP7 docs are the wrong version. | recommendedRole: implement | aliases: xp8-docs, enonic-xp8, develop-xp8-backend."
metadata:
  recommendedRole: implement
  aliases: xp8-docs, enonic-xp8, develop-xp8-backend
  cliDependencies:
    required: [agentctl, rg, python3]
    optional: [lychee]
---
## Local documentation search first

Run `agentctl docs search '<focused query>' --db ~/.agents/.cache/offline-docs.sqlite --json` when `agentctl` is available. If it is not on `PATH`, first try the installed helper at `~/.agents/bin/agentctl`.

If neither executable is available, do **not** browse the web as the first fallback. Route manually through the bundled offline index and open the returned local file:

```bash
rg -n -i '<focused terms>' ~/.agents/kb/offline-reference/xp8/**/llm-index.md
sed -n '1,240p' ~/.agents/kb/offline-reference/xp8/<path-from-index>
```

Only use the online documentation after the offline reference is missing, stale for the required version, or explicitly requested by the user. Record that reason in the response.

# Enonic XP 8 Documentation (offline)

## Documentation lookup order (prefer offline)

Docs live under `~/.agents/kb/offline-reference/xp8` (not under this skill).

1. Route via `~/.agents/kb/offline-reference/xp8/llm-index.md` (chooser: `cms` / `code` / `platform`).
2. Open the matching subtree `llm-index.md`, then the page under `~/.agents/kb/offline-reference/xp8/docs/{platform,cms,code}/stable/...`.
3. Online source of truth: https://developer.enonic.com/docs/platform/stable (and sibling `cms` / `code` trees).

## Shared `docs/*` base

Platform, CMS, and Code pages share offline paths under `docs/`. In-scope cross-links are stored as `docs/...md`.

## Refresh offline cache

From this skill directory (default output: `~/.agents/kb/offline-reference/xp8`):

```bash
python3 scripts/sync-xp8-docs.py
```

See `~/.agents/kb/offline-reference/xp8/README.md`.
