<!-- src:https://developer.enonic.com/docs/code/stable/web/sites/mappings generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/web/sites/mappings.md

# Mappings

Bind HTTP functions and filters to specific content types or site-relative URLs

## Introduction

Mappings are the first custom processing step in the [site service](docs/code/stable/web/sites.md). Mappings execute before the component rendering. You may define mappings for both [HTTP functions](docs/code/stable/web/request-response.md) and [filters](docs/code/stable/web/filters.md). The use cases are vast.

## Usage

Mappings are defined in the [site descriptor](docs/code/stable/web/sites.md) (`cms/site.yaml`). Examples of use cases:

- Bind an HTTP function to a specific URL pattern (e.g. `/mypath`).

- Bind an HTTP function to a specific set of content via content matches (e.g. only the `portal:fragment` content type).

- Bind a filter to part or all of the site structure.

cms/site.yaml mapping examples

```yaml
kind: "Site"
mappings:
- controller: "/cms/foobar/api.ts" (1) (2)
  pattern: '/api/v\d+/.*'          (3)
  order: 10
- controller: "/cms/pages/default/default.ts"
  match: "type:'portal:fragment'"  (4)
- filter: "/cms/foobar/filter.ts"  (5)
  pattern: '/dont-match-me/.*'
  invertPattern: true
  order: 10
- filter: "/cms/services/image.ts" (6)
  service: "image"
```

| ****1** | **controller** — path to an [HTTP function](docs/code/stable/web/request-response.md) implementation. |
| --- | --- |
| ****2** | **order** — execution order across apps. Default `50`. Lower number means higher priority, with `1` being the pole position. See [Execution order](#execution_order). |
| ****3** | **pattern** — regular expression matched against the site-relative URL. Default `/.*`. See [Pattern mappings](#pattern_mappings). |
| ****4** | **match** — property condition evaluated against the contextual content. See [Match mappings](#match_mappings). |
| ****5** | **filter** — path to an [HTTP filter](docs/code/stable/web/filters.md) implementation. |
| ****6** | **service** — system service handled by this mapping (e.g. the `.../_/image/...` endpoint). See [Service mappings](#service_mappings). |

> **Note:** Each mapping must specify either `filter:` or `controller:` — never both — and at least one of `pattern:` or `match:`.

### Execution order

An application may contain multiple mappings, and multiple applications can be added to a site. If two apps within a site share the same mapping path or match expression, the mapping with the **lower** `order` value wins.

If several mappings have the same `order` value, the sort order of the applications on the site determines which mapping is used.

## Pattern mappings

Pattern-based mappings can be used to take over the request for a specific URL before content rendering. Common cases include exposing an API endpoint on a contextual URL like `/api`, or triggering a filter for every request within the site.

The `pattern` property specifies a regular expression matched against the request URL.

The part of the URL involved is the path relative to the site where the application is configured. For example, if a site is deployed via the virtual host `example.com/mysite/`, then `pattern: '/api/.*'` matches requests with URL ending in `example.com/mysite/api/.*`. Protocol, host, and port are not involved in the pattern matching.

If the pattern contains the question mark `?` character, the URL to match also includes query parameters. The query parameters are normalized, so they are always in alphabetical order.

For example, the pattern `pattern: '/api\?category=foo&key=\d'+` matches both:

- `/api?category=foo&key=123`

- and `/api?key=123&category=foo`

> **Note:** The question mark `?` is escaped with a backslash in the pattern because it is a quantifier in regular expressions. Use **single-quoted** YAML strings for any pattern containing backslashes — YAML’s double-quoted form interprets backslash escapes and would corrupt regex tokens like `\d`.

Set `invertPattern: true` on a mapping to negate the result of evaluating the regular expression.

The pattern string must be a valid [regular expression](https://docs.oracle.com/en/java/javase/11/docs/api/java.base/java/util/regex/Pattern.html).

Examples:

- Anything ending with `.json` within the `/api/*` path: `pattern: '/api/.*\.json'`

- All items within the site, including the site itself: `pattern: '/.*'`

- Regex with query string: `pattern: '/endpoint\?bar=\d&foo=.*'+`

- Inverted via `invertPattern: true` together with `pattern: '/section/.*'`

### App key substitution

A pattern may include the literal token `${app}`, which is expanded at parse time to the owning application’s key. This lets you write site-mapping patterns that reference the app’s own key without hardcoding it.

cms/site.yaml in an app whose key is com.foo.bar

```yaml
mappings:
  - pattern: "/_/static/${app}/.+"
    controller: "/site/mappings/static-controller.js"
```

## Match mappings

Match-based mappings can be used to automatically render content types without using page templates or associating content with an implementation directly. A common case is automatic handling of the content type `portal:fragment`.

The `match` property specifies a condition related to the content corresponding with the requested URL path.

The condition takes the form of a property path followed by a `:`, and a value.

The property path can be one of the content properties (`_id`, `_name`, `_path`, `type`, `displayName`, `hasChildren`, `language`, `valid`) or any other custom property within the content.

Examples:

- Match fragment content type: `match: "type:'portal:fragment'"`

- Match content within the `/features/` path: `match: "_path:'/features/.*'"`

- Match custom property with string value: `match: "data.employee.type:'developer'"`

- Match custom property with a number: `match: "data.product.category:42"`

- Match custom property with a boolean: `match: "x.com-enonic-myapp.menuItem.show:true"`

- Match any content: `match: "type:'.+'"`

The expected value can be either a regular expression matched against the property value, or simply a string, number, or boolean (`true` | `false`).

> **Note:** Missing/unavailable content does not match any condition. Omit `match` if you need to map an HTTP function or filter to a URL that does not correspond to any content.

## Service mappings

Service-based mappings bind service requests directly to HTTP functions or filters.

Supported services:

component

Override the direct component rendering at `/_/component/`.

image (deprecated)

Override the legacy image service at `/_/image/[:]//` (e.g. `/_/image/123456/scale-100-100/photo.jpg`). Replaced by the `media:image` Universal API.

attachment (deprecated)

Override the legacy attachment service at `/_/attachment//[:]/` (e.g. `/_/attachment/inline/123456/logo.png`). Replaced by the `media:attachment` Universal API.

> **Note:** [Universal APIs](docs/code/stable/web/apis.md) mounted as points (`/_/<app>:<api>`) cannot be remapped through site mappings — they are routed before the site service processes mappings. If you need custom behavior on a service-point URL, implement a custom Universal API instead.
