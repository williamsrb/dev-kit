# How to fix a Playwright MCP instance stuck on "Needs authentication"

## Scope

A spawned `playwright-<TASK-ID>` HTTP instance is alive, but the vendor lists it as
`! Needs authentication` / `needs_auth` and none of its `mcp__playwright-<TASK-ID>__*`
tools load. Evidence runs are hard-blocked on that MCP, so this is a run-stopper.

Playwright MCP has **no** OAuth. `needs_auth` here is the vendor's rendering of an
HTTP **403** from the server itself, not a missing credential. Nothing the user can
sign into will fix it.

## Cause

`@playwright/mcp` 1.64.0-alpha (2026-09) enforces a Host allowlist and answers any
request whose `Host` header is not `localhost:<port>`:

```
HTTP/1.1 403 Forbidden
Access is only allowed at localhost:8931
```

`~/.agents/mcp/playwright.py` used to default to `DEFAULT_HOST = "127.0.0.1"` and both
bind and register that URL, so every instance spawned without `--host` was dead on
arrival for the vendor. The launcher now defaults to `localhost`. If you still see
this fault, the running instance predates that change. Do not try to "fix" it by
setting `allowedHosts` to both names — that 403s `localhost` as well.

## Diagnose (30 seconds, no vendor restart)

```bash
python3 ~/.agents/mcp/playwright.py list | grep -E '"alive"|"url"'
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8931/mcp \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"1"}}}'
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8931/mcp \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"1"}}}'
```

`alive: true` + `127.0.0.1 -> 403` + `localhost -> 200` confirms this exact fault.

## Fix

If the launcher is already on `DEFAULT_HOST = "localhost"`, just respawn (no `--host` flag):

```bash
python3 ~/.agents/mcp/playwright.py stop <ID> [<ID>...]
python3 ~/.agents/mcp/playwright.py spawn <ID> [<ID>...] --enable
claude mcp list | grep playwright        # expect "✔ Connected"
```

On an older launcher that still defaults to `127.0.0.1`, pass `--host localhost` on spawn. That flag sets the bind address **and** the registered URL, so it fixes both halves in one pass. Ports are unchanged (8931, 8932, 8933, …), instance output dirs and configs are reused.

Then clear the vendor's stale negative cache, or the next session will keep skipping
the server:

```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path.home()/'.claude/mcp-needs-auth-cache.json'
d = json.loads(p.read_text())
for k in [k for k in d if k.startswith('playwright-')]:
    d.pop(k)
p.write_text(json.dumps(d))
PY
```

## Pitfalls

- **The fix never lands in the current chat.** A vendor session binds its MCP URLs at
  start. After re-registering, `session_connectors_status` still reports `needs_auth`
  for that chat. Open a **new** chat before capture. Do not `reconnect_session_connector` —
  it only re-dials `kind: connector` rows, not `kind: user` HTTP servers.
- Do **not** ask the user to authenticate in `/mcp`. There is nothing to sign into,
  and it wastes a round trip.
- Do **not** fall back to a vendor-native browser to get unblocked. The evidence rule
  (`browser-mcp-preference`, hard exception) pins evidence capture to the spawned
  `playwright-<TASK-ID>` instance.
- Spawn **without** `--storage-state` when the plan says the capture's first call is
  `browser_set_storage_state`. Loading a session at spawn contaminates the public/anonymous
  steps that most evidence plans run before the authenticated ones.
- Nothing about this fault touches the deployment gates. Run the curl-only E0 gates first —
  they are worth having even when the browser is blocked, and they tell you whether the
  run is viable at all before you spend a session restart.

## Sample data

Verified 2026-09-17 on `@playwright/mcp` 1.64.0-alpha-2026-09-14, instances
`JOT-269` / `JOT-270` / `JOT-290` on ports 8931-8933: all three flipped from
`! Needs authentication` to `✔ Connected` after the respawn above.
