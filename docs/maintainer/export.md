# Changing what ships

`core/` is generated. Editing it directly is drift by definition — that is what
`devkit export --check` exists to catch.

```bash
./devkit export              # dry run
./devkit export --apply
./devkit export --check      # exit 1 if core/ is behind its source
```

## The allowlist

`export-allowlist.json` decides what ships, per layer. Three things about it are
load-bearing:

**`hard_excludes` wins over every allowlist entry.** A directory carrying
credentials cannot be re-admitted by a careless allowlist edit.

**Patterns are anchored at the export root.** Prefix with `**/` to mean "a
directory of this name at any depth". This distinction was learned the hard way:
an unanchored `graft/`, meant for the graph cache at the root, also matched
`skills/graft/` and silently dropped a real skill from the export.

**Every exclusion records its reason.** The `excluded` blocks are maps, not
lists, so `"ppt-master": "gitignored multi-hundred-MB asset trees"` survives as
an auditable decision rather than becoming a mystery.

## Adding a skill

Adding a skill to `core` is a publication decision. It ships to everyone who
installs the kit.

1. Put it in the right layer. `core` is generic; `enonic` is technology-bound;
   `client` carries anything that names a customer.
2. `./devkit export --apply` and read the gitleaks output.
3. `./devkit lint-paths` — a new skill often brings `~/` in a link target.
4. `python3 -m unittest discover -s tests` — one test asserts every skill on
   disk is classified, so an unlisted skill fails rather than vanishing quietly.

## Client identifiers

Core skills must not name a customer. If one needs a client-bound value, it
reads `config/client-overlay.json`; `core/` ships only the `.example.json`, and
the client profile supplies the real file.

When you find a client identifier in a core skill, sort it before fixing it:

- **Illustrative** — an example URL or path. Replace with a placeholder shape,
  keeping the structure: `https://review.<project>.<env-domain>/`.
- **Routing** — "open `<client>/How-to-…`". Make the route generic and let the
  project's own knowledge-base folder supply the specifics.
- **Behavioural, in code** — this is the only kind that needs a code change.
  Move the value into the overlay config.

With no overlay config present, a check that depends on it must be **skipped**,
not guessed at. A fallback heuristic fires on legitimate input.

## The secret gate

`gitleaks` runs over the result on every `--apply`. Verified false positives go
in `.gitleaks.toml`, scoped by path *and* by pattern.

The current entry covers Enonic's own API documentation, which uses content and
node UUIDs in every example. Those identify sample content in a doc build, and
the docs are vendored verbatim so they cannot be edited to avoid the pattern.

## Drift

`devkit export --check` is the gate. Wire it into a cron job beside the existing
session-sync job so drift surfaces instead of accumulating.
