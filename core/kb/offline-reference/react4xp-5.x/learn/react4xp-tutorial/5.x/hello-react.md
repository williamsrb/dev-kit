<!-- src:https://developer.enonic.com/learn/react4xp-tutorial/5.x/hello-react generated:2026-07-30T04:16:10Z format:llm-dense react4xp-5.x -->
#DOC learn/react4xp-tutorial/5.x/hello-react.md

# Hello React - server and clientside rendering

## Lesson overview

React4xp is made to cover many ways of combining XP and react. Let’s start with a simple scenario: displaying a working react component in content studio.

We’ll first do that in the serverside rendered way (this is the React4xp default). And afterwards add an option flag that turns the rendering into clientside-rendering instead.

## Code

Lets start by setting up a **regular XP page controller** called `hello-react`.

We’ll add the following files to the project

```files
/src/main/resources/site/pages/hello-react/
  hello-react.xml
  hello-react.ts
  hello-react.tsx
```

### Page descriptor

First, we need a *page * XML file. Just XP boilerplate:

pages/hello-react/hello-react.xml:

```xml
<page>
  <display-name>Hello React</display-name>
  <description>Super simple example</description>
  <form />
  <regions />
</page>
```

### React component

Next, we’ll add the **react component**. This displays a "Hello world" heading, and we’ll add some simple functionality to it: every time you click the message, it will update a number in the next line and print a message in the console. This is to show that we’re rendering an *active* react component; we’re not only using TSX/JSX as an XP templating language for static HTML - although sure, you could do that too if you want.

Obviously, the actual updating step is done with vanilla JS instead of actual react, just to keep everything as simple as possible. We’ll look at stateful/dynamic components later.

hello-react.tsx

```javascript
import React from 'react';

function HelloReact() {
  let bottleCount = 99;
  function dropBottle() {
    bottleCount--;
    console.log(bottleCount, 'bottles of beer on the wall.');
    (document.getElementById('counter') as HTMLElement).innerText = bottleCount.toString();
  };

  return (
    <div onClick={dropBottle}>
      <h1>Hello world!</h1>
      <p>Click me: <span id="counter">{bottleCount}</span> bottles of beer on the wall.</p>
    </div>
  );
}

export default () => <HelloReact/>;
```

| ****1** | One thing is mandatory for this to work, shown in the `export default` line: the TSX file **must default-export a function** that ***may* take a props object** and ***must* return a react component**. [More on this later](learn/react4xp-tutorial/5.x/source-file-structure.md).    Apart from that, you can use ordinary TS and import and nest other JS, react components and third-party stuff from *node_modules/* in the regular way. [We’ll also get back to that later](learn/react4xp-tutorial/5.x/imports-and-dependency-chunks.md), including a caveat or two. |
| --- | --- |

> **Note:** By the way, a quick gotcha on using `document` and `window` etc, during serverside vs clientside rendering:

Naturally, a lot of **browser-specific functionality won’t work well during server-side rendering**. React4xp has polyfilled `window` as *empty object*. To prevent weird behavior or errors, browser-specific code should only run in the browser.

In this example, `dropBottle` is the response to a click listener which won’t be triggered to actually *run* on the server (although the asset is compiled and read the asset into memory, but that is safe in itself), so we don’t need any more safeguards here. But if you do, it’s easy enough - for example:

`if (typeof window.navigator !== 'undefined') {
// ...This won't run during SSR...
}`

Of course, this also applies to imported packages / nested components and so on. Importing them is usually safe, but consider wrapping the areas where they’re called/used, like this.

### Page controller

Finally, we’ll add a bare-bone **page controller** that calls the rendering engine:

hello-react.ts:

```javascript
import {getContent} from '/lib/xp/portal';
import {render} from '/lib/enonic/react4xp'; (1)

export function get(request) {               (2)
  const entry = getContent().page;           (3)
  const props = {};
  const react4xpId = 'react4xpApp';

  return render(                             (4)
    entry,
    props,
    request,
    {
      id: react4xpId,                        (5)
      body:                                  (6)
`<!DOCTYPE html><html lang="en">
  <head>
    <meta charset="UTF-8">
  </head>
  <body class="xp-page">
      <div id="${react4xpId}"></div>
  </body>
</html>`,
      // ssr: false                          (7)
    }
  );
}
```

That’s it.

If you’ve used XP before, you’ll probably note that there’s no HTML view file, no `thymeleaf.render`, and so on - in this example, React4xp completely handles the page view. The essential thing here is that at the end of the `get` function, **React4xp in a single *render* call creates a *full* XP response object that makes react work.**

What’s going on in the controller?

| ****1** | The `render` function is imported from the library. |
| --- | --- |
| ****2** | We pick up the `request` data. The render call needs it to know the rendering context. |
| ****3** | We get the XP component data. Used directly in the `render` call, it’s a convenient shortcut for React4xp to "this XP component", for finding the same-name react component in the same folder: *hello-react.tsx*. React4xp has more ways to refer to react components, or *entries* (we’ll get to that, but for all the juicy details: [entries](learn/react4xp-tutorial/5.x/appendix/entries.md) and [jsxPath](learn/react4xp-tutorial/5.x/appendix/jsxpath.md)). |
| ****4** | The juicy bit: **the actual render call**. The rendered response from it can be returned directly from the `get` function, since `render` creates an object with a `body` HTML string and a `pageContributions` attribute with everything needed (more details: [the render API](learn/react4xp-tutorial/5.x/appendix/api.md#react4xp_render)). |
| ****5** | The `id` attribute *"react4xpApp"* is set in the **options** argument of `render`. This is the unique ID we’re giving to the react component, and the HTML id of the target element where react will render the component in the end. Note that the same ID is found in an element in the HTML `body`: |
| ****6** | We’re hardcoding a `body` option, an HTML string as a base for the output, with a *"react4xpApp"* ID element. In many cases you can do without this string but here it’s needed for the output, since react itself doesn’t like to render the tags `<html>`, `<head>`, `<body>` or anything outside of a containing root tag. |
| ****7** | On the server, a false `ssr` flag in the *options* object makes the server skip the HTML rendering (in *this* particular `render` call). |

## Setup and first render

If you’ve added those 3 files, let’s get this rendered! If you’ve used XP and Content Studio before, this is all run-of-the mill:

- If you’re not working in dev mode (`enonic dev`), then compile the project (`enonic project deploy` in a terminal from root) and start the sandbox (`enonic sandbox start`),

- Navigate your browser to `localhost:8080/admin`. Log in to XP and open Content Studio (if you haven’t already, you’ll need to [install Content Studio](https://market.enonic.com/vendors/enonic/content-studio) in XP).

- Create a new Site content and Edit it in a new tab. Add your React4xp app (*"starter-react4xp"*?) on the upper left.

- Select the new *Hello-react* page controller in the preview panel on the right. Store that change (and refresh the page if needed).

You should now see something like this:

- Click *Preview* on the top to open a new tab and view the content outside of Content Studio:

Clicking somewhere on the rendered text in the preview window will trigger the `dropBottle` function from *hello-react.tsx*, and modify the DOM and output a message in the browser console. Look at those bottles go!

## About the rendering

Two things are worth knowing about the rendering, before we move on:

### Content studio should only have static rendering

If you edit some content in *inside XP Content Studio*, you’d notice there was **no bottle-counting**. This is on purpose: react functionality may intervene with the Content Studio editorial workflow, or even disrupt Content Studio itself. Therefore, the `request` argument is used in `render` to handle this automatically: inside Content Studio edit mode, you’ll only see the rendering as a regular static XP preview / placeholder instead of active react.

> **Note:** Later, we’ll look at two other rendering functions: `renderBody` and `renderPageContributions`. These are intended for use cases where it’s good to be more explicit than `render`. For that reason, they *don’t automatically handle this for you*. Usually, you should still keep your components from being client-activated inside Content Studio, but you’ll have to handle it yourself. The [custom flow](learn/react4xp-tutorial/5.x/custom-flow-syntax.md) chapter shows you how.

### First serverside render can be slow

You may also have noticed that it took a little time for the first server-side rendering to be displayed. That’s the **server-side rendering engine warming up**. It reads and caches the basics (notably, some necessary polyfilling, react and react-dom) for performance.

**This delay only happens when your app is restarted**, i.e. you restart XP entirely, or redeploy the app.

## Output

Okay, back to the rendering of the page. Open the **page source** code in the browser. Here’s what `render` created - the response the client receives on the initial page request:

```html
<!DOCTYPE html><html lang="en">
<head>
  <meta charset="UTF-8">
  <script defer src="(...your.app.service) /react4xp/globals.js"></script>                            (1)
  <script defer src="(...your.app.service) /react4xp/runtime.js"></script>                            (2)
  <script defer src="(...your.app.service) /react4xp/site/pages/hello-react/hello-react.js"></script> (3)
  <script defer src="(...your.app.service) /react4xp/client-QZN5J5VC.global.js"></script>             (4)
  <script data-react4xp-app-name="com.enonic.app.samples_react4xp" data-react4xp-ref="react4xpApp" type="application/json">{"command":"hydrate","devMode":false,"hasRegions":0,"isPage":1,"jsxPath":"site/pages/hello-react/hello-react","props":{}}</script> (5)
</head>
<body class="xp-page">

    <div id="react4xpApp">
        <div data-reactroot="">                                                                       (6)
            <h1>Hello world!</h1>
            <p>Click me: <span id="counter">99</span> bottles of beer on the wall. </p>
        </div>
    </div>

    <script defer src="(...your.app.service) /react4xp/executor-BL4RRDZO.js"></script>                (7)
</body>
</html>
```

We can see this whole output is actually the `body` HTML string we passed into the `render` call in the controller - but **a lot has been inserted**. Most importantly, three assets are loaded into the client.

(The asset URLs are shortened for readability, and because some details may vary. At my computer for example, the `(…​your.app.service)` part actually looks like: `/admin/site/preview/default/draft/hello-react/_/service/com.enonic.app.react4xp/`)

| ****1** | The first asset is `globals.<contenthash>.js`: this is react and react-dom bundled together. They are served from XP instead of from a CDN. |
| --- | --- |
| ****2** | The second loaded asset is the runtime chunk. Shared boilerplate code needed to run entries. |
| ****3** | The third asset is the compiled version of *hello-react.tsx*, with the react component and the `dropBottle` routine. During `render`, React4xp used the `component` data to locate this asset *after* compiling. The react component gets an identifier string, `site/pages/hello-react/hello-react`, which is called a *jsxPath* in React4xp. We’ll cover jsxPaths later (full detail reference [here](learn/react4xp-tutorial/5.x/appendix/jsxpath.md)), but for now you just need to know that this identifier is also used when loading this asset into the the browser’s namespace: `React4xp['site/pages/hello-react/hello-react']`. |
| ****4** | The third asset is a client-wrapper. |
| ****5** | Properties and props, that the executor uses when calling the client wrapper. |
| ****6** | The `<div id="react4xpApp">` target container, now filled with a server-side rendering of the react component. At this point it’s only static markup, but it will be activated during step 7 below. |
| ****7** | The script that actually runs `hydrate` with the `props` on the clientside. |

> **Note:** The assets are served by lib-react4xp services. Most of them (*react4xp-client* and the content-hashed assets) are optimized for client-side caching, to minimize repeated requests.

## Client-side rendering

Sometimes you might want or need to skip the server-side rendering of a react component, and relay the react rendering entirely to the browser. This a one-line operation in `render`.

Let’s return to **the controller** and comment in the ssr: false line. Callout :

hello-react.ts:

```javascript
import {getContent} from '/lib/xp/portal';
import {render} from '/lib/enonic/react4xp'; (1)

export function get(request) {               (2)
  const entry = getContent().page;           (3)
  const props = {};
  const react4xpId = 'react4xpApp';

  return render(                             (4)
    entry,
    props,
    request,
    {
      id: react4xpId,                        (5)
      body:                                  (6)
`<!DOCTYPE html><html lang="en">
  <head>
    <meta charset="UTF-8">
  </head>
  <body class="xp-page">
      <div id="${react4xpId}"></div>
  </body>
</html>`,
      // ssr: false                          (7)
    }
  );
}
```

If you compare with [the serverside-rendered example](#hello_output), the `ssr` flag causes the **rendered output** to change slightly, changing the behavior in the browser.

```html
<html>
<head>
  <meta charset="UTF-8">
  <script defer src="(...your.app.service) /react4xp/globals.js"></script> (1)
  <script defer src="(...your.app.service) /react4xp/runtime.js"></script> (1)
  <script defer src="(...your.app.service) /react4xp/site/pages/hello-react/hello-react.js"></script> (1)
  <script defer src="(...your.app.service) /react4xp/client-QZN5J5VC.global.js"></script> (1)
  <script data-react4xp-app-name="com.enonic.app.samples_react4xp" data-react4xp-ref="react4xpApp" type="application/json">{"command":"render","devMode":false,"hasRegions":0,"isPage":1,"jsxPath":"site/pages/hello-react/hello-react","props":{}}</script> (2)
</head>
<body class="xp-page">
    <div id="react4xpApp"></div> (3)
    <script defer src="(...your.app.service) /react4xp/executor-BL4RRDZO.js"></script> (1)
</body>
</html>
```

| ****1** | The compiled assets and their URLs are exactly the same as in the serverside version. |
| --- | --- |
| ****2** | The script that actually runs `render` with the `props` on the clientside. |
| ****3** | As expected, the target container is no longer filled with a serverside-rendered HTML representation of the react component. Instead, the browser fills in the DOM from scratch in step 3 below. |

> **Note:** In Content Studio edit mode, a yellow placeholder is used for client-side rendered components. This is to avoid the components interactive behaviors from interfering with the Content Studio editing workflow.

Apart from these differences behind the scenes, the page will look and behave the same when presented to the user.

Finally, it’s worth mentioning a special case where you might want to *temporarily* clientside-render a component:

> **Tip:** You might get *serverside runtime errors* in the react components that you write. The React4xp rendering engine will dump an error message and some suspected code in the server log - but it’s not always easy to make sense of those.

Often, switching over to *clientside rendering* for that particular react component, will give you a better/sourcemapped error message in the browser console, making your debugging life easier.

Okay, ready for the next example lesson?
