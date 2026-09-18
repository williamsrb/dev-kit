<!-- src:https://developer.enonic.com/docs/code/stable/web/filters generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/web/filters.md

# HTTP filters

HTTP filters enable pipelined processing of http requests.

## Filters

> **Note:** You may wire a filter into the Site service’s execution pipeline via a [Site mapping](docs/code/stable/web/sites/mappings.md).

Filters enable you to step into the request pipeline, and execute code at both request and response of the execution pipeline, possibly intercepting the request directly. Similar to an [HTTP function](docs/code/stable/web/request-response.md), standalone filters are triggered based on an export.

As such, to make a filter, it must export a `filter` function:

Minimal filter timing the subsequent request

```js
exports.filter = function (req, next) {
    var before = new Date().getTime();
    var response = next(req);  // next(req) hands over the request to the pipeline and returns the response
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
