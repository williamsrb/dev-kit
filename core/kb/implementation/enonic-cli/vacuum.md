---
id: enonic-cli-vacuum
when_skills: [use-enonic-cli]
read: section
prose: caveman-lite
---

## Vacuum

### enonic vacuum

Purge old node versions and optionally unused blobs.

```
enonic vacuum [flags]
```

| Flag                  | Short | Description                       | Default          |
|-----------------------|-------|-----------------------------------|------------------|
| `--blob`              | `-b`  | Also remove unused binary blobs   | `false`          |
| `--threshold`         | `-t`  | Age threshold (ISO-8601 duration) | `P21D` (21 days) |
| + Standard auth flags |       |                                   |                  |
| `--force`             | `-f`  | Non-interactive mode              | `false`          |

---
