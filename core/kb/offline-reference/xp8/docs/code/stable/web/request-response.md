<!-- src:https://developer.enonic.com/docs/code/stable/web/request-response generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/web/request-response.md

# Request & Response

HTTP functions, the request and response objects they receive and return, and the cookie model.

## HTTP functions

An HTTP function is a [function](docs/code/stable/fundamentals/functions.md) that responds to an HTTP request. The file where it lives is invoked by one of XP’s services (webapp, site, API) based on URL routing defined in descriptors or path conventions.

Declare one export per HTTP method the function handles: `GET`, `POST`, `DELETE`, `PATCH`, `PUT`, `HEAD`, `OPTIONS`. A special `all` export catches any method that doesn’t have a specific handler.

Exports

```typescript
// Handles a GET request
exports.GET = (req) => {};

// Handles a POST request
exports.POST = (req) => {};

// Handles all requests, other than GET or POST which are handled by the functions above
exports.all = (req) => {};
```

Every function receives a [Request](#request) object and returns a [Response](#response) object.

Example

```typescript
exports.GET = (request) => {
  if (request.mode === 'edit') {
    // do something...
  }

  const name = request.params.name;
  log.info('Name = %s', name);

  return {
    body: `Hello ${name}`,
    contentType: 'text/plain'
  };
};
```

## Request

The `request` object is passed to every HTTP function. It carries the request method, URL parts, headers, cookies, and body — plus two XP-specific properties, `mode` and `branch`, which the site service sets to indicate the current rendering mode and repository branch.

```json
{
  "method": "GET",  (1)
  "scheme": "http",  (2)
  "host": "enonic.com",  (3)
  "port": "80",  (4)
  "path": "/my/page",  (5)
  "url": "https://enonic.com/my/page?debug=true",  (6)
  "remoteAddress": "10.0.0.1",  (7)
  "mode": "edit",  (8)
  "branch": "master",  (9)
  "body": null,  (10)
  "params": {  (11)
    "debug": "true"
  },
  "headers": {  (12)
    "Language": "en",
    "Cookies": "mycookie=123; other=abc;"
  },
  "cookies": {  (13)
    "mycookie": "123",
    "other": "abc"
  },
  "locales": [  (14)
    "en",
    "no"
  ]
}
```

| ****1** | HTTP method of the request. |
| --- | --- |
| ****2** | Scheme — `http` or `https`. |
| ****3** | Host name of the server to which the request was sent. |
| ****4** | Port of the server to which the request was sent. |
| ****5** | Path of the request. |
| ****6** | Full URL of the request. |
| ****7** | Client IP address. If the `X-Forwarded-For` [[1](#_footnotedef_1)] header is set, its value overrides the client IP. |
| ****8** | Site service rendering mode: `inline`, `edit`, `preview`, or `live`. |
| ****9** | Site service repository branch: `draft` or `master`. |
| ****10** | Request body, as a string, or `null` when absent. |
| ****11** | Query and form parameters. |
| ****12** | HTTP request headers. |
| ****13** | Parsed HTTP request cookies. |
| ****14** | Locale strings in decreasing order of preference, derived from the `Accept-Language` header. When the client sends no `Accept-Language` header, the array contains a single element with the server’s default locale. |

Use `request.getHeader(name)` to read a header case-insensitively. Prefer it over direct access to the `headers` object.

> **Note:** Modifications to the `headers` object do not affect the result of `getHeader(name)`.

## Response

The HTTP function returns a `response` object that XP converts to the outgoing HTTP response.

```json
{
  "status": 200,  (1)
  "body": "Hello World",  (2)
  "contentType": "text/plain",  (3)
  "headers": {  (4)
      "key": "value"
  },
  "cookies": {},  (5)
  "redirect": "/another/page",  (6)
  "postProcess": true,  (7)
  "pageContributions": {},  (8)
  "applyFilters": true  (9)
}
```

| ****1** | HTTP status code (default `200`). |
| --- | --- |
| ****2** | Response body — a string or a JavaScript object. |
| ****3** | MIME type (default `text/plain; charset=utf-8`). |
| ****4** | Response headers. A value of `null` or `undefined` removes a header set by an upstream function or filter. |
| ****5** | Cookies to set on the response. See [Cookies](#cookies). |
| ****6** | URI to redirect to. If set, XP places it in the `Location` header and sets the status to `303`. |
| ****7** | Site service only. If `true`, the rendered page is post-processed for component tags (default `true`). |
| ****8** | Site service only. HTML fragments contributed to the rendered markup — see [page contributions](docs/code/stable/web/sites/contributions.md). |
| ****9** | Site service only. If `false`, no further [response processors](docs/code/stable/web/sites/processors.md) or filters run (default `true`). |

## Cookies

Cookie values in the response object can be set as plain strings or as objects carrying full cookie configuration.

```javascript
return {
    status: 200,
    body: "Hello World",
    cookies: {
        "plain": "value",  (1)
        "complex": {  (2)
            value: "value",  (3)
            path: "/valid/path",  (4)
            domain: "enonic.com",  (5)
            comment: "Some cookie comments",  (6)
            maxAge: 2000,  (7)
            secure: false,  (8)
            httpOnly: false,  (9)
            sameSite: "Lax"  (10)
        }
    }
};
```

| ****1** | String value — cookie created with defaults. |
| --- | --- |
| ****2** | Object value — the settings below are applied. |
| ****3** | **Value** (required). The value stored in the cookie. |
| ****4** | Paths on the site where the cookie is available (and all contained paths). Default empty. |
| ****5** | Additional sites allowed to read the cookie. Default empty — only the origin server can read it. |
| ****6** | Cookie comment. Deprecated; will be removed in a future XP version. |
| ****7** | Lifetime in **seconds**. Default `-1` — the cookie lives until the browser is closed. |
| ****8** | If `true`, the cookie is only sent over HTTPS. Default `false`. |
| ****9** | If `true`, the cookie is inaccessible to client-side JavaScript. Default `false`. |
| ****10** | `SameSite` flag. One of `lax`, `strict`, `none`, or empty for "not set" (browser default). |
