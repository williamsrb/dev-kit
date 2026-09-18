<!-- src:https://developer.enonic.com/docs/platform/7.x/framework/main generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC framework/main.md

# Main controller

Handle application lifecycle events via the main controller.

## main.js

Enonic apps may contain a special controller known as the Application controller, or just "main.js". Simply place the file `src/main/resources/main.js` into your project.

`main.js` gets invoked when an application lifecycle event occurs. A common use of this controller is initialization like creating repositories, and registration of event listeners when the application starts.

The `main.js` execution should complete as quickly as possible to prevent application stalling. Never call remote endpoints or wait in loops for events inside `main.js` global scope.

> **Tip:** If you need to perform time consuming work in the main controller, consider implementing it as a [task](/docs/platform/7.x/framework/tasks).

Running code when the application starts:

main.js

```javascript
// Log application start
log.info('Application ' + app.name + ' started');
```

Running code when the application stops:

main.js

```javascript
// Log application stop
__.disposer(function() {
    log.info('Application ' + app.name + ' stopped');
});
```
