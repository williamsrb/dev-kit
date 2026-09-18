---
id: how-to-run-xp-tests-in-detfinneshjelp
when_skills: []
read: section
prose: caveman-lite
---

# How to run XP tests in detfinneshjelp

Server-side Enonic XP 7 tests for `detfinneshjelp` (services and libraries that call XP APIs).

## Prerequisites

- Work from `${HOME}/Workspace/Projects/detfinneshjelp/xp`.
- Confirm `xpVersion` in `gradle.properties`.
- Keep XP Test Framework dependency and JavaScript tests aligned with that version.

## Procedure

1. Use the XP Test Framework dependency in `build.gradle`:

   ```groovy
   testImplementation "com.enonic.xp:testing:${xpVersion}"
   ```

2. Put CommonJS tests under `src/test/resources/`, mirroring the resource path.
3. Add a `ScriptRunnerSupport` Java bootstrap under `src/test/java/` that returns the test resource path.
4. Mock `/lib/xp/*` and application library dependencies with `test.mock()` before requiring the module under test.
5. Run `./gradlew test` from `xp/`.

## Pitfalls

- This repository has no Jest configuration or Jest test project. `npx jest --selectProjects SERVER --no-coverage` is not a valid harness here; use the XP Test Framework for server-side runtime fidelity.
- The local `./gradlew test` task can pass with zero tests before the XP dependency and bootstrap are added, so verify the generated XML reports contain the expected test functions afterward.
- Runtime replay still requires a running/deployed XP instance; do not deploy or start a sandbox as part of a read-only test run.
