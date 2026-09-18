<!-- src:https://developer.enonic.com/docs/platform/7.x/framework/controllers generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC framework/controllers.md

# HTTP controllers

JavaScript controllers represent the core concept of the Enonic XP framework.

## Controller

HTTP controllers are essentially JavaScript files that are invoked by the various [runtime engines](/docs/platform/7.x/runtime), or by other controllers through the require system.

Common for all http controllers is that they export functions matching the desired HTTP Method it implements. As such, any controller must explicitly declare one or more "exports" in order to handle requests: `get`, `post`, `delete`, `patch` are examples of such methods.

> **Note:** `patch` is supported starting from XP 7.15.0.

A controller can also export a special function `all` which will handle any HTTP method, unless there is a more specific handler available.

The appropriate function will automatically be invoked for every request sent to the controller.

Example usage

```javascript
// Handles a GET request
exports.get = function(req) {}

// Handles a POST request
exports.post = function(req) {}

// Handles all requests, other than GET or POST which are handled by the functions above
exports.all = function(req) {}
```

A handler function receives a parameter with an [Http Request](/docs/platform/7.x/framework/http#http-request) object, and returns an [HTTP Response](/docs/platform/7.x/framework/http#http-response) object.

```javascript
exports.get = function(request) {

  if (request.mode === 'edit') {
    // do something...
  }

  var name = request.params.name;
  log.info('Name = %s', name);

  return {
    body: 'Hello ' + name,
    contentType: 'text/plain'
  };

};
```
