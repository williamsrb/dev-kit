# Godot 4.7 offline docs

Version: 4.7 (docs branch `4.7`; no unpinned `stable` alias in page headers)
Source: crawl of https://docs.godotengine.org/en/4.7/
Branch evidence: title='Godot Docs – 4.7 branch — Godot Engine (4.7) documentation in English' doc_version='4.7'
Generated: 2026-10-30
Pages: 344, about 1147259 tokens (chars/4)
Used by: `develop-godot`

Layout: docs path with `.html` replaced by `.md`, for example `classes/class_tilemaplayer.md`, `tutorials/2d/using_tilemaps.md`. Route via `llm-index.md` (`path<TAB>tokens<TAB>topic<TAB>skills<TAB>keywords`). Class pages are catalogs: read by section, never whole.

Conversion notes:
- Main content only. Sphinx/RTD chrome, Previous/Next, user notes, version banners and images are dropped (image alt text kept when meaningful).
- Code fences carry the Sphinx language (`gdscript`, `ini`, `shell`, ...). Where a page shows GDScript and C# tabs, only GDScript is kept. A C#-only block with no GDScript twin stays.
- Links to pages outside this catalog, and same-page anchors, become plain text. Links to catalog pages are relative `.md` paths without fragments.
- Section `index` pages (pure toctrees) are excluded.
- Pages have no per-page date, so re-runs diff cleanly.

## Pages by folder

| Folder | Pages |
| --- | --- |
| `classes` | 119 |
| `getting_started/first_2d_game` | 7 |
| `getting_started/first_3d_game` | 10 |
| `getting_started/step_by_step` | 6 |
| `tutorials/2d` | 14 |
| `tutorials/3d` | 35 |
| `tutorials/animation` | 7 |
| `tutorials/audio` | 6 |
| `tutorials/best_practices` | 12 |
| `tutorials/editor` | 1 |
| `tutorials/export` | 7 |
| `tutorials/inputs` | 7 |
| `tutorials/io` | 5 |
| `tutorials/migrating` | 5 |
| `tutorials/navigation` | 18 |
| `tutorials/performance` | 5 |
| `tutorials/physics` | 18 |
| `tutorials/rendering` | 6 |
| `tutorials/scripting` | 31 |
| `tutorials/shaders` | 14 |
| `tutorials/ui` | 11 |

## Refresh

Needs `beautifulsoup4` (`bs4`) besides the stdlib. A source flag is required.

```bash
python3 ~/.agents/skills/develop-godot/scripts/sync-godot-docs.py --version 4.7 --crawl --cache-dir ~/.local/share/godot/docs-src/<date>/html
# or, from the official offline build:
python3 ~/.agents/skills/develop-godot/scripts/sync-godot-docs.py --version 4.7 --zip <godot-docs-html-stable.zip|url>
# then rebuild the search index over ALL catalogs (each run drops the table):
~/.agents/bin/agentctl docs index $(for d in ~/.agents/kb/offline-reference/*/; do n=$(basename $d); [ $n = scripts ] || echo --root ${d%/}; done) --db ~/.agents/.cache/offline-docs.sqlite
```

Do NOT run `compact_offline_reference.py` on this catalog: footers are stripped at conversion and it blanks the skills column of `llm-index.md`. If it was run, repair with `sync-godot-docs.py --reindex`.
