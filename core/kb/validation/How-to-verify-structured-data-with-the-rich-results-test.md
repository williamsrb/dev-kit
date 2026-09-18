# How to verify structured data with the Google Rich Results Test

## Scope

Validating JSON-LD already served by a site (BreadcrumbList, Article, Organization,
WebPage, Product) against Google's Rich Results Test, headless, without a Google
account. Covers the deterministic pre-check that answers most requirements before
the browser is opened at all.

## Prerequisites

- `playwright-cli` (ordinary implementation/verification work — not an evidence plan,
  so the CLI is the right tier, not Playwright MCP).
- `curl`, `python3`.
- No Google sign-in is needed for a **URL** test. Search Console enhancement reports
  **do** require sign-in — treat that as a separate, credentialed step.

## Procedure

### 1. Deterministic pre-check first (no browser)

Most acceptance criteria — absolute URLs, contiguous `position`, `@type`, trailing-item
handling, head-vs-body placement — are answerable from the served HTML. Pull a URL
sample from the site's own `sitemap.xml`, fetch it, and parse every `application/ld+json`
block. Fetch/parse all pages in one script; do not loop `curl` from the agent.

Key regex — the block is often in `<body>`, not `<head>`, so do not scope the search to head:

```python
LD = re.compile(r'<script[^>]*type=[\'"]application/ld\+json[\'"][^>]*>(.*?)</script>', re.S|re.I)
head_end = html.lower().find('</head>')   # compare against match.start() to report HEAD vs BODY
```

Flag: non-`https://` `item` values, `position != range(1, n+1)`, a trailing item that
*does* carry `item`, empty `name`, `@context` other than `https://schema.org`.

Sample across page **types** (detail, category, article, deep nesting, top level), not
just three URLs — depth is where position arithmetic breaks.

### 2. Drive the Rich Results Test

```bash
playwright-cli open "https://search.google.com/test/rich-results?url=<urlencoded>"
# refs go stale between commands — re-read them right before the click
playwright-cli run-code "async page => await page.getByRole('button', { name: 'test url' }).click()"
# poll; a test takes 15-60s
playwright-cli --raw eval "document.body.innerText.replace(/\n{2,}/g,'|')"
playwright-cli screenshot --filename=rrt-<label>.png
```

Poll until the text matches `valid item|no items detected|invalid|cannot be reached`.

Outcomes: `check_circle <N> valid item detected` under "Detected structured data" with a
named type = pass. `info No items detected` + `Crawled successfully` = the page genuinely
serves no eligible markup (not a failure of the tool). `Page cannot be reached` = crawl
problem, re-run before concluding.

### 3. Post-hydration check

SSR markup can be replaced by a client re-render. Confirm the served block survives:

```bash
playwright-cli goto "<page>"
playwright-cli --raw eval "JSON.stringify([...document.querySelectorAll('script[type=\"application/ld+json\"]')].map(s=>({inHead:!!s.closest('head'),text:s.textContent})))"
```

A count that doubles after hydration means the component emits the block again instead of
hydrating it.

## Pitfalls

- **`?url=` does not auto-run the test.** The field is pre-filled; the button must be clicked.
- **`playwright-cli click eN` fails with "subtree intercepts pointer events"** when the
  user-agent listbox overlay is open. `press Escape`, then click by role via `run-code`
  instead of by ref — role targeting survives the re-render, refs do not.
- **Refs from `find` go stale after any interaction.** Re-run `find`, or skip refs entirely
  and use `run-code` with `getByRole`.
- **`document.querySelector(...).click()` inside `eval` is unreliable** on Google's
  `jsaction` UI; use Playwright's own click.
- **Google's own rules matter as much as validity.** BreadcrumbList requires **at least two
  `ListItem`s**; a one-crumb trail correctly produces nothing. `item` is **not required on
  the last item** — omitting it is compliant, not a defect. Verify against
  `developers.google.com/search/docs/appearance/structured-data/breadcrumb` before filing a bug.
- **Rendered ≠ eligible.** RRT reports what Googlebot fetches now; a CDN/app cache can serve
  older markup. Check `curl -sI <host>/ | grep -iE 'age|x-cache'` before calling a recent
  change missing.
- **Search Console enhancement reports are a separate credentialed step.** Do not treat an
  RRT pass as covering a "no errors in Search Console" requirement.

## The Code (paste-source) route — when the URL route is refused

A host whose `robots.txt` is `User-agent: * / Disallow: /` **cannot be tested by URL**:
RRT fetches as Googlebot and reports the page as unavailable. Review and staging
environments are usually in this state. Use the **Code** tab on `curl`-captured source,
and state the limitation in the evidence — Code mode proves the *markup* is valid; only
the capture proves the *host served it*.

```bash
curl -s -A "Mozilla/5.0" <article-url> > <slug>.html
```

### Driving the Code tab

The editor is **CodeMirror 5**. Do not try to click or type into it:

- The `<textarea placeholder="Paste code to test">` is `display:none`.
- The real input textarea is covered by `.CodeMirror-line`, so `click()` fails with
  *"subtree intercepts pointer events"*.
- A 100 KB+ page is far too large to `type`.

Set the value through the instance instead, then click the button by role:

```js
const cm = document.querySelector('.CodeMirror').CodeMirror;
cm.focus();
cm.setValue(html);            // fires the change the app listens for
// the "test code" button goes from disabled to enabled within ~1s
```

`page.getByRole('tab', { name: /code/i })` selects the tab; `page.getByRole('button',
{ name: /test code/i })` runs it. Poll `document.body.innerText` for
`Detected structured data` — do **not** poll for `/error/i`, because the pasted page
source is part of `innerText` and will match almost anything.

### Getting a large local file into the page

`browser_run_code_unsafe` has **no `fs` and no dynamic `import`**, and the page is on
`search.google.com`, so a cross-origin `fetch` of a local file is blocked. Serve the
captures locally and proxy a same-origin path through `page.route`:

```bash
python3 -m http.server 8731 --bind 127.0.0.1   # in the capture folder
```

```js
await page.route('https://search.google.com/__ev/**', async route => {
  const u = route.request().url();
  const r = await route.fetch({ url: 'http://127.0.0.1:8731/' + u.substring(u.lastIndexOf('/') + 1) });
  await route.fulfill({ response: r, headers: { 'content-type': 'text/plain; charset=utf-8' } });
});
// then, inside the page: await (await fetch('/__ev/<name>.html')).text()
```

Note: `URL` is **not defined** inside `browser_run_code_unsafe`; parse the path with
string operations.

### Reading the result

- Summary: `Detected structured data` → `<Type>` + `N valid item detected`. Errors would
  appear as invalid items; *Non-critical issues detected* is a **warning**, not an error.
- Field values: click the type row, then the detected-item row (`div.CNhTKe`) to expand
  the field table. Capture it with `elementHandle.screenshot()` — the panel is taller
  than the viewport and a `clip` will truncate it.
- A summary screenshot alone does **not** identify which page was tested. Capture the
  code pane and the result panel together (full width, scroll the editor to line 1) so
  the `<title>` is visible in the same shot; otherwise two runs produce byte-identical
  images.
- **The expanded field panel renders blank in a normal viewport.** `elementHandle.screenshot()`
  on a panel taller than the viewport returns mostly empty rows — the table is lazily painted,
  and the label column comes back missing. Set a viewport tall enough to hold the whole panel
  (`page.setViewportSize({ width: 1500, height: 4400 })`), wait, scroll to top, *then* take the
  element screenshot. A 4000 px-tall strip is unreadable once Jira scales it, so slice it and
  lay the slices side by side before upload:
  `convert panel.png -crop <W>x1400 +repage s-%d.png && montage s-*.png -tile 3x1 -geometry +10+10 -background '#dddddd' fields-3col.png`.
- **The URL route's "test url" button is covered by a ripple overlay.** `click()` fails with
  *subtree intercepts pointer events*; `click({ force: true })` works. The `?url=` parameter is
  also dropped on load in this build — fill the input, then force-click.
- **A stale "Something went wrong / Log in and try again" toast suppresses the controls.**
  Dismiss it (`getByRole('button', { name: 'Dismiss' })`) before looking for the tab or button.

## Sample data

- Jotron review base: `https://review.jotron.k8s.example.com`
- News article: `/news-insights/jotron-as-acquires-skipper-electronics-as`
- Insights article: `/news-insights/researching-future-digital-solutions`
