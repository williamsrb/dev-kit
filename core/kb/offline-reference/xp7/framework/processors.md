<!-- src:https://developer.enonic.com/docs/platform/7.x/framework/processors generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC framework/processors.md

# Response Processors

A special filter, mainly used to inject page contributions.

> **Note:** Response processors are only available in the [Site Engine](/docs/platform/7.x/runtime/engines/site-engine)

## Introduction

Proessors get executed between the `component rendring` step, and the `contributions filter` in the [site engine](/docs/platform/7.x/runtime/engines/site-engine) pipeline. Response processors are commonly used by apps that need to inject <<[page contributions](/docs/platform/7.x/framework/contributions) without placing a component on the page.

Use cases are:

- Dynamically adding page contributions (i.e. script tags)

- General manipulation of the response markup i.e. headers or body (i.e. adding SEO tags).

Consider using regular [HTTP Filters](/docs/platform/7.x/framework/filters) for other use-cases.

## Usage

Create a response processor by placing a controller file in you project folder under `src/main/resources/site/processors` i.e. `src/main/resources/site/processors/myprocessor.js`

The controller must export a `responseProcessor`. ResponseProcessors receive both a request and response objects. Below is an example that dynamically adds a `bodyEnd` [page contribution](/docs/platform/7.x/framework/contributions) to the response.

processors/tracker.js

```js
exports.responseProcessor = function (req, res) {
    var trackingScript = '<script src="http://some.cdn/js/tracker.js"></script>';

    // Check if contribution field exists, if not create it
    var bodyEnd = res.pageContributions.bodyEnd;
    if (!bodyEnd) {
        res.pageContributions.bodyEnd = [];
    }

    // Add contribution
    res.pageContributions.bodyEnd.push(trackingScript);

    return res;
};
```

## Triggering

To wire a processor into the execution pipeline, it must be declared in the app’s [site descriptor](/docs/platform/7.x/cms/sites#site_xml), and the application must be added to the respective site.

site.xml

```xml
<site>
  <processors>
    <response-processor name="tracker" order="10"/> (1) (2)
  </processors>
  <form/>
</site>
----
```

| ****1** | @name indicates name of the controller file |
| --- | --- |
| ****2** | @order indicates execution order, lower value means higher priority |

Response processors may change any of the values of the response object, including: HTTP status code, response body, HTTP headers, cookies and page contributions. It is also possible to return the response object received without any changes.

## Execution order

An application may contain multiple processors. Multiple applications can be added to a Site. When a page is rendered, all processors are ordered and executed accordingly.

The order of execution is determined by the `order` value (as defined in the [site descriptor](/docs/platform/7.x/cms/sites#site_xml)) combined with the order of the application list within the site.

Processors with a **lower** order will be executed first (across all apps within the site).

In case there are several filters with the same `order` number, the position of the applications (as configured on the site) determines the order of execution.

> **Note:** If `applyFilters` is set to `false` in the [response object](/docs/platform/7.x/framework/http#http-response), any further response processing or filters will be ignored. Default value is `true`.
