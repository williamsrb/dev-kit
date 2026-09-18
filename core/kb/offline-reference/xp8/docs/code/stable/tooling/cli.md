<!-- src:https://developer.enonic.com/docs/code/stable/tooling/cli generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/tooling/cli.md

# Enonic CLI

The Enonic CLI orchestrates most day-to-day development activities for Enonic XP apps — managing sandboxes, scaffolding projects, building and deploying apps, and administering running servers.

Full reference: [Enonic CLI documentation](https://developer.enonic.com/docs/enonic-cli/stable).

## Installation

Install globally via NPM:

```bash
npm install -g @enonic/cli
```

Verify:

```bash
enonic -v
```

For Homebrew, Snap, or standalone binary installs, see the [CLI install reference](https://developer.enonic.com/docs/enonic-cli/stable/install).

## Command overview

Commands are grouped under topic-specific namespaces. The most commonly used:

Sandboxes

`enonic sandbox create|list|start|stop` — manage local XP development environments.

Projects

`enonic project create|build|deploy|shell` — scaffold and build Enonic apps from starters.

Apps

`enonic app install|list|start|stop` — install and control apps on a running XP instance.

Remotes

`enonic remote add|list|use` — register and switch between XP servers for CLI operations.

Snapshots

`enonic snapshot create|list|restore` — create and restore repository snapshots.

Dumps

`enonic dump create|load` — export and import full system dumps for backup or migration.

Run `enonic` with no arguments for the full command list, or `enonic  --help` for details on any specific command. Full syntax and options are in the [CLI documentation](https://developer.enonic.com/docs/enonic-cli/stable).
