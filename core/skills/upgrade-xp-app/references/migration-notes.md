# Migration notes

## What changes between XP 7 and XP 8

Full breaking-change and descriptor notes live in progressive disclosure — read `~/.agents/kb/implementation/xp7-to-xp8-upgrade/xp7-to-xp8-changes.md` when executing or diagnosing an upgrade. Keep this SKILL.md focused on Detect → Plan → Execute → Verify.

## Tips for the conversation

- **Narrate before you act.** Before each step that runs a command or edits a file, say in one line what you're about to do and why, so the
  user can follow along and step in before it happens — don't open with silent tool calls. For consequential or hard-to-reverse actions
  (the migrator run, file deletions, the build, a deploy, a CLI install), state the intent and, where the workflow calls for it, wait for
  the go.
- **Quote what you found.** When presenting the plan, quote the actual current values (`xpVersion = 7.9.0`, plugin `3.6.2`) so the user can
  tell at a glance you read their files instead of guessing.
- **Use diffs, not prose.** When the change is non-trivial (e.g. multi-line `build.gradle` plugin or dependency edits), show a unified-diff
  snippet in the plan so the user can approve precisely what will land.
- **Don't auto-touch generated/wrapper files.** `gradlew`, `gradlew.bat`, `gradle/wrapper/gradle-wrapper.jar` should not be hand-edited. If
  Gradle needs to be bumped, run the wrapper task: `./gradlew wrapper --gradle-version 9.0.0`.
- **Stop on the first deal-breaker.** If a required file is missing or in an unexpected location, ask before proceeding — don't synthesize a
  guess.
- **Hand off to siblings when relevant.** For enonic CLI usage during the upgrade, consult `use-enonic-cli`. For build failures, point to
  `debug-xp-app`.

## See also

- <https://raw.githubusercontent.com/enonic/doc-code/refs/heads/master/docs/upgrade.adoc> — upstream Enonic XP 7 → XP 8 app upgrade guide (
  source of truth)
- `~/.agents/kb/implementation/xp7-to-xp8-upgrade/examples.md` — full `xplibs.*` alias tables (6 APIs + 24 libs), worked `build.gradle` examples (site app with version catalog;
  TS app with custom `dev` task), TypeScript wiring with `@enonic-types/*`
- `~/.agents/kb/implementation/xp7-to-xp8-upgrade/manual-schemes-migration.md` — comprehensive set of descriptor transformations (paths, `kind:` map, field renames, special
  cases) — read this when the migrator is unavailable or when reviewing what it produced
- <https://raw.githubusercontent.com/enonic/doc-xp/refs/heads/8.0/docs/release/upgrade.adoc> — full instance-level upgrade guide
  (dump/load, security, management API changes)
- `debug-xp-app` skill — diagnose build/runtime errors after upgrade
- `use-enonic-cli` skill — full reference for every `enonic` command this skill uses (`project build`/`deploy`, `sandbox create`/`list`,
  `dump create`/`load` for the data side)
