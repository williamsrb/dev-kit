<!-- src:https://developer.enonic.com/learn/react4xp-tutorial/5.x/custom-flow-syntax generated:2026-07-30T04:16:10Z format:llm-dense react4xp-5.x -->
#DOC learn/react4xp-tutorial/5.x/custom-flow-syntax.md

# Custom flow syntax

## Lesson overview

In this example things get a bit more complex. We’ll make another Part, and re-use the Page controller, Template and Content type we made [previously](learn/react4xp-tutorial/5.x/pages-parts-and-regions.md#template_with_react_page_controller).

- However, we won’t use the `render` shorthand function from before. Instead, we’ll look at a more **explicit React4xp syntax**:

It constructs one or more **data-holding React4xp objects**. This gives you better control and opportunities for logic steps when you handle your [entry](learn/react4xp-tutorial/5.x/appendix/entries.md); you can manipulate the object(s) or extract data from them *before* rendering.

- Here, each entry is rendered in **two separate methods**: `renderBody` and `renderPageContributions` (full details: [React4xp data object API](learn/react4xp-tutorial/5.x/appendix/api.md#react4xp_object))

- You can pretty easily render **multiple entries** from the same controller, by chaining together their rendering.

> **Note:** Rendering multiple entries like we do here will create multiple [independent react apps](learn/react4xp-tutorial/5.x/appendix/entries.md#assets_and_apps) in the browser.

- We will also use a **thymeleaf** template for one of the entries - and take advantage of the React4xp data object to send its ID to the thymeleaf model - just to demonstrate a way to combine react and thymeleaf rendering.

- In addition to chain-rendering more than one entry, we will use [jsxPaths](learn/react4xp-tutorial/5.x/appendix/jsxpath.md) to point to entries in a different location. Actually, let’s just recycle the same entries we used before:

### Files involved

```files
site/parts/
    custom-flow/            (1)
        custom-flow.xml
        custom-flow.ts
        custom-flow-view.html

    color/
        color.tsx           (2)

site/pages/
    hello-react/
        hello-react.tsx     (3)
```

| ****1** | The new Part we’re making, *custom-flow*. |
| --- | --- |
| ****2** | The already existing entry [*color.tsx*](learn/react4xp-tutorial/5.x/pages-parts-and-regions.md#color_jsx): a different folder from our *custom-flow* Part, and different name. |
| ****3** | We’re also reusing another existing entry [*hello-react.tsx*](learn/react4xp-tutorial/5.x/editorial-data-and-props.md#hello_react_jsx_modified) (with props, not the first hardcoded one), located under *site/**pages**/hello-react/*. So even though what we’re making here is a Part, an entry from a Page, or anywhere, is fine: when using jsxPaths, all entries are equal. |

## Code

### Part definition

The Part definition again defines some base data for us to play with. This is exactly the same definitions as before, just merged together into one Part: the greeting and bottle/thing counter from *hello-react.xml*, and the color from *color.xml*.

custom-flow.xml:

```xml
<part>
    <display-name>CustomFlow example</display-name>
    <description>Single part with multiple entries</description>
    <form>
        <input name="color" type="TextLine">
            <label>What's the color of the thing?</label>
            <occurrences minimum="1" maximum="1"/>
            <default>red</default>
        </input>

        <input type="TextLine" name="greeting">
            <label>What's the greeting?</label>
            <default>Hello</default>
            <occurrences minimum="1" maximum="1"/>
        </input>

        <input type="TextLine" name="greetee">
            <label>Who shall we greet?</label>
            <occurrences minimum="1" maximum="1"/>
            <default>world</default>
        </input>

        <input type="TextLine" name="things">
            <label>What are the things on the wall?</label>
            <occurrences minimum="1" maximum="1"/>
            <default>bottles of beer</default>
        </input>

        <input type="Long" name="startCount">
            <label>How many of them are there?</label>
            <occurrences minimum="1" maximum="1"/>
            <default>99</default>
        </input>
    </form>
</part>
```

### Thymeleaf view

Next, we’re adding a regular **thymeleaf view template file**.

This forms the initial HTML base, with `color` and `targetId` inserted by thymeleaf. This is actually not different from before: [previously](learn/react4xp-tutorial/5.x/hello-react.md#first_helloreact_jsx) we’ve used a hardcoded string as the HTML base that react is rendered into. Now we’re just letting thymeleaf make it. Same thing, the base HTML string can come from anywhere.

The controller will render *two* entries into this base HTML. To be clear: even though we’re using two entries, this is still *one single XP Part*. The first entry is *color.jsx* which will be inserted into the element `

`. The second one, *hello-react.jsx* will also be rendered and inserted into this base HTML, but it will have a React4xp-ID that does not match any element ID here. This will cause React4xp to revert to the default behavior: generate a new container `
` and insert it right at the end of the root element: after `
` here:

custom-flow-view.html:

```html
<div class="custom-flow-view">
  <section class="color-section">
      <h2 data-th-text="|Ain't nothing but a ${color} thing|"></h2>
      <p>Here it comes:</p>
      <div data-th-id="${targetId}"></div>
  </section>
</div>
```

### Part controller

**The controller** now has more complexity than before, so here’s an overview:

- Each entry is used to set up a data-holding reactxp object, in steps *before the rendering* is called. In these steps, data (options and props) can be both injected into the React4xp objects, and extracted from them.

- The output of one rendering is used as the base for the next; chaining them together and gradually building up a final multi-entry output.

- HTML body and page contributions are rendered/chained separately from each other: there’s one flow that repeats `renderBody` across multiple entries and builds one HTML body for all the entries. And another chain that repeates `renderPageContributions`.

- Just for demonstration, one entry will be client-side rendered and the other one server-side rendered. Both entries include a `request` option to easily automate correct behavior for inside-Content-Studio context. This is most important for the clientRendered one.

> **Note:** When client-side rendering an entry, it’s recommended to add a `request` option (for both of the entry’s rendering calls - see below).

One reason to also add `request` for SSR however, is that in cases of react component errors, React4xp will visualize the entry with an error placeholder. And `request` adds some clarity: allows it to add the actual error messages (except in live view mode - where the messages are always held back).

custom-flow.ts

```typescript
import type {PartComponent} from '@enonic-types/core';

import {getComponent} from '/lib/xp/portal';
import {React4xp} from '/lib/enonic/react4xp';
// @ts-expect-error No types for /lib/thymeleaf yet.
import {render as renderThymeleaf} from '/lib/thymeleaf';

declare global {
  interface XpPartMap {
    ['com.enonic.app.samples-react4xp:custom-flow']: {
      color: string
      greeting: string
      greetee: string
      things: string
      startCount: number
    }
  }
}

const VIEW = resolve('custom-flow-view.html');

export function get(request) {
    // Fetching data from the part config:
    const component = getComponent<PartComponent<'com.enonic.app.samples-react4xp:custom-flow'>>();
    const {
        color,
        greeting,
        greetee,
        things,
        startCount
    } = component.config;

    // Setting up the data-holding object for hello-react2.tsx:
    const helloObj = new React4xp(`site/pages/hello-react2/hello-react2`);     (1)
    helloObj.setProps({                                                      (2)
            message: greeting,
            messageTarget: greetee,
            droppableThing: things,
            initialCount: startCount
        })

    // Setting up colorObj, the data-holding object for color.tsx:
    const colorObj = new React4xp(`site/parts/color/color`);
    colorObj                                                                 (3)
        .setProps({ color })
        .setId("myColorThing")                                               (4)
        .uniqueId()                                                          (5)

    // Using thymeleaf to render container HTML,
    // inserting the colorObj's ID into the target container where colorObj will be rendered:
    const thymeleafModel = {
        color: colorObj.props.color,
        targetId: colorObj.react4xpId
    }
    const colorSectionContainer = renderThymeleaf(VIEW, thymeleafModel);    (6)

    // Render the color.tsx entry into the same-ID target container in the container HTML:
    const colorBody = colorObj.renderBody({
        body: colorSectionContainer,                                         (7)
        request
    });
    // Rendering the activating page contributions of color.tsx.
    const colorPageContributions = colorObj.renderPageContributions({
        pageContributions: {                                                 (8)
            bodyEnd: `<script>console.log('Created: ${colorObj.props.color} thing.');</script>`
        },
        request                                                              (9)
    });

    // Rendering helloObj's entry into colorBody (which is basically custom-flow-view.html with color.tsx added),
    // using client-side rendering only outside of Content Studio:
    const finalBody = helloObj.renderBody({
        body: colorBody,                                                     (10)
        ssr: false,                                                          (11)
        request
    });

    // Adding helloObj's page contributions to the previously rendered page contributions,
    // duplicating ssr between renderPageContributions and renderBody (pair-wise for each entry).
    const finalPageContributions = helloObj.renderPageContributions({
        pageContributions: colorPageContributions,                           (12)
        // hydrate: false, // Turn off hydration?
        ssr: false,
        request
    });

    // Finally, returning the response object in the standard XP-controller way:
    return {
        body: finalBody,
        pageContributions: finalPageContributions
    }
}
```

| ****1** | Constructing the data-holding React4xp object `helloObj` from the same *hello-react.jsx* entry we made [before](learn/react4xp-tutorial/5.x/editorial-data-and-props.md#hello_react_jsx_modified). The constructor takes one argument, which is mandatory: an [entry reference](learn/react4xp-tutorial/5.x/appendix/entries.md). This can be an XP `component` object like before, OR like we’re doing here: a [jsxPath](learn/react4xp-tutorial/5.x/appendix/jsxpath.md).    This entry reference is used the same way as the first argument, *entry*, in [`React.render`](learn/react4xp-tutorial/5.x/appendix/api.md#react4xp_render) (so just to be clear: a jsxPath reference string like this also works fine there). |
| --- | --- |
| ****2** | `setProps` modifies `helloObj`, to add some `props`. This of course corresponds to the second argument, `props`, in `React4xp.render`. |
| ****3** | After creating a React4xp object `colorObj` for the second entry, *color.jsx*, we’re modifying that too, starting with adding props.    Note the **builder-like pattern** here: each of the setter methods (`setProps`, `setId` and `uniqueId`) returns the React4xp object itself. This allows you to run them directly after each other like this, so this example is just a shorter way of writing:        colorObj.setProps({ color: partConfig.color }); colorObj.setId("myColorThing"); colorObj.uniqueId();`. |
| ****4** | `setId` sets the ID of the React4xp object and the target element that the rendering will look for in the HTML. If an ID has previously been set for the React4xp object, `setId` will overwrite it. |
| ****5** | `uniqueId` makes sure the React4xp object has a globally unique ID. It can work in two ways. If an ID has not been set previously, a simple random ID is generated. If an ID *has* been set, like here in step 4, the random number is appended after the existing ID. So the order between `setId` and `uniqueId` matters.    The ID ends up as `myColorThing-<someRandomNumber>`. This gives us something recognizable in the output but still ensures that the element ID is not repeated in cases where this part is used more than once on a page. If `setId` had been run *after* `uniqueId` however, `setId` would just overwrite the previous unique ID with the supplied string - and risk repeating it. |
| ****6** | Now there’s a random component in the ID string of the React4xp object, and we want that ID to match a specific element in the HTML. So we read the ID out from `colorObj.react4xpId` and inject it into the thymeleaf template as `targetId`. |
| ****7** | We render `colorObj` into an HTML string, based on the HTML output of the thymeleaf rendering…​ |
| ****8** | …​and render the page contributions for activating it in the client. We’ll even add a small extra script just to demonstrate that extra pageContributions can be added in `renderPageContributions` as well, by passing them through as before. Now we have both the HTML body and page contributions from the first entry, *color.jsx*. |
| ****9** | A best practice is to add `request` to options in *both* `renderBody` and `renderPageContributions`. This is the easiest way to automatically [take care of a couple of corner cases](learn/react4xp-tutorial/5.x/appendix/api.md#react4xp_object_request). Using it makes the output clearer in cases of errors. |
| ****10** | We’re going to add a second react entry to this Part’s controller. This demonstrates how to **chain the HTML rendering**: we’re including `colorBody` as the `body` option. If added to `renderBody`, the HTML in `body` (which is the output from the previous entry, *color.jsx*) will receive the output from the rendering of the this entry (*hello-react.jsx*).    Where in `colorBody` is that HTML added? ID and target element is handled the same way as in `React4xp.render`: we created `helloObj` without running `.setId`, so no ID is set, and therefore `helloObj` will get a random ID. Since that ID doesn’t match any ID in the base HTML (`colorBody`), the rendering will just create a target container element (with a matching ID) inside the root element of `colorBody`, after all other content. Now that there’s a matching-ID element, the new HTML is rendered into that.      In sum: *"Render hello-react.jsx into the HTML from color.jsx, right at the end."* |
| ****11** | This entry will be clientside rendered (even though *color.jsx* is serverside rendered - this is not a problem for the chain), but we’re adding `request` to let React4xp [keep it serverside-rendered and static](learn/react4xp-tutorial/5.x/appendix/api.md#react4xp_object_request) inside Content Studio.   @@BLOCK2@@ |
| ****12** | **Chaining the page contributions:** the activating page contributions for `helloObj` are rendered, and by adding to the previous `colorPageContributions` as a `pageContributions` option, thay’re passed through the rendering and added. |

> **Note:** **The rendering mode (client- or serverside) must match** between `renderBody` and `.renderPageContributions` for an entry!

This is on an entry-by-entry basis: there’s no problem mixing multiple entries in the same controller like in this example, where one entry is serverside and the other is clientside rendered - as long as each entry’s `renderBody` and `renderPageContributions` have a matching `ssr`.

(The same goes for `request`)

And we’re done, our new *custom-flow* Part is now ready.

## Setup

All of this amounted to a new Part, *custom-flow*. It can be added to any Region, so just follow [the same setup steps](learn/react4xp-tutorial/5.x/pages-parts-and-regions.md#adding_parts_to_new_content) in Content Studio to add and see it.

Again, if you add more than one *custom-flow* Part to a Region, you’ll see that they are independent both in behavior and output; separated by their unique ID.

## Further reading

The API behind the custom flow syntax: [React4xp data objects](learn/react4xp-tutorial/5.x/appendix/api.md#react4xp_object).
