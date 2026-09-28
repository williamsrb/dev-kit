---
id: enonic-cli-cms
when_skills: [use-enonic-cli]
read: section
prose: caveman-lite
---

## CMS Commands

### enonic cms reprocess

Reprocess content metadata (typically after migration).

```
enonic cms reprocess [flags]
```

| Flag                  | Short | Description                  | Default |
|-----------------------|-------|------------------------------|---------|
| `--path`              | —     | Content path (`branch:path`) | —       |
| `--skip-children`     | —     | Don't process descendants    | `false` |
| + Standard auth flags |       |                              |         |
| `--force`             | `-f`  | Non-interactive mode         | `false` |

---
