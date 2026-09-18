---
id: how-to-cold-build-rfd-xp7-without-local-jvm
when_skills: [run-plan]
read: section
prose: caveman-lite
---

# How to cold-build the rfd XP7 app without the local JVM

**Related:** `acme-group-multitask/How-to-verify-worktree-changes-without-shared-xp-container.md` (same idea,
different project — that one is XP8/acme, this is XP7/rfd, and rfd's `Makefile` has no `coldBuild` target yet).

## The problem

`cd xp && ./gradlew build` on the host fails two different ways in this environment:

1. Whatever JVM is first on `PATH` (Java 17/21) throws `Unsupported class file major version 61` compiling the
   Groovy `settings.gradle` — this project's Gradle/Groovy version can't parse newer bytecode. Switching
   `JAVA_HOME` to a local Java 11 install fixes compile, but then:
2. `xp/build/` from a prior container-based build is owned by `root` (build artifacts were produced inside a
   Docker container running as root, then left on the host bind mount). `processResources` tries to `chmod` those
   files and fails with `Could not set file mode 777` — even though they're already `0777`, only the owning user
   can `chmod` them, and the host user isn't root.

Neither failure has anything to do with the code change being validated.

## The fix: docker run with the project's own CI image, no shared container

rfd has no `coldBuild` Makefile target (unlike acme-group) — build the equivalent by hand:

```bash
cd ${HOME}/Workspace/Projects/rfd
docker run --rm \
  -e JAVA_HOME=/home/builder/.enonic/distributions/enonic-xp-linux-sdk-7.10.3/jdk \
  -e GRADLE_USER_HOME=/gradle-home \
  -e npm_config_cache=/npm-cache \
  -v "$(pwd)/xp:/work" \
  -v rfd-cold-xp-node-modules:/work/node_modules \
  -v rfd-cold-gradle-project:/work/.gradle \
  -v rfd-cold-gradle-home:/gradle-home \
  -v rfd-cold-npm-cache:/npm-cache \
  -w /work \
  --entrypoint bash leanon/enonic-ci:7.10 \
  -lc 'export PATH=$JAVA_HOME/bin:$PATH && ./gradlew --no-daemon build && ls -la build/libs/*.jar'
```

- Image comes from `.gitlab-ci.yml`'s `.build_template` (`image: leanon/enonic-ci:7.10`) — the same image CI
  actually builds with, so a pass here is a real signal, not a proxy.
- `docker pull leanon/enonic-ci:7.10` first if not already local — it's a different tag from acme-group's
  `leanon/enonic-ci:8.0.4-node24` (XP8), don't reuse that one for an XP7 project.
- The image has **no `java` on `PATH` and no `JAVA_HOME` set by default** — its only JDK lives under
  `/home/builder/.enonic/distributions/enonic-xp-linux-sdk-7.10.3/jdk`, bundled as part of the vendored Enonic
  SDK distribution. Find it once with `docker run --rm --entrypoint sh leanon/enonic-ci:7.10 -c 'find / -iname
  java 2>/dev/null'` if the version tag ever changes.
- `-v "$(pwd)/xp:/work"` bind-mounts the **current checkout's** `xp/` directly — run this from inside a worktree
  and it builds that worktree's own diff, same as acme's `coldJar`.
- Named volumes cache `.gradle`/node_modules/npm across runs; they don't need clearing between builds.
- No `copyComponents`/prototype step here — rfd doesn't have the react4xp-prototype wiring acme-group does, so
  don't port that part of the acme Makefile.

Confirmed empirically (RFD-682, 2026-08-18): after a one-line fix in
`xp/src/main/resources/lib/rfd/api/webatlas.js`, this produced `BUILD SUCCESSFUL` and a jar in `build/libs/`,
while the host-JVM `./gradlew build` failed both ways described above on the same worktree.

## Confirmed on other XP 7 repos

Same recipe, unchanged except image tag and volume prefix, worked on **cookiebot-app**
(`xpVersion=7.11.1`, Gradle 8.3, plugin 3.4.0) on 2026-08-25 using
`leanon/enonic-ci:7.13.3-node20`. Two notes for that variant:

- **No `JAVA_HOME` env override needed** on the `7.13.3-node20` tag — the image sets it
  (`/opt/java/openjdk`, Temurin 17.0.17). Only `export PATH=$JAVA_HOME/bin:$PATH` is required.
  Drop the `-e JAVA_HOME=...enonic-xp-linux-sdk-7.10.3/jdk` line; that path exists only on `:7.10`.
- Building an app whose `xpVersion` (7.11.1) differs from the image's bundled SDK (7.13.3) is fine —
  the XP deps resolve from `xp.enonicRepo()`, so the image tag only supplies the JDK and Gradle
  runtime. Do not bump `xpVersion` to match the image.

Use a per-repo named-volume prefix (`cookiebot-cold-*`, `rfd-cold-*`) so the Gradle/npm caches do
not collide between projects.

## Pitfalls

- Don't try to fix the root-owned `xp/build/` by chmod/chown from the host user unless you actually have sudo —
  check with `sudo -n true` before assuming it's available; asking the user to `sudo rm -rf` or fix ownership
  themselves is the safer default when it's not.
- Don't reach for the local JVM at all once cold-build is available for this repo — even with the right
  `JAVA_HOME`, the root-owned `build/` dir blocks `processResources` regardless of which Java runs it.
- This proves compile + packaging (a real jar in `build/libs/`), not runtime/visual behavior. Still hand off
  production verification (URL matrix on a real property, Norkart 401 volume) as a separate, user-owned step.
- On `leanon/enonic-ci:7.13.3-node20` (and similar client CI tags), `JAVA_HOME` is set (`/opt/java/openjdk`) but
  `java` is not on the default `PATH`. Cold recipes must `export PATH=$JAVA_HOME/bin:$PATH` before
  `./gradlew`. Node in that image is **20.13.1**.
