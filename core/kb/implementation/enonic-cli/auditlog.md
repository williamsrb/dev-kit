---
id: enonic-cli-auditlog
when_skills: [use-enonic-cli]
read: section
prose: caveman-lite
---

## Audit Log Commands

### enonic auditlog cleanup

Remove audit log records older than threshold.

```
enonic auditlog cleanup [flags]
```

| Flag                  | Short | Description                           | Default |
|-----------------------|-------|---------------------------------------|---------|
| `--age`               | —     | ISO-8601 duration (`P30D`, `P1DT12H`) | —       |
| + Standard auth flags |       |                                       |         |
| `--force`             | `-f`  | Non-interactive mode                  | `false` |

---
