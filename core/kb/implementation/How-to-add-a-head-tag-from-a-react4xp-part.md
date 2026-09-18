# How to add a `<head>` tag from a React4XP part without touching the page controller

## Scope

Enonic XP 7 + React4XP 5.x, where a `<meta>`, `<link>` or `<script>` must reach
`<head>` on **only the pages that carry one part**. Avoids editing the shared
page template, which in a multi-branch project is the worst merge-conflict site
in the repo.

Does not apply to tags that must appear on every page — those belong in the page
controller or template.

## Prerequisites

- The part is `site/parts/<name>/<name>.{xml,ts,tsx}` and its controller returns
  `render()` from `/lib/enonic/react4xp`.
- The page template actually has a `</head>`. Page contributions to `headBegin` /
  `headEnd` are **silently dropped** if the tag is missing.
- Response content type is `text/html`. Contributions are skipped otherwise.

## Procedure

1. Pass `pageContributions` as the **4th argument** to `render()`. The generic XP
   docs only show a raw controller return; with React4XP 5 the 4th arg is the
   route, and the lib merges it with the entry's own contributions:

```ts
return render(component, props, request, {
    pageContributions: {
        headEnd: ['<meta name="robots" content="noindex, follow">']
    }
})
```

`headBegin`, `headEnd`, `bodyBegin`, `bodyEnd` are the four positions. Values are
plain text and duplicates are de-duplicated by the Site Engine.

2. Confirm nothing else already emits the same tag. In a site running third-party
   admin apps (SEO Meta Fields, Security Headers, Favicon…) the tag may be
   injected outside the repository, so grepping the source proves nothing —
   `curl` the live page.

3. Verify the scoping on a **running** site, not from the source:

```bash
# present where the part is placed
curl -s -A "Mozilla/5.0" "<host>/<page-with-part>" | sed -n '1,/<\/head>/p' | grep -c '<needle>'
# absent everywhere else — run over at least three other page types
for p in / /some-product /some-article; do
  printf "%s: " "$p"
  curl -s -A "Mozilla/5.0" "<host>$p" | sed -n '1,/<\/head>/p' | grep -c '<needle>'
done
```

Expect 1 then 0, 0, 0. `sed -n '1,/<\/head>/p'` matters — without it you match
occurrences in the body and get a false positive.

## Pitfalls

- **Do not put the tag in the `.tsx` entry.** A React4XP entry renders into a
  region `<div>` in the body. A `<meta>` emitted there is in the wrong place and
  browsers may relocate or ignore it.
- **Do not drive it from the page controller** with a conditional on content
  type. It looks equivalent and is how the tag ends up leaking onto pages that
  merely share a template.
- **Caching hides the result.** Between deploy and browser there can be an app
  level response cache, an HTTP tier, and the controller's own page-content
  cache. Check `curl -sI <host>/ | grep -iE 'age|x-cache'` before concluding the
  contribution did not work.
- **Reuse an existing contribution in the repo as the proof the route works**
  before writing a new one. One live page already serving a contributed tag is
  stronger evidence than any amount of reading the lib.

## Sample data

Verified 2026-09-10 on `www.jotron.com` (XP 7.14.4, React4XP 5.0.4): the Google
Maps script contributed by `site/parts/maritime-partners/maritime-partners.ts`
appears in `<head>` on `/maritime-partners` and is absent from `/` and `/search`.
