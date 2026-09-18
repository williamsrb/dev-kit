<!-- src:https://developer.enonic.com/docs/code/stable/web/sites/processors generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/web/sites/processors.md

# Response Processors

A special filter, mainly used to inject page contributions.

> **Note:** Response processors are only available in [component rendering](docs/code/stable/web/sites/components.md), not via mappings.

## Introduction

Processors get executed between the `component rendering` step, and the `contributions filter` in the [site service](docs/code/stable/web/sites.md) pipeline. Response processors are commonly used by apps that need to inject [page contributions](docs/code/stable/web/sites/contributions.md) without placing a component on the page.

Use cases are:

- Dynamically adding page contributions (i.e. script tags)

- General manipulation of the response markup i.e. headers or body (i.e. adding SEO tags).

Consider using regular [HTTP Filters](docs/code/stable/web/filters.md) for other use-cases.

## Usage

Create a response processor by placing an implementation under `src/main/resources/cms/processors/`, for example `cms/processors/tracker.ts`.

The implementation must export a `responseProcessor` function. It receives a request and a response object. The example below dynamically adds a `bodyEnd` [page contribution](docs/code/stable/web/sites/contributions.md) to the response.

cms/processors/tracker.ts

```typescript
exports.responseProcessor = (req, res) => {
    const trackingScript = '<script src="http://some.cdn/js/tracker.js"></script>';

    if (!res.pageContributions.bodyEnd) {
        res.pageContributions.bodyEnd = [];
    }
    res.pageContributions.bodyEnd.push(trackingScript);

    return res;
};
```

## Triggering

To wire a processor into the execution pipeline, declare it in the app’s [site descriptor](docs/code/stable/web/sites.md), and add the application to the site.

cms/site.yaml

```yaml
kind: "Site"
processors:
- name: "tracker" (1)
  order: 10       (2)
```

| ****1** | **name** is the filename of the processor (without extension). |
| --- | --- |
| ****2** | **order** sets execution order; lower runs first. |

Response processors may change any of the values of the response object, including: HTTP status code, response body, HTTP headers, cookies and page contributions. It is also possible to return the response object received without any changes.

## Execution order

An application may contain multiple processors. Multiple applications can be added to a Site. When a page is rendered, all processors are ordered and executed accordingly.

The order of execution is determined by the `order` value (as defined in the [site descriptor](docs/code/stable/web/sites.md)) combined with the order of the application list within the site.

Processors with a **lower** order will be executed first (across all apps within the site).

In case there are several filters with the same `order` number, the position of the applications (as configured on the site) determines the order of execution.

> **Note:** If `applyFilters` is set to `false` in the [response object](docs/code/stable/web/request-response.md#response), any further response processing or filters will be ignored. Default value is `true`.
