<!-- src:https://developer.enonic.com/docs/code/stable/fundamentals/main generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/fundamentals/main.md

# Main

Handle application lifecycle events via `main.ts`.

## main.ts

Enonic apps may contain a special `main.ts` at `src/main/resources/main.ts`.

`main.ts` is invoked when an application lifecycle event occurs. A common use is initialization — creating repositories, registering event listeners when the application starts — and cleaning up resources when the application stops.

The code should complete as quickly as possible to prevent the application from stalling. Never call remote endpoints or wait in loops for events at the top level of `main.ts`.

> **Tip:** If you need to perform time-consuming work during startup, run it from a [task](docs/code/stable/background/tasks.md) instead.

Running code when the application starts:

main.ts

```typescript
// Log application start
log.info(`Application ${app.name} started`);
```

Running code when the application stops:

main.ts

```typescript
// Log application stop
__.disposer(() => {
    log.info(`Application ${app.name} stopped`);
});
```
