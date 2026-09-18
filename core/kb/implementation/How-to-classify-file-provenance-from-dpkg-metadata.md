---
id: how-to-classify-file-provenance-from-dpkg-metadata
when_skills: [run-plan]
inputs: [/var/lib/dpkg/status, /var/lib/dpkg/info/*.list, /var/lib/dpkg/info/*.md5sums]
outputs: [path -> verdict + evidence]
stop_if: [running as non-root and content reads matter]
read: whole
prose: caveman-lite
---

# Classify file provenance from dpkg metadata

Answering "did a package put this here, or did the user?" for every file on a Debian/Ubuntu system. Useful for migration, drift detection, and config auditing.

## Scope

Debian/Ubuntu with a normal dpkg database. Read-only. ~100k paths classify in ~40s on an SSD.

## Prerequisites

Python 3 stdlib. No `debsums`, no `dpkg -S` per file.

## Procedure

1. **Build the reverse index once.** Parse all `/var/lib/dpkg/info/*.list` into `path -> package` and all `*.md5sums` into `path -> md5`. Never shell out per file: `dpkg -S` on 100k paths is 100k forks.
   - `.list` files are named `pkg.list` or `pkg:arch.list`; strip at the first `:`.
   - `.md5sums` lines are `<md5>  <relative path>` (two spaces), path has **no** leading `/`.
   - Filter both indexes to the roots you actually scan. On a full system this drops ~90% of entries and the RSS with them (48 MB instead of ~400 MB).

2. **Parse `Conffiles` out of `/var/lib/dpkg/status`, not the `.conffiles` files.** The status stanza carries dpkg's own pristine md5; `/var/lib/dpkg/info/*.conffiles` carries only paths. Format is one indented ` /path md5 [obsolete|newconffile]` per line. The first element of the parsed field is the empty text on the `Conffiles:` line itself — discard it.

3. **Classify with conffile baselines taking priority** over `.md5sums`, then ownership, then hash comparison. Compute md5 and sha256 in a single read pass; hashing 100k files twice doubles the only expensive part.

4. **A claimed path that does not exist is a deletion**, not an absence. Iterate the index's claimed paths and check `os.path.lexists`. These migrate too — a restore that silently reinstates a file the user removed has not migrated the system.

## Pitfalls

- **`debsums` cannot substitute for this.** It skips conffiles entirely (verified: it reported 0 changes on a machine with 2 genuinely edited conffiles), cannot report claimed-but-missing paths, and adds an install dependency. It is still a useful independent oracle for the non-conffile subset.
- **"Unreadable" is not "no baseline."** Running as non-root, `/etc/sudoers` (0440) fails to read. Emitting `NO_BASELINE` there reports a permission problem as a provenance finding. Use a distinct `UNREADABLE` verdict.
- **`md5sums` does not cover maintainer-script output.** Files a postinst *generates* are owned by nobody and classify as user-authored. `/etc/hosts`, `/etc/passwd`, `/etc/group` and `/etc/libreoffice/registry/*.xcd` all hit this. This is the accuracy ceiling; the only real fix is diffing against a reference root built with the same package set (`mmdebstrap`). Disclose it rather than hiding it.
- **Check generated-file patterns only for paths that would otherwise be unowned.** Checking them first lets a filename match override a package-owned file's hash-derived verdict.
- **Do not use mtime as a provenance signal.** Unpacking preserves package mtimes and `touch` destroys them.
- **Paths are bytes.** dpkg `.list` entries are newline-delimited and may contain any other byte, including spaces (`/opt/Grok Bot`). Read them as bytes, decode with `surrogateescape`, and never shell-interpolate a discovered path. JSON cannot serialise lone surrogates — emit a base64 sidecar field for those.

## Sample data

Ubuntu 24.04.4, 2632 installed packages: every one ships `.md5sums` (0 gaps), 1715 registered conffiles with 0 obsolete, 102685 owned paths under the scan roots, 7 claimed-but-missing under `/etc`.

File capabilities: read the `security.capability` xattr directly instead of forking `getcap` per file. Little-endian `magic_etc`, then permitted/inheritable pairs (rev1 12 bytes, rev2 20, rev3 24 with a trailing rootid); low bit of `magic_etc` is the effective flag. Cross-checks exactly against `getcap` output.
