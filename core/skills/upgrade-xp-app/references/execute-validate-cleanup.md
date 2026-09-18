# Execute, validate, and clean up

### 4. Execute

If the plan included installing the Enonic CLI (Detect found it missing), do that first — the Validate step needs it:
`npm install -g @enonic/cli` (or the platform fallback from How-to-run-xp8migrator).

Apply the approved changes in two passes — descriptors first via the migrator, then build/code edits by hand.

**Descriptor pass (xp8migrator):**

```sh
# from the app project root
curl -fsSL https://raw.githubusercontent.com/enonic/xp8migrator/main/migrator-install.sh | sh
./migrator -e overwrite         # non-interactive — overwrite any pre-existing target files
```

> ⚠️ **Flag this to the user before running it.** The `curl … | sh` install pipes a remote script straight into a shell, which may require explicit user approval in Cursor agent mode. Tell the user up
> front that unattended runs may be blocked, and offer them the choice: run the installer themselves in a terminal, or approve the Shell command
> interactively. Once `./migrator` exists in the project root, the rest of the descriptor pass proceeds normally.

If the migrator errors out, run `./migrator -h` to inspect the available flags. **Don't run the migrator a second time with `-x`** — its
post-migration step tries to move `cms/style/style.yaml` again and fails with `FileAlreadyExistsException`. Cleanup of the original XML
happens via plain `rm` after the build is green (see the Cleanup step), not via `./migrator -x`.

The migrator leaves the original `site/` tree and `application.xml` in place. Sibling `.js`, `.html`, and `.svg` files are *copied* into the
new `cms/` location during migration. Don't delete anything yet — let `enonic project build` validate the result first. If it fails, the
originals are still there for diagnosis.

On Windows, use `.\migrator.exe` and the PowerShell installer (`migrator-install.ps1`). Useful flags: `-h` (help), `-a <app-name>` (override
`gradle.properties`), `-e ask|overwrite|skip` (conflict policy — use `overwrite` for non-interactive runs).
See <https://github.com/enonic/xp8migrator> for the canonical CLI reference.

If `xp8migrator` is unavailable (offline environment, descriptor not handled by the tool), fall back to hand-edits per
`~/.agents/kb/implementation/xp7-to-xp8-upgrade/manual-schemes-migration.md`.

**Build / code pass (hand-edits):**

Edit the files in-place (StrReplace/Write tools in Cursor) for changes to `build.gradle`, `gradle.properties`, and any controller/template
fixes. Keep edits minimal — don't reformat unrelated lines, don't change content the user didn't approve.

### 5. Validate (before any deletion)

Run `enonic project build -f` first — that catches descriptor-syntax errors and
dependency-resolution failures. The CLI drives the project's Gradle wrapper internally, so failures come back as ordinary Gradle output —
report success or paste the first failure with its file/line. If the build fails, the original `site/` tree and `application.xml` are
still in place, so the user can inspect them while you suggest a fix; ask before retrying.

**A green build does NOT prove the dependency set is right.** XP `include`s aren't transitive, so a bundled lib's runtime
`require('/lib/xp/*')` never surfaces at build time (see the *Migrate dependencies* edit under "Build files") — the only evidence that a
declared dep is used, or that a candidate for removal is truly dead, is a **JAR-level `require` scan** of the built artifact:

```sh
unzip -o build/libs/<app>.jar -d /tmp/<app>-jar >/dev/null
grep -rhoE "require\(['\"]/lib/[^'\"]+" /tmp/<app>-jar | sed -E "s/require\(['\"]//" | sort -u
```

Every `/lib/xp/<name>` the scan lists must have a matching `xplibs.<name>` `include`. This scan is the *prerequisite* for any dependency
pruning — and pruning itself is post-upgrade work, **out of scope for this skill**. During the upgrade, never remove an `include`.

### 6. Cleanup (only after the build is green AND the user confirms)

Once `enonic project build` passes, **ask the user whether to delete the originals before doing it** — don't remove anything automatically.
A green build with descriptors in both XML and YAML forms is a valid, recoverable state; once the originals are deleted the change is hard
to reverse without git. Phrase the prompt as a yes/no question listing the exact paths, e.g. "Build passed. OK to delete
`src/main/resources/site/`, `src/main/resources/application.xml`, and `./migrator`?"

Only after the user confirms, run:

```sh
rm -rf src/main/resources/site
rm src/main/resources/application.xml
rm ./migrator                   # remove the binary too
```

**Do NOT uninstall the Enonic CLI** during cleanup. Unlike `./migrator` (a single-purpose binary dropped into the project), the CLI is a
machine-level developer tool — if the upgrade installed it, it stays installed.

The migrator already copied sibling `.js`/`.html`/`.svg` files from `site/` into `cms/`, so wiping the entire `site/` directory is safe.
(Use plain `rm`, never `./migrator -x` — see the Descriptor pass under Execute.)

If both `cms/style/style.yaml` and `cms/styles/image.yaml` exist after migration (older migrator versions emitted both), delete
`cms/styles/image.yaml` — `cms/style/style.yaml` is the canonical XP 8 form.

### 7. Deploy (optional)

After cleanup, **ask the user whether to deploy** — don't run it automatically. Deploying mutates state outside the project (the sandbox),
so it warrants explicit confirmation. Phrase it as a yes/no question, e.g. "Build passed. Want me to deploy to a sandbox with
`enonic project deploy`?"

If the user says yes, run the deployment **purely via the Enonic CLI** — no direct gradle invocations — and follow the non-interactive
discipline from "Running the Enonic CLI non-interactively" above: list the candidates, let the *user* pick, then run with everything
pinned as explicit flags.

```sh
enonic sandbox list      # read-only — sandboxes + distro versions; the running one (only one at a time) is marked with a leading "*"
```

1. **Pick the sandbox WITH the user — never let `-f` choose.** From the list, present the sandboxes whose distro matches the app's new
   `xpVersion` (an XP 8 app on a leftover XP 7 sandbox fails to load) and ask which one to use — or whether to create a fresh one. If a new
   sandbox is needed, confirm the version, then create it with the **Essentials** template:
   `enonic sandbox create <name> -v <xpVersion> -t essentials -f`.
2. **Check whether a sandbox is already running before offering to start one.** In the `enonic sandbox list` output the running sandbox is
   marked with a leading **`*`**, and only one sandbox runs at a time. So:
    - **The sandbox you picked is already running** (`*` next to it) → don't start anything; stage the JAR with
      `enonic project deploy <sandbox> --skip-start -f` and the live server hot-loads it.
    - **A *different* sandbox is running** → you can't start the target while it's up. Surface this to the user; they decide whether to stop
      the running one (`enonic sandbox stop <name>`, for a detached sandbox) or just deploy to the one already running.
    - **Nothing is running** → proceed to settle the start mode below.
3. **Settle the start mode (when nothing relevant is already running).** `enonic project deploy <sandbox>` will, by default, start the
   sandbox and **attach to a long-running foreground XP server that hangs the agent shell**. Ask the user which they want:
    - `enonic project deploy <sandbox> --skip-start -f` — builds and stages the JAR into the sandbox without starting it (no live runtime,
      but the shell returns immediately); or
    - `enonic project deploy <sandbox> -f` run **in the background** (Shell with `block_until_ms: 0` in Cursor) — when they want a live runtime to
      poke at. Read the command's own output to report startup; do not otherwise probe the server (see below).

Always name the sandbox explicitly. Reach for `-f` only after the sandbox and start behaviour are pinned — it is there to suppress the
prompts you have already answered, not to answer them for you.

**Confirm the sandbox started — do not verify the app installed.** Report only what the deploy/start command itself prints (the sandbox
started, or the first failure with file/line). **Don't check whether the app actually installed** — don't open the Applications list,
don't tail `server.log`, don't grep XP_HOME. Once the sandbox reports started, hand the user a link to view it themselves:

- **Admin console / launcher:** <http://localhost:8080/admin> — default dev port is `8080`; if you passed `--http.port`, use that port.

The user inspects the running app from there. If they hit a runtime/load error and want help, hand off to the `debug-xp-app` skill.
