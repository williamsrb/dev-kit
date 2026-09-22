---
id: how-to-isolate-harness-tests-from-the-host-home
when_skills: [validate-impl, run-plan]
inputs: [tests that write under HOME, .gitlab-ci.yml]
outputs: [tests that cannot touch the real home, CI that runs as non-root]
stop_if: []
read: whole
prose: caveman-lite
---

# Isolate harness tests from the host home

Harness tests fake `HOME` with a temp dir. Two leaks survive that: git's global config also comes from `$XDG_CONFIG_HOME`, and CI images run as root, where tools that refuse root fail.

## Procedure

1. Every subprocess that runs `git config --global` (directly or inside a generated script) gets `HOME=<tmp>` **and** `XDG_CONFIG_HOME=<tmp>/.config` in its env.
2. In-process code that reads `os.environ["XDG_CONFIG_HOME"]` needs the same pin in `setUp`, restored in `tearDown`.
3. After a run that writes config, confirm the real files kept their mtime: `stat -c '%y' ~/.gitignore_global ~/.config/git/ignore`.
4. CI job on a root image (`python:3.12-slim`): create an account and run the suite as it.

   ```yaml
   script:
     - useradd --create-home ci
     - chown -R ci "$CI_PROJECT_DIR"
     - runuser -u ci -- env HOME=/home/ci python3 -m unittest discover -s tests -v
   ```

5. Reproduce locally before pushing: `docker run --rm -v <copy>:/builds/p -w /builds/p -e CI_PROJECT_DIR=/builds/p python:3.12-slim sh -c '<the three lines>'`. Mount a copy: the `chown` rewrites ownership.

## Pitfalls

- This machine's shell exports `XDG_CONFIG_HOME=~/.config`. A test that only sets `HOME` resolves the real `core.excludesFile` and can edit it.
- Git reads `$XDG_CONFIG_HOME/git/config` before `~/.gitconfig`. A temp `.gitconfig` wins for keys it sets, but every key it does not set comes from the real machine.
- `chown -R` is also what stops git's "dubious ownership" refusal when the checkout belongs to another uid.
- A test that passes locally and fails only in CI with "refusing to … as root" is this, not a regression. Do not weaken the root guard to green it.
- `unittest` prints its summary to stderr. Output printed to stdout during tests is flushed at exit, so `| tail` shows that output, not the result. Filter with `grep -E '^(Ran|OK|FAILED)'`.
