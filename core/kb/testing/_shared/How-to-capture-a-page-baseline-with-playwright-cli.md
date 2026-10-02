---
id: how-to-capture-a-page-baseline-with-playwright-cli
when_skills: [run-plan, playwright-cli]
inputs: [storage-state JSON, local or review URL]
outputs: [desktop and mobile full-page PNGs, HTML, request list]
stop_if: [production host, login page after state-load]
read: whole
prose: caveman-lite
---

# How to capture a page baseline (screenshots, HTML, network) with playwright-cli

**Scope:** `_shared`
**Applies to:** `playwright-cli` 0.1.x driven from a script (measured 2026-10-01, extractkit `enonic.baseline`)

## Prerequisites

- `playwright-cli` on PATH, a Playwright storage-state JSON for the target host.
- Local or review hosts only. Refuse production before starting a browser.

## Procedure

One named session per run, commands in this order:

```bash
playwright-cli -s=<session> open                       # headless, about:blank
playwright-cli -s=<session> state-load <state.json>
playwright-cli -s=<session> resize 1440 900
playwright-cli -s=<session> goto <url>
playwright-cli -s=<session> screenshot --filename=<abs.png> --full-page
playwright-cli -s=<session> --raw eval "document.documentElement.outerHTML"
playwright-cli -s=<session> --raw requests --static
playwright-cli -s=<session> resize 390 844             # then goto + screenshot again
playwright-cli -s=<session> close
```

Output shapes (stdout):

- `--raw eval` prints the value JSON-encoded on its first line. `json.loads` it to get the HTML.
- `--raw requests` prints `N. [GET] <url> => [200] OK` per line; failures read `=> [FAILED] net::ERR_...`.
- Without `--raw` every command prints `### Ran Playwright code` blocks; do not parse those.

## Pitfalls

- Any failing command exits 1 and prints `### Error`. A closed session says `The browser '<s>' is not open`.
- `playwright-cli` writes `.playwright-cli/` into its cwd. Run it from a temp directory and pass absolute `--filename` paths so nothing lands in the source tree or the sidecar.
- `requests` URLs carry query strings. Drop them before storing: they can hold tokens.
- The update banner prints a box to the terminal; ignore it, do not parse it.
- Mock `subprocess.run` in tests. The step must record a skip, not fail, when the binary is missing.
- Prefer `fuser -k <port>/tcp` over `pkill -f <pattern>` when cleaning a test server: `pkill -f` matches the calling shell's own command line and kills it.
