---
id: enonic-cli-export-import
when_skills: [use-enonic-cli]
read: section
prose: caveman-lite
---

## Export / Import

### enonic export

Export repository branch data to the exports directory.

```
enonic export [flags]
```

| Flag                  | Short | Description                           | Default |
|-----------------------|-------|---------------------------------------|---------|
| `-t`                  | —     | Export name                           | —       |
| `--path`              | —     | Source path (`repo:branch:path`)      | —       |
| `--skip-ids`          | —     | Don't export node IDs                 | `false` |
| `--skip-versions`     | —     | Don't export version history          | `false` |
| `--dry`               | —     | Dry run — show what would be exported | `false` |
| + Standard auth flags |       |                                       |         |
| `--force`             | `-f`  | Non-interactive mode                  | `false` |

### enonic import

Import data from the exports directory.

```
enonic import [flags]
```

| Flag                  | Short | Description                      | Default |
|-----------------------|-------|----------------------------------|---------|
| `-t`                  | —     | Export name to import from       | —       |
| `--path`              | —     | Target path (`repo:branch:path`) | —       |
| `--xsl-source`        | —     | XSL transformation file          | —       |
| `--xsl-param`         | —     | XSL parameters (`key=value`)     | —       |
| `--skip-ids`          | —     | Generate new node IDs            | `false` |
| `--skip-permissions`  | —     | Use target node permissions      | `false` |
| `--dry`               | —     | Dry run                          | `false` |
| + Standard auth flags |       |                                  |         |
| `--force`             | `-f`  | Non-interactive mode             | `false` |

---
