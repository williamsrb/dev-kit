---
id: enonic-cli-system
when_skills: [use-enonic-cli]
read: section
prose: caveman-lite
---

## System Commands

### enonic system info

Show XP instance info (version, mode, build hash, branch, timestamp). Alias: `i`.

```
enonic system info [flags]
```

Accepts `--force` and the standard auth flags. Earlier CLI versions required no auth (info port 2609); 4.0.0 added the auth flags — pass
them if the management API is secured.

---
