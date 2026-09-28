---
id: manual-schemes-7-sibling-files-and-cleanup
when_skills: [upgrade-xp-app, run-plan]
read: section
prose: caveman-lite
---

## 7. Sibling files and cleanup

The migrator copies — but does not move — sibling files (`.js`, `.html`, `.svg`) next to the descriptor into the new `cms/` location. After
running with `-x`:

- `site/parts/heading/heading.xml` → deleted (descriptor migrated)
- `site/parts/heading/heading.js` → still present (leftover)
- `cms/parts/heading/heading.yaml` → new
- `cms/parts/heading/heading.js` → copy of the original

The old `site/` tree is left as a husk of orphaned `.js`, `.html`, and `.svg` files. **Manual cleanup required after the user verifies the
migration:**

```sh
rm -rf src/main/resources/site
```

Run this only after confirming the new `cms/` tree is complete and the controllers under `cms/` match what the new YAML descriptors
reference. (XP 8 looks for the controller `<name>.js` next to its `<name>.yaml`, so the JS must live in `cms/<...>/<name>.js`, not the old
`site/<...>/<name>.js`.)
