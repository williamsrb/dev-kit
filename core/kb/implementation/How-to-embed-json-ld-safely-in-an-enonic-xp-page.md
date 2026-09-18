# How to embed JSON-LD safely in an Enonic XP page

**Scope:** XP 7 / React4XP server controllers that inject `application/ld+json` into the page
**Applies to:** `lib/modules/structured-data`-style builders, part/layout controllers, `default.js`-style page controllers
**Related:** [How-to-add-a-head-tag-from-a-react4xp-part.md](./How-to-add-a-head-tag-from-a-react4xp-part.md)

## Scope

Two recurring defects in schema.org JSON-LD emitted from XP controllers:

1. escaping re-implemented inline at each call site, and escaping only `</`;
2. `dateModified` published earlier than `datePublished` on every freshly published content.

Both were review-bounced on jotron JOT-269/JOT-270.

## Procedure

### One serialiser, escape every `<`

Export a single serialiser from the schema module and call it from every controller.

```ts
export function serialiseJsonLd(value: any): string | null {
    if (!value) {
        return null
    }
    // Every `<` is escaped, not only `</`: the script-data tokenizer also breaks
    // on `<!--`, and `<` parses back to `<`.
    return JSON.stringify(value).replace(/</g, '\\u003c')
}
```

- `<` is the JSON escape for `<`, so the block still parses and the consumer sees `<`.
- `JSON.stringify(x).split('</').join('<\\/')` is the incomplete idiom to replace: it leaves `<!--`,
  which the HTML script-data tokenizer also treats as special.
- The block is injected with `dangerouslySetInnerHTML` (react4xp entry) or a Thymeleaf
  `th:utext` model field — neither escapes, so the serialiser is the only guard.
- Verify with `grep -rn "split('</')" xp/src/main/resources` returning nothing.

### `dateModified` only when the content was really edited

XP's publish operation writes `publish.from` and leaves `modifiedTime` at the last draft save, so
`datePublished` (from `publish.from`) and `modifiedTime` are **never equal** and `modifiedTime` is
usually **earlier**. A string-equality guard therefore never fires and every fresh publish advertises
a modification preceding its own publication.

```ts
if (!input.dateModified || !input.datePublished) {
    return undefined
}

const modified = new Date(input.dateModified).getTime()
const published = new Date(input.datePublished).getTime()

if (!(modified > published)) {
    return undefined
}

return input.dateModified
```

- Compare instants, not strings: the two values can carry different fractional precision
  (`...T10:00:00Z` vs `...T10:00:00.000Z`), so a lexical `>` can disagree with the real order.
- `!(modified > published)` also drops `NaN` from an unparseable date; a plain `<=` does not.

## Pitfalls

- **Nashorn:** `new Date().getTime()`, `String.prototype.replace` and a global regex literal are all
  safe. `Array.prototype.includes`, `Object.assign` and `async`/`await` are not polyfilled by the
  tsup/esbuild pass — use `indexOf(x) !== -1`.
- Do **not** rename an already-exported serialiser to "improve" it when sibling tickets call it; the
  rename is churn on their call sites for no behavioural gain.
- A schema module shared by several tickets is a merge hot spot. One key owns the serialiser change
  and lands first; the others record it as satisfied instead of re-implementing it.
- The change is invisible to the Rich Results Test when the escaped characters never occur in the
  content. Prove it on the serialiser's own output (round-trip `JSON.parse`), not on a live page.

## Sample data

```
input  { datePublished: '2026-09-16T10:00:00Z', dateModified: '2026-09-14T08:12:00Z' } -> undefined
input  { datePublished: '2026-09-14T08:00:00Z', dateModified: '2026-09-16T10:00:00Z' } -> '2026-09-16T10:00:00Z'
value  { headline: '</script><!-- x' } -> {"headline":"</script><!-- x"}
```
