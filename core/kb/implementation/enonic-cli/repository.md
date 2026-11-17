---
id: enonic-cli-repository
when_skills: [use-enonic-cli]
read: section
prose: caveman-lite
---

## Repository Commands

### enonic repo reindex

Rebuild search indices for a repository.

```bash
enonic repo reindex [flags]
```

| Flag                  | Short | Description                            | Default |
|-----------------------|-------|----------------------------------------|---------|
| `-b`                  | —     | Comma-separated branch list            | —       |
| `-r`                  | —     | Repository name                        | —       |
| `-i`                  | —     | Recreate index data (delete + reindex) | `false` |
| + Standard auth flags |       |                                        |         |
| `--force`             | `-f`  | Non-interactive mode                   | `false` |

### enonic repo readonly

Toggle read-only mode.

```bash
enonic repo readonly <true|false> [flags]
```

| Flag                  | Short | Description                            | Default |
|-----------------------|-------|----------------------------------------|---------|
| `-r`                  | —     | Single repository (omit for all repos) | —       |
| + Standard auth flags |       |                                        |         |
| `--force`             | `-f`  | Non-interactive mode                   | `false` |

### enonic repo replicas

Set number of replicas for the cluster.

```bash
enonic repo replicas <1-99> [flags]
```

| Flag                  | Short | Description          | Default |
|-----------------------|-------|----------------------|---------|
| + Standard auth flags |       |                      |         |
| `--force`             | `-f`  | Non-interactive mode | `false` |

### enonic repo list

List all repositories. Alias: `enonic repo ls`.

```bash
enonic repo list [flags]
```

| Flag                  | Short | Description          | Default |
|-----------------------|-------|----------------------|---------|
| + Standard auth flags |       |                      |         |
| `--force`             | `-f`  | Non-interactive mode | `false` |

---
