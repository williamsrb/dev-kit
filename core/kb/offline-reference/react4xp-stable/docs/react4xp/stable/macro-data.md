<!-- src:https://developer.enonic.com/docs/react4xp/stable/macro-data generated:2026-07-30T04:17:59Z format:llm-dense react4xp-7.x -->
#DOC docs/react4xp/stable/macro-data.md

# Passing data to Macros

Macros are Enonic XP components that can be used in RichText. They are defined by an XML descriptor, and they can have a data processor that will run on the server and pass data to the macro. They also have access to all the common and meta data objects, just like any other component.

> **Important:** Macro still needs an XML descriptor! In tutorial we created a sandbox with `app-hmdb` app preinstalled, which had a factbox macro descriptor.

After you’ve gotten that, there are at least 3 ways to pass any arbitrary data to a macro in addition to all the data that is provided by default!

## 1. Macro gets passed a lot of data by default

Factbox component, which is used as a macro in the Person content type’s bio field:

```typescriptjsx
import {MacroComponentParams} from '@enonic/react-components';
import React from 'react';
import styles from './FactBox.module.css';

export const Factbox = (params: MacroComponentParams) => {

    const {
        component,  (1)
        common,     (2)
        data,       (3)
        meta,       (4)
        children,   (5)
    } = params;

    console.info('Factbox', params);

    return (
        <ins className={styles.factBox}>
            <i>💬</i>
            <strong className={styles.header}>{data.header ? data.header as unknown as string : "Fact Box"}</strong>
            <div className={styles.bodyContent}> {children}</div>
        </ins>
    );
};
```

| ****1** | the macro metadata (like name, type, descriptor, etc.) |
| --- | --- |
| ****2** | the result of the common data processor |
| ****3** | the result of this macro data processor (which returns the macro config in our demo) |
| ****4** | general metadata about the execution environment (like content, request, runMode, etc.) |
| ****5** | parsed contents of the macro tag, which can be rendered as a part of the macro component’s output |

Here is the example of real data:

```json
{
    "loading": "lazy",
    "component": {
        "type": "macro",
        "name": "factbox",
        "descriptor": "factbox",
        "ref": "1"
    },
    "common": {
        "logoUrl": "/admin/site/preview/hmdb/draft/hmdb/_/service/com.enonic.app.react4xpdemo/asset/1772616603914/react4xp.svg"
    },
    "meta": {
        "type": "com.enonic.app.hmdb:person",
        "id": "a8b374a2-c532-45eb-9aa1-73d1c37cd681",
        "path": "/hmdb/persons/lea-seydoux",
        "mode": "preview",
        "componentRegistry": {...}
    },
    "data": {
        "body": "\n<ul>\n\t<li><strong>French actress:</strong> Léa Seydoux is a prominent French actress known for her roles in both French and international films.</li>\n\t<li><strong>Cannes Film Festival winner:</strong> She won the prestigious Palme d'Or at the Cannes Film Festival in 2013 for her role in <em>Blue Is the Warmest Colour</em>.</li>\n\t<li><strong>James Bond franchise:</strong> Seydoux portrayed Dr. Madeleine Swann in the James Bond films <em>Spectre</em> (2015) and <em>No Time to Die</em> (2021).</li>\n\t<li><strong>Family ties to cinema:</strong> She comes from a family with strong ties to the French film industry; her grandfather, Jérôme Seydoux, is the chairman of Pathé, a major French film production company.</li>\n\t<li><strong>Diverse filmography:</strong> Her acting range spans from independent arthouse films like <em>The Lobster</em> (2015) to blockbuster hits like <em>Mission: Impossible – Ghost Protocol</em> (2011).</li>\n</ul>\n"
    },
    "children": [...]
}
```

## 2. Adding data to a macro data processor

One can add any additional data to macro’s `data` field by simply returning it from the data processor. Data processor is a function that runs on the server before rendering the macro, and it can fetch data from XP (content, assets, etc.) and return it to be passed to the macro component as the `data` property.

Adding displayName to FactboxProcessor:

```typescript
import type {ComponentProcessor, MacroProcessorParams} from '@enonic-types/lib-react4xp/DataFetcher';
import {Content} from '/lib/xp/content';

export const factboxProcessor: ComponentProcessor<'com.enonic.app.hmdb:factbox', MacroProcessorParams> = (params) => {
    const macro = params.macro;

    const {
        dataFetcher,    (1)
        request,        (2)
        macro,          (3)
        runMode,        (4)
        content,        (5)
    } = params;

    const displayName = (content as Content).displayName;

    return {
        ...macro.config['factbox'],
        displayName,
    };
};
```

| ****1** | the data fetcher instance, where all the data processors are registered |
| --- | --- |
| ****2** | the request object, which can be used to get information about the current request (like params, cookies, etc.) |
| ****3** | the macro metadata (like name, type, descriptor, etc.) |
| ****4** | the current XP run mode ("development" or "production") |
| ****5** | the content for which the macro is rendered (if any) |

## 3. Adding data to a common processor

One can add data to **EVERY** component on the page including macros, by adding it to the common processor.

> **Tip:** You don’t want to add too much data here, since it will be passed to every component on the page, but it’s a good place for small amounts of data that is needed globally, like site name, logo, etc.

Addding displayName to CommonProcessor:

```typescript
import {assetUrl} from '/lib/enonic/asset';
import type {ComponentProcessor} from '@enonic-types/lib-react4xp/DataFetcher';
import {Content} from '/lib/xp/content';

export const commonProcessor: ComponentProcessor<'com.enonic.app.hmdb:main'> = (_props) => {

    const logoUrl = assetUrl({path: 'react4xp.svg'});

    const {
        dataFetcher,
        request,
        component,      (1)
        runMode,
        content,
    } = _props;

    const displayName = (content as Content).displayName;

    return {
        logoUrl,
        displayName
    };
};
```

| ****1** | Notice that common processor receives component metadata in the field named component! That is because it is a common processor and is not specific to macros. |
| --- | --- |

## 4. Augment RichText with additional data

One can augment `RichText` with any data that will be passed to Images, Links, and Macros used inside it.

Define an interface with the necessary fields, and pass it as a generic type to `RichText`:

```typescriptjsx
interface AdditionalProps extends Record<string, unknown> {
    displayName: string;
}

<RichText<AdditionalProps>
    displayName={displayName}
    data={bio}
    meta={meta}
    common={common}
    component={component}
    loading="lazy"
/>
```

After that, every Image, Macro, and Link used inside `RichText` will receive it too!

## 5. Consuming data in a macro component

After we’ve added `displayName` to the macro data processor, common processor, and passed it to `RichText`, we can access it in the **Factbox** component.

Accessing displayName in Factbox component:

```typescriptjsx
import {MacroComponentParams} from '@enonic/react-components';
import React from 'react';
import styles from './FactBox.module.css';
import {AdditionalProps} from '/react4xp/components/content/Person';

export const Factbox = (params: MacroComponentParams<AdditionalProps>) => {

    const {
        data,
        common,
        component,
        meta,
        children,
        displayName
    } = params;

    console.info(`Data value: ${data.displayName}`);
    console.info(`Common value: ${common.displayName}`)
    console.info(`RichText value: ${displayName}`);

    return (
        <ins className={styles.factBox}>
            <i>💬</i>
            <strong className={styles.header}>{data.header ? data.header as unknown as string : "Fact Box"}</strong>
            <div className={styles.bodyContent}> {children}</div>
        </ins>
    );
};
```
