<!-- src:https://developer.enonic.com/docs/react4xp/6.x/upgrade generated:2026-07-30T04:18:15Z format:llm-dense react4xp-6.x -->
#DOC docs/react4xp/6.x/upgrade.md

# Recommended upgrade

This page covers upgrading an application from **React4XP 5 to 6**. It is the recommended route: it migrates pages and layouts to React and gives you the full React4XP 6 feature set. If you would rather upgrade the build and plumbing while keeping the version 5 rendering model, follow the [legacy mode upgrade](docs/react4xp/6.x/legacy-upgrade.md) instead.

> **Note:** To go from React4XP 6 to 7, switch to the **7.x** documentation - that upgrade also moves the application from Enonic XP 7 to XP 8.

## Step by step

This describes upgrading to the full feature set of react4xp 6 including migrating pages and layouts to react.

- Create an app using the [starter](docs/react4xp/6.x/starter.md) and give it a new name.

- [Migrate](#migrating-parts) each react component to the new app.

- Migrate your [page](#migrate-page) and [layout](#migrate-layout) to react components

- [Deploy](docs/react4xp/6.x/legacy-upgrade.md#build-deploy) the application on your existing site.

You will now have one application with your schemas, and one containing your frontend. If you prefer having a single application, follow these steps:

- Move the cms schemas and other files you want to keep to the new application.

- Rename it to the same name as your old application.

- Make a production build and [Deploy](docs/react4xp/6.x/legacy-upgrade.md#build-deploy) it.

- The old application can now be discarded.

## Migrating parts

Now let’s go a little bit deeper and use the example component as a part along with our new components. To do this we need to do the following:

- Make an xml file for it so XP knows that it exists, here we can also give it a good description.

src/main/resources/site/parts/example/example.xml

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<part>
  <display-name>Example part</display-name>
  <description>Example part description</description>
</part>
```

- Move the example component to the `parts/example` folder and update as follows.

src/main/resources/react4xp/components/parts/example/example.tsx

```TypeScript
import Hello from '/lib/myReactComponents/Hello';
import dayjs from 'dayjs';
import React, {useState} from 'react';
import type {ComponentProps, PartData} from '@enonic/react-components';

export const Example = (props: ComponentProps<PartData>) => {

    const [count, setCount] = useState(0);

    return <>
            <Hello/>
            <div>Part: {dayjs().format()}</div>
            <button onClick={() => setCount(prev => prev + 1)}>{count}</button>
    </>;
};

export default Example;
```

Notice how the Example component receives `ComponentProps` type props. This is going to be true for any other component as well, except that `PartData`, specifying type of the component field, will be `LayoutData` for layouts, or `PageData` for pages:

```TypeScript
interface ComponentProps<T extends ComponentData = ComponentData> {
    meta: MetaData;                         (1)
    component: T;                           (2)
    data?: Record<string, unknown>;         (3)
    common?: Record<string, unknown>;       (4)
}
```

| ****1** | Runtime metadata, such as the current content path, id and type as well as request mode. |
| --- | --- |
| ****2** | Enonic XP component data that contains type, descriptor and some extra data based on the type (i.e. regions for layouts and pages). |
| ****3** | Component data fetched by the associated data processor, if any. |
| ****4** | Common data fetched by the common processor, if any.        Now, instead of fetching in get(), create a processor that returns its data and React4xp will forward it to your view along with some additional data like meta and component.    src/main/resources/react4xp/components/parts/example/exampleProcessor.ts    `import type {ComponentProcessor} from '@enonic-types/lib-react4xp/DataFetcher';  export const exampleProcessor: ComponentProcessor<'com.enonic.app.react4xp:example'> = (props) => {  return {}; };`          Add it to the componentRegistry and dataFetcher with the same descriptor as in previous task.    src/main/resources/react4xp/componentRegistry.ts    `import {ComponentRegistry} from '@enonic/react-components'; import Example from './components/parts/example/example';  ...  export const componentRegistry = new ComponentRegistry();  ...  componentRegistry.addPart('com.enonic.app.react4xp:example', {View: Example});`        src/main/resources/react4xp/dataFetcher.ts    `import {DataFetcher} from '/lib/enonic/react4xp'; import {exampleProcessor} from './components/parts/example/exampleProcessor';  ...  export const dataFetcher = new DataFetcher();  ...  dataFetcher.addPart('com.enonic.app.react4xp:example', {processor: exampleProcessor});` |

## Pages

Your current page part might look something like this:

src/main/resources/site/pages/default/default.tsx

```typeScript
import {Regions} from '@enonic/react-components';
import dayjs from 'dayjs';
import React from 'react';
import type {PageComponentProps} from './default.d';

function Page(props: PageComponentProps) {
    return (
        <div className="default-page">
            <Regions {...props} />
            <div>Page: {dayjs().format()}</div>
        </div>
    );
}

export default (props: PageComponentProps) => <Page {...props}/>;
```

with a controller like this:

src/main/resources/site/pages/default/default.ts

```TypeScript
import {render} from '/lib/enonic/react4xp';
import {getContent} from '/lib/xp/portal';
import type {Enonic} from '@enonic/js-utils/types/Request';
import type {PageComponentProps} from './default.d';

export function get(request: Enonic.Xp.Http.Request) {
    const content = getContent();

    const {page: entry} = content;

    const react4xpId = `react4xp_${content._id}`;

    const props: PageComponentProps = {
        regionsData: content.page.regions,
        names: "main",
        tag: "main",
    };

    const htmlBody = `<!DOCTYPE html><html lang="en">
	<head>
		<meta charset="UTF-8">
		<title>${content.displayName}</title>
	</head>
	<body class="xp-page">
		<div id="${react4xpId}"></div>
	</body>
</html>`;

    const output = render(
        entry,
        props,
        request,
        {
            body: htmlBody,
            hydrate: false,
            id: react4xpId,
        }
    );

    return output;
}
```

And an xml like this:

src/main/resources/site/pages/default/default.xml

```xml
<page>
  <display-name>Default page</display-name>
  <description>R4xp5 react-rendered page controller</description>
  <form/>
  <regions>
    <region name="main"/>
  </regions>
</page>
```

This is how we migrate it to a react4xp v6 component:

First let’s handle the controller which becomes a processor, the most important prop to pass from the processor used to be the regionsData. We can still get regions from component and return it, but this is not necessary anymore!

> **Important:** Component gets passed to the view automatically now, so you don’t have to define a processor function if it’s only regions you want to access.

src/main/resources/react4xp/components/page/PageProcessor.ts

```TypeScript
import {PageComponent} from "@enonic-types/core";
import type {ComponentProcessor} from '@enonic-types/lib-react4xp/DataFetcher';

export const pageProcessor: ComponentProcessor<'com.enonic.app.react4xp:Page'> = (props) => {
    const {regions} = props.component as PageComponent;

    return {
        regions,
        name: "main"
    };
};
```

Next we need to change out the part `default.tsx` with a component `Page.tsx`, which is very similar except that we pass `component` to the `Regions` react component, because it contains regions now.

src/main/resources/react4xp/components/page/Page.tsx

```TypeScript
import {Regions, type ComponentProps, type PageData} from '@enonic/react-components';
import dayjs from 'dayjs';
import styles from './Page.module.css';

export const Page = ({data, common, meta, component}: ComponentProps<PageData>) => {

    return (
        <div className={styles[data.name as string]}>
            <Regions common={common} meta={meta} component={component}/>
            <div>Page: {dayjs().format()}</div>
        </div>
    );
};
```

In this example there is also a css module that is used to style the page.

src/main/resources/react4xp/components/page/Page.module.css

```css
.main {
  padding-bottom: 0;
  margin-bottom: 0;
  display: flow-root;
}
```

For XP to see it we need to keep the xml file, but we will change the name to `Page.xml` and add a description to it. This way we can call on it using a descriptor in the component registry and data fetcher.

src/main/resources/site/pages/Page/Page.xml

```xml
<page>
  <display-name>Upgraded page</display-name>
  <description>Upgraded page component</description>
  <form/>
  <regions>
    <region name="main"/>
  </regions>
</page>
```

Let’s add it to componentRegistry and dataFetcher, this is done in the same way as we did with the part.

src/main/resources/react4xp/componentRegistry.ts

```TypeScript
import {ComponentRegistry} from '@enonic/react-components';
import {Page} from './components/page/Page';

...

export const componentRegistry = new ComponentRegistry();

...

componentRegistry.addPage('com.enonic.app.react4xp:Page', {View: Page});
```

src/main/resources/react4xp/dataFetcher.ts

```TypeScript
import {DataFetcher} from '/lib/enonic/react4xp';
import {pageProcessor} from './components/page/PageProcessor';

...

export const dataFetcher = new DataFetcher();

...

dataFetcher.addPage('com.enonic.app.react4xp:Page', {processor: pageProcessor});
```

Now we have a fully functional page component that is using the new regions and component registry.

## Layouts

Lastly we need to migrate the layout, this is done in a similar way to the page.

Your current layout part might look something like this:

src/main/resources/site/layouts/twoColumns/twoColumns.tsx

```typeScript
import {Regions} from '@enonic/react-components';
import dayjs from 'dayjs';
import React from 'react';

export default (props: Parameters<typeof Regions>[0]) => {
    return <div style={{
        columnGap: '1em',
        display: 'grid',
        gridTemplateColumns: '1fr 1fr'
    }}>
        <Regions {...props}/>
        <div>{dayjs().format()}</div>
    </div>;
};
```

with a controller like this:

src/main/resources/site/layouts/twoColumns/twoColumns.ts

```TypeScript
import {render} from '/lib/enonic/react4xp';
import {getComponent} from '/lib/xp/portal';
import type {Enonic} from '@enonic/js-utils/types/Request';
import type {Regions} from '@enonic/react-components';

export function get(request: Enonic.Xp.Http.Request) {

    const component = getComponent();

    const props: Parameters<typeof Regions>[0] = {
        classes: true,
        names: ['left', 'right'],
        regionsData: component.regions,
        tags: 'section',
    };

    return render(
        component,
        props,
        request,
        {
            hydrate: false,
        }
    );
}
```

And an xml like this:

src/main/resources/site/layouts/twoColumns/twoColumns.xml

```xml
<layout>
  <display-name>Two columns</display-name>
  <description>Two columns react-rendered layout controller</description>
  <form/>
  <regions>
    <region name="left"/>
    <region name="right"/>
  </regions>
</layout>
```

Similar to the page, we need to implement a processor, and a component.

src/main/resources/react4xp/components/layouts/TwoColumnProcessor.ts

```TypeScript
import {LayoutComponent} from '@enonic-types/core';
import type {ComponentProcessor} from '@enonic-types/lib-react4xp/DataFetcher';

export const layoutProcessor: ComponentProcessor<'com.enonic.app.react4xp:TwoColumns'> = ({component}) => {
    const {regions} = component as LayoutComponent;

    return {
        regions,
        tags: 'section'
    };
};
```

The Layout component is depending on regions like the page, but let’s use `Region` built-in component this time to render every region manually. We need to pass list of components as data to each `Region` component:

src/main/resources/react4xp/components/layouts/TwoColumn.tsx

```TypeScript
import {type ComponentProps, type LayoutData, Region} from '@enonic/react-components';
import dayjs from 'dayjs';
import styles from './TwoColumn.module.css';

export const TwoColumnLayout = ({component, meta, data}: ComponentProps<LayoutData>) => {

    return <>
        <div className={styles.row + ' ' + styles[data.tags as string]}>
            <Region data={component.regions.left.components} meta={meta} name="left"/>
            <Region data={component.regions.right.components} meta={meta} name="right"/>
        </div>
        <div>Layout:{dayjs().format()}</div>
    </>;
};
```

> **Note:** Notice how we used data fetcher result stored in `data` field to access the `tags` property.

src/main/resources/components/layouts/twoColumn.css

```css
.section {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.section :global(> div) {
  flex: 1;
  min-width: 200px;
}

.section :global(.xp-page-editor-region-placeholder) {
  margin-bottom: 0;
}
```

We need to add the layout to the component registry and data fetcher, this is done in the same way as we did with the part and page.

src/main/resources/react4xp/componentRegistry.ts

```TypeScript
import {ComponentRegistry} from '@enonic/react-components';
import {TwoColumnLayout} from './components/layouts/TwoColumn';

...

export const componentRegistry = new ComponentRegistry();

...

componentRegistry.addLayout('com.enonic.app.react4xp:TwoColumns', {View: TwoColumnLayout});
```

src/main/resources/react4xp/dataFetcher.ts

```TypeScript
import {DataFetcher} from '/lib/enonic/react4xp';
import {layoutProcessor} from './components/layouts/TwoColumnProcessor';

...

export const dataFetcher = new DataFetcher();

...

dataFetcher.addLayout('com.enonic.app.react4xp:TwoColumns', {processor: layoutProcessor});
```

And finally we need to update the xml file to match the descriptor, this is done in the same way as the page.

src/main/resources/site/layouts/TwoColumn/TwoColumn.xml

```xml
<layout>
  <display-name>Two columns</display-name>
  <description>Upgraded Two columns controller</description>
  <form/>
  <regions>
    <region name="left"/>
    <region name="right"/>
  </regions>
</layout>
```

Now we have a fully functional layout component that is using the new regions and component registry.

And just like that we have not only upgraded the old component, but also made it compatible with the new ones!
