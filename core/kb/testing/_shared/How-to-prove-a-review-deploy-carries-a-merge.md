# How to prove a review deploy carries a merge (when the change is a deletion)

**Scope:** `_shared`
**Applies to:** any environment where you must show that the app serving traffic
contains a specific merge, and the merge's visible effect is that something is *gone*.

## Why absence is never the gate

"The bad token is not in the served HTML" is equally true of:

- a build that never contained the fix,
- a build that predates the merge,
- a 404 or an error page,
- a cached response from before the deploy.

A deletion therefore cannot be evidenced by its own absence. You need a **positive,
countable token produced by the same merged head**.

## Procedure

1. **Find a co-located positive marker.** Look for another ticket that merged into the
   same branch and added something in the *same* region of the *same* served artefact —
   ideally the same `<head>`, the same file, adjacent lines. A sibling ticket that lost a
   merge conflict against yours is ideal: the conflict resolution means both outcomes are
   visible in one place.

2. **Assert both directions in one request.** One fetch, two counts: the marker must be
   present at its exact expected count, and the deleted token must be zero.

```bash
BODY=$(curl -s -m 30 -A "Mozilla/5.0" -H "Cache-Control: no-cache" "$URL")
echo "$BODY" | grep -c 'rel="preload"'           # positive marker, expect exactly N
echo "$BODY" | grep -ciE 'httpequiv|http-equiv'  # deleted token, expect 0
```

   Marker present **and** token zero is the only passing combination. Marker present *and*
   token present means the conflict was resolved the wrong way — that is a defect report,
   not a retry.

3. **Add the build fingerprint.** Enonic XP stamps an app version into every asset URL
   (`/_/asset/<app.name>:<fingerprint>/...`). Extract it and record it; it changes on every
   jar install, so it dates the deploy independently of anything in your diff.

```bash
grep -oE '<app\.name>:[0-9a-f]+' body.html | sort -u
```

4. **Rule out cache before calling a fail.** Three layers commonly sit between deploy and
   browser: an app-level cache (Booster), an HTTP tier returning `age` / `x-cache`, and the
   application's own per-host page cache in `live` mode. Re-request with
   `-H "Cache-Control: no-cache"` and read `age` / `cache-status` from the response headers
   before concluding the deploy is missing.

## Pitfalls

- **A green `review_deploy` does not mean XP installed the jar.** On the client XP8 helm
  deploy (`.xp8_helm_deploy_template`) the job can report `Release … upgraded` while the
  running pod keeps the previous bundle (no pod restart, no install). Prove the install in
  the XP log, timestamped after the deploy job finished:

```bash
kubectl -n enonic-review logs acme-group-0 -c xp-app --since=24h --timestamps \
  | grep -E 'ApplicationRegistryImpl|ApplicationServiceImpl' | grep '<app.name>' | tail -4
```

  Expect `Installed application <app.name> bundle N` + `Started application …` after the
  job's `finished_at`. No such line = the precondition fails; stop before any content write.
  (acme-group, 2026-09-24: pipeline 88472 deploy green 13:31Z, last install bundle 142 at
  2026-09-23 23:41Z.)
  An install can also land later with **no** new pipeline (bundles 143/144 on 2026-09-24 15:21Z,
  source jar not provable from GitLab). Then prove the build by a log line only the new code emits.

- **Multi-line tags defeat line-based greps.** Attributes wrap across lines in served HTML,
  so `grep -oE '<link[^>]*preload[^>]*>'` returns nothing on a page that has all of them.
  Match on a single attribute (`rel="preload"`), or normalise newlines first
  (`tr -d '\n'`) before matching whole tags.
- **Assert both spellings of a camelCase token.** A template engine that passes unknown
  attributes through verbatim will emit `httpEquiv`, while HTML-correct code emits
  `http-equiv`. Grep case-insensitively for both (`grep -ciE 'httpequiv|http-equiv'`) so the
  check cannot pass by spelling the token wrong.
- **Re-run the gate at execution time.** A passing reading taken during planning is not a
  substitute: a redeploy, a rollback or a cache layer can regress it in between.

## Sample data

Jotron review, JOT-293 (deletion) with JOT-284 (addition) as the co-located marker; the two
tickets conflicted on adjacent lines of the same `<head>`:

```
preload count                   -> 3
httpequiv|http-equiv count      -> 0
asset fingerprint               -> com.example.jotron:000001a090959fc0
```
