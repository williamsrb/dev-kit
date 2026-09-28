---
id: enonic-cli-commands
when_skills: [use-enonic-cli]
read: section
prose: caveman-lite
---

# Enonic CLI command reference

Open only the matching family file. Do not read this whole tree.

| Family | File |
|--------|------|
| Project Commands | `project.md` |
| Sandbox Commands | `sandbox.md` |
| Snapshot Commands | `snapshot.md` |
| Dump Commands | `dump.md` |
| Export / Import | `export-import.md` |
| App Commands | `app.md` |
| Repository Commands | `repository.md` |
| CMS Commands | `cms.md` |
| System Commands | `system.md` |
| Audit Log Commands | `auditlog.md` |
| Vacuum | `vacuum.md` |
| Cloud Commands | `cloud.md` |
| Global Commands | `global.md` |
| Auth flags / `--compat` | this file, below |

## Standard Auth Flags

These flags apply to all **remote** commands (commands that talk to a running XP instance).

| Flag            | Short | Description                                                 | Default |
|-----------------|-------|-------------------------------------------------------------|---------|
| `--auth`        | `-a`  | Basic auth `user:password` (deprecated for XP 7.15+)        | —       |
| `--cred-file`   | —     | Service account key file (JSON, XP 7.15+)                   | —       |
| `--client-key`  | —     | Private key for mTLS (must pair with `--client-cert`)       | —       |
| `--client-cert` | —     | Client certificate for mTLS (must pair with `--client-key`) | —       |

---
## Compatibility Mode (`--compat`)

CLI 4.x talks to the **XP 8** management API by default. Four data commands accept a `--compat` flag to target a legacy **XP 7** instance:
`snapshot create`, `snapshot restore`, `dump create`, `dump load`.

| Flag       | Values                          | Effect                                                            |
|------------|---------------------------------|-------------------------------------------------------------------|
| `--compat` | `7` (or any value starting `7`) | Use the legacy XP 7 API format. Omit for the default XP 8 format. |

The `--archive` flag on `dump create` / `dump load` is **only effective in compat mode** (XP 7).

---
