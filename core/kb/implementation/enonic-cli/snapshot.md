---
id: enonic-cli-snapshot
when_skills: [use-enonic-cli]
read: section
prose: caveman-lite
---

## Snapshot Commands

### enonic snapshot create

Create a snapshot of one or all repositories.

```
enonic snapshot create [flags]
```

| Flag                  | Short | Description                                    | Default |
|-----------------------|-------|------------------------------------------------|---------|
| `--repo`              | `-r`  | Repository name (omit for all)                 | —       |
| `--compat`            | —     | XP version compat mode (`7` = legacy XP 7 API) | XP 8    |
| + Standard auth flags |       |                                                |         |
| `--force`             | `-f`  | Non-interactive mode                           | `false` |

### enonic snapshot list

List all snapshots. Alias: `enonic snapshot ls`.

```
enonic snapshot ls [flags]
```

| Flag                  | Short | Description          | Default |
|-----------------------|-------|----------------------|---------|
| + Standard auth flags |       |                      |         |
| `--force`             | `-f`  | Non-interactive mode | `false` |

### enonic snapshot restore

Restore a snapshot.

```
enonic snapshot restore [flags]
```

| Flag                  | Short    | Description                                          | Default |
|-----------------------|----------|------------------------------------------------------|---------|
| `--snapshot`          | `--snap` | Snapshot name                                        | —       |
| `--repo`              | `-r`     | Target repository                                    | —       |
| `--latest`            | —        | Use latest snapshot (takes precedence over `--snap`) | `false` |
| `--clean`             | —        | Delete indices before restoring                      | `false` |
| `--compat`            | —        | XP version compat mode (`7` = legacy XP 7 API)       | XP 8    |
| + Standard auth flags |          |                                                      |         |
| `--force`             | `-f`     | Non-interactive mode                                 | `false` |

### enonic snapshot delete

Delete snapshots by name or date. Alias: `del`.

```
enonic snapshot delete [flags]
```

| Flag                  | Short    | Description                             | Default |
|-----------------------|----------|-----------------------------------------|---------|
| `--snapshot`          | `--snap` | Snapshot name                           | —       |
| `--before`            | `-b`     | Delete before date (format: `2 Jan 06`) | —       |
| + Standard auth flags |          |                                         |         |
| `--force`             | `-f`     | Non-interactive mode                    | `false` |

---
