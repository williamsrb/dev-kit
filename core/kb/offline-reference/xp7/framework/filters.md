<!-- src:https://developer.enonic.com/docs/platform/7.x/framework/filters generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC framework/filters.md

# HTTP filters

HTTP filters enable pipelined processing of http requests.

## Filters

> **Note:** You may wire a a filter into the Site engine’s execution pipeline via a [Site mapping](/docs/platform/7.x/framework/mappings).

Filters enable you to step into the request pipeline, and execute code at both request and response of the execution pipeline, possibly intercepting the request directly. Similar to an [HTTP Controller](/docs/platform/7.x/framework/controllers), standalone filters are triggered based on an export.

As such, to make a filter, it must export a `filter` function:

Minimal filter timing the subsequent request

```js
exports.filter = function (req, next) {
    var before = new Date().getTime();
    var response = next(req);  // next(req) hands over the request to the engine pipeline and returns the response
    var after = new Date().getTime();
    log.info((after - before) + 'ms');
    return response;
};
```

Filter manipulating the request

```js
exports.filter = function (req, next) {
  req.requestLogging = true; // Manipulate request
  log.info("Request:" + JSON.stringify(req, null, 2));
  var response = next(req); // Continue request pipeline
  response.responseLogging = true; // Manipulate response
  log.info("Response:" + JSON.stringify(response, null, 2));
  return response;
};
```

Filter intercepting the request

```js
exports.filter = function (req, next) {

    if (req.getHeader('X-Auth-Token') !== 'letMeIn') {
        // intercept request pipeline
        return {
            status: 403
        }
    }

    req.headers['Authenticated'] = true;
    return next(req);
};
```

Filter changing request params

```js
exports.filter = function (req, next) {
    req.params = {
            param1: 'val', // if param1 was not in the original request it will be added, otherwise the original value will be replaced
            param2: null, // remove param2 from the original request
            param3: [] // another way to remove a parameter
        }
    return next(req);
};
```
