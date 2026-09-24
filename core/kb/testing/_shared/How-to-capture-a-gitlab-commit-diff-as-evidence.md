# How to capture a GitLab commit diff as evidence

**Scope:** `_shared`
**Applies to:** projects on `git.example.com`

## Prerequisites

- Storage state `~/.agents/.auth/git-<host>.json` (host match via `find-auth-storage.py --host https://git.example.com`).
- Spawned `playwright-<TASK-ID>` MCP with that state.

## Procedure

1. Navigate to `https://git.example.com/<group>/<project>/-/commit/<sha>`.
2. The diff loads async. `browser_wait_for` on a literal from the added line before inspecting the DOM.
3. The per-file block is `article.rd-diff-file` (inside `diff-file[data-testid="rd-diff-file"]`). Header carries path and `+N −M`. File stats: `[data-testid="diff-stats"]`.
4. `browser_take_screenshot` with `target: "article.rd-diff-file"` and `scale: "device"`. At a 1280 viewport, a one-hunk file gives about 656x244.
5. `filename` must sit under the MCP allowed roots (`~/.agents/.playwright-mcp/<TASK-ID>/` or the repo). Writing straight into `~/.agents/prds/<TASK-ID>/evidence/` is refused. Save there, then `cp`.

## Pitfalls

- Selectors from the old diff UI (`.diff-file`, `.file-holder`) match nothing on the current GitLab rapid-diffs view.
- A sign-in page means the state has expired. Treat it as a failed step.
