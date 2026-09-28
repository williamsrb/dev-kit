---
id: enonic-cli-sandbox
when_skills: [use-enonic-cli]
read: section
prose: caveman-lite
---

## Sandbox Commands

### enonic sandbox create

Create a new local XP sandbox.

```
enonic sandbox create [name] [flags]
```

| Flag              | Short | Description                                             | Default       |
|-------------------|-------|---------------------------------------------------------|---------------|
| `--template`      | `-t`  | Use specific template                                   | —             |
| `--skip-template` | —     | Don't use a template                                    | `false`       |
| `--version`       | `-v`  | XP distribution version                                 | latest stable |
| `--image`         | `-i`  | Use specific Docker image (e.g. `enonic/xp:7.13.4-sdk`) | —             |
| `--all`           | —     | List all distro versions                                | `false`       |
| `--prod`          | —     | Non-development mode                                    | `false`       |
| `--skip-start`    | —     | Don't start after creation                              | `false`       |
| `--force`         | `-f`  | Non-interactive mode                                    | `false`       |

### enonic sandbox list

List all sandboxes. Alias: `enonic sandbox ls`.

```
enonic sandbox list
```

No additional flags. Running sandbox is marked with `*`.

### enonic sandbox start

Start a sandbox (only one can run at a time).

```
enonic sandbox start [name] [flags]
```

| Flag          | Short | Description               | Default |
|---------------|-------|---------------------------|---------|
| `--prod`      | —     | Non-development mode      | `false` |
| `--debug`     | —     | Enable debug on port 5005 | `false` |
| `--detach`    | `-d`  | Run in background         | `false` |
| `--http.port` | —     | Custom HTTP port          | `8080`  |
| `--force`     | `-f`  | Non-interactive mode      | `false` |

### enonic sandbox stop

Stop the running sandbox.

```
enonic sandbox stop
```

No additional flags.

### enonic sandbox upgrade

Upgrade sandbox XP distribution version. Downgrades are not allowed. Alias: `up`.

```
enonic sandbox upgrade [name] [flags]
```

| Flag        | Short | Description                                           | Default |
|-------------|-------|-------------------------------------------------------|---------|
| `--version` | `-v`  | Target distribution version                           | —       |
| `--image`   | `-i`  | New Docker image to use (e.g. `enonic/xp:7.13.4-sdk`) | —       |
| `--all`     | `-a`  | List all distro versions                              | `false` |
| `--force`   | `-f`  | Non-interactive mode                                  | `false` |

### enonic sandbox delete

Delete sandbox and all its data. Aliases: `del`, `rm`.

```
enonic sandbox delete [name] [-f]
```

| Flag      | Short | Description          | Default |
|-----------|-------|----------------------|---------|
| `--force` | `-f`  | Non-interactive mode | `false` |

### enonic sandbox copy

Clone an existing sandbox to a new one. Alias: `cp`.

```
enonic sandbox copy [source] [target] [-f]
```

| Flag      | Short | Description          | Default |
|-----------|-------|----------------------|---------|
| `--force` | `-f`  | Non-interactive mode | `false` |

---
