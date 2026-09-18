<!-- src:https://developer.enonic.com/learn/react4xp-tutorial/5.x/editorial-data-and-props generated:2026-07-30T04:16:10Z format:llm-dense react4xp-5.x -->
#DOC learn/react4xp-tutorial/5.x/editorial-data-and-props.md

# Editorial data and props

## Lesson overview

Here we’ll spice up our react component a little bit, by using `props` to insert editorial data from XP into the react component.

We’ll modify a copy of the same files you created [previously](learn/react4xp-tutorial/5.x/hello-react.md#code):

Files involved:

```files
site/pages/hello-react2/
  hello-react2.xml
  hello-react2.ts
  hello-react2.tsx
```

## Code

Let’s change the files some more so we can use Content Studio to input some data into the react rendering.

### Page definition

We start with some standard XP procedure: defining the data in the page definition XML file. This file is the same as in [example 1](learn/react4xp-tutorial/5.x/hello-react.md#page_definition), but we’re adding a few [input fields](https://developer.enonic.com/docs/xp/stable/cms/schemas/input-types) under ``: `greeting`, `greetee`, `counted` and `startCount` are the basis for the initial props of the react component:

hello-react.xml:

```xml
<page>
  <display-name>Hello React 2</display-name>
  <description>Super simple example 2</description>
  <form>
        <input type="TextLine" name="greeting">
            <label>What's the greeting?</label>
            <default>Hello</default>
            <occurrences minimum="1" maximum="1"/>
        </input>

        <input type="TextLine" name="greetee">
            <label>Who shall we greet?</label>
            <default>world</default>
            <occurrences minimum="1" maximum="1"/>
        </input>

        <input type="TextLine" name="things">
            <label>What are the things on the wall?</label>
            <default>bottles of beer</default>
            <occurrences minimum="1" maximum="1"/>
        </input>

        <input type="Long" name="startCount">
            <label>How many of them are there?</label>
            <default>99</default>
            <occurrences minimum="1" maximum="1"/>
        </input>
    </form>
  <regions />
</page>
```

### Type declarations

Declare which inputs come from the XML, and what props we want to pass on into the react component.

hello-react2.d.ts

```typescript
export type HelloPageConfig = {
  greeting: string
  greetee: string
  things: string
  startCount: number
}

export type HelloProps = {
  message: HelloPageConfig['greeting']
  messageTarget: HelloPageConfig['greetee']
  droppableThing: HelloPageConfig['things']
  initialCount: HelloPageConfig['startCount']
}

// Adding the page configuration to the global XP type map.
declare global {
  interface XpPageMap {
    'com.enonic.app.samples-react4xp:hello-react2': HelloPageConfig
  }
}
```

### Page controller

Next, we’ll modify [the controller](learn/react4xp-tutorial/5.x/hello-react.md#page_controller) to fetch the data we defined in XML, then use a `props` object to inject the data into the react component:

hello-react.ts:

```typescript
// Importing type utils from the XP core type library.
import type {
  Content,
  PageComponent
} from '@enonic-types/core';

// Importing types for the page configuration and the component props.
import type {HelloProps} from './hello-react2.d';

import {getContent} from '/lib/xp/portal';
import {render} from '/lib/enonic/react4xp';

export function get(request) {
  // Getting the page content object
  const content = getContent<
    // Using the imported type utils and the global XP type map,
    // so `the page content object` will be properly typed.
    Content<
      {},
      'portal:page',
      PageComponent<'com.enonic.app.samples-react4xp:hello-react2'>
    >
  >();

  // Deconstructing the page configuration
  // If your IDE supports it, you can hover over the variable names and see their types
  const {
    greeting,
    greetee,
    things,
    startCount
  } = content.page.config;

  // Renaming the page configuration variables into the component props, just for fun.
  // You don't have to pass along all the page configuration variables to the component.
  // And you can ofcourse add other props, that doesn't come from the page configuration.
  const props: HelloProps = {
    message: greeting,
    messageTarget: greetee,
    droppableThing: things,
    initialCount: startCount
  };

  const react4xpId = 'react4xpApp';

  return render(
    content.page, // Using the page content object as the component entry
    props,
    request,
    {
      id: react4xpId,
      body:
`<!DOCTYPE html><html lang="en">
  <head>
    <meta charset="UTF-8">
  </head>
  <body class="xp-page">
      <div id="${react4xpId}"></div>
  </body>
</html>`
    }
  );
}
```

| ****1** | Fetching the content data defined in the XML (and in the next line, we’re unpacking it into `pageConfig` while choosing that missing data should just display emptiness, not throw an error). |
| --- | --- |
| ****2** | The `props` object is just any standard JS object. So the data can of course come from anywhere you want and take any shape - with one exception: `props` needs to be **serializable**, so functions can’t be passed here! |
| ****3** | Connecting the field names in `pageConfig` from *hello-react.xml* to the prop names that *hello-react.jsx* needs. |
| ****4** | See how this makes the first two arguments of `React4xp.render` analogous to XP’s `thymeleaf.render` template engine? The first argument, `entry`, is just a reference to what should be rendered (*react component* ~ *template*), and the second one is a collection of data injected into it (*props* ~ *model*). |
| ****5** | To keep things simpler and clearer, just remove the `ssr = false` flag from the previous example. |

### React component

Finally, we’ll modify [the react component](learn/react4xp-tutorial/5.x/hello-react.md#react_component) so that it displays data from a `props` object, instead of hardcoding everything.

hello-react2.tsx

```typescript
import type {HelloProps} from './hello-react2.d';

import React from 'react';

function HelloReact({
  // Decontruct the props, do they can be used below:
  message,
  messageTarget,
  droppableThing,
  initialCount
}: HelloProps) {

  function makeThingDropper(droppableProp: string, initialCountProp: number) {
    let currentCount = initialCountProp;
    return () => {
      currentCount--;
      console.log(currentCount.toString(), droppableProp, 'on the wall.');

      // React4xp no longer polyfill's document, so an if block is needed to avoid SSR errors.
      if (document) {
        (document.getElementById('counter') as HTMLElement).innerText = currentCount.toString();
      }

    };
  }

  const dropThing = makeThingDropper(droppableThing, initialCount);

  return (
    <div onClick={dropThing}>
      <h1>{message} {messageTarget}!</h1>
      <p>Click me: <span id="counter">{initialCount}</span> {droppableThing} on the wall.</p>
    </div>
  );
}

// Pass on the props to the component:
export default (props: HelloProps) => <HelloReact {...props}/>;
```

> **Tip:** `props` are of course the standard react way to do this. It all is. As long as a *props ⇒ reactComponent* function is default-exported, React4xp accepts standard valid TSX/JSX/TS/JS/ES6.

Although, if you think that the *makeObjectDropper* closure thing is a strange way to do something react itself could do better…​ sure. Just trying to stay focused on one thing at a time.

There it is, now let’s take a look!

## Setup and rendering

Compile the project, enter Content Studio (see the first two steps in [the previous setup](learn/react4xp-tutorial/5.x/hello-react.md#first_setup_render)), and edit the content you created (double-click it to open a new tab).

You should still see it in the preview panel on the right (although, since you probably created the content without any data created along with it, it might not display much of the text. We’ll fix that):

Now, when you click the preview panel, the page-config editing panel should open on the right, with the data fields containing the default text we defined. Once you click Apply/save, the preview panel to the left should update.

So now, it looks the same as before, but with editorial data instead of hardcoded text. Boring, and too similar to the previous example; just repeating "Hello World" might cause a little confusion. **Try adding your own data in the fields**, for example changing *"world"* into *"[Bruce](https://montypython.fandom.com/wiki/Bruces_sketch)"* etc, to keep it clear.

**Apply/save** your new props, and the output should change again. But since we’re still in Content Studio, it’s just a static serverside-rendered update. To see the final rendering with your new data, all active, click *Preview* on the top to open the page in a fresh tab:

## Output

So did anything change in the rendered response, compared to [the first serverside-rendered example](learn/react4xp-tutorial/5.x/hello-react.md#hello_output)? Not all that much, actually. Depending on what data you inserted and the resulting `props`, your page source should look something like this:

```html
<html>
<head>
  <meta charset="UTF-8">
  <script defer src="(...your.app.service) /react4xp/globals.4427e5cbb5e9bb528fc6.js"></script> (1)
  <script defer src="(...your.app.service) /react4xp/runtime.706073d99846f9d14ca4.js"></script> (1)
  <script defer src="(...your.app.service) /react4xp/site/pages/hello-react2/hello-react2.53c91627acf165d77409.js"></script> (1)
  <script defer src="(...your.app.service) /react4xp/client-QZN5J5VC.global.js"></script> (1)
  <script data-react4xp-app-name="com.enonic.app.samples_react4xp" data-react4xp-ref="react4xpApp" type="application/json">{"command":"hydrate","devMode":false,"hasRegions":0,"isPage":1,"jsxPath":"site/pages/hello-react2/hello-react2","props":{"message":"G'day","messageTarget":"Dave","droppableThing":"dudas","initialCount":50}}</script> (2)
</head>
<body class="xp-page">

    (3)
    <div id="react4xpApp">
        <div data-reactroot="">
            <h1>G'day<!-- --> <!-- -->Bruce<!-- --> !</h1>
            <p>Click me: <span id="counter">42</span> <!-- -->tubes<!-- --> on the wall.</p>
        </div>
    </div>

  <script defer src="(...your.app.service) /react4xp/executor-BL4RRDZO.js"></script> (1)
</body>
</html>
```

| ****1** | There’s still no change in the asset URLs, but since we changed *hello-react.jsx*, the content of *hello-react.js* has of course been recompiled. |
| --- | --- |
| ****2** | The script that actually runs `hydrate` with the `props` on the clientside. |
| ****3** | Since we removed the `ssr = false` flag again, the target container `react4xpApp` comes filled from the server. But now with a rendering with *your* texts from `props` already inserted. |

## Further reading

Now might be a good time to take a closer look at [the API overview of the .render call](learn/react4xp-tutorial/5.x/appendix/api.md#react4xp_render) from the ES6 controller in the example above.

Either way, you should be ready for the last of the three basic lesson chapters.
