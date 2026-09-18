# How to fix dual-shape view-model / x-data reads in Enonic XP apps

## Scope

Enonic XP 7 apps (confirmed on `as` / Authentic Scandinavia) where a shared module
reads booking-like data that arrives in **two shapes**:

- a **view model** with camelCase properties (`viewModel.bookingInfo`), or
- **raw content** from `contentLib.query` / `masterContext.query`, where the same data
  only exists under `content.x[<xDataName>]['booking-info']`.

Symptom: a value renders correctly in one email/page and falls back to a hard-coded
default in another, with no error logged. Cron/task code is the usual victim, because
tasks pass raw query hits while controllers pass view models.

## Prerequisites

- `git log --follow` on the shared module (the regression is almost always a commit that
  "cleaned up" a `a || trySafe(() => b)` read down to `a`).
- `grep -rn "<factoryFn>" xp/src/main/resources` to classify every call site as
  view-model or raw-content.

## Procedure

1. Find the fallback object. A silent wrong value usually means the resolution block was
   skipped and a constants default was returned (`lib/util/constants/index.js`), not that
   a computation was wrong. Match the wrong number against the default to confirm.
2. `git show <suspect>^:<path>` and diff against today. A narrowing from
   `x.foo || trySafe(() => x.x[xDataName]['foo'])` to `x.foo` is the signature.
3. Classify callers before editing:
   ```bash
   grep -rn "fromBookingViewModel" xp/src/main/resources
   ```
   Raw-content callers are the ones passing a query hit directly. In `as` there is exactly
   one (`lib/util/tasks/sendBookingPaymentRemind.js`); the other 15 pass view models.
4. Restore the `||` fallback rather than adapting the caller. It is additive and cannot
   change behaviour for the camelCase callers.
5. **Verify the fallback is inert for view-model callers** before claiming low risk:
   ```bash
   grep -n "x: .*\.x" xp/src/main/resources/lib/modules/viewModel/index.js
   ```
   No hit means no view model carries `x`, so the restored branch is unreachable for them.
   A hit means the restoration changes view-model behaviour too — adapt the caller instead.

## Pitfalls

- Two identical source lines in different functions: edit by line number (a small
  `python3` script), not by string match, or you will patch the wrong one.
- `fillMissingWithDummyDates` mutates the option object it receives. Reached through
  `booking.x[...]` on an in-memory query hit nothing is persisted, but do not add a
  `modify`/`publish` of that object.
- The scheduling queries and the template substitution are separate paths. A correct
  send date with a wrong printed date means only the substitution is broken — do not
  touch the queries.
- After the reminder caller is already a flattened view model, unique conditions
  with **no Availability** can still fall through to the site default. That is
  `fillMissingWithDummyDates` using `DateFns.minTime` / `DateFns.maxTime`, which
  `/lib/external/date-fns` does not export (`Invalid Date`). See
  [How-to-fill-missing-payment-condition-availability-with-valid-dates.md](./How-to-fill-missing-payment-condition-availability-with-valid-dates.md).
  Do not restore `viewModel.x[...]` reads to fix that (AS-1167).

## Running the linter in `as`

Root `.eslintrc.json` extends `standard`, but `eslint-config-standard` is not installed
(there is no root `node_modules`). The only eslint binary is `xp/node_modules/.bin/eslint`
(v5, no `--resolve-plugins-relative-to`). To lint a touched file:

```bash
node --check <file>
xp/node_modules/.bin/eslint -f compact --no-eslintrc -c <minimal-config> <file>
```

with a minimal config enabling `no-undef` / `no-unused-vars` and the XP globals
(`Java`, `__`, `app`, `log`, `resolve`). Say explicitly in the report that the project's
configured `standard` ruleset could not be run.
