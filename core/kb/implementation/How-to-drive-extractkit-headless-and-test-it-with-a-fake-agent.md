---
id: how-to-drive-extractkit-headless-and-test-it-with-a-fake-agent
when_skills: [run-plan, plan-implementation, validate-impl]
inputs: [extract-kit checkout]
outputs: [a --json command, an env option, a headless stage, tests that need no model]
stop_if: [a core command would have to call a model]
read: whole
prose: caveman-lite
---

# Drive extractkit headless, and test it with a fake agent

**Scope:** `extract-kit`
**Applies to:** `extractkit_cli/{result,envflags,resources,kitguard,headless,install}.py`, `tests/support.py` (measured 2026-10-02)

## Procedure

1. JSON output: commands keep printing text. `cli.main` redirects stdout in `--json` mode and prints one envelope (`schemas/result.schema.json`). A command feeds it through hooks that already exist: `deps.render_row` (rows), `guide.render_next` (`next_command`), `result.note_run` (sidecar, writes, skips, phase), `result.note_problems`, `result.note_error`. A new command only needs `--json` (`_add_json_flag`) and, when it does not use those printers, one `result.note_*` call. Never print to stdout outside `result.print_json` in JSON mode.
2. Error codes: `ExtractkitError(..., code="...")`. A command that returns 1 without raising (`check`) sets its code with `result.note_error`.
3. Env options: nothing per command. `envflags.apply_defaults(parser)` gives every `--foo-bar` the env var `EXTRACTKIT_FOO_BAR`; a new flag gets it for free. A flag that must never come from the environment goes in `envflags.FORBIDDEN`.
4. Resources: a key in `schemas/resources.schema.json` plus one row in `resources.FIELDS` (key to option dest). Probes live in `resources.probe_rows`.
5. A headless stage: add its id to `headless.STAGES` and a method to `Headless.run`'s table. It calls `extractkit` through `_kit(...)` (subprocess, `--json`), never in-process. Children get no `EXTRACTKIT_*` variable: pass every setting as a flag.
6. Agent CLIs are the `agents:` block of `extractkit.yaml`. Tests patch `headless.agent_table()` to return the fake (`tests/fixtures/fake_agent.py`, modes via `FAKE_AGENT_MODE`: ok, block, noop, sleep, crash). No env var adds an agent.
7. Test shape: run `cli.main([...])` in-process from a temp copy of the fixture with `os.chdir`, patch `HOME` to `support.TEST_HOME` and prepend its `.local/bin` to `PATH` (the `install` stage and `doctor` preflight install into `$HOME`). The fixture needs a `.gitlab-ci.yml` and a folder no build names, or `context.exclude` is already decided and never reaches the agent.

## Pitfalls

- Running `./extractkit deps` or `doctor --source` from the checkout does a full install into the real `$HOME`. Use `HOME=<scratch>` for manual smoke tests.
- The CLI refuses to run from the kit: tests run from `support.TEST_CWD` or a temp source, and `support.run` goes through the installed launcher (the detached copy), not the working tree. `support.run_checkout` runs the checkout's own `extractkit`.
- The install is a snapshot: `support.py` installs once at import. A test that edits the working tree after import still runs the old copy through `support.run`.
- `argparse` exits 2 before `--json` is read. A required option is satisfied by an env var because `apply_defaults` sets `required=False` before parsing.
- `append` options: argparse appends CLI values to the env default, so `envflags.finish` trims the env items when raw argv names the flag.
- `codex` 0.151.0 has no `--full-auto`; use `--sandbox workspace-write`. `claude -p` reads the prompt on stdin.
- `graphify update .` builds `graphify-out/graph.json` with no model.
- `graft` compiles native modules: a Docker image needs `build-essential` for the npm install step.
- A Docker `COPY` of the checkout stays in a layer; use `RUN --mount=type=bind,target=/build/kit ... install` so no copy remains.
