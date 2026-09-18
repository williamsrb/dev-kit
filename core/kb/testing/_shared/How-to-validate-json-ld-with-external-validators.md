# How to validate JSON-LD with external validators (code-paste mode)

**Scope:** `_shared`
**Applies to:** any environment whose markup you can read with `curl` — including hosts
Google cannot fetch (review environments behind `Disallow: /` and `x-robots-tag: noindex`)
**Related:** [How-to-check-evidence-screenshots-before-jira.md](./How-to-check-evidence-screenshots-before-jira.md)

## Prerequisites

- No auth. Both validators below run without a Google sign-in for a code-paste test.
- Spawned headless Playwright MCP (`playwright-<TASK-ID>`). Do not open a vendor-native browser.
- `curl` + `python3` to lift the exact served `ld+json` blocks.

## Procedure

### 1. Build the paste document from the served bytes

Never retype the payload. Extract the blocks and wrap them in a minimal document so the
validator sees byte-identical markup:

```python
LD = re.compile(r'(<script[^>]*application/ld\+json[^>]*>.*?</script>)', re.S | re.I)
blocks = LD.findall(fetch(path))
doc = ('<!doctype html>\n<html><head><title>' + KEY + ' served markup: ' + path + '</title>\n'
       '<link rel="canonical" href="' + BASE + path + '">\n</head>\n<body>\n'
       + '\n'.join(blocks) + '\n</body></html>\n')
```

Keep the title and canonical in the document: they make the screenshot self-identifying,
since the validator prints the pasted code next to its verdict.

### 2. Google Rich Results Test — code mode

1. `browser_navigate` to `https://search.google.com/test/rich-results`.
2. Click the tab named `code` (`role=tab[name="code"]`).
3. Fill `role=textbox` (the CodeMirror input) with the whole document in one call.
4. Click `role=button[name="test code"]`; the result page is `/test/rich-results/result?id=…`.
5. Read the verdict with `browser_evaluate` on `document.body.innerText` — the tail of the
   text carries `N valid item detected` / `No items detected` and the per-type rows.

### 3. Schema.org validator — the one that covers non-rich-result types

1. `browser_navigate` to `https://validator.schema.org/?hl=en` (without `?hl=en` it may load
   in the machine's locale).
2. Click `role=link[name="Code snippet"]` in the "Test your structured data" dialog.
3. Fill the dialog's `textbox` ref with the document, click `role=button[name="Run test"]`.
4. The result lists every item with `0 ERRORS` / `0 WARNINGS` counts and a resolved property
   table. Use `Run new test` (top right) for the next document.

## Pitfalls

- **The Rich Results Test only lists types Google can turn into a decorated listing.**
  `WebPage`, `WebSite` and `SearchAction` are not among them since the sitelinks-searchbox
  rich result was retired, so a document containing only those reports **No items detected**
  with an `info` icon and zero errors. That is the tool's supported-type list, not a markup
  defect — prove the markup with the Schema.org validator, which reports the full item tree,
  and keep a second Rich Results run on a document that *does* carry a supported type
  (e.g. `Organization`) to show the same tool parses the page without errors.
- **`browser_type` on a CodeMirror editor appends; it does not replace.** A second fill
  concatenates two documents and the validator then reports on the merged text. Reload the
  page (or clear with select-all) before each new paste, and confirm the line numbers in
  `document.body.innerText` before trusting a verdict.
- **The visible `textarea[placeholder="Paste code to test"]` is not fillable** (`element is
  not visible`). Target the CodeMirror `role=textbox` instead.
- **Do not truncate the payload to make it shorter.** A shortened Organization node makes the
  verdict about markup that was never served. A 3-4 KB document fills fine in one call.
- **URL mode against a review host is expected to fail**, since review answers `Disallow: /`
  and `x-robots-tag: noindex`. Code mode is the primary path; a refused URL test is the
  environment, not a defect. The exact verdict on a `Disallow: /` host is
  `error | URL is not available to Google | Crawl failed on <date>` — grep for
  `not available to Google`, not for `cannot be reached`.
- **`?url=` *does* auto-run the test in the current build** (2026-09-17), contradicting the
  older "the button must be clicked" note. Navigating to
  `…/test/rich-results?url=<urlencoded>` lands straight on `/test/rich-results/result?id=…`,
  and `getByRole('button', { name: /test url/i })` then times out because the pre-filled
  input and its button are no longer on the page. Read `document.body.innerText` first; only
  fill-and-force-click if no verdict is present.
- **Getting the paste document in without `page.route`.** `browser_run_code_unsafe` has no
  `require`, `fs` or `process`, but `page.context().request` is a full `APIRequestContext` and
  reaches loopback directly. Serve the folder (`python3 -m http.server 8731 --bind 127.0.0.1`)
  and read it with `await ctx.request.get('http://127.0.0.1:8731/paste-front.html').then(r => r.text())`.
  That is one line instead of the `page.route('https://search.google.com/__ev/**')` proxy, which
  is only needed when the fetch has to originate **inside** the page.
- The Schema.org validator resolves `@id` references across blocks in one document: a
  `WebSite.about` pointing at an `Organization` `@id` in a *sibling* block renders as the full
  Organization (name, logo, address). That is the cheapest proof that cross-node references
  actually join rather than dangle.

- **Do not locate the result rows by visible text.** The pasted source is part of the page, so
  `text=Articles` also matches CodeMirror's `"articleSection"` spans and fails on strict mode.
  Use the row's own classes: `div.MreLB.QrfJGb:has-text("Articles")` for the type row, then
  `div.CNhTKe` for the detected item that expands the field table.
- **`div.eiWkLe` is the scrollable results pane** — the element to screenshot for the expanded
  field table. Its `clientHeight` follows the viewport, so set the viewport tall enough that
  `clientHeight === scrollHeight` (1500 was enough for a BlogPosting with ~9 fields), scroll it
  to 0, then take the element screenshot. At that size a plain element screenshot paints
  correctly — the 4400 px strip plus `montage` recipe is only needed for panels that stay taller
  than any workable viewport.
- **The element screenshot is padded to the viewport height**, so it carries dead space under the
  panel. Measure with `convert <f> -trim +repage -format "%wx%h" info:` and crop to that height
  before the stamp pass; a stamped file must not be re-cropped, because the crop can cut the
  stamp off.

## Sample data (minimal)

| Field | Example |
|-------|---------|
| Rich Results Test | `https://search.google.com/test/rich-results` (tab `code`) |
| Schema.org validator | `https://validator.schema.org/?hl=en` (link `Code snippet`) |
| Document size that fills in one call | ~3.3 KB (front page: Organization + WebPage) |
| Verdict strings to grep | `valid item detected`, `No items detected`, `0 ERRORS`, `0 WARNINGS` |
