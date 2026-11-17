# How to bump an XP 8 minor and regenerate the lock in the CI image

## Scope

acme-group style XP 8 minor upgrades (e.g. 8.0.4 to 8.1.0) where host npm/gradle under `xp/` is forbidden.

## Procedure

1. Pin edits: `xp/gradle.properties` xpVersion, `xp/settings.gradle` plugin, `gradle-wrapper.properties` distributionUrl (Gradle properties edit is enough, no wrapper jar change), `xp/gradle/libs.versions.toml`, image tags (`grep -rn "<old>"`).
2. Lock regen without host npm: `docker run --rm -v $PWD/xp:/work -v acme-cold-npm-cache:/npm-cache -w /work --entrypoint bash <ci-image> -lc 'npm install --package-lock-only; npm update --package-lock-only <@enonic-types/* names>; chown $(id -u):$(id -g) package*.json'`.
3. Verify: `make coldBuild`, then `npm run check` in the same image with `-v acme-cold-xp-node-modules:/work/node_modules` after `npm ci`.

## Pitfalls

- The Makefile has no check target; use the docker run above.
- `git rm` stages; `git restore --staged` to leave deletions unstaged.
- `@enonic/js-utils` 2.x still resolves `object/getIn` through the `./*` export, so the import needs no change.
