<!-- src:https://developer.enonic.com/docs/react4xp/6.x/app generated:2026-07-30T04:18:15Z format:llm-dense react4xp-6.x -->
#DOC docs/react4xp/6.x/app.md

# App.ts

The app function is responsible for bootstrapping all important elements of React4XP.

## Site mapping

React4XP runs on top of XP’s site engine. By adding a React4XP application to a site, it is injected into request pipeline - where it hijackes the rendering.

This happens because the application declares a "catch all" pattern mapping in `site.xml`.

/src/main/resources/site/site.xml

```XML
<?xml version="1.0" encoding="UTF-8"?>
<site>
  <form/>
  <mappings>
    <mapping controller="/site/app.js" order="10">   (1)
      <pattern invert="true">/r4xp5.*</pattern>
    </mapping>
    <mapping controller="/site/component.js" order="10">   (2)
      <service>component</service>
    </mapping>
  </mappings>
</site>
```

| ****1** | Pattern mapping that catches all requests except the react4xp routes (`invert="true"`) |
| --- | --- |
| ****2** | Enables drag’n drop support in the visual page editor |

React4XP’s own assets and SSR endpoints are served by services that come with the library, so there is nothing to mount - see [Asset serving](docs/react4xp/6.x/library.md#asset-serving).

## App function

The app function is by default located in `/src/main/resources/site/app.ts`. It exports `get`, which XP’s site engine invokes for every request the [site mapping](#site-mapping) catches:

/src/main/resources/site/app.ts

```TypeScript
import {render} from '/lib/enonic/react4xp';
import {getContent} from '/lib/xp/portal';
import {dataFetcher} from '/react4xp/dataFetcher';
import type {Request, Response} from '@enonic-types/core';

export function get(request: Request): Response {
    // the three steps below
}
```

Declare one export per HTTP method the function handles - `get`, `post`, `put`, `delete` - or `all` as a fallback for any method without its own export.

Inside, it follows a simple three-step flow:

- Get component props using the dataFetcher

```TypeScript
const content = getContent();
const data = dataFetcher.process({
  content,
  request,
});
```

- Defines raw HTML with the React4XP app element

```TypeScript
const react4xpId = `react4xp_${content._id}`;
const htmlBody = `<!DOCTYPE html><html lang="en">
	<head>
		<meta charset="UTF-8">
		<title>${content.displayName}</title>
	</head>
	<body>
		<div id="${react4xpId}"></div>
	</body>
</html>`;
```

- Invokes React4XP’s render function

```TypeScript
const output = render(
  'App', (1)
  data, (2)
  request,
  {
    body: htmlBody, (3)
    id: react4xpId, (4)
  }
);

return output;
```

| ****1** | React entry - React4XP will look for a matching component in `/src/main/resources/react4xp/entries` |
| --- | --- |
| ****2** | Content from dataFetcher |
| ****3** | The bootstrap HTML |
| ****4** | Element ID to use for the React app |

The render function kicks off React server-side rendering by invoking the `App` component.

/src/main/resources/react4xp/entries/App.tsx

```React
import '@enonic/react-components/utils/initPublicPath';
import Footer from "/react4xp/components/common/Footer";
import '../components/globalStyles.css'
import type {MetaData} from '@enonic/react-components';
import {BaseComponent} from '@enonic/react-components';
import * as React from 'react';
import {componentRegistry} from '../componentRegistry';
import {AppProps} from '/types/AppProps';

const App: React.FC<AppProps> = ({component, data, common, meta}) => {
    const compMeta: MetaData = meta as MetaData;
    compMeta.componentRegistry = componentRegistry;
    return (
        <>
            <BaseComponent component={component} data={data} common={common} meta={compMeta}/>
            {
                (component.type == "page" || component.type == "contentType") && <Footer logoUrl={common.logoUrl as string}/>
            }
        </>
    );
}

App.displayName = 'App';

export default App;
```

From here on, it is all React.

## Output

If you take a closer look at the page markup produced by the app function, you should see something like this:

> **Tip:** The links have been shortened for better readability

```html
<!DOCTYPE html><html lang="en">
<head>
  <meta charset="UTF-8">
  <script defer src=".../react4xp/globals.js"></script>                            (1)
  <script defer src=".../react4xp/runtime.js"></script>                            (2)
  <script defer src=".../react4xp/App.js"></script>                                (3)
  <script defer src=".../react4xp/client-QZN5J5VC.global.js"></script>             (4)
  <script data-react4xp-app-name="my.first.r4xp" data-react4xp-ref="react4xpApp" type="application/json">{"command":"hydrate","devMode":false,"hasRegions":0,"isPage":1,"jsxPath":"App","props":{}}</script> (5)
</head>
<body class="xp-page">

    <div id="react4xpApp">
        <div data-reactroot="">                                                    (6)
            <h1>Hello React4XP</h1>
        </div>
    </div>

    <script defer src=".../react4xp/executor-BL4RRDZO.js"></script>                (7)
</body>
</html>
```

The result is the HTML string we passed to the `render` request of our app function - but **a lot of stuff** has also been inserted.

| ****1** | `globals.<contenthash>.js` is react and react-dom bundled together. For improved security, they are served from XP instead of a random CDN. |
| --- | --- |
| ****2** | `runtime.js` containst chunked boilerplate code to run entries. |
| ****3** | `App.js` is the compiled version of *App.tsx* |
| ****4** | `client-QZN5J5VC.global.js` is the client-wrapper. |
| ****5** | Properties and props needed for the client-side rendering to work properly (pun intended) |
| ****6** | The `<div id="react4xpApp">` target container, now filled with a server-side rendering of the react component |
| ****7** | Script that triggers `hydration` - see [Hydration](docs/react4xp/6.x/ssr.md#hydration) |

> **Note:** Most of these static assets are content-hashed, and optimized for client-side caching - thus running a CDN in front of the application, in production, will speed up the delivery.
