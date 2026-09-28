---
id: enonic-cli-app
when_skills: [use-enonic-cli]
read: section
prose: caveman-lite
---

## App Commands

### enonic app install

Install an application on all cluster nodes. Alias: `i`.

```
enonic app install [flags]
```

| Flag                  | Short | Description                                       | Default |
|-----------------------|-------|---------------------------------------------------|---------|
| `--url`               | —     | URL to application JAR                            | —       |
| `--file`              | —     | Local path to JAR (takes precedence over `--url`) | —       |
| + Standard auth flags |       |                                                   |         |
| `--force`             | `-f`  | Non-interactive mode                              | `false` |

### enonic app start

Start an installed application.

```
enonic app start <app-key> [flags]
```

| Flag                  | Short | Description          | Default |
|-----------------------|-------|----------------------|---------|
| + Standard auth flags |       |                      |         |
| `--force`             | `-f`  | Non-interactive mode | `false` |

### enonic app stop

Stop a running application.

```
enonic app stop <app-key> [flags]
```

| Flag                  | Short | Description          | Default |
|-----------------------|-------|----------------------|---------|
| + Standard auth flags |       |                      |         |
| `--force`             | `-f`  | Non-interactive mode | `false` |

---
