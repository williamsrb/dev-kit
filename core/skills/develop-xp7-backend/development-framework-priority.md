# Development + Framework Priority Map

Use this file to pick the shortest doc path for XP backend tasks.

## 1) Development docs (consult first)

- Development root: <https://developer.enonic.com/docs/xp/stable/development>
- Sandboxes: <https://developer.enonic.com/docs/xp/stable/development/sandboxes>
- Code: <https://developer.enonic.com/docs/xp/stable/development/code>
- Building: <https://developer.enonic.com/docs/xp/stable/development/build>
- Configuration: <https://developer.enonic.com/docs/xp/stable/development/config>
- TypeScript: <https://developer.enonic.com/docs/xp/stable/development/typescript>

When to consult:
- Environment/setup/build failures -> Sandboxes, Building, Configuration
- Project structure/runtime code loading -> Code
- TS compile/type/runtime mismatch -> TypeScript

## 2) Framework docs by entrypoint

- Framework root: <https://developer.enonic.com/docs/xp/stable/framework>
- Controllers: <https://developer.enonic.com/docs/xp/stable/framework/controllers>
- Globals: <https://developer.enonic.com/docs/xp/stable/framework/globals>
- HTTP: <https://developer.enonic.com/docs/xp/stable/framework/http>
- Events: <https://developer.enonic.com/docs/xp/stable/framework/events>
- Error handler: <https://developer.enonic.com/docs/xp/stable/framework/error>
- Filters: <https://developer.enonic.com/docs/xp/stable/framework/filters>
- ID provider: <https://developer.enonic.com/docs/xp/stable/framework/idprovider>
- Tasks: <https://developer.enonic.com/docs/xp/stable/framework/tasks>
- Templating: <https://developer.enonic.com/docs/xp/stable/framework/templating>
- Localization: <https://developer.enonic.com/docs/xp/stable/framework/i18n>
- Websocket: <https://developer.enonic.com/docs/xp/stable/framework/websocket>
- Mappings: <https://developer.enonic.com/docs/xp/stable/framework/mappings>
- Components: <https://developer.enonic.com/docs/xp/stable/framework/components>
- Processors: <https://developer.enonic.com/docs/xp/stable/framework/processors>
- Contributions: <https://developer.enonic.com/docs/xp/stable/framework/contributions>
- Main controller: <https://developer.enonic.com/docs/xp/stable/framework/main>
- Java bridge: <https://developer.enonic.com/docs/xp/stable/framework/java-bridge>

Entrypoint mapping:
- `site` / `admin` / `webapp` / `http` handlers -> Controllers + HTTP
- Request interception/normalization -> Filters
- Background or long-running jobs -> Tasks
- Event-driven workflows -> Events
- CMS rendering pipeline custom behavior -> Components + Processors + Contributions
- Vhost/routing behavior -> Mappings + Main controller
- Realtime channels -> Websocket
- Locale-sensitive responses -> Localization + I18N API

## 3) API docs (after framework constraints are clear)

Use [api-priority.md](api-priority.md) for the full API list and selection order.

## Fast decision matrix

- "Cannot start/run locally" -> Development/Sandboxes + Building + Configuration
- "Wrong request/response behavior" -> Framework/Controllers + HTTP + Error handler
- "Auth or permissions issue" -> Framework/ID provider + `lib-auth` + `lib-context`
- "Slow or broken storage/query" -> Storage docs + `lib-content`/`lib-node`/`lib-repo`
- "Need async processing" -> Framework/Tasks + `lib-task` + `lib-scheduler`
