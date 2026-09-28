---
id: enonic-cli-global
when_skills: [use-enonic-cli]
read: section
prose: caveman-lite
---

## Global Commands

### enonic create

Simplified project creation with defaults.

```
enonic create [project-name] [flags]
```

| Flag           | Short            | Description          | Default |
|----------------|------------------|----------------------|---------|
| `--repository` | `-r` OR `--repo` | Starter repo path    | —       |
| `--sandbox`    | `-s` OR `--sb`   | Link to sandbox      | —       |
| `--prod`       | —                | Non-development mode | `false` |
| `--skip-start` | —                | Don't start sandbox  | `false` |
| `--force`      | `-f`             | Non-interactive mode | `false` |

### enonic dev

Start hot-reload development mode. Alias for `enonic project dev`.

```
enonic dev [-f]
```

Starts sandbox in detached mode, deploys app, watches for changes. Exit with Ctrl-C.

### enonic latest

Show the latest available CLI version.

```
enonic latest [flags]
```

Accepts `--force` and the standard auth flags, though it only checks the CLI version.

### enonic upgrade

Upgrade CLI to the latest version.

```
enonic upgrade
```

### enonic uninstall

Remove CLI from the system.

```
enonic uninstall
```
