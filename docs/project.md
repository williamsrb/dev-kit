# Projects

`devkit project` applies the harness to a work repo, next to profiles instead of
replacing them. A **profile** carries how the agent runs: hooks, MCP, auth,
environment, the desktop identity. A **project** carries what the agent knows:
the skills of the flavors and profile types you name, skills the repo owns, and an
`AGENTS.md`. A project never writes hooks, MCP, settings, auth or `AGENTS_HOME`.

Use a project when a team should get the same skills in a repo without each
developer creating a profile. Keep using profiles for isolation between
accounts, tools and desktop apps. The two compose: a developer with an active
profile can also build a project (see [Duplicates](#duplicates-with-the-active-profile)).

```bash
cd <repo>
devkit project init . --layer core --layer enonic --apply   # writes harness/project.json
devkit project build .                                      # dry run: lists every link and file, and the exclude file with an entry count
devkit project build . --apply
devkit project status .
devkit project clean . --apply                              # removes what the build wrote
```

Every write command is a dry run without `--apply`. `PATH` defaults to `.` and
must be the root of the git work tree.

## What a build writes

One skills tree, linked twice, the layout `extract-kit` already uses:

| Path | Is | Excluded from git |
|------|----|-------------------|
| `.agents/skills/<name>` | link to `<kit home>/current/core/skills/<name>` (Codex, Cursor) | yes |
| `.claude/skills/<name>` | relative link to `../../.agents/skills/<name>` (Claude Code) | yes |
| `.agents/skills/<name>` for a repo-owned skill | relative link to `../../harness/skills/<name>` | no |
| `.claude/skills/<name>` for a repo-owned skill | relative link to `../../.agents/skills/<name>` | no |
| `AGENTS.md` | generated, only when the repo has neither `AGENTS.md` nor `CLAUDE.md` and there is content | yes |
| `CLAUDE.md` | relative link to `AGENTS.md`, written with it | yes |
| `.devkit-project.json` | stamp: what the build wrote | yes |

Base links name `current`, so a kit update reaches the project without a
rebuild. A rebuild is needed only when the set of skills changes (`status` says
so).

## Configuration

`harness/project.json`, or any file passed with `--config FILE`:

```json
{ "schema": 1, "layers": ["core", "enonic"] }
```

`layers` is a non-empty list of flavors or profile types. A name resolves to a
repo flavor, then a kit flavor, then a profile type (see [Flavors](#flavors)).
A profile type goes through the profile loader, so `extends` still composes
inside it (`enonic` brings `core`). The skills of all layers are unioned in
layer order. An unknown name fails with the lists of flavors and profile types.
`devkit project init` writes the file (`--force` overwrites) and validates each
`--layer` the same way.

A client repo that must not carry a `harness/` directory keeps the file
elsewhere and passes `--config` to `build` and `status`. `init` has no
`--config` and always writes `harness/project.json`, so that file is written by
hand.

## Flavors

A flavor is a named, skills-only set: one JSON file per flavor in the kit's
`flavors/` folder, or in the repo's `harness/flavors/`. It carries no colour,
deps, MCP or instances, so it is not a profile type and `devkit profile create`
does not offer it.

```json
{
  "_comment": ["Skills for an Enonic XP 8 project."],
  "name": "enonic-xp8",
  "description": "Enonic XP 8: shared Enonic skills plus the XP 8 docs and React4XP 7 skills.",
  "includes": ["enonic-base"],
  "skills": ["develop-xp8", "develop-react4xp-v7"],
  "exclude": []
}
```

- `name` is required and equals the file name without `.json`. Any key other
  than `_comment`, `name`, `description`, `includes`, `skills`, `exclude` and
  `detect` is refused. `detect` must be an object; it is otherwise ignored for now.
- `includes` names flavors or profile types, resolved recursively; a loop or an
  unknown name is refused. `skills` are kit skill names (`core/skills`), never
  repo-owned ones: `harness/skills/` is linked by every build anyway.
- The skills of a flavor are its includes in order, then its own `skills`, minus
  `exclude`. An `exclude` entry the flavor does not hold is refused.
- A repo flavor with the same name as a kit flavor wins, and build and `status`
  print a `warn` line. A repo flavor named like a profile type is refused.
  Changing a repo flavor so the skill set changes shows up in `status` as drift.
  The whole `harness/flavors/` folder is loaded on every command, so one invalid
  file there makes `flavors`, `build`, `status` and `init` fail, even for layers
  that do not use it.

```
devkit project flavors                  # every valid layer name, tier, skill count
devkit project flavors enonic-xp8       # includes and resolved skills, in order
devkit project flavors --path ~/work/app   # also reads ~/work/app/harness/flavors
```

<!-- devkit:generated:flavor-table -->

| Flavor | Tier | Includes | Skills |
|--------|------|----------|--------|
| `enonic-base` | kit | `core` | 41 |
| `enonic-xp7` | kit | `enonic-base` | 45 |
| `enonic-xp8` | kit | `enonic-base` | 43 |

<!-- /devkit:generated:flavor-table -->

## Repo-owned layer

Anything under `harness/` is the repo's:

- `harness/skills/<name>/` become relative links, so a teammate who clones the
  repo gets them without devkit. They are not excluded, so the repo can commit
  them. A repo-owned skill with the same name as a base skill wins; the build and
  every `status` print `warn  .agents/skills/<name>: harness/skills/<name> wins
  over the base skill of the same name`. Directories starting with `.` are ignored.
- `harness/AGENTS.md` is the text of the generated `AGENTS.md`, after a
  generated-header line. With `--rules` the build appends the kit's rules,
  separated by a `---` line, (`core`, plus `client` when a layer's
  lineage includes `client`). Without `--rules` the rules are left out on
  purpose: a profile already projects them, and loading them twice costs tokens.
  `status` and later builds reuse the choice the stamp recorded; pass
  `--rules` or `--no-rules` to change it.

Only the base layer needs devkit. The committed repo-owned links are the
no-devkit path.

## Keeping a client repo clean

- The build creates untracked paths, writes `.git/info/exclude` and nothing
  else. It never edits or replaces a tracked file. A tracked path in the way of
  a link or file is skipped with `warn  <path>: <reason>`; a tracked
  `AGENTS.md` or `CLAUDE.md` is left alone and no instructions are written.
- A path the build did not create (a real directory, a foreign link) is skipped
  the same way. A link is the build's own only when it is in the stamp or points
  into `current/core/skills` or `harness/skills`.
- `.agents`, `.agents/skills`, `.claude` or `.claude/skills` that is a link or
  a file is left alone, so a build never writes through a link out of the repo.
- Generated entries live in a block of `.git/info/exclude` between
  `# >>> devkit project <id> >>>` and `# <<< devkit project <id> <<<`. `<id>` is
  `main`, or `worktree <name>` in a linked worktree. Linked worktrees share one
  `info/exclude`, so each worktree owns only its block and `clean` in one never
  un-hides another. Lines outside the block are never touched, and an unchanged
  block is not rewritten.
- No project command writes outside the repo and its exclude file. The kit home
  and profile folders are read only. The build never installs the kit; with no
  `current` it stops and says to run `install.py`.

## Status and clean

`devkit project status` compares the repo with what a build would write now and
exits 1 on a missing or dangling link, or an entry set that changed (a skill
added or removed in the kit, a changed layer, a stale `AGENTS.md`). A newer kit
release with the same entry set is printed as informational and exits 0. On a
repo that was never built it prints `not built` and exits 1.

A rebuild also prunes links in `.agents/skills` and `.claude/skills` that the
stamp lists, or that point into the kit's `core/skills` or the repo's
`harness/skills`, and are no longer wanted. The build owns `AGENTS.md` only while
its content still matches the stamp: after you edit it, a build warns that
instructions were not written, and `clean` leaves it.

`devkit project clean` on a repo with no stamp prints `nothing to clean` and exits 0.
Otherwise it removes the links and files the stamp lists, only while
they still point where the build put them, then this worktree's exclude block,
the stamp, and the `.agents` / `.claude` directories left empty. Repo-owned
links and tracked files stay. A project is not removed by `devkit-uninstall.sh`;
run `devkit project clean` in each repo first.

### Duplicates with the active profile

When `AGENTS_HOME` is set (a profile's shell) and the profile provides a skill
with the same name as a project skill, `status` prints a warning, because the
agent may load both. It does not change the exit code. Which copy wins is not
verified (see below).

## Verified behaviour

Checked on 2026-10-07 in a scratch git repo with a skill reached through
`.claude/skills/x -> ../../.agents/skills/x -> <absolute path outside the repo>`,
a repo-owned skill, and `CLAUDE.md -> AGENTS.md`.

| Check | Tool | Result |
|-------|------|--------|
| Lists a skill reached by the two-hop link, and a repo-owned relative one | Claude Code 2.1.280 | verified |
| Loads `CLAUDE.md` when it is a link to `AGENTS.md` | Claude Code 2.1.280 | verified |
| Lists the same skills from `.agents/skills` | Codex CLI 0.151.0 | verified |
| Loads `AGENTS.md` | Codex CLI 0.151.0 | verified |
| A skill of the same name at user level and project level: which wins | Claude Code, Codex | not verified: the run needs a scratch config dir with credentials, which was not set up |
| Loads `.agents/skills` | Cursor | reported by the owner, not verified here |
| `generate-agents-md.py --stdout --layer core` | the kit's `core/bin` copy | 606 lines; 712 with `--layer client` (run from the checkout; the same file ships in a release) |

## Not in v1

No static `export` of a project, no config lookup by repo name, no list-valued
`extends`, no `devkit doctor` check of built projects, no `CLAUDE.local.md` or
`AGENTS.override.md` fallback for a repo that already tracks `AGENTS.md`, and no
rules or kb projected into `.claude/rules`. Each waits for a consumer or an
unconfirmed vendor behaviour.
