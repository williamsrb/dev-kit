---
id: how-to-run-search-boundary-evidence-in-detfinneshjelp
when_skills: []
read: section
prose: caveman-lite
---

# How to run search-boundary evidence in detfinneshjelp

Anonymous staging evidence for the `detfinneshjelp` search service: decoded character limits, token limits, empty-query short-circuit, quote sanitisation, response shape.

## Prerequisites

- Resolve the service URL from the rendered landing page's `data-search-service` attribute.
- Use one controlled anonymous request per case.
- Keep a token-boundary sample below the independent 255-character limit.

## Procedure

1. Confirm the landing page returns HTTP 200 and read `document.body.dataset.searchService`.
2. Check a normal term and record status, content type, array shape, item keys, ordering, and result count.
3. Check absent, blank, all-stop-word, quote-only, apostrophe, and double-quote values. Record parsed JSON and confirm no 5xx response.
4. Check exact 255/256-character values and exact 20/21-token values. For the token cases, use short unique tokens such as `z01` through `z21`; long descriptive tokens can exceed 255 characters and exercise the character guard instead of the token guard.
5. Check a raw percent-encoded value such as repeated `%61` sequences whose decoded value exceeds 255 characters. Validate the decoded length, not the raw URL length.
6. Require over-limit responses to be HTTP 400 JSON objects with a top-level `error` field and no result array.
7. Run `./gradlew cleanTest test` from `xp/`, then verify the generated XML suite files contain the expected JavaScript test functions and zero failures/errors.

## Pitfalls

- A 20-token sample can accidentally exceed the character limit; choose the sample so both dimensions are independently within bounds.
- A successful Gradle task may be up-to-date or may run zero tests. Inspect `build/test-results/test/` and the generated report names.
- A GitLab commit URL that redirects to `/users/sign_in` is not source evidence. Use an authenticated session or report the source-evidence step as blocked.
- Screenshot files intended for Jira must be visually checked for the correct page, target element, and readable scale before upload.

## Sample data

- Exact token boundary: `z01 z02 z03 z04 z05 z06 z07 z08 z09 z10 z11 z12 z13 z14 z15 z16 z17 z18 z19 z20`.
- Over token boundary: the exact 20-token sample plus `z21`.
- Percent-encoded length guard: `searchWord=` followed by 256 repetitions of `%61`.
