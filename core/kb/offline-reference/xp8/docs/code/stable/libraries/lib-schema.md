<!-- src:https://developer.enonic.com/docs/code/stable/libraries/lib-schema generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries/lib-schema.md

# Dynamic schema library

API for fetching and manipulating dynamic schemas.

> **Warning:** In XP 8 all `resource` strings passed to and returned from this library are **YAML**. XML resources are no longer accepted — `createSchema`, `createComponent`, `createStyles`, `updateSite`, and the `update*` counterparts all parse YAML only. Examples below use the XP 8 `kind:` form.

> **Tip:** Functions of this library require the Schema Admin role. It means that user role in the current context may lack sufficient permissions, for example when executed from inside a service - in this case you must explicitly execute the function in the [context](docs/code/stable/libraries/lib-context.md#runcontext) of `system.schema.admin` role.

## Usage

```groovy
dependencies {
  include xplibs.schema
}
```

```typescript
import schemaLib from '/lib/xp/schema';
```

## Functions

### getSchema

Fetches a schema from an application.

Parameters

`getSchema()` takes a single `GetDynamicContentSchemaParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| name | string | Schema name. |
| type | string | Schema type (`CONTENT_TYPE`, `FORM_FRAGMENT`, or `MIXIN`). |

Returns

**object** : ([`Schema`](#schema)) Property object of the fetched schema — a [`ContentTypeSchema`](#content-type), [`FormFragmentSchema`](#form-fragment), or [`MixinSchema`](#mixin) depending on `type` — or `null` if the schema does not exist.

Example

Fetches a content type schema:

```typescript
import {getSchema} from '/lib/xp/schema';

const result = getSchema({
    name: 'myapp:mytype',
    type: 'CONTENT_TYPE'

});
```

Return value:

```typescript
const expected = {
  name: "myapp:mytype",
  title: "Tag",
  titleI18nKey: "",
  createdTime: "2021-09-25T10:00:00Z",
  creator: "user:system:anonymous",
  modifiedTime: "2021-09-25T10:00:00Z",
  "resource" : <!-- resource string value -->,
  type: "CONTENT_TYPE",
  icon: {
    data: {},
    mimeType: "image/png",
    modifiedTime: "2016-01-01T12:00:00Z"
  },
  form: [
    {
      formItemType: "Input",
      name: "tag",
      label: "Tag, unlimited occurrences",
      maximize: true,
      inputType: "Tag",
      occurrences: {
        maximum: 0,
        minimum: 0
      },
      config: {}
    }
  ],
  config: {}
};
```

### listSchemas

Fetches schemas of a particular type from an application.

Parameters

`listSchemas()` takes a single `ListDynamicSchemasParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| application | string | Application key. |
| type | string | Schema type (`CONTENT_TYPE`, `FORM_FRAGMENT`, or `MIXIN`). |

Returns

**object[]** : ([`Schema[]`](#schema)) Array of the fetched schemas — [`ContentTypeSchema`](#content-type), [`FormFragmentSchema`](#form-fragment), or [`MixinSchema`](#mixin) objects depending on `type`.

Example

Fetches application’s content type schemas:

```typescript
import {listSchemas} from '/lib/xp/schema';

const result = listSchemas({
    application: 'myapp',
    type: 'CONTENT_TYPE'

});
```

Return value:

```typescript
const expected = {
    name: 'myapp:type1',
    title: 'My type display name',
    description: 'My type description',
    modifiedTime: '2010-01-01T10:00:00Z',
    resource: 'kind: "ContentType"\ntitle: "My type display name"\nform: []\n',
    type: 'CONTENT_TYPE',
    form: [
        {
            formItemType: 'Layout',
            name: 'myLayout',
            label: 'My layout',
            items: [
                {
                    formItemType: 'ItemSet',
                    name: 'mySet',
                    occurrences: {
                        maximum: 1,
                        minimum: 1
                    },
                    items: [
                        {
                            formItemType: 'Input',
                            name: 'myInput',
                            label: 'Input',
                            maximize: true,
                            inputType: 'TextLine',
                            occurrences: {
                                maximum: 1,
                                minimum: 0
                            },
                            config: {}
                        }
                    ]
                }
            ]
        }
    ],
    config: {}
},
{
    name: 'myapp:type2',
    title: 'My type display name 2',
    description: 'My type description 2',
    modifiedTime: '2012-01-01T10:00:00Z',
    resource: 'kind: "ContentType"\ntitle: "My type display name 2"\nform: []\n',
    type: 'CONTENT_TYPE',
    form: [],
    config: {}
};
```

### createSchema

Creates a dynamic schema in a virtual application.

Parameters

`createSchema()` takes a single `CreateDynamicContentSchemaParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| name | string | Dynamic schema name. |
| type | string | Dynamic schema type (`CONTENT_TYPE`, `FORM_FRAGMENT`, or `MIXIN`). |
| resource | string | Dynamic schema resource value. |

Returns

**object** : ([`Schema`](#schema)) The created schema — a [`ContentTypeSchema`](#content-type), [`FormFragmentSchema`](#form-fragment), or [`MixinSchema`](#mixin) depending on `type`.

Example

Creates a content type schema:

```typescript
import {createSchema} from '/lib/xp/schema';

const resource = `kind: "ContentType"
title: "Tag"
superType: "base:structured"
form:
- type: "Tag"
  name: "tag"
  label: "Tag, unlimited occurrences"
  occurrences:
    min: 0
    max: 0
`;

const result = createSchema({
    name: 'myapp:mytype',
    type: 'CONTENT_TYPE',
    resource
});
```

Return value:

```typescript
const expected = {
  name: "myapp:mytype",
  title: "Tag",
  titleI18nKey: "",
  createdTime: "2021-09-25T10:00:00Z",
  creator: "user:system:anonymous",
  modifiedTime: "2021-09-25T10:00:00Z",
  "resource" : <!-- resource string value -->,
  type: "CONTENT_TYPE",
  icon: {
    data: {},
    mimeType: "image/png",
    modifiedTime: "2016-01-01T12:00:00Z"
  },
  form: [
    {
      formItemType: "Input",
      name: "tag",
      label: "Tag, unlimited occurrences",
      maximize: true,
      inputType: "Tag",
      occurrences: {
        maximum: 0,
        minimum: 0
      },
      config: {}
    }
  ],
  config: {}
};
```

### updateSchema

Updates a dynamic schema in a virtual application.

Parameters

`updateSchema()` takes a single `UpdateDynamicContentSchemaParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| name | string | Dynamic schema name. |
| type | string | Dynamic schema type (`CONTENT_TYPE`, `FORM_FRAGMENT`, or `MIXIN`). |
| resource | string | Dynamic schema resource value. |

Returns

**object** : ([`Schema`](#schema)) The modified schema — a [`ContentTypeSchema`](#content-type), [`FormFragmentSchema`](#form-fragment), or [`MixinSchema`](#mixin) depending on `type`.

Example

Updates a mixin schema:

```typescript
import {updateSchema} from '/lib/xp/schema';

const resource = `kind: "Mixin"
title: "Virtual Mixin"
description: "Mixin description"
form:
- type: "TextLine"
  name: "text2"
  label: "Text 2"
- include: "myapplication:inline"
`;

const result = updateSchema({
    name: 'myapp:mytype',
    type: 'MIXIN',
    resource
});
```

Return value:

```typescript
const expected = {
    name: 'myapp:mytype',
    title: 'Virtual Mixin',
    titleI18nKey: '',
    description: 'Mixin description',
    descriptionI18nKey: '',
    createdTime: '2021-09-25T10:00:00Z',
    modifiedTime: '2021-09-25T10:00:00Z',
    resource: <!-- resource string value -->,
    type: 'MIXIN',
    form: [
        {
            formItemType: 'Input',
            name: 'text2',
            label: 'Text 2',
            maximize: true,
            inputType: 'TextLine',
            occurrences: {
                maximum: 1,
                minimum: 0
            },
            config: {}
        },
        {
            formItemType: 'InlineMixin',
            name: 'myapplication:inline'
        }
    ]
};
```

### deleteSchema

Removes a schema from a virtual application.

Parameters

`deleteSchema()` takes a single `DeleteDynamicContentSchemaParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| name | string | Dynamic schema name. |
| type | string | Dynamic schema type (`CONTENT_TYPE`, `FORM_FRAGMENT`, or `MIXIN`). |

Returns

**boolean** : `true` if deletion was successful.

Example

Deletes a mixin schema:

```typescript
import {deleteSchema} from '/lib/xp/schema';

const result = deleteSchema({
    name: 'myapp:mytype',
    type: 'MIXIN'
});

if (result) {
    log.info('Deleted mixin: [myapp:mytype]');
} else {
    log.info('Mixin deletion failed: [myapp:mytype]');
}
```

### getComponent

Fetches a component from an application.

Parameters

`getComponent()` takes a single `GetDynamicComponentParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Component key. |
| type | string | Component type (`PAGE`, `PART` or `LAYOUT`). |

Returns

**object** : ([`ComponentDescriptor`](#component)) The fetched component — a [`PageDescriptor`](#page), [`PartDescriptor`](#part), or [`LayoutDescriptor`](#layout) depending on `type`.

Example

Fetches a page component:

```typescript
import {getComponent} from '/lib/xp/schema';

const result = getComponent({
    key: 'myapp:mypage',
    type: 'PAGE'

});
```

Return value:

```typescript
const expected = {
    key: 'myapp:mypage',
    title: 'News page',
    description: 'My news page',
    descriptionI18nKey: 'key.description',
    componentPath: 'myapp:/cms/pages/mypage',
    modifiedTime: '2021-02-25T10:44:33.170079900Z',
    resource: 'kind: "Page"\ntitle: "News page"\nform: []\nregions:\n- "region-one"\n',
    type: 'PAGE',
    form: [
        {
            formItemType: 'Input',
            name: 'width',
            label: 'width',
            maximize: true,
            inputType: 'Double',
            occurrences: {
                maximum: 1,
                minimum: 0
            },
            config: {}
        }
    ],
    config: {},
    regions: [
        'region-one'
    ]
};
```

### listComponents

Fetches components of a particular type from an application.

Parameters

`listComponents()` takes a single `ListDynamicComponentsParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| application | string | Application key. |
| type | string | Component type (`PAGE`, `PART` or `LAYOUT`). |

Returns

**object[]** : ([`ComponentDescriptor[]`](#component)) Array of the fetched components — [`PageDescriptor`](#page), [`PartDescriptor`](#part), or [`LayoutDescriptor`](#layout) objects depending on `type`.

Example

Fetches application’s part components:

```typescript
import {listComponents} from '/lib/xp/schema';

const result = listComponents({
    application: 'myapp',
    type: 'PART'

});
```

Return value:

```typescript
const expected = [
    {
        key: 'myapp:part1',
        title: 'News part',
        description: 'My news part',
        descriptionI18nKey: 'key.description',
        componentPath: 'myapp:/cms/parts/part1',
        modifiedTime: '2021-02-25T10:44:33.170079900Z',
        resource: 'kind: "Part"\ntitle: "News part"\nform: []\n',
        type: 'PART',
        form: [
            {
                formItemType: 'Input',
                name: 'width',
                label: 'width',
                maximize: true,
                inputType: 'Double',
                occurrences: {
                    maximum: 1,
                    minimum: 0
                },
                config: {}
            }
        ],
        config: {}
    },
    {
        key: 'myapp:part2',
        title: 'Other part',
        componentPath: 'myapp:/cms/parts/part2',
        modifiedTime: '2022-02-25T10:44:33.170079900Z',
        resource: 'kind: "Part"\ntitle: "Other part"\nform: []\n',
        type: 'PART',
        form: [],
        config: {}
    }
];
```

### createComponent

Creates a dynamic component in a virtual application.

Parameters

`createComponent()` takes a single `CreateDynamicComponentParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Dynamic component key. |
| type | string | Dynamic component type (`PAGE`, `PART` or `LAYOUT`). |
| resource | string | Dynamic component resource value. |

Returns

**object** : ([`ComponentDescriptor`](#component)) The created component — a [`PageDescriptor`](#page), [`PartDescriptor`](#part), or [`LayoutDescriptor`](#layout) depending on `type`.

Example

Creates a part type component:

```typescript
import {createComponent} from '/lib/xp/schema';

const resource = `kind: "Part"
title: "Virtual Part"
description: "My Part Description"
form:
- type: "Double"
  name: "width"
  label: "Column width"
  occurrences:
    min: 0
    max: 1
- include: "myapplication:link-urls"
`;

const result = createComponent({
    key: 'myapp:mypart',
    type: 'PART',
    resource
});
```

Return value:

```typescript
const expected = {
    key: 'myapp:mypart',
    title: 'Virtual Part',
    titleI18nKey: 'key.display-name',
    description: 'My Part Description',
    descriptionI18nKey: 'key.description',
    componentPath: 'myapp:/cms/parts/mypart',
    modifiedTime: '2021-09-25T10:00:00Z',
    resource: <!-- resource string value -->,
    type: 'PART',
    form: [
        {
            formItemType: 'Input',
            name: 'width',
            label: 'Column width',
            helpText: 'key.help-text',
            maximize: true,
            inputType: 'Double',
            occurrences: {
                maximum: 1,
                minimum: 0
            },
            config: {}
        },
        {
            formItemType: 'InlineMixin',
            name: 'myapplication:link-urls'
        }
    ],

    config: {
        input: [{
            value: '', '@name': 'width', '@type': 'Double'
        }]
    }
};
```

### updateComponent

Updates a dynamic component in a virtual application.

Parameters

`updateComponent()` takes a single `UpdateDynamicComponentParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Dynamic component key. |
| type | string | Dynamic component type (`PAGE`, `PART` or `LAYOUT`). |
| resource | string | Dynamic component resource value. |

Returns

**object** : ([`ComponentDescriptor`](#component)) The modified component — a [`PageDescriptor`](#page), [`PartDescriptor`](#part), or [`LayoutDescriptor`](#layout) depending on `type`.

Example

Updates a layout component:

```typescript
import {updateComponent} from '/lib/xp/schema';

const resource = `kind: "Layout"
title: "Virtual Layout"
description: "My Layout Description"
form:
- type: "Double"
  name: "pause"
  label: "Pause parameter"
  occurrences:
    min: 0
    max: 1
- type: "ItemSet"
  name: "myFormItemSet"
  label: "My form item set"
  occurrences:
    min: 0
    max: 1
  items:
  - type: "TextLine"
    name: "myTextLine"
    label: "My text line"
    occurrences:
      min: 1
      max: 1
  - type: "TextLine"
    name: "myCustomInput"
    label: "My custom input"
    occurrences:
      min: 0
      max: 1
regions:
- "header"
- "main"
- "footer"
`;

const result = updateComponent({
    key: 'myapp:mylayout',
    type: 'LAYOUT',
    resource
});
```

Return value:

```typescript
const expected = {
    key: 'myapp:mylayout',
    title: 'Virtual Layout',
    titleI18nKey: 'key.display-name',
    description: 'My Layout Description',
    descriptionI18nKey: 'key.description',
    componentPath: 'myapp:/cms/layouts/mylayout',
    modifiedTime: '2021-09-25T10:00:00Z',
    resource: <!-- resource string value -->,
    type: 'LAYOUT',
    form: [
        {
            formItemType: 'Input',
            name: 'pause',
            label: 'Pause parameter',
            helpText: 'key1.help-text',
            maximize: true,
            inputType: 'Double',
            occurrences: {
                maximum: 1,
                minimum: 0
            },
            config: {}
        },
        {
            formItemType: 'ItemSet',
            name: 'myFormItemSet',
            label: 'My form item set',
            occurrences: {
                maximum: 1,
                minimum: 0
            },
            items: [
                {
                    formItemType: 'Input',
                    name: 'myTextLine',
                    label: 'My text line',
                    maximize: true,
                    inputType: 'TextLine',
                    occurrences: {
                        maximum: 1,
                        minimum: 1
                    },
                    config: {}
                },
                {
                    formItemType: 'Input',
                    name: 'myCustomInput',
                    label: 'My custom input',
                    maximize: true,
                    inputType: 'TextLine',
                    occurrences: {
                        maximum: 1,
                        minimum: 0
                    },
                    config: {}
                }
            ]
        }
    ],
    config: {},
    regions: [
        'header',
        'main',
        'footer'
    ]
};
```

### deleteComponent

Deletes a dynamic component from a virtual application.

Parameters

`deleteComponent()` takes a single `DeleteDynamicComponentParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Dynamic component key. |
| type | string | Dynamic component type (`PAGE`, `PART` or `LAYOUT`). |

Returns

**boolean** : `true` if deletion was successful.

Example

Removes a layout component:

```typescript
import {deleteComponent} from '/lib/xp/schema';

const result = deleteComponent({
    key: 'myapp:mylayout',
    type: 'LAYOUT'
});

if (result) {
    log.info('Deleted layout: [myapp:mylayout]');
} else {
    log.info('Layout deletion failed: [myapp:mylayout]');
}
```

### getStyles

Fetches styles (f.ex. image styles) from an application.

Parameters

`getStyles()` takes a single `GetDynamicStylesParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| application | string | Application key. |

Returns

**object** : ([`StyleDescriptor`](#styles)) Property object of the fetched styles, or `null` if the application has no styles descriptor.

Example

Fetch application styles:

```typescript
import {getStyles} from '/lib/xp/schema';

const result = getStyles({
    application: 'myapp'
});
```

Return value:

```typescript
const expected = {
    application: 'myapp',
    modifiedTime: '2021-02-25T10:44:33.170079900Z',
    resource: 'kind: "Style"\nstyles: []\n',
    elements: [
        {
            label: 'Style display name',
            name: 'mystyle'
        }
    ]
};
```

### createStyles

Creates styles in a virtual application.

Parameters

`createStyles()` takes a single `CreateDynamicStylesParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| application | string | Virtual application key. |
| resource | string | Dynamic styles resource value. |

Returns

**object** : ([`StyleDescriptor`](#styles)) Property object of the created dynamic styles.

Example

Creates application styles:

```typescript
import {createStyles} from '/lib/xp/schema';

const resource = `kind: "Style"
styles:
- name: "warning"
  type: "Style"
  label: "Warning"
  editor:
    css: |
      .warning { /* CSS selectors */ }
- name: "editor-width-auto"
  type: "Image"
  label: "Override \${width}"
  editor:
    css: |
      .editor-width-auto { /* CSS selectors */ }
- name: "editor-style-cinema"
  type: "Image"
  label: "Cinema"
  aspectRatio: "21:9"
  filter: "pixelate(10)"
  editor:
    css: |
      .editor-style-cinema { /* CSS selectors */ }
`;

const result = createStyles({
    application: 'myapp',
    resource
});
```

Return value:

```typescript
const expected = {
    application: 'myapp',
    modifiedTime: '2021-09-25T10:00:00Z',
    resource: <!-- resource string value -->,
    elements: [
        {
            label: 'Warning',
            name: 'warning'
        },
        {
            label: 'Override ${width}',
            name: 'editor-width-auto'
        },
        {
            label: 'Cinema',
            name: 'editor-style-cinema'
        }
    ]
};
```

### updateStyles

Updates styles in a virtual application.

Parameters

`updateStyles()` takes a single `UpdateDynamicStylesParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| application | string | Dynamic application key. |
| resource | string | Dynamic styles resource value. |

Returns

**object** : ([`StyleDescriptor`](#styles)) Property object with the modified styles.

Example

Updates application styles:

```typescript
import {updateStyles} from '/lib/xp/schema';

const resource = `kind: "Style"
styles:
- name: "warning"
  type: "Style"
  label: "Warning"
  editor:
    css: |
      .warning { /* CSS selectors */ }
- name: "editor-width-auto"
  type: "Image"
  label: "Override \${width}"
  editor:
    css: |
      .editor-width-auto { /* CSS selectors */ }
- name: "editor-style-cinema"
  type: "Image"
  label: "Cinema"
  aspectRatio: "21:9"
  filter: "pixelate(10)"
  editor:
    css: |
      .editor-style-cinema { /* CSS selectors */ }
`;

const result = updateStyles({
    application: 'myapp',
    resource
});
```

Return value:

```typescript
const expected = {
    application: 'myapp',
    modifiedTime: '2021-09-25T10:00:00Z',
    resource: <!-- resource string value -->,
    elements: [
        {
            label: 'Warning',
            name: 'warning'
        },
        {
            label: 'Override ${width}',
            name: 'editor-width-auto'
        },
        {
            label: 'Cinema',
            name: 'editor-style-cinema'
        }
    ]
};
```

### deleteStyles

Deletes styles from a virtual application.

Parameters

`deleteStyles()` takes a single `DeleteDynamicStylesParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| application | string | Dynamic application key. |

Returns

**boolean** : `true` if deletion was successful.

Example

Removes an application styles:

```typescript
import {deleteStyles} from '/lib/xp/schema';

const result = deleteStyles({
    application: 'myapp'
});

if (result) {
    log.info('Styles were deleted: [myapp]');
} else {
    log.info('Styles deletion failed: [myapp]');
}
```

### getSite

Fetches a site descriptor from an application.

Parameters

`getSite()` takes a single `GetDynamicSiteParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| application | string | Application key. |

Returns

**object** : ([`SiteDescriptor`](#site)) Property object of the fetched site descriptor, or `null` if the application has no CMS descriptor.

Example

Fetch application site descriptor:

```typescript
import {getSite} from '/lib/xp/schema';

const result = getSite({
    application: 'myapp'
});
```

Return value:

```typescript
const expected = {
    application: 'myapp',
    resource: <!-- resource string value -->,
    modifiedTime: '2021-02-25T10:44:33.170079900Z',
    form: [
        {
            formItemType: 'Input',
            name: 'input',
            label: 'Input',
            maximize: true,
            inputType: 'Double',
            occurrences: {
                maximum: 1,
                minimum: 0
            },
            config: {}
        }
    ],
    mixinMappings: [
        {
            name: 'myapplication:my',
            optional: false
        }
    ]
};
```

### updateSite

Updates dynamic site descriptor in a virtual application.

Parameters

`updateSite()` takes a single `UpdateDynamicSiteParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| application | string | Dynamic application key. |
| resource | string | Dynamic site descriptor resource value. |

Returns

**object** : ([`SiteDescriptor`](#site)) Property object of the modified site descriptor.

Example

Updates the application’s CMS descriptor (form and mixin references):

```typescript
import {updateSite} from '/lib/xp/schema';

const resource = `kind: "CMS"
mixins:
- name: "myapp1:menu-item"
  optional: false
- name: "myapp2:my-meta-mixin"
  optional: false
form:
- type: "TextLine"
  name: "some-name"
  label: "Textline"
  occurrences:
    min: 0
    max: 1
`;

const result = updateSite({
    application: 'myapp',
    resource
});
```

> **Note:** Despite its name, `updateSite` writes the **CMS descriptor** (`cms/cms.yaml`) which holds the site form and mixin references. The site descriptor (`cms/site.yaml`) — which carries `processors`, `mappings`, and `apis` — is not modifiable through this library; manage it as part of the application source.

Return value:

```typescript
const expected = {
    application: 'myapp',
    modifiedTime: '2021-09-25T10:00:00Z',
    resource: <!-- resource string value -->,
    form: [
        {
            formItemType: 'Input',
            name: 'some-name',
            label: 'Textline',
            customText: '',
            maximize: true,
            inputType: 'TextLine',
            occurrences: {
                maximum: 1,
                minimum: 0
            },
            config: {}
        }
    ],
    mixinMappings: [
        {
            name: 'myapp1:menu-item',
            optional: false,
            allowContentTypes: ''
        },
        {
            name: 'myapp2:my-meta-mixin',
            optional: false,
            allowContentTypes: ''
        }
    ]
};
```

## Type Definitions

### Schema

Base shape shared by [`ContentTypeSchema`](#content-type), [`FormFragmentSchema`](#form-fragment) and [`MixinSchema`](#mixin). `getSchema`, `createSchema`, `updateSchema` and `listSchemas` always return one of those concrete types depending on the `type` argument.

Type

**object**

Properties

| Name | Type | Description |
| --- | --- | --- |
| name | string | Schema name. |
| title | string | Title. |
| titleI18nKey | string | Title i18n key. |
| description | string | Schema description. |
| descriptionI18nKey | string | Schema description i18n key. |
| createdTime | string | Created zulu time. |
| creator | [UserKey](docs/code/stable/fundamentals/types.md#user-key) | Principal that created the schema. |
| modifiedTime | string | Modified zulu time. |
| modifier | [UserKey](docs/code/stable/fundamentals/types.md#user-key) | Principal that last modified the schema. |
| resource | string | Schema resource value (YAML). |
| type | string | Schema type (`CONTENT_TYPE`, `FORM_FRAGMENT`, `MIXIN`). |
| icon | [Icon](#icon) | **Optional.** Schema icon. |

### ContentTypeSchema

Extends [`Schema`](#schema). Returned by the schema functions when `type` is `CONTENT_TYPE`. This is the dynamic content-type schema descriptor — distinct from `lib-content’s `ContentType` (the `getType` return value).

Type

**object**

Properties

| Name | Type | Description |
| --- | --- | --- |
| form | [FormItem](docs/code/stable/fundamentals/types.md#form-item)[] | Content type form. |
| config | object | Content type config. Map of config values keyed by name. |
| superType | string | **Optional.** Key of the content type this one inherits from. |
| abstract | boolean | **Optional.** `true` if the content type cannot be instantiated directly. |
| final | boolean | **Optional.** `true` if the content type cannot be extended. |
| allowChildContent | boolean | **Optional.** `true` if content of this type may have children. |
| allowChildContentType | string[] | **Optional.** Patterns of content types allowed as children. |
| displayNamePlaceholder | string | **Optional.** Placeholder shown in the display name field. |
| displayNamePlaceholderI18nKey | string | **Optional.** i18n key for the display name placeholder. |
| displayNameExpression | string | **Optional.** Expression used to derive the display name. |
| displayNameListExpression | string | **Optional.** Expression used to derive the display name in list views. |
| mixinNames | string[] | **Optional.** Names of mixins applied to this content type. |

### FormFragmentSchema

Extends [`Schema`](#schema). Returned by the schema functions when `type` is `FORM_FRAGMENT`.

Type

**object**

Properties

| Name | Type | Description |
| --- | --- | --- |
| form | [FormItem](docs/code/stable/fundamentals/types.md#form-item)[] | Form fragment form. |

### MixinSchema

Extends [`Schema`](#schema). Returned by the schema functions when `type` is `MIXIN`. Each mixin attaches optional metadata to a content item.

Type

**object**

Properties

| Name | Type | Description |
| --- | --- | --- |
| form | [FormItem](docs/code/stable/fundamentals/types.md#form-item)[] | Mixin form. |
| config | object | Mixin config. Map of config values keyed by name. |

### ComponentDescriptor

Base shape shared by [`PageDescriptor`](#page), [`PartDescriptor`](#part) and [`LayoutDescriptor`](#layout). `getComponent`, `createComponent`, `updateComponent` and `listComponents` always return one of those concrete types depending on the `type` argument.

Type

**object**

Properties

| Name | Type | Description |
| --- | --- | --- |
| key | string | Component key. |
| title | string | Title. |
| titleI18nKey | string | Title i18n key. |
| description | string | Component description. |
| descriptionI18nKey | string | Component description i18n key. |
| componentPath | string | Component path. |
| modifiedTime | string | Modified zulu time. |
| resource | string | Component resource value (YAML). |
| type | string | Component type (`PAGE`, `PART`, `LAYOUT`). |
| form | [FormItem](docs/code/stable/fundamentals/types.md#form-item)[] | Component form. |
| config | object | Component config. Map of config values keyed by name. |

### PageDescriptor

Extends [`ComponentDescriptor`](#component). Returned when `type` is `PAGE`.

Type

**object**

Properties

| Name | Type | Description |
| --- | --- | --- |
| regions | string[] | **Optional.** Page regions. |

### LayoutDescriptor

Extends [`ComponentDescriptor`](#component). Returned when `type` is `LAYOUT`.

Type

**object**

Properties

| Name | Type | Description |
| --- | --- | --- |
| regions | string[] | **Optional.** Layout regions. |

### PartDescriptor

Extends [`ComponentDescriptor`](#component). Returned when `type` is `PART`.

Type

**object**

Properties

| Name | Type | Description |
| --- | --- | --- |
| icon | [Icon](#icon) | **Optional.** Part icon. |

### SiteDescriptor

Type

**object**

Properties

| Name | Type | Description |
| --- | --- | --- |
| application | string | Application key. |
| resource | string | Site CMS descriptor YAML resource value. |
| modifiedTime | string | Site zulu modified time. |
| form | [FormItem](docs/code/stable/fundamentals/types.md#form-item)[] | Site descriptor form. |
| mixinMappings | [MixinMapping[]](#mixin-mapping) | **Optional.** Mixin mappings. |

### StyleDescriptor

Type

**object**

Properties

| Name | Type | Description |
| --- | --- | --- |
| application | string | Application key. |
| modifiedTime | string | Styles zulu modified time. |
| resource | string | Styles YAML resource value. |
| elements | [StyleElement[]](#element) | Style elements. |

### MixinMapping

Type

**object**

Properties

| Name | Type | Description |
| --- | --- | --- |
| name | string | Mixin name. |
| optional | boolean | `true` if optional. |
| allowContentTypes | string | Allowed content type pattern. |

### StyleElement

Type

**object**

Properties

| Name | Type | Description |
| --- | --- | --- |
| name | string | Style element name. |
| label | string | Style element label. May be `null`. |
| type | string | Style element type (e.g. `Style`, `Image`). |
| aspectRatio | string | **Optional.** Aspect ratio applied by an image style (e.g. `21:9`). |
| filter | string | **Optional.** Image filter expression applied by the style. |
| editor | [EditorConfig](#editor-config) | **Optional.** Editor configuration, including the CSS applied in the editor. |

### EditorConfig

Type

**object**

Properties

| Name | Type | Description |
| --- | --- | --- |
| css | string | **Optional.** CSS applied by the style in the editor. |

### Icon

Type

**object**

Properties

| Name | Type | Description |
| --- | --- | --- |
| data | [ByteSource](docs/code/stable/fundamentals/types.md#byte-source) | Icon stream data. |
| mimeType | string | Icon mime type. |
| modifiedTime | string | Icon modified time. |
