<!-- src:https://developer.enonic.com/docs/react4xp/stable/ssr generated:2026-07-30T04:17:59Z format:llm-dense react4xp-7.x -->
#DOC docs/react4xp/stable/ssr.md

# Server Side Rendering (SSR)

By default React4XP renders your React components on the server, sends the resulting HTML to the browser, and then hydrates them into live React apps in the browser

## How it works

The default running mode of React4xp is [serverside rendering (SSR)](https://www.freecodecamp.org/news/demystifying-reacts-server-side-render-de335d408fe4/) (although `ssr` can override this).

In a nutshell, source files like TSX and JSX are compiled into JS assets that lib-react4xp’s SSR engine runs to render HTML. This output is then delivered to the browser along with dependency code (usually references to necessary assets like CSS, JS etc) - these dependencies are also rendered, as page contributions. Rendering the HTML body and the page contributions happens to two different steps, using either [`render`](docs/react4xp/stable/library.md#react4xp_render) (which wraps both steps for convenience) or the ["custom flow"](docs/react4xp/stable/library.md#react4xp_object).

The aim of react4xp is [isomorphic rendering](https://medium.com/capital-one-tech/why-everyone-is-talking-about-isomorphic-universal-javascript-and-why-it-matters-38c07c87905): after the react component(s) are serverside rendered, they are activated ([hydrated](#hydration)) in the browser, turning them into running, active react apps. It’s *the same react code* that runs at the server as in the browser: no need to write the same component twice - one for SSR and one for the browser (although occasionally, tweaks are needed to prevent browserspecific code from running on the server).

## Hydration

By default React4XP renders entries both server-side and client-side: the HTML is rendered on the server first, then **hydrated** - activated - in the browser. You can also switch to server-side only, or client-side only.

### Controlling SSR and hydration

The mode is set per rendering, through the `options` argument of [`render`](docs/react4xp/stable/library.md#react4xp_render):

```TypeScript
const output = render(
  'MyComponent',
  props,
  request,
  {
    body: myHtmlBody,
    id: myId,
    ssr: true, (1)
    hydrate: true (2)
  }
);

return output;
```

| ****1** | Set to `false` to disable server-side rendering |
| --- | --- |
| ****2** | Set to `false` to disable client-side rendering |

Both default to the matching [application config](docs/react4xp/stable/config.md) value - `react4xp.ssr` and `react4xp.hydrate` - which are themselves `true` unless you set them. See the [render parameters](docs/react4xp/stable/library.md#react4xp_render_parameters) for the full option list.

### Server- and client-side gotchas

When using isomorphic JavaScript, selected features may only be working on server-side, and some only on client side, like `document` and `window` - which are pure client-side concepts. React4xp has polyfilled `window` as *empty object*. To prevent weird behavior or errors, take care to only execute browser-specific code in the browser.

For example, the click counter in the starter’s `Hello` component is compiled and read into memory on the server, but its click handler is never triggered to actually *run* there - so it needs no extra safeguard. Where you do need one, it’s easy enough:

```javascript
if (typeof window.navigator !== 'undefined') {
    // ...This won't run during SSR...
}
```

Of course, this also applies to imported packages / nested components and so on. Importing them is usually safe, but consider wrapping the areas where they’re called/used.

> **Tip:** Your React components may produce server-side errors, but these are not always easily interpreted.

Switching over to pure *clientside rendering* (by setting SSR false, Hydrate true) in your app function, the particular React component will likely give you a better/sourcemapped error message in the browser console, making your debugging life easier.

## Warmup time

After your React4xp app is (re)started, the first time React4xp is triggered to render something, the engine will initialize. This means the engine will load the *compiled assets* necessary for the rendering, into memory:

- react and reactDOM (`globals.*.js`),

- packages from *node_modules* (`vendors.*.js`),

- dependency assets imported by the react components (aka. [chunks](docs/react4xp/stable/chunks.md)),

- and finally, the [entry assets](docs/react4xp/stable/entries.md) themselves.

**This causes some warmup time** when starting your app: a noticable delay before the first rendering shows up. This may be just a couple of seconds in total, but it may also take longer. It depends on the size and complexity of the *compiled* assets involved. This will happen on every restart of the app.

But as long as the code runs without errors, initialization happens only once - each asset is loaded once at most. After the warmup, the react apps are ready-to-run from memory, so repeated renderings after that (even with different props) are fast.

> **Note:** If an SSR throws an error, the engine discards and rebuilds the affected worker, which has to load its assets again. A single rendering can therefore be slow right after an error, even on a warmed-up app.

### Improving warmup time for development

Since development can involve repeated app/server restarts, here is one way to improve initial loading time when developing large projects:

- Don’t build React4xp components with `NODE_ENV = development`, but use `production` (which is the default - see [Build environment](docs/react4xp/stable/build.md#NODE_ENV)). Assets built with `development` are much more verbose, and this size difference - although functionally equal - actually makes a difference.

(Other optimizations and approaches are under consideration, to shorten the warmup time even more).

## SSR performance

Apart from when assets are initialized during the engine [warmup](#warmup), each SSR should be fast. However, in cases where you need to improve SSR performance further, it can be done by wrapping the rendering in a [cache](https://developer.enonic.com/docs/cache-library) in the app function.

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

exports.GET = request => {
    const props = {
        // ... build props from whatever sources are needed
    };

    const key = makeKey(props);

    // Now render is only called when the key is new.
    // If the key is cached before, just returns the output for that key.
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
