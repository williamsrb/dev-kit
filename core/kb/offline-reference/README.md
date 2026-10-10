# Offline API / platform reference

LLM-dense documentation snapshots used by Cursor skills. Skills point here; they do not host the docs.

| Catalog | Path | Used by |
| --- | --- | --- |
| Enonic XP 7.x | `xp7/` | `develop-xp7-backend` (`xp7-backend`, …) |
| Enonic XP 8 / stable | `xp8/` | `develop-xp8` (`xp8-docs`, …) |
| React4XP stable / 7.x (XP 8 default) | `react4xp-stable/` | `develop-react4xp-v7` |
| React4XP 6.x (XP 7, new work) | `react4xp-6.x/` | `develop-react4xp-v6` |
| React4XP 5.x (XP 7, legacy maintenance) | `react4xp-5.x/` | `develop-react4xp-v5` |
| Content Studio stable (6.x) | `content-studio-stable/` | `plan-task-evidence` (CMS create/edit/publish evidence) |
| Content Studio 5.x | `content-studio-5.x/` | `plan-task-evidence` (XP7 / CS 5.x hosts) |
| Godot 4 — 2D | `godot-2d/` | `develop-godot-2d` |
| Godot 4 — 3D | `godot-3d/` | `develop-godot-3d` |

**React4XP routing:** stable/7.x → XP 8; 6.x → new XP 7 work; 5.x → XP 7 legacy maintenance only. 5.x and 6.x are XP 7 exclusive.

Route via each catalog’s `llm-index.md` (`path<TAB>tokens<TAB>topic<TAB>skills<TAB>keywords`). If that file is a chooser (rows ending in `llm-index.md`), open the matching subtree index next. Then open the matching page and heading. Do not load a whole library file (for example `lib-content.md`) just in case. After a docs sync, chrome-strip with `kb/_shared/scripts/compact_offline_reference.py` — see `kb/_shared/How-to-compact-kb-skills-and-offline-reference.md`.

Root: `~/.agents/kb/offline-reference/`

## Refresh React4XP

```bash
python3 ~/.agents/skills/develop-react4xp-v7/scripts/sync-react4xp-docs.py
python3 ~/.agents/skills/develop-react4xp-v6/scripts/sync-react4xp-docs.py
python3 ~/.agents/skills/develop-react4xp-v5/scripts/sync-react4xp-docs.py
```

## Refresh Content Studio

```bash
python3 ~/.agents/kb/offline-reference/scripts/sync-content-studio-docs.py --channel stable
python3 ~/.agents/kb/offline-reference/scripts/sync-content-studio-docs.py --channel 5.x
```
