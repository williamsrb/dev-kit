<!-- src:https://developer.enonic.com/docs/react4xp/6.x/library generated:2026-07-30T04:18:15Z format:llm-dense react4xp-6.x -->
#DOC docs/react4xp/6.x/library.md

# Library reference

The React4xp library ([Enonic Market](https://market.enonic.com/vendors/enonic/react4xp-lib)) exposes a few functions, the [DataFetcher](#data_fetcher) class and a `React4xp` object that can be used in your Enonic app.

For the [SSR engine](docs/react4xp/6.x/ssr.md) and [hydration](docs/react4xp/6.x/ssr.md#hydration), and for compilation and runtime [configuration](docs/react4xp/6.x/config.md), see the respective chapters.

## Usage

### Add library dependency

Add the `lib-react4xp` dependency to your project with a single line:

build.gradle

```gradle
dependencies {
  include "com.enonic.lib:lib-react4xp:${libVersion}"
}
```

Replace `${libVersion}` with the desired version of lib-react4xp. For a full project setup (including the `@enonic/react4xp` build integration), see [the library docs](https://github.com/enonic/lib-react4xp#readme) on GitHub.

### Import library

Add the import statement to your script file.

```typescript
import {React4xp} from '/lib/enonic/react4xp';
```

Individual functions can also be imported directly, e.g. `import {render, processHtml} from '/lib/enonic/react4xp'`.

### Asset serving

React4XP 6 serves its compiled assets and SSR endpoints through two XP **services** that ship inside the library itself:

react4xp

serves the compiled entry, chunk and client assets

react4xp-dependencies

serves the dependency manifest the client needs

Because they are services rather than APIs, they are addressable as soon as the library is on the classpath - there is nothing to declare or mount in `site.xml`.

Use [`serviceUrl`](#serviceurl) if you need to build a URL to a service yourself. The library’s own URL helpers - `assetUrl`, `getClientUrl` and `getExecutorUrl` - are built on it.

> **Note:** React4XP 7 replaces these services with an XP 8 **universal API**, which must be explicitly mounted. If you are upgrading, see [Upgrade notes](docs/react4xp/6.x/upgrade.md).

### Invocation example

A minimal HTTP function passes an [entry](docs/react4xp/6.x/entries.md), `props`, and the `request` to `render`. The return value is an XP response object you return directly:

```typescript
import {React4xp} from '/lib/enonic/react4xp';
import type {Request} from '@enonic-types/core';

export function get(request: Request) {
    // 'my-entry' is a JsxPath to a compiled react component
    return React4xp.render('my-entry', {greeting: 'Hello world'}, request);
}
```

`render` returns a `{body, pageContributions}` response object, so returning it straight from the function both renders server-side and adds everything the browser needs to activate the react app. Each function and its options are documented below.

## Functions

### render

All-in-one shorthand function for a lot of use cases. Covers both client- and serverside rendering.

Inserts a react component into an (optional) pre-existing HTML string and adds any necessary page contributions to make all work: links to assets, both shared and specific to the entry, and a client-side JS call (`render` or `hydrate` in the client wrapper) that activates the react component in the browser.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| `entry` | string \| component object | Reference to an [entry](docs/react4xp/6.x/entries.md): the react component to be rendered. [JsxPath](docs/react4xp/6.x/entries.md#jsxPath) reference - or if the entry is a TSX/JSX file with the *same name* in the *same folder* as the component implementation, you can use a `portal.getComponent()` object here. Corresponds to the template argument in `thymeleaf.render`. |
| `props` | object | **Optional.** Data model passed into the react component. JS object must be serializable (no functions can be passed). Corresponds to the model argument in `thymeleaf.render`. |
| `request` | [XP request object](https://developer.enonic.com/docs/code/stable/web/request-response) | **Optional** (but *required for react activation*). Include to detect the rendering mode inside/outside Content Studio: inside Content Studio there should be only a static serverside-rendering, no browser react activation (or client-side rendering), only returning get an HTML visualization with the initial `props`. Special case: if `request` is not an object but omitted/falsy, page-contributions rendering is *completely skipped*. In this case, the *options* argument (below) is still valid: any added `body` there will still serve as a container for the rendered output from this call, and any `pageContributions` inside *options* are still added and returned. |
| `options` | object | **Optional.** Additional options to control the rendering (see below). |

The `options` object accepts these properties, all optional:

| Name | Type | Description |
| --- | --- | --- |
| `id` | string | **Optional.** ID of the component, targeting the ID of an element in `body`: react renders into that container element. Should be unique within the HTML document. If no matching element ID is found in `body`, this sets the ID of a generated element. Defaults to a generated unique ID (random or derived from the content). |
| `body` | string | **Optional.** Valid HTML to serve as container for the react content. On server-side rendering the output is inserted into the matching-`id` element; on client-side rendering the insertion happens in the browser. If no `body` is supplied, an empty `<div>` with a matching `id` is generated. If `body` has no matching-`id` element, one is generated and appended. Defaults to a `<div>` with matching `id`. |
| `pageContributions` | object | **Optional.** Existing [page contributions](https://developer.enonic.com/docs/code/stable/web/sites/contributions) to add. These are added *before* the ones rendered by this call (within each section `headBegin`, `bodyEnd`, etc). |
| `hydrate` | boolean | **Optional.** When SSR is true, choose whether to hydrate. Defaults to `app.config['react4xp.hydrate']` or `true`. |
| `ssr` | boolean | **Optional.** Switch between client-side and server-side rendering for this particular rendering; other renderings are not affected. If falsy, you get server-side rendering and the client calls `.hydrate`; if truthy, SSR is skipped and the client calls `.render`. Only applies in live mode and previews. Defaults to `app.config['react4xp.ssr']` or `true`. |
| `wrapper` | boolean | **Optional.** Whether to render the surrounding container element around the target element. |
| `urlType` | `server` \| `absolute` | **Optional.** URL type for assets: server-relative or absolute. Defaults to `app.config['react4xp.urlType']` or `server`. Available from `React4xp-5.1.0`. |
| `uniqueId` | boolean \| string | **Optional.** Force a unique target id. Pass a string to set the id explicitly, or `true` to append a random suffix to the generated id. Alternative to `id`. |

Returns

Returns an [XP response object](https://developer.enonic.com/docs/code/stable/web/request-response) with these main attributes:

| Name | Type | Description |
| --- | --- | --- |
| `body` | string, rendered HTML | HTML output.      The root of this HTML is always a **surrounding container** HTML that will have a matching-ID **target element** in it somewhere (an element matching the ID of the clientside call to `.render` or `.hydrate`: that ID is `options.id` if that was set, or a generated unique one if not). This surrounding structure is `options.body`, unchanged if that already contained a matching-ID element, or with a new target element generated and inserted at the end if it didn’t have one. If there is no `options.body`, the surrounding container is just a generated target `<div>` element.      Inside that matching-ID element, there will be a serverside rendering of the entry (with the initial props from `options.props`) if `options.ssr` is not false. |
| `pageContributions` | object | Regular [page contributions](https://developer.enonic.com/docs/code/stable/web/sites/contributions). Includes everything the browser needs to activate (or client-side render) the react component: script tags with urls to auto-compiled assets for the entry and its dependencies, a client-side react4xp wrapper asset and an activating client-wrapper call. Urls point to React4xp’s own optimized asset services. Also included before this, are any input `options.pageContributions`. |

#### Request and automated behavior

`.render` is intended to be convenient to work with and safely wrap around some common corner cases. It automates a little bit of behavior, depending on the `request` object argument (which stems from the HTTP function):

render with request:

```javascript
React4xp.render(entry, props, request);
React4xp.render(entry, props, request, options); // ...etc etc
```

If `request` is supplied, viewing context is detected from `request.mode`: is rendering happening inside or outside of Content Studio edit mode?

- **Inside Content Studio edit mode**, `.render` will always select serverside rendering (no matter what `ssr` is) and skip JS dependency assets and the clientside `render`/`hydrate` trigger (but still supply other dependencies, such as CSS). This ensures that a static HTML placeholder rendering is visible inside Content Studio’s edit mode, but keeps react from being activated. This is by design: preventing the possibility that react code might intervene with the UX of Content Studio itself.

- **Outside Content Studio edit mode**, the rendering will be activated as a react app (i.e. all pageContributions are rendered). Also, `ssr` is used, so if this is `false`, serverside rendering is skipped. The ``and `render` is called in the client instead of `hydrate`.

Also, when `request` is used, `.render` will output **error messages from SSR** in error containers and browser consoles (except in live view mode, where error containers and browser log are more generic: shown without the specific messages).

render without request:

```javascript
React4xp.render(entry, props);
React4xp.render(entry, props, null);
React4xp.render(entry, props, undefined, options); // ...etc etc
```

**Omitting `request` from `render` has the effect of always rendering as if it’s inside Content Studio** (see above). Again, this is by design - trying to make sure that a viewable and safe rendering is always returned, even when viewing context can’t be determined.

However, it also means that `hydrate` and `ssr` options are ignored (you always get SSR without Hydration), and there is no call to activate the react app in the browser. Basically, it’s as if TSX/JSX is used as a pure, static HTML templating language (same as XP’s Thymeleaf renderer - which shares the same basic signature).

When `request` is omitted, `.render` will ** never output error messages from SSR** in error containers or browser console.

Examples

See the [invocation example](#invocation-example) above for the minimal case, and the [React4xp object](#react4xp_object) when you need the two rendering steps separately.

### processHtml

Transforms raw rich text HTML (typically the value of an `HtmlArea` input) into the `RichTextData` format consumed by the `RichText` component from `@enonic/react-components` - resolving links, sizing images and preparing macros for rendering. Typically used inside a data processor, like in the [React4XP tutorial](https://developer.enonic.com/learn/react4xp-tutorial).

Parameters

The `params` object accepts the same parameters as XP’s [portal.processHtml](https://developer.enonic.com/docs/code/stable/libraries/lib-portal#processhtml), plus `dataFetcher` and `component`:

| Name | Type | Description |
| --- | --- | --- |
| `value` | string | The raw HTML string to process. |
| `dataFetcher` | DataFetcher | The dataFetcher instance - inside a processor, pass `params.dataFetcher` along. |
| `component` | component object | **Optional.** The component currently being processed (`params.component`). |
| `imageWidths` | number[] | **Optional.** Widths (in pixels) of scaled image variants to generate, used for the `srcset` attribute of images. |
| `imageSizes` | string | **Optional.** Value for the `sizes` attribute of images, mapping media conditions to the image widths above. |
| `type` | `server` \| `absolute` | **Optional.** URL type of the processed links. Either server (server-relative URL, default) or absolute. |

Returns

Returns a `RichTextData` object, ready to be passed to the `data` prop of the `RichText` react component.

Example

src/main/resources/react4xp/components/parts/ParagraphProcessor.ts

```typescript
import {PartComponent} from '@enonic-types/core';
import type {ComponentProcessor} from '@enonic-types/lib-react4xp/DataFetcher';
import {processHtml} from '/lib/enonic/react4xp';

export const paragraphProcessor: ComponentProcessor<'com.enonic.app.hmdb:paragraph'> = (params) => {
    const component = params.component as PartComponent;
    const text = component.config?.text as string;

    return {
        text: text ? processHtml({
            value: text,
            imageWidths: [200, 400, 800],
            dataFetcher: params.dataFetcher,
            component: params.component
        }) : '',
    };

};
```

### serviceUrl

Builds a URL to an XP service. React4XP uses it internally to serve its own assets, and it is exported for cases where you need a service URL of your own with React4XP’s URL-type handling applied.

```TypeScript
import {serviceUrl} from '/lib/enonic/react4xp';

const url = serviceUrl({service: 'myService'});
```

| Name | Type | Description |
| --- | --- | --- |
| `service` | string | **Required.** Name of the service to link to. |
| `path` | string | **Optional.** Path appended to the service URL. Defaults to `/`. |
| `params` | object | **Optional.** Query parameters to add to the URL. |
| `application` | string | **Optional.** Application the service belongs to. Defaults to the current app (`app.name`). |
| `type` | `server` \| `absolute` | **Optional.** URL type. Defaults to `app.config['react4xp.urlType']` - see [Configuration](docs/react4xp/6.x/config.md). |

> **Note:** `serviceUrl` is removed in React4XP 7, where assets are served through an XP 8 universal API instead of services.

## Classes

### DataFetcher

`DataFetcher` is the server-side props layer. You register **processor** functions against content types, page/part/layout descriptors and macros, then call `process()` once per request to walk the content’s component tree and produce the props object that [render](#react4xp_render) passes to your [entry](docs/react4xp/6.x/entries.md).

This is the model the [starter](docs/react4xp/6.x/starter.md#single-entry) is built on: a single React entry renders the whole page, and the `DataFetcher` decides what data each component in that tree receives.

The class is exported by the library itself - the processor **types** come from the companion npm types package:

```TypeScript
import {DataFetcher} from '/lib/enonic/react4xp';
import type {ComponentProcessor} from '@enonic-types/lib-react4xp/DataFetcher';

export const dataFetcher = new DataFetcher();
```

> **Note:** Instantiate the `DataFetcher` once in its own module and import that instance where needed - both in the [app function](docs/react4xp/6.x/app.md) and in the React entry via `componentRegistry`. The constructor takes no arguments.

#### Registering processors

| Method | Registers a processor for |
| --- | --- |
| `addContentType(contentTypeName, {processor})` | A content type, e.g. `'portal:site'` or `'com.example.app:article'`. Takes precedence over all component-level processors. |
| `addPage(descriptor, {processor})` | A page descriptor, e.g. `'com.example.app:main'` |
| `addPart(descriptor, {processor})` | A part descriptor |
| `addLayout(descriptor, {processor})` | A layout descriptor |
| `addMacro(descriptor, {processor})` | A macro name - see [Macros](docs/react4xp/6.x/macro-data.md) |
| `addCommon({processor})` | Data needed by **every** component on the page. Takes no descriptor, and the result is placed on `common` rather than `data`. |

Matching lookup helpers are also available: `hasContentType(name)`, `hasPage(name)`, `hasPart(name)`, `hasLayout(name)`, `hasMacro(name)`, `hasCommon()` and `getMacro(descriptor)`.

src/main/resources/react4xp/dataFetcher.ts

```TypeScript
import {DataFetcher} from '/lib/enonic/react4xp';
import {helloProcessor} from './components/hello/HelloProcessor';

export const dataFetcher = new DataFetcher();

dataFetcher.addContentType('portal:site', {processor: helloProcessor});
```

#### The processor function

A processor is a synchronous function that receives request context and returns a plain object of props. It runs **server-side only** - never in the browser - so it is where content queries, permission checks and any other backend work belong.

```TypeScript
import type {ComponentProcessor} from '@enonic-types/lib-react4xp/DataFetcher';
import type {PageDescriptor} from '@enonic-types/core';

export const helloProcessor: ComponentProcessor<PageDescriptor> = (params) => {
    const title = params.content?.displayName || params.content._name || 'Display name not set';
    return {
        title,
        initialCount: 0,
    };
};
```

The `params` object contains:

| Property | Type | Description |
| --- | --- | --- |
| `content` | PageContent | The content being rendered |
| `component` | Component | The component this processor was invoked for. Undefined for content-type processors when using automatic page templates. |
| `request` | Request | The current XP request |
| `dataFetcher` | DataFetcher | The instance itself - pass it along to [processHtml](#processhtml) when processing rich text |
| `runMode` | XpRunMode | `'development'` or `'production'` |

Any extra properties passed to `process()` are forwarded to every processor as part of `params`, which is how you thread request-scoped values down the tree without globals.

The returned object becomes the `data` prop of the corresponding component in the React tree.

#### process

Resolves the whole component tree and returns the props for the entry.

```TypeScript
const data = dataFetcher.process({
    content,   (1)
    request,   (2)
    component, (3)
});
```

| ****1** | Optional. Defaults to `portal.getContent()`; throws if neither is available. |
| --- | --- |
| ****2** | **Required** - `process` throws if omitted. |
| ****3** | Optional. Defaults to `content.page` or `content.fragment`. |

The return value is a `ProcessResult`:

| Property | Type | Description |
| --- | --- | --- |
| `component` | ComponentData | The resolved component tree, including nested regions |
| `data` | Record<string, unknown> | Props from the processor that matched |
| `common` | Record<string, unknown> | Props from the `addCommon` processor, if one is registered |
| `meta` | MetaData | `type`, `id` and `path` of the content, plus the request `mode` |

Pass the whole result straight to `render` - see the [app function](docs/react4xp/6.x/app.md):

```TypeScript
const data = dataFetcher.process({content, request});

return render('App', data, request, {body, id});
```

#### Resolution order

For each component, `process` picks **one** processor:

- If a processor is registered for the **content type**, it wins - no component-level processor is consulted.

- Otherwise the component’s own type decides: `part`, `layout`, `text` or `fragment`.

- If the component type is undefined - which is the case for automatic page templates - it is treated as a `page`.

Afterwards, the `addCommon` processor runs and its result is placed on `common`. It is skipped if the tree already resolved to an error.

> **Tip:** Registering a content-type processor is the shortcut for taking over a whole page from one function. Register page/part/layout processors instead when you want per-component data with regions resolved for you.

#### Error handling

If a processor throws, React4XP does not fail the request. The error is logged server-side and the offending component is replaced with an error component (`type: 'error'`) carrying an HTML message naming the descriptor and content path, so the rest of the page still renders. The thrown error message is included in that HTML (sanitized), so keep in mind it is visible to whoever views the page - treat a rendered error component as a processor that needs fixing, not as a supported rendering path.

### React4xp

More flexible and controllable than `React4xp.render`: create a data-holding react4xp object with the React4xp contructor, manipulate it or extract data from it, combine with other objects, and then later render it to an HTML body string and/or page contributions, separately. This is actually what `React4xp.render` does behind the scenes.

Call the two rendering methods from the same react4xp object. Remember, if using `hydrate`, `ssr` and/or `request` options, they should usually be the same value across the two corresponding calls. A typical (compact) usage example:

```javascript
exports.get = (request) => {

    // Object constructor:
    const myComponent = new React4xp('my-entry');

    // ...read myComponent attributes and/or use its setter methods...

    // const ssr = ...true or false...

    // Call the rendering methods:
    return {
        body: myComponent.renderBody({
            // ssr, etc
            request
        }),
        pageContributions: myComponent.renderPageContributions({
            // hydrate, ssr, etc
            request
        })
    }; // ...etc, etc
}
```

The methods and options are documented in full below, starting with the [constructor](#constructor).

The setter methods (below) are all optional; if not used, the object renders with empty values or placeholders where needed, along the same logic as [`render`](#react4xp_render). They all **return the data object itself**, so you can chain them in a **builder pattern**: `myComponent.setProps(…​).setId(…​)`. The order doesn’t matter - except for `setId` and `uniqueId`, which affect each other.

#### Constructor

```javascript
const myComponent = new React4xp(entry);
```

Creates an initial react4xp data object from an entry.

| Name | Type | Description |
| --- | --- | --- |
| `entry` | string \| component object | Reference to an [entry](docs/react4xp/6.x/entries.md): the react component to be rendered. Direct [JsxPath](docs/react4xp/6.x/entries.md#jsxPath) string, or a `portal.getComponent()` object. If you use a component object like that, the entry must be a TSX/JSX file with the *same name* in the *same folder* as the component implementation, and react4xp will try to generate an ID from the content. |

**Constructs** a react4xp data object, which exposes the attributes and methods below.

#### Object attributes

Extract from the object the data that has been generated or set in it.

| Name | Type | Description |
| --- | --- | --- |
| `react4xpId` | string | Target `id` of the HTML element the entry will be rendered into (if it’s been set yet - see `setId` and `uniqueId` below). Also identifies the object. |
| `jsxPath` | string | [jsxPath](docs/react4xp/6.x/entries.md#jsxPath) to the entry. |
| `props` | object | `props` for the entry’s initial rendering. At the time of rendering, an attribute `react4xpId` is added to the props, allowing each entry to access its own unique ID at runtime. |

Example:

```javascript
const targetElementId = myComponent.react4xpId;
```

#### setProps

```javascript
myComponent.setProps(props);
```

Sets props for the entry.

| Name | Type | Description |
| --- | --- | --- |
| `props` | object | `props` passed into the react component for initial rendering. JS object must be serializable (no functions can be passed). |

#### setId

```javascript
myComponent.setId(id);
```

Sets an ID - directly and literally, so uniqueness is up to you. This ID both identifies this react4xp object (aka. `react4xpId`), and crucially, points React to an HTML element (in the `body` param, during `render` or `renderBody` later) which is the target container for rendering the entry into. Phew.

> **Note:** If `render` or `renderBody` are called without an ID having been set yet, then a unique random ID will be generated on the fly. This of course implies that there will be no matching-ID element in `body`. In cases like this (or when there’s no `body` at all), an empty target element with a matching ID will be generated/inserted, to contain the React rendering.

If the data object already has an ID, `.setId(id)` will overwrite it. If `id` is omitted/empty, `.setId()` just deletes any previous ID (which has the later effect of giving this a new, unique ID at the time of rendering).

| Name | Type | Description |
| --- | --- | --- |
| `id` | string | **Optional.** ID of both the target HTML element and the data object itself. |

#### uniqueId

```javascript
myComponent.uniqueId();
```

Enforces a unique ID, either by itself or after running `.setId()`. If the object already has an ID (`react4xpId`), a random string will be added to it. If not, the ID will just be the random string.

No parameters.

#### setJsxPath

```javascript
myComponent.setJsxPath(jsxPath);
```

If you for some reason need to override the JsxPath that was set (or inferred from the component object) in the constructor.

| Name | Type | Description |
| --- | --- | --- |
| `jsxPath` | string | New [jsxPath](docs/react4xp/6.x/entries.md#jsxPath) to a different entry. |

The two rendering methods below perform specific rendering tasks independently, using the data object as set up with the setters and constructor (or `setJsxPath`).

> **Note:** Most of these rendering methods will lock down the jsxPath and ID of the react4xp data object the first time one of them is run. After this, the setters will prevent these from being changed so that another conflicting rendering can’t be performed from the same data object.

#### renderBody

```javascript
const responseBody = myComponent.renderBody(options);
```

Similar to [`render`](#react4xp_render) above, but `renderBody` in itself ***only* renders a static HTML output**.

> **Note:** Does *not* render page contributions. Combine with a corresponding [renderPageContributions](#render_pgcontr) call from the same data object, or the rendering will not be active in the browser.

→ See [Request and automated behavior](#react4xp_object_request) for the custom flow examples.

`renderBody` renders based on the state of the data object reached at the time of rendering.

Just like `render` does, `renderBody` ensures that the output HTML will always contain a matching-ID target element for react-rendering/hydrating the entry into (in the browser). And if serverside rendering is switched on (that is, `ssr` is not false, or safe context-dependent rendering is enforced by adding `request` - [see the summary](#react4xp_object_request)), the target element will contain the static HTML rendering.

Parameters

`renderBody()` takes a single `options` object; all properties are optional. Other renderings are not affected, *even from the same data object*, so make sure a different rendering from the same data object uses the same mode.

| Name | Type | Description |
| --- | --- | --- |
| `body` | string | **Optional.** Valid HTML to serve as container - same as `body` in `render’s options. Defaults to a `<div>` with matching `id` (same as `react4xpId` in the data object). |
| `ssr` | boolean | **Optional.** Switch between client-side and server-side rendering for this particular rendering. Defaults to `app.config['react4xp.ssr']` or `true`. |
| `wrapper` | boolean | **Optional.** Whether to render the surrounding container element around the target element. |
| `request` | [XP request object](https://developer.enonic.com/docs/code/stable/web/request-response) | **Optional.** Including this here (*and* in the corresponding [`renderPageContributions`](#render_pgcontr) call) is the easiest way to handle [view-context dependent behavior](#react4xp_object_request). |

Returns

Returns an HTML string ready to return as the `body` attribute in a [response object](https://developer.enonic.com/docs/code/stable/web/request-response) from the function.

The root of the returned HTML is always a **surrounding container** HTML that will have a matching-ID **target element** in it somewhere (an element matching the data object’s ID (`react4xpId`), either from the [ID setter methods](#set_id), or a generated ID if they haven’t been run). This surrounding structure is `options.body`, unchanged if that already contained a matching-ID element, or with a new target element generated and inserted at the end if it didn’t have one. If there is no `options.body`, the surrounding container is just a generated target element.

Inside that matching-ID element, there will be a serverside rendering of the entry (with the initial props from `.setProps`) if `options.ssr` is not false.

#### renderPageContributions

```javascript
const outputPageContributions = myComponent.renderPageContributions(options);
```

Similar to [`render`](#react4xp_render) above, but *only* renders the [page contributions](https://developer.enonic.com/docs/code/stable/web/sites/contributions) needed to run and activate the react component in the browser:

- references to the entry’s own asset,

- dependency assets,

- and the react-activating trigger call in the browser (`.render` or `.hydrate`, depending on the `hydrate`, `ssr` and `request` options).

Renders based on the state of the data object at the time of rendering.

> **Note:** Does *not* render any HTML. Run `.renderBody` from the same data object, or the browser may have nothing to activate / nowhere to render the entry.

Also, unless you add the `request` option, there is **no detection of inside-vs-outside Content Studio**, and consequently the client is *not* automatically prevented from running client-side code in Content Studio. That is not recommended - see [the summary](#react4xp_object_request).

Parameters

`renderPageContributions()` takes a single `options` object; all properties are optional. Other renderings are not affected, *even from the same data object*, so make sure a different rendering from the same data object uses the same mode.

| Name | Type | Description |
| --- | --- | --- |
| `pageContributions` | [page contributions](https://developer.enonic.com/docs/code/stable/web/sites/contributions) | **Optional.** Existing page contributions to add *before* the ones rendered here (within each section `headBegin`, `bodyEnd`, etc). Defaults to an empty object. |
| `hydrate` | boolean | **Optional.** When SSR is true, choose whether to hydrate. Defaults to `app.config['react4xp.hydrate']` or `true`. |
| `ssr` | boolean | **Optional.** Switch between client-side and server-side rendering for this particular rendering. Defaults to `app.config['react4xp.ssr']` or `true`. |
| `urlType` | `server` \| `absolute` | **Optional.** URL type for assets: server-relative or absolute. Defaults to `app.config['react4xp.urlType']` or `server`. |
| `request` | [XP request object](https://developer.enonic.com/docs/code/stable/web/request-response) | **Optional.** Including this here (*and* in the corresponding [`renderBody`](#render_body) call) is the easiest way to handle [view-context dependent behavior](#react4xp_object_request). |

Returns

A regular [page contributions](https://developer.enonic.com/docs/code/stable/web/sites/contributions) object, ready to be used as the `pageContributions` attribute in an [response object](https://developer.enonic.com/docs/code/stable/web/request-response) from the function.

Includes everything the browser needs to activate (or client-side render) the react component: script tags with urls to auto-compiled assets for the entry and its dependencies, a client-side react4xp wrapper asset and an activating trigger call to the client wrapper. Urls point to react4xp’s own optimized asset services. Also included before this, are any input `options.pageContributions`.

With a serverside rendering (`options.ssr` is not false), the client will expect an existing target element with a pre-rendered entry in the response `body`, and call `hydrate`. If `options.ssr` is false, an empty target element is expected in the response `body`, and the rendering is left to the client with `render`.

#### Request and automated behavior

The "custom flow" (`.renderBody` in tandem with `.renderPageContributions`) is intended as a more low-level approach: less hand-holding, more control to the developer for cases where that’s needed.

However, lib-react4xp version 1.6.0 introduced support for a `request` option parameter for these methods as well. The main idea is that **using `request` in both calls will now automate some behavior** the same way as calling `.render` with `request` (see [above](#render_request)).

Omitting `request` will still work the same way as before, leaving more to developers.

Custom flow with request

```javascript
const body = myComponent.renderBody({
    // ssr, etc
    request
});
const pageContributions = myComponent.renderPageContributions({
    // hydrate, ssr, etc
    request
});
// ...etc, etc
```

This will act [the same way as `render` used with a request](#render_request): viewing context is detected, so inside Content Studio edit mode, `hydrate` and `ssr` are ignored and you always get SSR, and JS assets and the `.hydrate` call is held back so the react component isn’t activated inside Content Studio edit mode. And outside Content Studio edit mode, you get a fully active render.

As with `render`, error message details are held back in live view mode.

Custom flow without request:

```javascript
const body = myComponent.renderBody({ /* ssr, etc */ });
const pageContributions = myComponent.renderPageContributions({ /* hydrate, ssr, etc */ });
// ...etc, etc
```

Contrary to when working with `.render`, omitting `request` from the custom flow does *not* enforce a max-safety rendering. Quite the opposite, removing `request` will remove all the "safety wheels", so this rendering mode **needs a bit of attention to guarantee that everything works everywhere**:

- `.renderBody` will take `ssr` into account in all contexts. What you set it to *will* take effect.

> **Note:** This risks a missing/empty visualization inside Content Studio, since `ssr: false` makes sure no SSR will render a static placeholder.

- And `.renderPageContributions` will render *all* page contributions in all contexts, including JS dependency assets and the `hydrate`/`render` browser-side calls.

> **Note:** Best case scenario: this might make a client-side rendered entry visible in Content Studio too. Worst case, it risks intervening with Content Studio’s UX, or even break its functionality, depending on the code used/imported by the entry.

> **Tip:** For a complete custom flow function, see the [usage example](#react4xp_object) at the start of this section.
