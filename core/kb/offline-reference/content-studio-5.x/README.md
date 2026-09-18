# Offline Content Studio 5.x Docs (LLM-dense)

Cascade snapshots for AI lookup only (not human-oriented).

| Seed | Offline tree |
| --- | --- |
| https://developer.enonic.com/docs/content-studio/5.x | `docs/content-studio/5.x/**` |

## Format

- LLM-dense markdown (`format:llm-dense content-studio-5.x`)
- Routing: [`llm-index.md`](llm-index.md) — matching page + heading only (v2: topic + keywords)
- Listing: [`index.md`](index.md)

## Refresh

```bash
python3 ~/.agents/kb/offline-reference/scripts/sync-content-studio-docs.py --channel 5.x
```
