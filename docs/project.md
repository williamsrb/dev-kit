# Projects

`devkit project` applies the harness to a work repo, next to profiles instead of
instead of them. A **profile** carries how the agent runs: hooks, MCP, auth,
environment, the desktop identity. A **project** carries what the agent knows:
the skills of the profile types you name, skills the repo owns, and an
`AGENTS.md`. A project never writes hooks, MCP, settings, auth or `AGENTS_HOME`.

Use a project when a team should get the same skills in a repo without each
developer creating a profile. Keep using profiles for isolation between
accounts, tools and desktop apps. The two compose: a developer with an active
profile can also build a project (see [Duplicates](#duplicates-with-the-active-profile)).

```bash
cd <repo>
devkit project init . --layer core --layer enonic --apply   # writes harness/project.json
devkit project build .                                      # dry run: lists every link, file and exclude entry
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

`layers` is a non-empty list of profile types of the installed kit. Each goes
through the profile loader, so `extends` still composes inside a type (`enonic`
brings `core`). The skills of all layers are unioned in layer order. An unknown
type fails with the list of the kit's profile types. `devkit project init`
writes the file (`--force` overwrites) and validates each `--layer` against the
installed kit.

A client repo that must not carry a `harness/` directory keeps the file
elsewhere and passes `--config` to `build` and `status`.

## Repo-owned layer

Anything under `harness/` is the repo's:

- `harness/skills/<name>/` become relative links, so a teammate who clones the
  repo gets them without devkit. They are not excluded, so the repo can commit
  them. A repo-owned skill with the same name as a base skill wins; the build
  reports the base skill as skipped.
- `harness/AGENTS.md` is the text of the generated `AGENTS.md`. With `--rules`
  the build appends the kit's rules (`core`, plus `client` when a layer's
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
release with the same entry set is printed as informational and exits 0.

`devkit project clean` removes the links and files the stamp lists, only while
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
