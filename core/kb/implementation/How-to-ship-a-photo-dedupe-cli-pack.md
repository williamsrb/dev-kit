---
id: how-to-ship-a-photo-dedupe-cli-pack
when_skills: [run-plan]
inputs: [~/.agents/plans/photo-dedupe]
outputs: [Workspace/Personal/photo-dedupe pack + tests]
stop_if: [phase-2 live Photos UI mapping still TBD]
read: section
prose: caveman-lite
---

# Ship a photo-dedupe CLI pack for Grok Bot

Local Python CLI that hashes a Google Takeout / originals folder and writes a gated keep/drop plan. Not Enonic. Not Drive. Not a Chrome extension. Grok Bot unpacks a TAR and follows `PROMPT.md`.

## Scope

Phase 1: pack, OAuth PKCE identity, index/hash/cluster/plan, `apply --dry-run`. Phase 2 live Photos web UI stays stubbed until TBD mapping (local `dir:` ids → Photos UI targets) is answered.

## Prerequisites

Python 3.12+, Pillow. ImageMagick `compare` optional (SSIM corroboration). Working tree: `${HOME}/Workspace/Personal/photo-dedupe`. Do **not** put the pack under `~/.agents/skills/`.

## Procedure

1. Unpack root = folder with `PROMPT.md`, `scripts/`, `assets/`. Runtime `data/` (mode 700) or `$PHOTO_DEDUPE_DATA`.
2. CLI: `python3 scripts/photodedupe.py <auth|index|hash|cluster|plan|apply|pack>`. Exit 0 / 2 (usage-auth) / 3 (`--max-delete` exceeded). No `confirm` subcommand — corroboration is inside `plan`.
3. `index --root` walks images, skips `*.json` sidecars, no network fetch. `auth` is identity only (`openid` `email`); detect does not need a token.
4. Hashes: 64-bit dHash + pHash in Pillow (no numpy/`imagehash`). Store them as **16-char hex TEXT** in SQLite. SQLite INTEGER is signed 64-bit and overflows when the high bit is set.
5. `cluster --min-similarity 0.80` → Hamming ≤ 13. `confidence: auto` only Hamming ≤ 2 **and** corroboration (aspect, EXIF/stem/downsample, plus dHash or SSIM).
6. `pack` writes `PROMPT.md` + `scripts/` + `assets/` (example OAuth client + plan schema). Exclude `data/`, `tests/`, live `oauth-client.json`, tokens.
7. Tests: `python3 -m unittest tests.test_photodedupe -v` from the working tree. Mock the token endpoint. Never live Google.

## Pitfalls

- Photos Library API cannot list or delete the user library (2025-03-31). Do not call `mediaItems.list` / `search` / delete. Tokens are not Playwright cookies.
- Live `apply` without `data/tokens.json` exits 2. With a token, Phase 1 still returns not-implemented.
- Do not use Profile 9 “Williams” for this library. Do not install bulk-delete Chrome extensions.
- Pillow 12 deprecates `Image.getdata`; prefer `get_flattened_data` when present.
- `agentctl plan validate photo-dedupe` from `$HOME` looks for `~/photo-dedupe`. Validate the folder: `agentctl plan validate ~/.agents/plans/photo-dedupe`.
