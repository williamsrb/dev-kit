---
id: enonic-cli-project
when_skills: [use-enonic-cli]
read: section
prose: caveman-lite
---

## Project Commands

### enonic project create

Create a new Enonic project from a starter.

```
enonic project create [name] [flags]
```

| Flag            | Short            | Description                                            | Default                   |
|-----------------|------------------|--------------------------------------------------------|---------------------------|
| `--repository`  | `-r` OR `--repo` | Starter repo (`<enonic>`, `<org>/<repo>`, or full URL) | —                         |
| `--branch`      | `-b`             | Branch to checkout                                     | `master`                  |
| `--checkout`    | `-c`             | Commit hash to checkout (excludes `--branch`)          | —                         |
| `--destination` | `-d` OR `--dest` | Destination path                                       | last word of project name |
| `--version`     | `-v` OR `--ver`  | Version number                                         | `1.0.0-SNAPSHOT`          |
| `--name`        | `-n`             | Application name (overrides positional arg)            | —                         |
| `--sandbox`     | `-s` OR `--sb`   | Link to existing sandbox                               | —                         |
| `--prod`        | —                | Run XP in non-development mode                         | `false`                   |
| `--skip-start`  | —                | Don't start sandbox after creation                     | `false`                   |
| `--force`       | `-f`             | Non-interactive mode                                   | `false`                   |

### enonic project sandbox

Set or change the project's default sandbox. Aliases: `sbox`, `sb`.

```
enonic project sandbox [name] [-f]
```

| Flag      | Short | Description          | Default |
|-----------|-------|----------------------|---------|
| `--force` | `-f`  | Non-interactive mode | `false` |

### enonic project build

Build project via Gradle.

```
enonic project build [-f]
```

| Flag      | Short | Description                             | Default |
|-----------|-------|-----------------------------------------|---------|
| `--force` | `-f`  | Non-interactive mode (uses system Java) | `false` |

### enonic project clean

Clean build artifacts (alias for `gradlew clean`).

```
enonic project clean [-f]
```

| Flag      | Short | Description          | Default |
|-----------|-------|----------------------|---------|
| `--force` | `-f`  | Non-interactive mode | `false` |

### enonic project test

Run tests via Gradle.

```
enonic project test [-f]
```

| Flag      | Short | Description          | Default |
|-----------|-------|----------------------|---------|
| `--force` | `-f`  | Non-interactive mode | `false` |

### enonic project deploy

Build and deploy project to associated sandbox.

```
enonic project deploy [sandbox-name] [flags]
```

| Flag           | Short | Description                              | Default |
|----------------|-------|------------------------------------------|---------|
| `--prod`       | —     | Non-development mode                     | `false` |
| `--debug`      | —     | Enable debug on port 5005                | `false` |
| `--continuous` | `-c`  | Watch for changes, redeploy continuously | `false` |
| `--skip-start` | —     | Don't start sandbox                      | `false` |
| `--force`      | `-f`  | Non-interactive mode                     | `false` |

### enonic project install

Build and install project to a running XP instance via management API. Alias: `i`.

```
enonic project install [flags]
```

| Flag                  | Short | Description          | Default |
|-----------------------|-------|----------------------|---------|
| + Standard auth flags |       |                      |         |
| `--force`             | `-f`  | Non-interactive mode | `false` |

### enonic project shell

Open shell with project's `JAVA_HOME` and `XP_HOME` set.

```
enonic project shell
```

No additional flags. Exit with `quit`.

### enonic project gradle

Run arbitrary Gradle tasks with project context.

```
enonic project gradle [tasks / flags ...]
```

Everything after `gradle` is forwarded to `gradlew`.

### enonic project env

Export `JAVA_HOME` and `XP_HOME` for the current shell.

```
eval $(enonic project env)
```

Not available on Windows.

---
