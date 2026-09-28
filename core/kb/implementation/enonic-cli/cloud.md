---
id: enonic-cli-cloud
when_skills: [use-enonic-cli]
read: section
prose: caveman-lite
---

## Cloud Commands

### enonic cloud login

Login to Enonic Cloud via browser-based OAuth.

```
enonic cloud login [--qr]
```

| Flag   | Short | Description                     | Default |
|--------|-------|---------------------------------|---------|
| `--qr` | —     | Display QR code for mobile auth | `false` |

**Note:** This is interactive (browser-based). `-f` does not apply.

### enonic cloud logout

Log out from Enonic Cloud.

```
enonic cloud logout
```

No additional flags.

### enonic cloud app install

Install project JAR to Enonic Cloud.

```
enonic cloud app install [flags]
```

| Flag | Short | Description               | Default              |
|------|-------|---------------------------|----------------------|
| `-j` | —     | JAR file path             | `./build/libs/*.jar` |
| `-t` | —     | Upload timeout in seconds | `300`                |
| `-y` | —     | Skip confirmation prompt  | `false`              |

---
