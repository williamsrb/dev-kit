---
id: xp7-to-xp8-changes
when_skills: [upgrade-xp-app, run-plan]
read: section
prose: caveman-lite
---

# What changes between XP 7 and XP 8

Apply only the items that exist in the user's app. Do not invent files.

Open only the matching family file.

| Family | File |
|--------|------|
| Build files | `changes-build-files.md` |
| Application descriptor | `changes-application-descriptor.md` |
| Admin tools | `changes-admin-tools.md` |
| Admin widgets → admin extensions | `changes-admin-widgets-admin-extensions.md` |
| APIs | `changes-apis.md` |
| Site descriptors → `cms/` tree (YAML) | `changes-site-descriptors-cms-tree-yaml.md` |
| Server-side configuration files | `changes-server-side-configuration-files.md` |


> **Verify the public API of any XP `lib-*` before editing JS/Java that calls it.** This skill's lists of removed/renamed functions are a
> starting point, not the source of truth — they may be incomplete or out of date. Library APIs evolve between XP 8 pre-releases. Before
> recommending a replacement function (`getHomeToolUrl`, `extensionUrl`, etc.), confirm it actually exists by reading the relevant
> `.ts`/`.js` file **at the release tag matching the `xpVersion` you're pinning**, not `master` — `master` can be a major ahead of what you
> install (read it only when you're tracking the very latest or a SNAPSHOT). Browse the libs at
> <https://github.com/enonic/xp/tree/master/modules/lib/> and switch the branch selector to that tag. Don't assume a function survived just
> because it was in XP 7; the same applies to Java APIs — verify before editing controllers that import XP types.

