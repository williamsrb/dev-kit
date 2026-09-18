<!-- src:https://developer.enonic.com/docs/code/stable/web generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/web.md

# Developing for the web

Every client interaction with Enonic XP — browser request, API call, admin tool, websocket upgrade etc flow through a common http gateway in XP, aka the Web endpoint.

## Request pipeline

Every request, regardless of which service ultimately handles it, passes through a common pre-processing pipeline before reaching your code:

Vhost filters

Request routing based on [virtual hosts](https://developer.enonic.com/docs/platform/xp8/config/vhosts).

Platform filters

Optional system-level request filters. Implemented in Java as OSGi components — a platform extension mechanism, not part of the JS/TS app surface.

Autologin filter

The [virtual host contextual ID provider](https://developer.enonic.com/docs/platform/xp8/config/system#idprovider) is invoked, unless a user already exists in the context.

Service pipeline

The Web endpoint (default port `8080`) dispatches the request to one of four services — each with a fixed URL prefix and a distinct role — and runs the matching service’s own pipeline:

/api

Custom web APIs, microservices, headless integrations etc.

/admin

XP administration UIs (Content Studio is itself an admin tool) and extensions that mount inside them.

/site

Content-driven websites: pages, parts, layouts, content rendering.

/webapp

Standalone web applications — served by your app, no CMS context.

ID provider

Triggered if the pipeline returns a `401 Unauthorized`. The contextually mounted [ID provider](docs/code/stable/web/id-providers.md) is invoked and may handle the request.

Custom error handler

If the pipeline returns an unhandled error (400/500 status witout a response body) the contextual [error handler](docs/code/stable/web/error.md) kicks in.

Fallback error handler

Finally, if the request fails with an error that is still unhandled, XP’s standard error handler kicks in.

## ID providers

[ID providers](docs/code/stable/web/id-providers.md) work across the services to provide pluggable authentication and that hooks into the request pipeline — `handle401`, `autoLogin`, `login`/`logout` endpoints, and ID-provider-as-HTTP-function.
