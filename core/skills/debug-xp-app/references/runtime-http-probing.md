# Probing a Running Instance Over HTTP

Use when a symptom is an HTTP response (4xx/5xx, or a blank / "not available"
preview or widget) and `server.log` has **no matching entry**. XP logs many 4xx
only at DEBUG and renders generic error pages (e.g. a styled "404"), so the real
reason is in the **response body**, not the log. Reproduce the request and read it.

This is environment-specific plumbing: the port, the auth method, and the HTTP
tool all depend on the user's setup. Discover them — do not hardcode.

## 1. Find the instance and its port

Do not assume 8080. Find the XP process, then read the ports IT listens on:

    pid=$(pgrep -f 'com.enonic.xp.launcher.LauncherMain')
    lsof -nP -iTCP -sTCP:LISTEN -a -p "$pid"

Or read the configured port from `$XP_HOME/config/com.enonic.xp.web.jetty.cfg`.
If the process line carries `-Dxp.install=<local source>`, the running server is
that local build — so "running behavior == source you can read", and a
code-vs-reality contradiction is trustworthy rather than version skew.

## 2. Authenticate — always required; method is environment-specific

XP 8.0+ always requires authentication (older versions may allow a Guest login).
Find credentials in this order, and never guess them:

1. Project instruction / memory files (CLAUDE.md, AGENTS.md, prompt or memory) —
   use any auth method documented there.
2. Dev environment only: XP initializes a default `su` user whose password may
   match a known default hashed in `config/system.properties`. Use only with the
   user's explicit OK.
3. Otherwise — production has none of these defaults, or you simply cannot
   authenticate — stop and ask the user how to authenticate.

## 3. Issue the request and READ THE BODY

Use whatever the user's setup provides — an HTTP client with a session cookie or
token, the user's browser, etc. No specific tool is required or assumed. The point
is to read the **raw response body**, not the rendered page.

- Browser note (general, not tool-specific): the admin session cookie is usually
  HttpOnly, so issue same-origin requests with credentials included to carry it.

## 4. Verify a fix

Re-run the identical request before and after the change. Same request, status
flips (e.g. `404` → `200`) — that turns "I think this fixes it" into "this fixes it".

## XP HTTP cheatsheet

Paths are canonical; host/port are environment-specific (8080 shown as the common
local default). `<project>`/`<branch>`, e.g. `sample-blog`/`draft`.

    Content Studio UI : /admin/com.enonic.app.contentstudio/main
                        (most common app; e.g. http://localhost:8080/admin/com.enonic.app.contentstudio/main)
    Admin render      : /admin/com.enonic.app.contentstudio/site/<edit|preview|inline|admin>/<project>/<branch>/<path>
                        returns {"status":4xx,"message":"<real reason>"} — read it
    Projects (REST)   : GET  /admin/rest-v2/cs/project/list
    Content query     : POST /admin/rest-v2/cs/cms/<project>/<branch>/content/query
                        body requires contentTypeNames (type filter) and queryExpr
    Content by path   : GET  /admin/rest-v2/cs/cms/<project>/<branch>/content/bypath?path=/x
