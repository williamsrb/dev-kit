---
name: use-enonic-cli
description: "Enonic CLI (`enonic`): sandboxes, deploy, export/import, snapshots, cloud, admin. Use when running enonic commands or managing XP instances. | recommendedRole: follow | aliases: enonic-cli, enonic-command, xp-cli, enonic-sandbox-cli."
license: MIT
metadata:
  recommendedRole: follow
  aliases: enonic-cli, enonic-command, xp-cli, enonic-sandbox-cli
  author: enonic
  source: enonic/ai-enonic-marketplace@v0.3.1
  cli-version: "4.0.0"
  cliDependencies:
    required: [enonic]
    optional: [docker]
---
## Cursor IDE

Adapted from [enonic/ai-enonic-marketplace](https://github.com/enonic/ai-enonic-marketplace) v0.3.1. Run `enonic` via **Shell**.

## Knowledge base (mandatory How)

Before remote ops or unfamiliar commands, read:

| Topic | Path |
|-------|------|
| Index + patterns | `~/.agents/kb/implementation/enonic-cli/README.md` |
| Command/flag tables | `~/.agents/kb/implementation/enonic-cli/commands.md` — grep the matching `### enonic …` heading. Do not read the whole file. |
| Auth, env, ports, CI | `~/.agents/kb/implementation/enonic-cli/auth-and-env.md` |
| Multi-step recipes | `~/.agents/kb/implementation/enonic-cli/workflows.md` |

This skill owns the **critical rules** below. The KB owns catalogs and recipes — do not copy flag tables back here.

## Critical Rules

1. **Always use `-f` (force) flag.** Every `enonic` command that accepts `-f` must include it. This prevents interactive prompts that block automation. The only exception is `enonic cloud login` (browser-based OAuth).

2. **Local vs remote commands:**
   - **Local** (no auth): `project *` (except `install`), `sandbox *`, `create`, `dev`.
   - **Remote** (auth flags): `snapshot *`, `dump *`, `export`, `import`, `app *`, `repo *`, `cms *`, `system info`, `auditlog *`, `vacuum`.
   - `project install` is local build + remote install — auth required.
   - Maintenance (`latest`, `upgrade`, `uninstall`) manage the CLI itself.

3. **Management port is 4848, not 8080.** Never use 8080 for CLI remote operations.

4. **`.enonic` file** — `project create` links the project to a sandbox; `project deploy` / `dev` use it automatically.

5. **Command aliases:** `create`/`dev` shortcuts; `sbox`/`sb`, `i`, `ls`, `del`/`rm`, `up`, `cp` as documented in the KB command tables.

6. **XP 8 API format is the default (CLI 4.x).** For XP 7 instances add `--compat 7`. `--archive` on dump create/load is only effective in compat mode.

## When to load more

- Need exact flags → `commands.md`
- CI / service-account auth → `auth-and-env.md`
- Export/import/dump/sandbox recipes → `workflows.md`
