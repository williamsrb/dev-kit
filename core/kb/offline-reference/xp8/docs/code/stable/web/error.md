<!-- src:https://developer.enonic.com/docs/code/stable/web/error generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/web/error.md

# HTTP Error handler

The framework supports the definition of custom error handlers.

## Introduction

Enonic XP ships with a default error handler that will produce a stack trace whenever an error occurs. Stack traces may not be the best way to greet your users. By implementing an error handler this will effectively replace the default error handler.

## error.js

You may add a site-specific error handler to your application by creating the file `src/main/resources/cms/error/error.js`.

> **Note:** A generic error handler can be defined at `src/main/resources/error/error.js`. This handler also catches errors that are not site related (admin tools, extensions, …).

When an error occurs in the request processing pipeline, the XP framework will look for an error handler to execute. For sites specifically, it will (iteratively, in order) go through all applications added to the site, and attempt to execute the handler functions until an [HTTP response](docs/code/stable/web/request-response.md#response) object is returned. This essentially means that developers may choose not to handle particular errors explicitly. If the error is not properly handled, it will fallback to the default XP error handler.

> **Note:** Should an error occur inside an error handler, the framework will take over and fallback to the default error handler.

Rather than exporting HTTP methods like regular HTTP functions and filters, the error handler exports "error code handlers".

For instance, if the current error is a 404, the framework will first attempt to execute the export `handle404`. If not found, it will attempt to execute the fallback export `handleError`.

Basic error handler example

```javascript
exports.handle404 = function (err) {
  return {
    contentType: 'text/html',
    body: `
<html>
  <body>
      <h1>No page for you!</h1>
  </body>
</html>
`
  }
};

exports.handleError = function (err) {
  return {
    contentType: 'text/html',
    body: `
<html>
  <body>
      <h1>Error code "${err.status}" </h1>
  </body>
</html>
`
  }
};
```

> **Warning:** Error handlers should be implemented to execute as fast as possible, and preferably without additional API requests, i.e. fetching content. The reason for this is that the error handler itself may then recursively fail. Also, slow error pages may impact the performance of a node negatively if errors occur frequently. You can choose different handling based on the type of error. A 404 might for instance be handled differently than other errors.

## The Error object

The input parameter for handler functions is an error JSON object. The object contains the status code, error message, Exception object, and the original [HTTP request](docs/code/stable/web/request-response.md#request) object:

Sample error object

```javascript
{
    "status": 404,
    "message": "Some error message",
    "exception": "<the actual exception object in Java>",
    "request": "<original request JSON>"
}
```
