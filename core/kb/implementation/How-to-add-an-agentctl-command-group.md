---
id: how-to-add-an-agentctl-command-group
when_skills: [run-plan, plan-implementation]
inputs: [bin/agentctl, a sibling bin/agentctl_*.py]
outputs: [registered group, tests under tests/test_agentctl_*.py]
stop_if: [growing pack or merge logic inside bin/agentctl]
read: whole
prose: caveman-lite
---

# Add an agentctl command group

Heavy groups live in `bin/agentctl_<name>.py`. `bin/agentctl` only registers them. Shared `emit` / `run` / markdown helpers live in `bin/agentctl_common.py` so groups never import `bin/agentctl` (cycle).

Existing siblings: `plan`, `image` (also evidence), `security`, `skills`, `docs` (also local), `kb`, `jira`, `code`.

## Procedure

1. Put pack/merge/REST logic in `bin/agentctl_<name>.py`. Export `add_<name>_parsers(group)` and a typed error (`KbError`, `JiraError`) when the group can fail in a user-facing way.
2. Resolve `$AGENTS_HOME` at call time via `agentctl_common.agents_home()` (re-export of `agentctl_jira.agents_home()`). Do not cache the kb/prd/plans path at import.
3. Emit bounded JSON via `agentctl_common.emit`. Do not import `emit` from `bin/agentctl` (cycle).
4. In `bin/agentctl` `build_parser()`: `import agentctl_<name>`, then `group("<name>", "<summary>.")` and `agentctl_<name>.add_<name>_parsers(<name>)`. Insert `kb` before `jira`.
5. Catch the new error in `main()` next to `JiraError`.
6. Tests go in `tests/test_agentctl_<name>.py`. Point `$AGENTS_HOME` at a temp dir and pass `--root` so writes never hit `~/.agents/kb`.

## Pitfalls

- `group()` already prints that group's help on bare invocation. Do not set `required=True` on the group's subparsers.
- A missing CLI (`zstd`) is a `KbError`, not a silent skip.
- Do not document a new group as a How-to under `kb/_shared` unless that extra is ticked.
