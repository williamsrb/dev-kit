---
id: enonic-cli-dump
when_skills: [use-enonic-cli]
read: section
prose: caveman-lite
---

## Dump Commands

### enonic dump create

Export all repositories to a dump.

```
enonic dump create [flags]
```

| Flag                  | Short | Description                                      | Default |
|-----------------------|-------|--------------------------------------------------|---------|
| `-d`                  | —     | Dump name                                        | —       |
| `--skip-versions`     | —     | Don't include version history                    | `false` |
| `--max-version-age`   | —     | Max age of versions in days                      | —       |
| `--max-versions`      | —     | Max number of versions per node                  | —       |
| `--archive`           | —     | Create as ZIP archive (only in compat/XP 7 mode) | `false` |
| `--compat`            | —     | XP version compat mode (`7` = legacy XP 7 API)   | XP 8    |
| + Standard auth flags |       |                                                  |         |
| `--force`             | `-f`  | Non-interactive mode                             | `false` |

### enonic dump upgrade

Upgrade dump format for newer XP version. Alias: `up`.

```
enonic dump upgrade [flags]
```

| Flag                  | Short | Description          | Default |
|-----------------------|-------|----------------------|---------|
| `-d`                  | —     | Dump name            | —       |
| + Standard auth flags |       |                      |         |
| `--force`             | `-f`  | Non-interactive mode | `false` |

Output name: `<dump-name>_upgraded_<version>`.

### enonic dump list

List all dumps. Alias: `enonic dump ls`.

```
enonic dump ls [flags]
```

| Flag                  | Short | Description          | Default |
|-----------------------|-------|----------------------|---------|
| + Standard auth flags |       |                      |         |
| `--force`             | `-f`  | Non-interactive mode | `false` |

### enonic dump load

Import a dump. Deletes existing repos before loading.

```
enonic dump load [flags]
```

| Flag                  | Short | Description                                      | Default |
|-----------------------|-------|--------------------------------------------------|---------|
| `-d`                  | —     | Dump name                                        | —       |
| `--upgrade`           | —     | Automatically upgrade dump before loading        | `false` |
| `--archive`           | —     | Load from ZIP archive (only in compat/XP 7 mode) | `false` |
| `--compat`            | —     | XP version compat mode (`7` = legacy XP 7 API)   | XP 8    |
| + Standard auth flags |       |                                                  |         |
| `--force`             | `-f`  | Non-interactive mode                             | `false` |

---
