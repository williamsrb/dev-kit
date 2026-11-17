---
id: how-to-authenticate-to-enonic-xp7-admin-on-review
when_skills: [plan-task-evidence, run-plan]
read: section
prose: caveman-lite
---

# How to authenticate to Enonic XP 7 admin / Content Studio 5.x on a review host

Generic procedure, distilled from a verified client run. XP 8 / CS 6:
use [How-to-use-content-studio-xp8.md](./How-to-use-content-studio-xp8.md) instead.

## Version check first

| | XP 7 / CS 5.x | XP 8 / CS 6 |
|---|---|---|
| Content Studio URL | `<base>/admin/tool/com.enonic.app.contentstudio/main` | `<base>/admin/com.enonic.app.contentstudio/main` |
| Admin tool list | `<base>/admin/tool` | no `/tool/` segment |

Anonymous `/admin/tool` answers **401** on XP 7. A 404 on the CS path means the wrong XP version,
not a missing session.

## Get a session (no login-tier browser)

`review-auth` (`~/.agents/bin`) logs in as `su` with the password in `~/.agents/.auth/<user>.passwd`
and prints the session cookies:

```bash
review-auth <review-base-url> --json > <scratch>/auth.json
```

Cookies behind the k8s ingress: `INGRESSCOOKIE` (pod affinity) and `JSESSIONID` (XP session).
Both are required; the session is pinned to the pod the affinity cookie selects.

Cheapest confirmation, before any browser call:

```bash
curl -s -H "Cookie: INGRESSCOOKIE=<v>; JSESSIONID=<v>" <base>/admin/tool -o /dev/null -w "%{http_code}\n"
```

## Convert to a Playwright storage state

```bash
python3 - <<'PY'
import json, pathlib
src = json.load(open('<scratch>/auth.json'))
assert src.get('authenticated'), src
state = {"cookies": [
    {"name": n, "value": v, "domain": "<review host>", "path": "/",
     "expires": -1, "httpOnly": True, "secure": True, "sameSite": "Lax"}
    for n, v in src['cookies'].items()], "origins": []}
out = pathlib.Path.home() / '.agents/.auth/<realm>-review.state.json'
assert not out.is_symlink(), f"{out} is a symlink - refusing to write through it"
out.write_text(json.dumps(state, indent=1))
print(out)
PY
```

Rules that bit the client run:

- Hand the state over at spawn: `python3 ~/.agents/mcp/playwright.py spawn <TASK-ID> --storage-state ~/.agents/.auth/<realm>-review.state.json` boots logged in, no tool call. A second realm: `--extra-storage-state <file>`, then `browser_set_storage_state` with `~/.agents/.playwright-mcp/<TASK-ID>/auth/<file name>`. The MCP reads files only inside the instance's output dir, never `~/.agents/.auth/` directly.
- Never write through a symlink, and never overwrite the shared Atlassian state `~/.agents/.auth/user.json`; evidence uploads need it. Use a distinct real file.
- Delete the file, and any scratch copy, after the run. Do not leave cookies in an evidence folder.

## Load it into the browser

Call `browser_set_storage_state` with the absolute filename as the **first** browser call, before
navigating to any authenticated URL. Headless only. A capture that lands on a login page is a
failed step, not evidence.

If the instance has no `browser_set_storage_state` (spawned without `--storage-state`):

- `browser_run_code_unsafe` has no `require`, `fs`, `process` or dynamic `import`. It cannot read
  the state file itself.
- `document.cookie` cannot replace `INGRESSCOOKIE`: the ingress sets it `HttpOnly`.
- Have a shell step inline the cookie array into a `.mjs` file inside the instance's allowed roots
  (`chmod 600`), run it with `browser_run_code_unsafe`'s `filename`, then delete it. Code:
  `await page.context().addCookies([...])`.
- Return cookie **names and counts only**. A snippet that returns values is refused as credential
  materialization.
- Alternative: serve the cookie JSON on `127.0.0.1` with `python3 -m http.server`, fetch it with
  `ctx.request.get`, then kill the server and delete the file.

## Confirm the session is real

Before capturing:

- `document.title` is `Content Studio - Enonic XP Admin`
- no `input[type=password]`
- `.grid-canvas .slick-row` count is non-zero on the browse view

No-UI probe: any admin REST 404 returns JSON with `context.authenticated: true` and a
`context.principals` array. `role:system.admin` plus `user:system:su` means Super User.

## Driving Content Studio 5.x headless

- Open content with the **path** form `…/main/<project>/edit/<content-id>`. The hash form
  (`…/main#/<project>/edit/<id>`) opens a new tab and you screenshot the wrong one.
- Allow ~8 s for the editor; the tab title changes to the content's display name when ready.
- `browser_take_screenshot` writes under the Playwright server's working directory, not the MCP
  output folder. Move captures into the evidence folder and check `git status` is clean.

## Not verified generically

- Whether `review-auth` has a `.passwd` for a given client realm. If it fails, escalate; do not
  guess credentials.
- Whether `POST <base>/admin/_/idprovider/system` works on XP 7 as it does on XP 8. client used
  `review-auth` cookies, not this POST.
