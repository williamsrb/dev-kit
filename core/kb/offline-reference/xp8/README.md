# Offline XP 8.x Docs Cache (LLM-dense)

Cascade snapshots of Enonic **XP 8 / stable** documentation for AI lookup.

## client / allowlists

| Seed | Offline tree |
| --- | --- |
| https://developer.enonic.com/docs/platform/stable | `docs/platform/stable/**` |
| https://developer.enonic.com/docs/cms/stable | `docs/cms/stable/**` |
| https://developer.enonic.com/docs/code/stable | `docs/code/stable/**` |

Shared base for mutual refs: `docs/*` (in-scope links rewritten to `docs/...md`).

## Format

- LLM-dense markdown (`format:llm-dense xp:8.x`)
- Routing: [`llm-index.md`](llm-index.md) — chooser (`cms` / `code` / `platform`), then matching page + heading only. `lib-content.md` / `lib-node.md` are catalogs; do not read whole.
- Listing: [`index.md`](index.md)

## Refresh

From the skill directory:

```bash
python3 scripts/sync-xp8-docs.py
```

Optional:

```bash
python3 scripts/sync-xp8-docs.py --delay 0.1
python3 scripts/sync-xp8-docs.py --max-pages 20
```

Docs live at `~/.agents/kb/offline-reference/xp8/` (not under the skill).
