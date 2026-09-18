---
id: how-to-add-an-editor-facing-input-to-an-xp7-schema
when_skills: [run-plan, plan-implementation, validate-impl]
inputs: [an XP 7 site.xml or content-type XML, i18n/phrases*.properties]
outputs: [an input that is labelled in every locale and degrades to prior behaviour while empty]
read: section
prose: caveman-lite
---

# How to add an editor-facing input to an XP 7 schema

**Scope:** adding a `CheckBox`, repeating `TextLine`, or similar input to
`site/site.xml` or `site/content-types/<type>/<type>.xml` in a client XP 7 app, when the
field ships empty on every existing content item. Verified on jotron (JOT-270, XP 7.14.4).

## Prerequisites

- The schema XML and both `i18n/phrases.properties` and `i18n/phrases_no.properties`.
- In-repo precedent for the input type; the descriptor XML is **not** covered by the
  offline XP 7 catalog (`api/lib-schema.md` documents the runtime dynamic-schema API, a
  different thing), so precedent in the repo is the source of truth.

## Procedure

1. **Copy an existing input of the same type.** A `CheckBox` is `<label>` +
   `<occurrences minimum="0" maximum="1" />`. A repeating text list is
   `<input type="TextLine">` with `<occurrences minimum="0" maximum="0" />` — `maximum="0"`
   means unbounded, not zero.
2. **Add `<help-text>` when the field drives something invisible** (a schema, a feed, a
   crawler file). Key convention is the label key plus `_help-text`.
3. **Add every key to BOTH properties files.** A key present in only one locale renders as
   the raw key in Content Studio for the other. Norwegian copy is a translation of the
   English label, not new product copy. Both files are plain UTF-8 — write `ø`/`å`
   literally, do not `\u`-escape.
4. **Read it back-compatibly.** XP unwraps a single repeating value, so always
   `forceArray` from `/lib/modules/util/collections`. A `CheckBox` arrives as `true`
   **or** the string `'true'` — accept both (`flag === true || flag === 'true'`), the
   pair `lib/modules/product/index.ts` already handles for its hide flag.
5. **Keep the old behaviour as the fallback, do not replace it.** Every existing content
   item predates the field, so an empty field must produce byte-identical output. Trim
   entries and drop blanks before use, then fall back to whatever shipped before
   (a module constant, a string match) when the trimmed list is empty. `log.warning`
   (a Nashorn global, no import) is the way to make the fallback visible without
   changing output.
6. **Which field-set.** Check that the one the plan names actually exists — plans written
   from a Jira comment often name a grouping the XML does not have. Prefer the field-set
   already holding the nearest related field over inventing one, since a new `<field-set>`
   costs a fifth i18n key pair that the requirement did not budget for.

## Verification without a running instance

No sandbox is needed to prove steps 1-3. This catches the two failures that actually ship
(malformed XML, a key missing in one locale):

```python
import xml.dom.minidom, io, re
keys = set()
for p in ['site/site.xml', 'site/content-types/office/office.xml']:
    xml.dom.minidom.parse(p)                      # well-formedness
    keys |= set(re.findall(r'i18n="([^"]+)"', io.open(p, encoding='utf-8').read()))
for props in ['i18n/phrases.properties', 'i18n/phrases_no.properties']:
    present = {l.split('=', 1)[0].strip()
               for l in io.open(props, encoding='utf-8').read().splitlines()
               if '=' in l and not l.strip().startswith('#')}
    print(props, sorted(k for k in keys if k not in present))
```

Run it from `xp/src/main/resources`. It also surfaces **pre-existing** gaps (jotron is
missing `site.input.vacancy_base_url` in `phrases_no.properties`) — diff against
`git stash` output before claiming one as yours.

## Pitfalls

- `npx tsc --noEmit -p tsconfig.xp.nashorn.json` cannot run in a worktree: `xp/node_modules`
  is not installed there and the config is broken independently (jotron DECISIONS R31/R44,
  ~23 pre-existing errors). `node --experimental-strip-types --check <file>.ts` is a real
  syntax gate that needs nothing installed; it is not a typecheck and must not be reported
  as one.
- Ticking the new box on existing content is a **content action**, not part of the commit.
  Say so explicitly, or a reviewer reads the unchanged output as a broken feature.
