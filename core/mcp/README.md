# MCP installers

Reusable fetch + register scripts for the user-level MCP servers that are
already configured on this machine. Extracted from the three agent vendors:

| Vendor | Home | How it stores MCP |
|--------|------|-------------------|
| Cursor | `~/.cursor` | `mcp.json` |
| Claude | `~/.claude` | `CLAUDE_CONFIG_DIR` + `claude mcp add-json -s user` |
| Codex | `~/.codex` | `codex mcp add` / `config.toml` |

Do **not** walk `~/.agents/local-vendor-folders/` — those are symlinks back to
the homes above.

`image-to-disk/` is a local server (already here). Everything else is a remote
HTTP endpoint, an `npx` package, or a binary/source tree under `~/.local`.

Playwright MCP is **not** a resident stdio server. Spawn isolated HTTP
instances with `playwright.py` (also `agentctl playwright`).

## Commands

```bash
python3 ~/.agents/mcp/install.py list
python3 ~/.agents/mcp/install.py fetch              # binaries / clone / npx cache
python3 ~/.agents/mcp/install.py register           # write vendor configs
python3 ~/.agents/mcp/install.py unregister playwright
python3 ~/.agents/mcp/install.py install gitlab --vendors cursor,claude
python3 ~/.agents/mcp/install.py register --dry-run
python3 ~/.agents/mcp/install.py register --force   # replace existing entries

python3 ~/.agents/mcp/playwright.py spawn TASK-101 TASK-102 --enable
python3 ~/.agents/mcp/playwright.py revive
python3 ~/.agents/mcp/playwright.py list
python3 ~/.agents/mcp/playwright.py stop --all
```

Default `register` **skips** a vendor that already has the server. Use
`--force` to remove+add (needed to change args). Codex has no JSON upsert —
`--force` is the only way to rewrite a Codex entry.

`register` also **skips parked** catalog names unless `--force`. Do not
`--force` register the Playwright stub; it has no live port.

## Secrets

This directory has **no tokens**. Register reads:

| File / env | Used by |
|------------|---------|
| `$AGENTS_HOME/.auth/gitlab-access-token.yaml` | `gitlab` via `bin/gitlab-mcp` (`access_token`, `gitlab_url`) |
| `~/.browser-control-mcp.env` | `browser-control` (`EXTENSION_SECRET`, `EXTENSION_PORT`) |
| `SLACK_MCP_CLIENT_ID` | Cursor Slack OAuth client id |
| `SLACK_MCP_TOKEN` | Claude/Codex Slack bearer (`codex` uses `--bearer-token-env-var`) |

If a browser-control env file is missing, register reuses whatever is already in that vendor's
config (so a re-run does not blank a working token). GitLab tokens stay in the auth yaml;
`gitlab-mcp` injects them at launch.

OAuth HTTP servers (`context7`, `atlassian-rovo-preview`) need a one-time login
in the vendor after register (`claude mcp login <name>`, `codex mcp login <name>`,
or Cursor's MCP auth prompt).

## Catalog vs current vendors

See `catalog.json`. Intentional gaps (do not “fix” by registering everywhere):

- Playwright — parked. HTTP instances via `mcp/playwright.py`; one process and
  `--output-dir` per task id. See `How-to-enable-playwright-mcp.md`.
- `image-to-disk` / `filesystem` — Claude only
- Codex `node_repl` — Desktop-bundled; skipped

Marketplace plugins that also expose MCP (`atlassian@claude-plugins-official`,
`slack@claude-plugins-official`) are **not** installed by this script.

## Fetch recipes

| Recipe | What it installs |
|--------|------------------|
| `gitlab-mcp-server` | GitHub release `v2.6.2` linux-amd64 → `~/.local/bin/gitlab-mcp-server` |
| `browser-control-mcp` | Clone + `npm install` + `npm run build` → `~/.local/src/browser-control-mcp` |
| `playwright-mcp` / `filesystem-mcp` | Warm the `npx` cache |
| `serena-agent` | `uv tool install -p 3.13 serena-agent` → `~/.local/bin/serena` |

Firefox still needs the Browser Control add-on; this script only builds the
MCP server side.

Serena starts with `--project-from-cwd` and a per-vendor `--context`
(`ide` for Cursor, `claude-code`, `codex`). Global config: `~/.serena/serena_config.yml`.
