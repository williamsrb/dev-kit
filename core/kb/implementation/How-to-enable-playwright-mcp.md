---
id: how-to-enable-playwright-mcp
when_skills: [spawn-playwright-mcp, plan-task-evidence, run-plan, generate-worklogs]
read: section
prose: caveman-lite
---

# Enable on-demand Playwright MCP

Playwright MCP is parked. Do not register the catalog stub. Spawn one HTTP process per task id so parallel runs do not share a browser or `--output-dir`.

Evidence default: `plan-task-evidence` spawns `playwright-<TASK-ID>` after the auth map is ready, then hard-stops. `run-plan` is a **new** session that captures on that instance. After the run, `stop <TASK-ID>`.

Anything else (reboot, crash, ad-hoc MCP) → skill `spawn-playwright-mcp`. Do not re-run `plan-task-evidence` just to start the server.

```bash
python3 ~/.agents/mcp/playwright.py spawn <TASK-ID> --enable --storage-state ~/.agents/.auth/<env>.json
python3 ~/.agents/mcp/playwright.py revive          # dead ids after reboot
python3 ~/.agents/mcp/playwright.py revive --default  # empty registry → id default
# later, in a new chat
python3 ~/.agents/mcp/playwright.py stop <TASK-ID>
```

Each agent uses only `playwright-<id>` (`user-playwright-JOT-101` / `mcp__playwright-JOT-101__*`). A chat that started before spawn cannot see the new name.

`mcp/install.py register` skips `playwright` unless `--force`. Never `--force` that stub: it has no real port. `spawn --enable` also writes `playwright-<id>` into every devkit profile MCP file (`~/.agents-profiles/<name>/{cursor/mcp.json,claude/.claude.json,codex/config.toml}`) so an isolated profile session sees the instance.

## Playwright instances

Headless, `--isolated`, unique output dir `~/.agents/.playwright-mcp/<id>/`. Optional `--storage-state` is copied into that dir (mode 600) and applied as `contextOptions.storageState`.

### Procedure

1. **Planning** (`plan-task-evidence`) spawns the id after the auth map is ready. Pass `--storage-state` when a host-matched file exists. `--enable` writes HTTP `url` entries onto the vendor live files. Do not navigate.
2. **Reboot / missing MCP / not an evidence plan:** follow `spawn-playwright-mcp`. `list`, then `revive` (dead registry ids) or `spawn <id> --enable`. `--default` on revive only when the registry has nothing to revive (id `default`). Then **stop this chat**.
3. Open a **new** session for that id (`run-plan` for evidence). Do not reuse the spawn chat.
4. Capture on `playwright-<id>` only. Absolute screenshot paths under that instance's `output_dir`.
5. `stop` the id when the run ends. Output dirs stay on disk.

### Parallel batch

Five keys (JOT-101…JOT-105) → five processes, five ports, five output dirs, five MCP names. One shared stdio `playwright` is why Cursor, Claude, and Codex all fail this pattern.

Do not put five servers in a session that only needs one. Token cost is ~80 tool names per live instance.

### Pitfalls

- A new MCP name needs a vendor restart or a new chat. Enable-then-continue in the same transcript will not see `playwright-JOT-101`.
- `revive` always `--enable` (ports change after a reboot). It reuses `storage_state` from `instance.json` when the file still exists.
- Bind and register `localhost`, never `127.0.0.1`. `@playwright/mcp` 403s the numeric Host header (`Access is only allowed at localhost:<port>`), and vendors render that as "Needs authentication". The launcher now defaults to `localhost`. Do not set `allowedHosts` / `--allowed-hosts` to include `127.0.0.1` — that 403s every Host, including `localhost`. See `How-to-fix-playwright-mcp-needs-authentication.md` for the diagnose/respawn recipe if an old instance is still on `127.0.0.1`.
- `browser_set_storage_state` still enforces allowed roots. Prefer `--storage-state` at spawn. If you set state later, copy the file into the instance `output_dir`.
- Screenshot `filename` must be absolute.
- `--headed` / `--extension` are spawn flags only. There are no parked `playwright-headed` / `playwright-extension` servers. New logins: `npx playwright codegen --save-storage=…`.
- `--shared-browser-context` is never set.

## Slack (generate-worklogs only)

Parked MCP: `slack-workspace-leanon`. Parked plugins: Cursor marketplace Slack (`plugin-slack-slack`, plugin id `674`), Codex `slack@openai-curated` and `slack@claude-plugins-official`. Snippets: `~/.agents/.auth/mcp-on-demand/`.

### Procedure

1. Merge parked `slack-workspace-leanon` into the vendor live MCP file. Codex: move the nested `[mcp_servers.slack-workspace-leanon.http_headers]` table with it.
2. Cursor: enable the Slack marketplace plugin (Settings → Plugins), or restore plugin id `674` on `cursor.plugins.installedIds.*` as recorded in `cursor-slack-plugin.json`.
3. Codex: set `enabled = true` on `[plugins."slack@openai-curated"]` and `[plugins."slack@claude-plugins-official"]`.
4. Restart the vendor. Discover with pattern `slack`. Collect, then remove the MCP key and disable the plugins again.

Do not leave Slack live after the worklog run.

## graft MCP (optional)

Default is the `graft` CLI plus `graft.mdc`. The `graft` MCP server is parked. Merge it only when the operator wants host-native graft tools. Remove it after. `graft build` stays CLI-only.

## Other parked snippets

`browser-control` stays in `~/.agents/.auth/mcp-on-demand/`. Merge it only when the operator named that surface.
