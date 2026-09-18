<!-- src:https://developer.enonic.com/learn/react4xp-tutorial/5.x/appendix/api generated:2026-07-30T04:16:10Z format:llm-dense react4xp-5.x -->
#DOC learn/react4xp-tutorial/5.x/appendix/api.md

# API reference

The React4xp library ([Enonic Market](https://market.enonic.com/vendors/enonic/react4xp-lib)) exposes a couple of methods that can be run from XP controllers.

This chapter also covers the [SSR engine](#ssr), compilation, and [configuration](learn/react4xp-tutorial/5.x/appendix/config.md) of those.

## Getting started

### Install

Instructions on how to install the library locally or insert it into your project are at [the library docs](https://github.com/enonic/lib-react4xp#readme) at github.

### Import library

In an XP controller:

```javascript
const React4xp = require('/lib/enonic/react4xp');
```

## React4xp.render

All-in-one shorthand function for a lot of use cases. Covers both client- and serverside rendering.

Inserts a react component into an (optional) pre-existing HTML string and adds any necessary page contributions to make all work: links to assets, both shared and specific to the entry, and a client-side JS call (`render` or `hydrate` in the client wrapper) that activates the react component in the browser.

### Signature

The signature is analogous to Thymeleaf’s familiar `render(view, model)`. But there are two extra parameters and a full XP response object is returned:

```javascript
{body, pageContributions} = React4xp.render(entry, props, request, options);
```

### Parameters

| Name | Type | Description |  |  |  |
| --- | --- | --- | --- | --- | --- |
| `entry` | string or component object, mandatory | Reference to an [entry](learn/react4xp-tutorial/5.x/appendix/entries.md): the react component to be rendered. [JsxPath](learn/react4xp-tutorial/5.x/appendix/jsxpath.md) reference - or if the entry is a TSX/JSX file with the *same name* in the *same folder* as the controller, you can use a `portal.getComponent()` object here. Corresponds to the template argument in `thymeleaf.render`. |  |  |  |
| `props` | object, optional | Data model passed into the react component. JS object must be serializable (no functions can be passed). Corresponds to the model argument in `thymeleaf.render`. |  |  |  |
| `request` | [XP request object](https://developer.enonic.com/docs/xp/stable/framework/http), optional (but *mandatory for react activation*) | Include to detect the rendering mode inside/outside Content Studio: inside Content Studio there should be only a static serverside-rendering, no browser react activation (or client-side rendering), only returning get an HTML visualization with the initial `props`. Special case: if `request` is not an object but omitted/falsy, page-contributions rendering is *completely skipped*. In this case, the *options* argument (below) is still valid: any added `body` there will still serve as a container for the rendered output from this call, and any `pageContributions` inside *options* are still added and returned. |  |  |  |
| `options` | object, optional | Additional options to control the rendering. All of them are optional within this object:      Properties                  Name | Type | Default | Description |
| `id` | string | Generated unique string | ID of the component, targeting the ID of an element in `body` (below): react will render into that container element. Should be a unique ID within the entire HTML document.      If no matching element ID is found in `body`, this sets the ID of a generated element in the HTML output. If `id` is missing, a unique ID is generated, either random or generated from the content. |  |  |
| `body` | string: valid HTML | `<div>` with matching `id` | HTML to serve as container for the react content. Can be a hardcoded string, come from a thymeleaf/mustache/XSLT render, or any source. When server-side rendering, the rendered output will be inserted into the matching-`id` element inside here (replacing whatever was already in that element), and everything (container `body` with rendered content in it) is returned as one HTML string. When client-side rendering, this insertion happens in the browser.      If no `body` is supplied, an empty `<div>` element with an ID matching `id` is generated and used as a container.      If a `body` is supplied but it doesn’t contain any element with a matching `id`, an extra matching-`id` `<div>` element will be generated and inserted into `body` - as a child of the root element of `body` and after any other content that’s already there. |  |  |
| `pageContributions` | object: valid [XP page contributions](https://developer.enonic.com/docs/xp/stable/framework/contributions) |  | If you already have some page contributions you want to add to the output of this rendering, add them here. These added page contributions will be added *before* the ones that will be rendered (within each section `headBegin`, `bodyEnd` etc). |  |  |
| `hydrate` | boolean | app.config['react4xp.hydrate'] or true | When SSR is true, choose whether you want hydration or not. |  |  |
| `ssr` | boolean | app.config['react4xp.ssr'] or true | Switch between clientside and serverside rendering, on this particular rendering. Other renderings are not affected, even within the same controller or using the same entry more than once.      If `false` / falsy or omitted, you get serverside rendering and the returned object will contain an HTML representation of the react component with the initial `props`, and page contributions will make the client call `.hydrate`.      If `true` / truthy, the server-side rendering is skipped for this particular rendering. The client will call `.render`.      This **only applies in live mode and previews**: inside *edit* or *browse* modes in Content Studio, you still only get a static server-side rendered representation). |  |  |
| `urlType` | server \| absolute | app.config['react4xp.urlType'] or server | URL type. Either server (server-relative URL) or absolute. The default is server. Available from `React4xp-5.1.0`. |  |  |

### Returns

Returns an [XP response object](https://developer.enonic.com/docs/xp/stable/framework/http) with these main attributes:

| Attribute | Type | Description |
| --- | --- | --- |
| `body` | string, rendered HTML | HTML output.      The root of this HTML is always a **surrounding container** HTML that will have a matching-ID **target element** in it somewhere (an element matching the ID of the clientside call to `.render` or `.hydrate`: that ID is `options.id` if that was set, or a generated unique one if not). This surrounding structure is `options.body`, unchanged if that already contained a matching-ID element, or with a new target element generated and inserted at the end if it didn’t have one. If there is no `options.body`, the surrounding container is just a generated target `<div>` element.      Inside that matching-ID element, there will be a serverside rendering of the entry (with the initial props from `options.props`) if `options.ssr` is not false. |
| `pageContributions` | object | Regular [XP page contributions](https://developer.enonic.com/docs/xp/stable/framework/contributions). Includes everything the browser needs to activate (or client-side render) the react component: script tags with URLs to auto-compiled assets for the entry and its dependencies, a client-side react4xp wrapper asset, and an activating client-wrapper call. URLs point to React4xp’s optimized asset services. Also included before this, are any input `options.pageContributions`. |

### Request and automated behavior

`.render` is intended to be convenient to work with and safely wrap around some common corner cases. It automates a little bit of behavior, depending on the `request` object argument (which stems from the XP controller):

#### `render` with `request`:

```javascript
React4xp.render(entry, props, request);
React4xp.render(entry, props, request, options); // ...etc etc
```

If `request` is supplied, viewing context is detected from `request.mode`: is rendering happening inside or outside of Content Studio edit mode?

- **Inside Content Studio edit mode**, `.render` will always select serverside rendering (no matter what `ssr` is) and skip JS dependency assets and the clientside `render`/`hydrate` trigger (but still still supply other dependencies, such as CSS). This ensures that a static HTML placeholder rendering is visible inside Content Studio’s edit mode, but keeps react from being activated. This is by design: preventing the possibility that react code might intervene with the UX of Content Studio itself.

- **Outside Content Studio edit mode**, the rendering will be activated as a react app (i.e. all pageContributions are rendered). Also, `ssr` is used, so if this is `false`, serverside rendering is skipped. The ``and `render` is called in the client instead of `hydrate`.

Also, when `request` is used, `.render` will output **error messages from SSR** in error containers and browser consoles (except in live view mode, where error containers and browser logs are more generic: shown without the specific messages).

#### `render` without `request`:

```javascript
React4xp.render(entry, props);
React4xp.render(entry, props, null);
React4xp.render(entry, props, undefined, options); // ...etc etc
```

**Omitting `request` from `render` has the effect of always rendering as if it’s inside Content Studio** (see above). Again, this is by design - trying to make sure that a viewable and safe rendering is always returned, even when viewing context can’t be determined.

However, it also means that `hydrate` and `ssr` options are ignored (you always get SSR without Hydration), and there is no call to activate the react app in the browser. Basically, it’s as if TSX/JSX is used as a pure, static HTML templating language (same as XP’s Thymeleaf renderer - which shares the same basic signature).

When `request` is omitted, `.render` will ** never output error messages from SSR** in error containers or browser console.

### Examples

Most of the lessons in the guide use `React4xp.render` (except the "custom flow" ones). For example [here](learn/react4xp-tutorial/5.x/hello-react.md#first_helloreact_jsx) or [here](learn/react4xp-tutorial/5.x/pages-parts-and-regions.md#color_part_controller).

## React4xp object: custom flow

More flexible and controllable than `React4xp.render`: create a data-holding react4xp object with the React4xp constructor, manipulate it or extract data from it, combine it with other objects, and then later render it to an HTML body string and/or page contributions, separately. This is actually what `React4xp.render` does behind the scenes.

Call the two rendering methods from the same react4xp object. Remember, if using `hydrate`, `ssr` and/or `request` options, they should usually be the same value across the two corresponding calls. A typical (compact) usage example:

```javascript
exports.get = function(request) => {

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

See the [custom flow syntax](learn/react4xp-tutorial/5.x/custom-flow-syntax.md) lesson to go more in depth.

### Object constructor

```javascript
const myComponent = new React4xp(entry);
```

Creates an initial react4xp data object from an entry.

| Parameter | Type | Description |
| --- | --- | --- |
| `entry` | string or component object, mandatory | Reference to an [entry](learn/react4xp-tutorial/5.x/appendix/entries.md): the react component to be rendered. Direct [JsxPath](learn/react4xp-tutorial/5.x/appendix/jsxpath.md) string, or a `portal.getComponent()` object. If you use a component object like that, the entry must be a TSX/JSX file with the *same name* in the *same folder* as the controller, and react4xp will try to generate an ID from the content. |

**Constructs** a react4xp data object, which exposes the attributes and methods below:

### Main object attributes

Extract from the object the data that has been generated or set in it.

| Name | Type | Description |
| --- | --- | --- |
| `react4xpId` | string | Target `id` of the HTML element the entry will be rendered into (if it’s been set yet - see `setId` and `uniqueId` below). Also identifies the object. |
| `jsxPath` | string | [jsxPath](learn/react4xp-tutorial/5.x/appendix/jsxpath.md) to the entry. |
| `props` | object | `props` for the entry’s initial rendering. At the time of rendering, an attribute `react4xpId` is added to the props, allowing each entry to access its own unique ID at runtime. |

Example:

```javascript
const targetElementId = myComponent.react4xpId;
```

### Setter methods

Use these to set the object’s properties. All of them are optional; if not used, the object will render with empty values or placeholders where needed, along the same logic as for [React4xp.render](#react4xp_render) above.

All the setter methods **return** the data object itself, so that you can use a **builder pattern** where…​

```javascript
myComponent.firstSetter("a").secondSetter("b").thirdSetter("c");
```

…​is equivalent to:

```javascript
myComponent.firstSetter("a");
myComponent.secondSetter("b");
myComponent.thirdSetter("c");
```

The order between the setters doesn’t matter - except for `setId` and `uniqueId`, which affect each other.

#### .setProps

```javascript
myComponent.setProps(props);
```

Sets props for the entry.

| Parameter | Type | Description |
| --- | --- | --- |
| `props` | object, mandatory | `props` passed into the react component for initial rendering. JS object must be serializable (no functions can be passed). |

#### .setId

```javascript
myComponent.setId(id);
```

Sets an ID - directly and literally, so uniqueness is up to you. This ID both identifies this react4xp object (aka. `react4xpId`), and crucially, points React to an HTML element (in the `body` param, during `render` or `renderBody` later) which is the target container for rendering the entry into. Phew.

> **Note:** If `render` or `renderBody` are called without an ID having been set yet, then a unique random ID will be generated on the fly. This of course implies that there will be no matching-ID element in `body`. In cases like this (or when there’s no `body` at all), an empty target element with a matching ID will be generated/inserted, to contain the React rendering.

If the data object already has an ID, `.setId(id)` will overwrite it. If `id` is omitted/empty, `.setId()` just deletes any previous ID (which has the later effect of giving this a new, unique ID at the time of rendering).

| Parameter | Type | Description |
| --- | --- | --- |
| `id` | string, optional | ID of both the target HTML element and the data object itself. |

#### .uniqueId

```javascript
myComponent.uniqueId();
```

Enforces a unique ID, either by itself or after running `.setId()`. If the object already has an ID (`react4xpId`), a random string will be added to it. If not, the ID will just be the random string.

No parameters.

#### .setJsxPath

```javascript
myComponent.setJsxPath(jsxPath);
```

If you for some reason need to override the JsxPath that was set (or inferred from the component object) in the constructor.

| Parameter | Type | Description |
| --- | --- | --- |
| `jsxPath` | string, mandatory | New [jsxPath](learn/react4xp-tutorial/5.x/appendix/jsxpath.md) to a different entry. |

### Rendering methods

These methods perform specific rendering tasks independently, using the data object as a basis, the way it’s set up with the [setters](#setter_methods) and with the entry from the [constructor](#constructor) (or the `setJsxPath` setter).

> **Note:** Most of these rendering methods will lock down the jsxPath and ID if the react4xp data object, the first time one of them is run. After this, the setters will prevent these from being changed so that another conflicting rendering can’t be performed from the same data object.

#### .renderBody

```javascript
const responseBody = myComponent.renderBody(options);
```

Similar to [React4xp.render](#react4xp_render) above, but `renderBody` in itself ***only* renders a static HTML output**.

> **Note:** Does *not* render page contributions. Combine with a corresponding [renderPageContributions](#render_pgcontr) call from the same data object, or the rendering will not be active in the browser.

→ See the [custom flow syntax](learn/react4xp-tutorial/5.x/custom-flow-syntax.md) examples.

`renderBody` renders based on the state of the data object reached at the time of rendering.

Just like `render` does, `renderBody` ensures that the output HTML will always contain a matching-ID target element for react-rendering/hydrating the entry into (in the browser). And if serverside rendering is switched on (that is, `ssr` is not false, or safe context-dependent rendering is enforced by adding `request` - [see the summary](#react4xp_object_request)), the target element will contain the static HTML rendering.

Parameters

| Parameter | Type | Description |  |  |  |
| --- | --- | --- | --- | --- | --- |
| `options` | object, optional | Options to control the rendering, all of them optional:      Properties                  Name | Type | Default | Description |
| `body` | string: valid HTML | `<div>` with matching `id` (same as `react4xpId` in the data object) | Same as the `options.body` in [React4xp.render](#react4xp_render_parameters) above. |  |  |
| `ssr` | boolean | app.config['react4xp.ssr'] or true | Switch between clientside and serverside rendering, on this particular rendering. |  |  |
| `request` | [XP request object](https://developer.enonic.com/docs/xp/stable/framework/http) | undefined | Including this here (*and* in the corresponding [`renderPageContributions`](#render_pgcontr) call) is the easiest way to handle [view-context dependent behavior](#react4xp_object_request). |  |  |

Other renderings are not affected, *even from the same data object* (so you usually want to make sure a different rendering from the same data object uses the same mode).

Returns

Returns an HTML string ready to return as the `body` attribute in an [XP response object](https://developer.enonic.com/docs/xp/stable/framework/http#http-response) from the controller.

The root of the returned HTML is always a **surrounding container** HTML that will have a matching-ID **target element** in it somewhere (an element matching the data object’s ID (`react4xpId`), either from the [ID setter methods](#set_id), or a generated ID if they haven’t been run). This surrounding structure is `options.body`, unchanged if that already contained a matching-ID element, or with a new target element generated and inserted at the end if it didn’t have one. If there is no `options.body`, the surrounding container is just a generated target element.

Inside that matching-ID element, there will be a serverside rendering of the entry (with the initial props from `.setProps`) if `options.ssr` is not false.

#### .renderPageContributions

```javascript
const outputPageContributions = myComponent.renderPageContributions(options);
```

Similar to [React4xp.render](#react4xp_render) above, but *only* renders the [page contributions](https://developer.enonic.com/docs/xp/stable/framework/contributions) needed to run and activate the react component in the browser:

- references to the entry’s own asset,

- dependency assets,

- and the react-activating trigger call in the browser (`.render` or `.hydrate`, depending on the `hydrate`, `ssr` and `request` options).

Renders based on the state of the data object at the time of rendering.

> **Note:** Does *not* render any HTML. Run `.renderBody` from the same data object, or the browser may have nothing to activate / nowhere to render the entry.

Also, unless you add the `request` option, there is **no detection of inside-vs-outside Content Studio**, and consequently the client is *not* automatically prevented from running client-side code in Content Studio. That is not recommended - see [the summary](#react4xp_object_request).

**Parameters:**

| Parameter | Type | Description |  |  |  |
| --- | --- | --- | --- | --- | --- |
| `options` | object, optional | Options to control the rendering, all of them optional:      Properties                  Name | Type | Default | Description |
| `pageContributions` | object: valid [XP page contributions](https://developer.enonic.com/docs/xp/stable/framework/contributions) | empty object | If you already have some page contributions you want to add to the output of this rendering, add them here. These added page contributions will be added *before* the ones that will be rendered (within each section `headBegin`, `bodyEnd` etc). |  |  |
| `hydrate` | boolean | app.config['react4xp.hydrate'] or true | When SSR is true, choose whether you want hydration or not. |  |  |
| `ssr` | boolean | app.config['react4xp.ssr'] or true | Switch between clientside and serverside rendering, on this particular rendering. |  |  |
| `request` | [XP request object](https://developer.enonic.com/docs/xp/stable/framework/http) | undefined | Including this here (*and* in the corresponding [`renderPageContributions`](#render_body) call) is the easiest way to handle [view-context dependent behavior](#react4xp_object_request).      Other renderings are not affected, *even from the same data object* (so you usually want to ensure a different rendering from the same data object uses the same mode). |  |  |

**Returns:**

A regular [XP page contributions](https://developer.enonic.com/docs/xp/stable/framework/contributions) object, ready to be used as the `pageContributions` attribute in an [XP response object](https://developer.enonic.com/docs/xp/stable/framework/http#http-response) from the controller.

Includes everything the browser needs to activate (or client-side render) the react component: script tags with URLs to auto-compiled assets for the entry and its dependencies, a client-side react4xp wrapper asset, and an activating trigger call to the client wrapper. URLs point to react4xp’s own optimized asset services. Also included before this, are any input `options.pageContributions`.

With a serverside rendering (`options.ssr` is not false), the client will expect an existing target element with a pre-rendered entry in the response `body`, and call `hydrate`. If `options.ssr` is false, an empty target element is expected in the response `body`, and the rendering is left to the client with `render`.

### Request and automated behavior

The ["custom flow"](learn/react4xp-tutorial/5.x/custom-flow-syntax.md) (`.renderBody` in tandem with `.renderPageContributions`) is intended as a more low-level approach: less hand-holding, more control to the developer for cases where that’s needed.

However, lib-react4xp version 1.6.0 introduced support for a `request` option parameter for these methods as well. The main idea is that **using `request` in both calls will now automate some behavior** the same way as calling `.render` with `request` (see [above](#render_request)).

Omitting `request` will still work the same way as before, leaving more to developers.

#### Custom flow with `request`

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

#### Custom flow without `request`:

```javascript
const body = myComponent.renderBody({ /* ssr, etc */ });
const pageContributions = myComponent.renderPageContributions({ /* hydrate, ssr, etc */ });
// ...etc, etc
```

Contrary to when working with `.render`, omitting `request` from the custom flow does *not* enforce a max-safety rendering. Quite the opposite, removing `request` will remove all the "safety wheels", so this rendering mode **needs a bit of attention to guarantee that everything works everywhere**:

- `.renderBody` will take `ssr` into account in all contexts. What you set it to *will* take effect.

> **Note:** This risks a missing/empty visualization inside Content Studio, since `ssr: false` makes sure no SSR will render a static placeholder.

- And `.renderPageContributions` will render *all* page contributions in all contexts, including JS dependency assets and the `hydrate`/`render` browser-side calls.

> **Note:** Best case scenario: this might make a client-side rendered entry visible in Content Studio too. Worst case, it risks intervening with Content Studio’s UX or even breaking its functionality, depending on the code used/imported by the entry.

### Custom flow examples

Custom flow usage is demonstrated [here](learn/react4xp-tutorial/5.x/custom-flow-syntax.md).

## SSR engine

The default running mode of React4xp is [serverside rendering (SSR)](https://www.freecodecamp.org/news/demystifying-reacts-server-side-render-de335d408fe4/) (although `ssr` can override this).

In a nutshell, source files like TSX and JSX are compiled into JS assets that lib-react4xp’s SSR engine runs to render HTML. This output is then delivered to the browser along with dependency code (usually references to necessary assets like CSS, JS, etc) - these dependencies are also rendered, as page contributions. Rendering the HTML body and the page contributions happens in two different steps, using either [`render`](#react4xp_render) (which wraps both steps for convenience) or the ["custom flow"](#react4xp_object).

The aim of react4xp is [isomorphic rendering](https://medium.com/capital-one-tech/why-everyone-is-talking-about-isomorphic-universal-javascript-and-why-it-matters-38c07c87905): after the react component(s) are serverside rendered, they are activated (hydrated) in the browser, turning them into running, active react apps. It’s *the same react code* that runs at the server as in the browser: no need to write the same component twice - one for SSR and one for the browser (although occasionally, tweaks are needed to prevent browser specific code from running on the server).

### Renderers

Starting from version 1.5.0, react4xp handles multithreaded rendering. This is done by setting up a number of renderers where each one is ready to answer to rendering requests in parallel, independently.

The number of renderer workers is [determined in java but can be overriden](learn/react4xp-tutorial/5.x/appendix/config.md#ssrMaxThreads).

When a renderer runs into an error during SSR, that renderer is torn down and a new one is initialized (see warmup time below). This happens as far as possible during idle time.

### Warmup time

After your React4xp app is (re)started, the first time React4xp is triggered to render something, the engine will initialize. This means the renderers will load the *compiled assets* necessary for the rendering, into the engine memory:

- react and reactDOM (`globals.*.js`),

- packages from *node_modules* (`vendors.*.js`),

- dependency assets imported by the react components (aka. [chunks](learn/react4xp-tutorial/5.x/appendix/chunks.md)),

- and finally, the [entry assets](learn/react4xp-tutorial/5.x/appendix/entries.md) themselves.

**This causes some warmup time** when starting your app: a noticeable delay before the first rendering shows up. This may be just a couple of seconds in total, but it may also take longer. It depends on the size and complexity of the *compiled* assets involved. This will happen on every restart of the app (and every [renderer](#renderers) must be initialized, but they do this in parallel).

But as long as the code runs without errors, initialization happens only once (i.e. each asset is loaded once at most, on each renderer). After the warmup, the react apps are ready to run from memory, so repeated renderings after that (even with different props) are fast.

#### Improving warmup time for development

Since development can involve repeated app/server restarts, here is one way to improve initial loading time when developing large projects:

- Don’t build React4xp components with `NODE_ENV = development`, but use `production` (which is the default - see [Build environment](learn/react4xp-tutorial/5.x/appendix/build.md#NODE_ENV)). Assets built with `development` are much more verbose, and this size difference - although functionally equal - actually makes a difference.

(Other optimizations and approaches are under consideration, to shorten the warmup time even more).

### SSR performance

Apart from when assets are initialized during the engine [warmup](#warmup), each SSR should be fast. However, in cases where you need to improve SSR performance further, it can be done by wrapping the rendering in a [cache](https://developer.enonic.com/docs/cache-library) in the controller.

Be sure to use any value that can change the rendering output - usually from `props` (and `options`?) or a subset of them - as a **key** in the cache.

For example:

```javascript
const cacheLib = require('/lib/cache');

// Set the cache up with a size that's reasonable
// for the most used props combinations
// and the size of the rendered output HTML string:
const cache = cacheLib.newCache({
    size:   100,
    expire: 3600
});

const makeKey = props => {
    // ...return a string that's reliably determined by the relevant values from props
};

exports.get = request => {
    const props = {
        // ... build props from whatever sources are needed
    };

    const key = makeKey(props);

    // Now render is only called when the key is new.
    // If the key is cached before, it just returns the output for that key.
    return cache.get(
        key,
        () => React4xp.render(
            myEntry,
            props,
            request,
            options
        )
    );

};
```
