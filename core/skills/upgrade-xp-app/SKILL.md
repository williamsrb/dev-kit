---
name: upgrade-xp-app
description: "Migrate an Enonic XP 7 app to XP 8 (YAML descriptors, Gradle plugin 4.x, xp8migrator). Not for new XP 8 apps or XP 7 minor bumps. Use only when the operator or an orchestrator names this skill. | recommendedRole: task-owner | aliases: xp-app-upgrader, xp8-upgrade, xp-upgrader, migrate-xp7-to-xp8."
license: MIT
metadata:
  recommendedRole: task-owner
  aliases: xp-app-upgrader, xp8-upgrade, xp-upgrader, migrate-xp7-to-xp8
  author: enonic
  source: enonic/ai-enonic-marketplace@v0.3.1
  xp-version: "7.x → 8.x"
  cliDependencies:
    required: [agentctl, git, rg, python3, enonic, xmllint, xmlstarlet, yq]
    optional: [docker]
---
## Local deterministic first

Run `agentctl repo detect --cwd <repo> --json` before reading build files. Use XML/YAML CLIs for descriptor checks and return file/line failures.

## Cursor IDE

| Claude Code | Cursor |
|-------------|--------|
| Bash | Shell |
| Read / Write / Edit | Read / Write / StrReplace |
| WebFetch | WebFetch |
| AskUserQuestion | AskQuestion |
| `run_in_background` | Shell with `block_until_ms: 0` |

Invoke the `use-enonic-cli` skill before running any `enonic` command. For build/runtime failures after upgrade, hand off to `debug-xp-app`.

## What this skill does

Upgrades a single XP application's source tree from XP 7 to XP 8. Out of scope: dumping/loading content data between XP 7 and XP 8
instances (covered briefly at <https://raw.githubusercontent.com/enonic/doc-xp/refs/heads/8.0/docs/release/upgrade.adoc>), and
upgrading 3rd-party market apps (replace those with their XP 8 versions yourself).

The skill leans on the official [`xp8migrator`](https://github.com/enonic/xp8migrator) tool for descriptor conversion (`application.xml`,
the entire `site/` tree, admin tools, APIs, webapp → YAML with `kind:`) and only does the things the migrator doesn't handle by hand:
build-system reorganization (settings plugin, `xplibs.*` catalog, `gradle.properties` flow), TypeScript/bundler config, code-level breaking
changes, `logback.xml`, and post-migration cleanup of the orphaned `site/` directory. Upstream descriptor shapes: <https://raw.githubusercontent.com/enonic/doc-code/refs/heads/master/docs/upgrade.adoc>. Open **one** local catalog from the table below — never all three.

## Knowledge base (How)

Operational How for CLI install, non-interactive flags, and migrator catalogs:

| Topic | Path |
|-------|------|
| CLI install + non-interactive rules + migrator | `~/.agents/kb/implementation/How-to-run-xp8migrator.md` |
| Breaking changes | `~/.agents/kb/implementation/xp7-to-xp8-upgrade/xp7-to-xp8-changes.md` chooser, then one `changes-*.md` family |
| Descriptor transforms | `~/.agents/kb/implementation/xp7-to-xp8-upgrade/manual-schemes-migration.md` chooser, then one `schemes-*.md` step |
| build.gradle / xplibs examples | `~/.agents/kb/implementation/xp7-to-xp8-upgrade/examples.md` |
| Enonic CLI critical rules + command catalogs | `use-enonic-cli` + `~/.agents/kb/implementation/enonic-cli/` |

**REQUIRED:** invoke `use-enonic-cli` before any `enonic` command. Prefer `enonic project build` / `deploy` over raw `./gradlew` (except `./gradlew wrapper --gradle-version …`). Do not install the CLI until the Plan is approved; never uninstall it during cleanup. Open **one** chooser (`xp7-to-xp8-changes.md` / `manual-schemes-migration.md` / `examples.md`) per need, then only the matching family/step file. Never load all three catalogs in one pass.

## Workflow (must follow in order)

The upgrade has two strict phases: **inventory & plan** (read-only, presented to the user), then **execute & validate** (only after the user
approves). Never edit files before the user approves the plan — silent edits frustrate users who want to inspect the change set first.
Throughout both phases, **announce before you act**: before each step that runs a command or edits a file, say in one line what you're
about to do and why, so the user always knows what's happening without having to ask.

```
1. Detect      → check the Enonic CLI is present (read-only); read gradle.properties, build.gradle, app descriptor, list directories
2. Inventory   → enumerate every file the upgrade will touch (group by category)
3. Plan        → present a numbered checklist of changes (incl. installing the Enonic CLI if it's missing); ask for approval
                 (descriptor changes are run via xp8migrator, not hand-edited)
4. Execute     → install the CLI if the plan said so; run xp8migrator for descriptors; edit build/code by hand
5. Validate    → run `enonic project build` BEFORE any cleanup (so a failure leaves the originals intact for diagnosis)
6. Cleanup     → only after the build is green AND the user confirms: `rm -rf src/main/resources/site` and delete `application.xml`
7. Deploy      → offer `enonic project deploy` to a sandbox and run it only after the user confirms
```

### Phase router

Load only the active phase:

1. Read [detect-inventory-plan.md](references/detect-inventory-plan.md) for detection, inventory, migration planning, and the plan template.
2. Read [execute-validate-cleanup.md](references/execute-validate-cleanup.md) only after the plan is accepted; it covers execution, validation, guarded cleanup, and optional deployment.
3. Read [migration-notes.md](references/migration-notes.md) only when a concrete migration detail or conversation pattern is needed.

Do not preload execution or cleanup instructions during detection.
