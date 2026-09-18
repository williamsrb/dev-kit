---
id: how-to-prove-a-tool-is-write-confined
when_skills: [run-plan, validate-impl]
inputs: [the tool's source tree, the roots it reads]
outputs: [pass/fail gate before any correctness acceptance]
stop_if: [any check fails - confinement is blocking]
read: whole
prose: caveman-lite
---

# Prove a tool is write-confined

When a tool claims "this only writes under `--out`" and the claim actually matters — capture tools, scanners, auditors, anything pointed at a system the user cannot afford to have modified.

## Scope

Prose in a README is not evidence. This is the four-layer gate that produces evidence. Run it **before** any correctness acceptance: a tool that mutates its subject is wrong regardless of how good its output is.

## Prerequisites

`unshare` with unprivileged user namespaces (`kernel.unprivileged_userns_clone=1`) for layer 4. Degrade gracefully when absent — skip, do not silently pass.

## Procedure

1. **Route every mutation through one guard object.** `guard.open/write/copy/chmod/unlink/symlink/rmdir`. The guard resolves the absolute destination and raises unless it lands under an allowed root. Nothing else in the confined code path calls `os.*` or `shutil.*` mutators directly.

2. **Static audit by AST, not grep.** Walk each module in the confined path and flag calls to filesystem mutators whose receiver is not the guard. Qualify mutator names by module (`os.replace`, `shutil.move`) — bare name matching flags every `str.replace` and buries the real finding. Flag `open()` only when the mode contains `w`, `a`, `x` or `+`.

3. **Test the guard's properties, not its wording.** Assert it permits writes inside, refuses outside, refuses every mutation verb, and — the one that matters — refuses a write through a symlink planted inside the allowed root that points out of it.

4. **Observe the subject before and after.** Snapshot `mode, uid, gid, size, mtime_ns, ctime_ns` plus a content hash for small files across every root, run the tool, snapshot again, diff. Exclude atime deliberately and say why.

5. **Re-run with the roots mounted read-only.** `unshare -m --map-root-user sh -c 'mount --bind $R $R && mount -o remount,ro,bind $R && ...'`. This is strictly stronger than the diff: the kernel refuses a stray write instead of you noticing it afterwards.

6. **Allowlist subprocesses, log every invocation, diff the log against the allowlist.** Test the allowlist behaviourally by asserting that unforeseen commands are refused — grepping the source for the word "denylist" trips on the docstring explaining it is not one.

## Pitfalls

- **`realpath` is wrong for operations that act on a link.** Writing *through* a path must follow the final symlink (or a planted link walks past the guard). Creating or removing a link acts *on* it, and following it both mis-locates the check and refuses legitimate work — re-staging a captured symlink to `/dev/null` resolves to `/dev/null` and gets refused. Resolve the parent chain always; make following the final component a parameter.
- **Test the idempotent re-run.** Confinement bugs hide in the second run against an existing output directory, where the output tree now contains symlinks and files the first run created. A first-run-only test misses them.
- **Snapshot `ctime`, not just `mtime`.** A metadata-only change (chmod, chown, xattr) moves ctime and leaves mtime alone.
- **A guard that only wraps `open` is not a guard.** `chmod`, `utime`, `setxattr`, `unlink`, `symlink` and `rmdir` all mutate.

## Sample data

Real finding from this gate: a scratch-directory cleanup called `os.rmdir` directly. Harmless (the path was inside the output root) but outside the guard, so it was invisible to the audit — exactly the drift the static layer exists to catch.
