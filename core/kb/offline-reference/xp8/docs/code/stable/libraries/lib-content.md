<!-- src:https://developer.enonic.com/docs/code/stable/libraries/lib-content generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries/lib-content.md

# Content library

Functions to find and manipulate content.

## Usage

```groovy
dependencies {
  include xplibs.content
}
```

```typescript
import contentLib from '/lib/xp/content';
```

## Constants

### CONTENT_ROOT_PATH

String constant with the root path of content nodes (`/content`).

Usage

```typescript
import {CONTENT_ROOT_PATH} from '/lib/xp/content';

const myRoot = CONTENT_ROOT_PATH; // "/content"
```

### ARCHIVE_ROOT_PATH

String constant with the root path of archived nodes (`/archive`).

Usage

```typescript
import {ARCHIVE_ROOT_PATH} from '/lib/xp/content';

const myRoot = ARCHIVE_ROOT_PATH; // "/archive"
```

## Functions

### addAttachment

Adds an attachment to an existing content.

**Parameters:**

`addAttachment()` takes a single `AddAttachmentParam` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id to the content. |
| name | string | Attachment name (unique within the content). |
| mimeType | string | Attachment content type. |
| label | string | **Optional.** Attachment label. |
| data | object | **Optional.** Stream with the binary data for the attachment. |

Examples

```typescript
import {addAttachment} from '/lib/xp/content';

// Adds an attachment.
addAttachment({
    key: '/mySite/mycontent',
    name: 'image',
    mimeType: 'image/png',
    label: 'photo',
    data: dataStream
});
```

### archive

Archives a content

**Parameters:**

`archive()` takes a single `ArchiveContentParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| content | string | Path or id of the content to be archived |

Returns

**string[]** : List with ids of the contents that were archived

Examples

```typescript
import {archive} from '/lib/xp/content';

// Archive content by path.
const result1 = archive({
    content: '/path/to/mycontent',
});

log.info('Archived content ids: %s', result1.join(','));

// Archive content by id.
const result2 = archive({
    content: 'my-content-id'
});

log.info('Archived content ids: %s', result2.join(','));
```

### create

Creates a content.

Either `name` or `displayName` (or both) must be specified. When `name` is not set, the system will auto-generate a name based on the `displayName`, by lower-casing and replacing certain characters. If there is already a content with the auto-generated name, a suffix will be added to `name` in order to make it unique.

To create a content where `name` is not important and there could be multiple instances under the same parent content, skip the `name` parameter and specify a `displayName` instead.

**Parameters:**

`create()` takes a single `CreateContentParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| name | string | **Optional.** Name of content. |
| parentPath | string | Path to place content under. |
| displayName | string | **Optional.** Display name. Defaults to the same as `name`. |
| requireValid | boolean | **Optional.** The content has to be valid, according to the content type, to be created. If `true` and the content is not strictly valid, an error will be thrown. Defaults to `true`. |
| refresh | boolean | **Optional.** If `true`, the created content will be searchable through queries immediately, otherwise within 1 second. Since there is a performance penalty doing this refresh, set to `false` for bulk operations. Defaults to `true`. |
| contentType | string | Content type to use. |
| language | string | **Optional.** The language tag representing the content’s locale. |
| childOrder | string | **Optional.** Default ordering of children when doing `getChildren` if no order is given in query. |
| data | object | Actual content data. |
| page | object | **Optional.** Content [page](docs/code/stable/fundamentals/types.md#page-component). |
| x | object | **Optional.** eXtra data to use. |
| workflow | object | **Optional.** Workflow information to use. Default has state `READY` and an empty check list. |

Returns

**object** : Content created as JSON

Examples

```typescript
import {create} from '/lib/xp/content';

// Creates a content.
const result1 = create({
    name: 'mycontent',
    parentPath: '/a/b',
    displayName: 'My Content',
    contentType: 'test:myContentType',
    language: 'es',
    data: {
        a: 1,
        b: 2,
        c: ['1', '2'],
        d: {
            e: {
                f: 3.6,
                g: true
            }
        }
    },
    x: {
        "com-enonic-myapplication": {
            myschema: {
                a: 1
            }
        }
    },
    workflow: {
        state: 'PENDING_APPROVAL',
        checks: {
            'Review by lawyer': 'PENDING'
        }
    },
});

log.info('Content created with id %s', result1._id);
```

```typescript
import {create} from '/lib/xp/content';

// Check if content already exists.
try {
    const result2 = create({
        name: 'mycontent',
        parentPath: '/a/b',
        displayName: 'My Content',
        contentType: 'test:myContentType',
        data: {}
    });

    log.info('Content created with id %s', result2._id);

} catch (e) {
    if (e.code == 'contentAlreadyExists') {
        log.error('There is already a content with that name');
    } else {
        log.error('Unexpected error: %s', e.message);
    }
}
```

```typescript
// Content created.
const expected = {
    _id: "123456",
    _name: "mycontent",
    _path: "/a/b/mycontent",
    creator: "user:system:anonymous",
    createdTime: "1975-01-08T00:00:00Z",
    type: "test:myContentType",
    displayName: "My Content",
    hasChildren: false,
    language: "es",
    valid: false,
    data: {
        a: 1,
        b: 2,
        c: [
            "1",
            "2"
        ],
        d: {
            e: {
                f: 3.6,
                g: true
            }
        }
    },
    x: {
        "com-enonic-myapplication": {
            myschema: {
                a: 1
            }
        }
    },
    page: {},
    attachments: {},
    publish: {}
};
```

### createMedia

Creates a media content

**Parameters:**

`createMedia()` takes a single `CreateMediaParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| name | string | Name of content. |
| parentPath | string | **Optional.** Path to place content under. Defaults to `/`. |
| focalX | number | **Optional.** Focal point for X axis (if it’s an image). |
| focalY | number | **Optional.** Focal point for Y axis (if it’s an image). |
| artist | string \| string[] | **Optional.** Artist of the media. |
| tags | string \| string[] | **Optional.** Tags of the media. |
| caption | string | **Optional.** Caption of the media. |
| altText | string | **Optional.** Alt text of the media. |
| copyright | string | **Optional.** Copyright of the media. |
| data | object | Data (as stream) to use. |
| idGenerator | function | **Optional.** Function used to generate the id-suffix appended to the content name. |

Returns

**object** : Returns the created media content

Examples

```typescript
import {createMedia} from '/lib/xp/content';

// Creates a media.
const result = createMedia({
    name: 'mycontent',
    parentPath: '/a/b',
    data: stream
});
```

```typescript
// Media created.
const expected = {
    _id: "123456",
    _name: "mycontent",
    _path: "/a/b/mycontent",
    creator: "user:system:anonymous",
    createdTime: "1975-01-08T00:00:00Z",
    type: "base:unstructured",
    hasChildren: false,
    valid: false,
    data: {},
    x: {},
    page: {},
    attachments: {},
    publish: {}
};
```

### updateMedia

Updates a media content

**Parameters:**

`updateMedia()` takes a single `UpdateMediaParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id of the media content. |
| name | string | Name of the media content. |
| data | object | Media data (as a stream). |
| focalX | number | **Optional.** Focal point for X axis (if content is an image). |
| focalY | number | **Optional.** Focal point for Y axis (if content is an image). |
| caption | string | **Optional.** Caption. |
| artist | string \| string[] | **Optional.** Artist. |
| copyright | string | **Optional.** Copyright. |
| tags | string \| string[] | **Optional.** Tags. |

Returns

**object** : Returns the modified media content

Examples

```typescript
import {updateMedia} from '/lib/xp/content';

// Updates a media.
const result = updateMedia({
    key: '/a/b/mycontent',
    name: 'mycontent',
    data: stream,
    artist: ['Artist 1', 'Artist 2'],
    caption: 'Caption',
    copyright: 'Copyright',
    tags: ['tag1', 'tag2']
});
```

```typescript
// Modified media.
const expected = {
    _id: "123456",
    _name: "myMedia",
    _path: "/a/b/myMedia",
    creator: "user:system:anonymous",
    createdTime: "1975-01-08T00:00:00Z",
    type: "base:unstructured",
    hasChildren: false,
    valid: false,
    data: {
        caption: "Caption",
        artist: [
            "Artist 1",
            "Artist 2"
        ],
        copyright: "Copyright",
        tags: [
            "tag1",
            "tag2"
        ]
    },
    x: {},
    page: {},
    attachments: {},
    publish: {}
};
```

### deleteContent

Deletes a content. A published content will be unpublished before deletion.

> **Note:** Renamed from `delete` to avoid the JavaScript reserved word. The old `delete` export is still available for backward compatibility.

**Parameters:**

`deleteContent()` takes a single `DeleteContentParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id to the content |

Returns

**boolean** : `true` if deleted, `false` otherwise

Examples

```typescript
import {deleteContent} from '/lib/xp/content';

// Deletes a content by path.
const result = deleteContent({
    key: '/features/js-libraries/mycontent'
});

if (result) {
    log.info('Content deleted');
} else {
    log.info('Content was not found');
}
```

### duplicate

Duplicates a content.

**Parameters:**

`duplicate()` takes a single `DuplicateContentParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| contentId | string | Id of the content. |
| workflow | object | **Optional.** Workflow state. Defaults to `{ state: "READY", checks: {} }`. |
| includeChildren | boolean | **Optional.** Indicates that children contents must be duplicated, too. Ignored if `variant=true`. Defaults to `true`. |
| variant | boolean | **Optional.** Indicates that duplicated content is a variant. Defaults to `false`. |
| parent | string | **Optional.** Destination parent path. By default, a duplicated content will be added as a sibling of the source content. |
| name | string | **Optional.** New content name. |

Returns summary of the content duplicate.

**object** : Summary of the content duplicate.

Examples

Duplicate a content

```typescript
import {duplicate} from '/lib/xp/content';

// Duplicate content by id
const result = duplicate({
    contentId: '79e21db0-5b43-45ce-b58c-6e1c420b22bd',
    includeChildren: false,
});

// Summary of the duplicated content.
const expected = {
    contentName: "sourcecontentname-copy",
    sourceContentPath: "/path/to/duplicated-content",
    duplicatedContents: [
        "duplicated-content-id"
    ]
};
```

Create a variant

```typescript
import {duplicate} from '/lib/xp/content';

// Create a variant of the content
const result = duplicate({
    contentId: '79e21db0-5b43-45ce-b58c-6e1c420b22bd',
    variant: true,
    name: 'variant-name'
});

const expected = {
    contentName: "variant-name",
    sourceContentPath: "/path/to/variant-name",
    duplicatedContents: [
        "variant-content-id"
    ]
}
```

### exists

Checks if a content exists in the current context.

**Parameters:**

`exists()` takes a single `ContentExistsParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id to the content |

Returns

**boolean** : `true` if exists, `false` otherwise

Examples

```typescript
import {exists} from '/lib/xp/content';

// Checking if a content exists
const result = exists({
    key: '/path/to/mycontent'
});

if (result) {
    log.info('Content exists');
} else {
    log.info('Content does not exist');
}
```

### get

Returns a content

**Parameters:**

`get()` takes a single `GetContentParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id to the parent content. |
| versionId | string | **Optional.** Content version id. |

Returns

**object** : The content (as JSON) fetched from the repository

Examples

```typescript
import {get as getContentByKey} from '/lib/xp/content';

// Gets a single content by path.
const result = getContentByKey({
    key: '/path/to/mycontent'
});

if (result) {
    log.info('Display Name = %s', result.displayName);
} else {
    log.info('Content was not found');
}
```

```typescript
// Content as it is returned.
const expected = {
    _id: "123456",
    _name: "mycontent",
    _path: "/path/to/mycontent",
    creator: "user:system:admin",
    modifier: "user:system:admin",
    createdTime: "1970-01-01T00:00:00Z",
    modifiedTime: "1970-01-01T00:00:00Z",
    type: "base:unstructured",
    displayName: "My Content",
    hasChildren: false,
    language: "en",
    valid: true,
    childOrder: "_ts DESC, _name ASC",
    data: {
        myfield: "Hello World"
    },
    x: {},
    page: {},
    attachments: {
        "logo.png": {
            name: "logo.png",
            label: "small",
            size: 6789,
            mimeType: "image/png"
        },
        "document.pdf": {
            name: "document.pdf",
            size: 12345,
            mimeType: "application/pdf"
        }
    },
    publish: {}
};
```

### getActiveVersions

Returns the active content version for each specified branch.

**Parameters:**

`getActiveVersions()` takes a single `GetActiveVersionsParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id of the content |
| branches | string[] | Array of branch names to get active versions for |

Returns

**object** : Object with branch names as keys and content versions as values.

Examples

```typescript
import {getActiveVersions} from '/lib/xp/content';

// Fetch active versions for draft and master branches
const result = getActiveVersions({
    key: 'contentid',
    branches: ['draft', 'master']
});

log.info('Draft version: %s', result.draft.versionId);
log.info('Master version: %s', result.master.versionId);
```

### getAttachments

This function returns a content attachments

**Parameters:**

`getAttachments()` takes the content’s path or id as a single string argument.

Returns

**object** : An object with all the attachments stored in the content, where the key is the attachment name. Or null if the content was not found.

Examples

```typescript
// Attachments returned.
const expected = {
    "logo.png": {
        name: "logo.png",
        label: "small",
        size: 6789,
        mimeType: "image/png"
    },
    "document.pdf": {
        name: "document.pdf",
        size: 12345,
        mimeType: "application/pdf"
    }
};
```

### getAttachmentStream

This function returns a data-stream for the specified content attachment

**Parameters:**

`getAttachmentStream()` takes a single `GetAttachmentStreamParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id to the content |
| name | string | Attachment name |

Returns

**object** : Stream of the attachment data

Examples

```typescript
import {getAttachmentStream} from '/lib/xp/content';

// Get stream for attachment.
const stream = getAttachmentStream({
    key: '/a/b/mycontent',
    name: 'document.pdf'
});
```

### getChildren

Fetches children of a content

**Parameters:**

`getChildren()` takes a single `GetChildContentParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id to the parent content. |
| start | number | **Optional.** Start index (used for paging). Defaults to `0`. |
| count | number | **Optional.** Number of contents to fetch. Defaults to `10`. |
| sort | string | **Optional.** Sorting expression. |

Returns

**object** : Result object with `total`, `count` and `hits` properties listing the children fetched from the repository

Examples

```typescript
import {getChildren} from '/lib/xp/content';

// Returns the children of specified path.
const result = getChildren({
    key: '/path/to',
    start: 0,
    count: 2,
    sort: '_modifiedTime ASC'
});

log.info('Found %s number of contents', result.total);

result.hits.forEach((content) => {
  log.info('Content %s loaded', content._name);
});
```

```typescript
// Result set returned.
const expected = {
    total: 20,
    count: 2,
    hits: [
        {
            _id: "id1",
            _name: "name1",
            _path: "/a/b/name1",
            creator: "user:system:admin",
            modifier: "user:system:admin",
            createdTime: "1970-01-01T00:00:00Z",
            modifiedTime: "1970-01-01T00:00:00Z",
            type: "base:unstructured",
            displayName: "My Content 1",
            hasChildren: false,
            valid: false,
            data: {},
            x: {},
            page: {},
            attachments: {},
            publish: {}
        },
        {
            _id: "id2",
            _name: "name2",
            _path: "/a/b/name2",
            creator: "user:system:admin",
            modifier: "user:system:admin",
            createdTime: "1970-01-01T00:00:00Z",
            modifiedTime: "1970-01-01T00:00:00Z",
            type: "base:unstructured",
            displayName: "My Content 2",
            hasChildren: false,
            valid: false,
            data: {},
            x: {},
            page: {},
            attachments: {},
            publish: {}
        }
    ]
};
```

### getOutboundDependencies

Returns the list of content items that are outbound dependencies of specified content.

**Parameters:**

`getOutboundDependencies()` takes a single `GetOutboundDependenciesParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id to the content |

Returns

**string[]** : List with ids of dependent content items

Examples

```typescript
import {getOutboundDependencies} from '/lib/xp/content';

// Gets outbound dependencies of content by its Id.
const result = getOutboundDependencies({
    key: '/features/js-libraries/mycontent'
});

if (result) {
    log.info('Outbound dependencies: %s', JSON.stringify(result, null, 4));
} else {
    log.info('Outbound dependencies were not found');
}
```

### getPermissions

Returns content permissions

**Parameters:**

`getPermissions()` takes a single `GetPermissionsParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id to the content |

Returns

**object** : Content permissions

Examples

```typescript
import {getPermissions} from '/lib/xp/content';

// Return permissions for content by path.
const result = getPermissions({
    key: '/features/js-libraries/mycontent'
});

if (result) {
    log.info('Content inherits permissions: %s', result.inheritPermissions);
} else {
    log.info('Content not found');
}
```

```typescript
// Permissions returned.
const expected = {
    permissions: [
        {
            principal: "user:system:anonymous",
            allow: [
                "READ"
            ],
            deny: []
        }
    ]
};
```

### getSite

Returns the parent site of a content

**Parameters:**

`getSite()` takes a single `GetSiteParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id to the content |

Returns

**object** : The current site as JSON

Examples

```typescript
import {getSite} from '/lib/xp/content';

// Returns content's parent site
const result = getSite({
    key: '/path/to/mycontent'
});
log.info('Site name = %s', result._name);
```

```typescript
// Site data returned.
const expected = {
    _id: "100123",
    _name: "my-content",
    _path: "/my-content",
    type: "base:unstructured",
    hasChildren: false,
    valid: false,
    data: {
        siteConfig: {
            applicationKey: "myapplication",
            config: {
                Field: 42
            }
        }
    },
    x: {},
    page: {},
    attachments: {},
    publish: {}
};
```

### getSiteConfig

Returns configuration of a specified application assigned to the site of a content

**Parameters:**

`getSiteConfig()` takes a single `GetSiteConfigParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id to the content |
| applicationKey | string | Application key |

Returns

**object** : App config (as JSON)

Examples

```typescript
import {getSiteConfig} from '/lib/xp/content';

// Returns config of the content's parent site
const result = getSiteConfig({
    key: '/path/to/mycontent',
    applicationKey: app.name
});
log.info('Field value for the site config = %s', result.Field);
```

```typescript
// Site config returned.
const expected = {
    Field: 42
};
```

### getType

Returns properties and icon of the specified content type

**Parameters:**

`getType()` takes the content type name as a single string argument, formatted as `:` (for example, `com.enonic.myapp:article`).

Returns

**[ContentType](#contenttype)** : The content type object if found, or `null` otherwise. See ContentType type definition below

Examples

```typescript
import {getType} from '/lib/xp/content';

// Get a content type by name
const contentType = getType('com.enonic.myapp:person');
```

```typescript
// Content type returned:
const expected = {
    name: "com.enonic.myapp:person",
    title: "Person",
    description: "Person content type",
    superType: "base:structured",
    abstract: false,
    final: true,
    allowChildContent: true,
    modifiedTime: "2016-01-01T12:00:00Z",
    icon: {
        mimeType: "image/png",
        modifiedTime: "2016-01-01T12:00:00Z"
    },
    form: [
        {
            formItemType: "Input",
            name: "name",
            label: "Full name",
            maximize: true,
            inputType: "TextLine",
            occurrences: {
                maximum: 1,
                minimum: 1
            },
            config: {}
        },
        {
            formItemType: "Input",
            name: "title",
            label: "Photo",
            helpText: "Person photo",
            maximize: true,
            inputType: "ImageSelector",
            occurrences: {
                maximum: 1,
                minimum: 1
            },
            config: {}
        },
        {
            formItemType: "Input",
            name: "bio",
            label: "Bio",
            maximize: true,
            inputType: "HtmlArea",
            occurrences: {
                maximum: 1,
                minimum: 1
            },
            config: {}
        },
        {
            formItemType: "Input",
            name: "birthdate",
            label: "Birth date",
            maximize: true,
            inputType: "Date",
            occurrences: {
                maximum: 1,
                minimum: 0
            },
            config: {}
        },
        {
            formItemType: "Input",
            name: "email",
            label: "Email",
            helpText: "Email address",
            maximize: true,
            inputType: "TextLine",
            occurrences: {
                maximum: 1,
                minimum: 1
            },
            config: {
                regexp: [
                    {
                        value: "^[^@]+@[^@]+\\.[^@]+$"
                    }
                ]
            }
        },
        {
            formItemType: "Input",
            name: "nationality",
            label: "Nationality",
            maximize: true,
            inputType: "ContentSelector",
            occurrences: {
                maximum: 1,
                minimum: 0
            },
            config: {
                allowContentType: [
                    {
                        value: "com.enonic.myapp:country"
                    }
                ]
            }
        }
    ]
};
```

```typescript
import {getType} from '/lib/xp/content';

// Get a content type icon
const ct = getType('com.enonic.myapp:person');
const icon = ct.icon;
return {
    body: icon.data,
    contentType: icon.mimeType
};
```

### getTypes

Returns the list of all the content types currently registered in the system

Returns

**[ContentType](#contenttype)[]** : Array with all the content types found. See ContentType type definition below

Examples

```typescript
import {getTypes} from '/lib/xp/content';

// Gets the list of all content types in the system
const contentTypes = getTypes();

log.info('%s content types found:', contentTypes.length);
contentTypes.forEach(({title, name, superType}) => {
    if (superType === 'base:structured') {
        log.info('%s - %s', name, title);
    }
});
```

### getVersions

Returns content versions, with cursor-based pagination.

**Parameters:**

`getVersions()` takes a single `GetVersionsParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id of the content. |
| count | number | **Optional.** Number of content versions to fetch. Defaults to `10`. |
| cursor | string | **Optional.** Cursor for pagination. |

Returns

**object** : Result object with `total`, `count`, `cursor` and `hits` properties listing the content versions.

Examples

```typescript
import {getVersions} from '/lib/xp/content';

// Fetch first page
const result = getVersions({
    key: 'contentid',
    count: 2
});

log.info('Total versions: %s', result.total);

// Fetch next page using cursor
if (result.cursor) {
    const nextPage = getVersions({
        key: 'contentid',
        count: 2,
        cursor: result.cursor
    });
}
```

### update

Update a content

> **Note:** Properties starting with `_` may not be modified using this function. To rename or move a content (ie to change the `_name` property), use the [move function](#move) instead.

**Parameters:**

`update()` takes a single `UpdateContentParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id to the content. |
| editor | function | Editor callback function. |
| requireValid | boolean | **Optional.** The content has to be valid (according to the content type) to be updated. If `true` and the content is not strictly valid, an error will be thrown. Defaults to `true`. |

Returns

**object** : Modified content as JSON

Examples

```typescript
import {update} from '/lib/xp/content';

// Editor to call for content.
function editor(c) {
    c.displayName = 'Modified';
    c.language = 'en';
    c.data.myCheckbox = false;
    c.data["myTime"] = "11:00";
    c.publish.from = "2016-11-03T10:01:34Z";
    c.workflow.state = "READY";
    return c;
}

// Update content by path
const result = update({
    key: '/a/b/mycontent',
    editor: editor
});

if (result) {
    log.info('Content modified. New title is %s', result.displayName);
} else {
    log.info('Content not found');
}
```

```typescript
// Content modified.
const expected = {
    _id: "123456",
    _name: "mycontent",
    _path: "/path/to/mycontent",
    creator: "user:system:admin",
    modifier: "user:system:admin",
    createdTime: "1970-01-01T00:00:00Z",
    modifiedTime: "1970-01-01T00:00:00Z",
    type: "base:unstructured",
    displayName: "Modified",
    hasChildren: false,
    language: "en",
    valid: true,
    childOrder: "_ts DESC, _name ASC",
    data: {
        myfield: "Hello World",
        myCheckbox: "false",
        myTime: "11:00"
    },
    x: {},
    page: {},
    attachments: {
        "logo.png": {
            name: "logo.png",
            label: "small",
            size: 6789,
            mimeType: "image/png"
        },
        "document.pdf": {
            name: "document.pdf",
            size: 12345,
            mimeType: "application/pdf"
        }
    },
    publish: {
        from: "2016-11-03T10:01:34Z"
    },
    workflow: {
        state: "READY",
        checks: {}
    }
};
```

### updateMetadata

Updates metadata (`owner` and `variantOf`) for a content. The update is applied to both the master and draft branches.

**Parameters:**

`updateMetadata()` takes a single `UpdateMetadataParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id to the content |
| editor | function | Editor callback function to modify metadata |

The editor callback receives an object with the current `source` content, `owner` and `variantOf`, and must return the same object with the desired modifications.

Returns

**object** : Result object with the updated `content` property.

Examples

```typescript
import {updateMetadata} from '/lib/xp/content';

// Update content metadata by path
const result = updateMetadata({
    key: '/a/b/mycontent',
    editor: (c) => {
        c.owner = 'user:system:new-owner';
        return c;
    }
});

if (result) {
    log.info('Content metadata updated');
} else {
    log.info('Content not found');
}
```

### updateWorkflow

Updates workflow information (state and checks) for a content. The update is applied to the draft branch only.

**Parameters:**

`updateWorkflow()` takes a single `UpdateWorkflowParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id to the content |
| editor | function | Editor callback function to modify workflow |

The editor callback receives an object with the current `source` content and a writable `state` property, and must return the same object with the desired modifications.

Returns

**object** : Result object with the updated `content` property.

Examples

```typescript
import {updateWorkflow} from '/lib/xp/content';

// Mark content workflow as READY
const result = updateWorkflow({
    key: '/a/b/mycontent',
    editor: (w) => {
        w.state = 'READY';
        return w;
    }
});
```

### patch

Patches a content

> **Warning:** This is a low-level and potentially dangerous operation.

It should be used with caution. Access is restricted to users with `admin` or `cms.admin` roles.

`patch()` takes a single `PatchContentParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id to the content. |
| patcher | function | Patcher callback function. |
| branches | string[] | **Optional.** A list of branches to patch. Defaults to `[]`.    * If not provided or empty, the content in the current branch will be patched.    * If one branch is listed, the patch occurs in that specific branch.    * If multiple branches are listed:    1. The patch is applied to the **first** branch in the list.    2. For each subsequent branch in the list:    * If its content version is identical to the **original** (pre-patch) version from any processed branch, it is simply switched to point to the new, patched version.    * If its content version is **different**, the patch is applied to it separately. |
| skipSync | boolean | **Optional.** If `true`, skip synchronization of the content in children projects after patching. Defaults to `false`. |
| attachments | object | **Optional.** Object for managing content attachments. Contains optional arrays: [`createAttachments` (add new)](#createAttachments_details), [`modifyAttachments` (update existing)](#modifyAttachments_details) and `removeAttachments` (a string array with attachment names to remove). |

`patcher` is a function that receives the current content as parameter and must return the modified content. A list of supported fields that can be patched is provided below.

**Patchable Fields:**

| Name | Type | Description |
| --- | --- | --- |
| displayName | string | The display name of the content. |
| language | string | The language tag representing the content’s locale. |
| childOrder | string | String defining the sort order of children. |
| manualOrderValue | number | Numeric value used for manual sorting across siblings (when parent’s childOrder is manual). |
| valid | boolean | Sets the content’s validity status. |
| data | object | A JSON object containing the main data (properties) of the content, according to its content type. |
| page | object | A JSON object describing the [page](docs/code/stable/fundamentals/types.md#page-component) configuration including regions and components. |
| x | object | A JSON object containing extra data (x-data) associated with the content. |
| owner | string | The owner of the content. Must be a PrincipalKey string. |
| creator | string | The creator of the content. Must be a PrincipalKey string. |
| createdTime | string | The creation timestamp. Must be an ISO 8601 formatted string. |
| modifier | string | The principal who last modified the content. Must be a PrincipalKey string. |
| modifiedTime | string | The last modified timestamp. Must be an ISO 8601 formatted string. |
| archivedBy | string | The principal who archived the content. Must be a PrincipalKey string. |
| archivedTime | string | The archival timestamp. Must be an ISO 8601 formatted string. |
| publish | object | A JSON object containing publishing information. |
| workflow | object | A JSON object containing [workflow](docs/code/stable/fundamentals/types.md#workflow) state information. |
| inherit | string[] | An array of strings specifying which properties to inherit from the parent (e.g., ["owner", "language"]). |
| variantOf | string | The ContentId (as a string) of the content this item is a variant of (used for localization). |
| processedReferences | string[] | An array of ContentId strings that this content references. |
| validationErrors | [ValidationError](docs/code/stable/fundamentals/types.md#validation-error)[] | An array of objects describing validation errors. |
| originProject | string | The name of the project this content was inherited from. |
| originalParentPath | string | The original parent path in the parent project. |
| originalName | string | The original name in the parent project. |
| attachments | object | An object listing the content’s existing attachments, keyed by attachment name. Use the `attachments` patch parameter (with `createAttachments` / `modifyAttachments` / `removeAttachments`) to manage the attachment binaries themselves. |

**createAttachments:** Each entry is an object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| name | string | Name of the attachment to create. |
| mimeType | string | **Optional.** Mime-type of the data. |
| label | string | **Optional.** Label of the attachment. |
| textContent | string | **Optional.** Text content to set. |
| data | object \| string | **Optional.** Data (as stream) to use. |

**modifyAttachments:** Each entry is an object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| name | string | Name of the attachment to modify. |
| mimeType | string | **Optional.** Mime-type of the data. |
| label | string | **Optional.** Label of the attachment. |
| textContent | string | **Optional.** Text content to set. |
| sha512 | string | **Optional.** SHA-512 hash of the data. |
| size | number | **Optional.** Size of the data in bytes. |

Examples

Patching archival info.

```typescript
import {patch} from '/lib/xp/content';
function patcher(c) {
    c.archivedBy = 'user:system:admin';
    c.archivedTime = new Date().toISOString();
    return c;
}

const result = patch({
    key: '/a/b/mycontent',
    patcher: patcher
});
```

Patching content’s attachments.

```typescript
import {patch} from '/lib/xp/content';
import {newStream} from '/lib/xp/io';

// Patcher function to modify content.
function patcher(c) {
    c.displayName = 'Patched Content';
    c.data.myField = 'New Value';
    return c;
}
// Patch content by path
const result = patch({
    key: '/a/b/mycontent',
    patcher: patcher,
    branches: ['draft', 'master'],
    attachments: {
        createAttachments: [
            {
                name: 'new-attachment.txt',
                mimeType: 'text/plain',
                data: newStream('Hello World')
            }
        ],
        modifyAttachments: [
            {
                name: 'existing-attachment.txt',
                mimeType: 'text/plain',
                label: 'updated-label'
            }
        ],
        removeAttachments: [
            'old-attachment.txt'
        ]
    }
});
```

### move

Renames a content or moves it to a new path

**Parameters:**

`move()` takes a single `MoveContentParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| source | string | Path or id of the content to be moved or renamed |
| target | string | New path or name for the content. If the target ends in slash '/', it specifies the parent path where to be moved. Otherwise it means the new desired path or name for the content |

Returns

**object** : The content that was moved or renamed

Examples

```typescript
import {move} from '/lib/xp/content';

// Rename content by path. Keeps same parent.
const content1 = move({
    source: '/my-site/my-content-name',
    target: 'new-name'
});

log.info('New path: %s', content1._path); // '/my-site/new-name'
```

```typescript
import {move} from '/lib/xp/content';

// Move content by path. New parent path, keeps same name.
const content2 = move({
    source: '/my-site/my-content-name',
    target: '/my-site/folder/'
});

log.info('New path: %s', content2._path); // '/my-site/folder/my-content-name'
```

```typescript
import {move} from '/lib/xp/content';

// Move content by id to new path. New parent path, keeps same name.
const content3 = move({
    source: '8d933461-ede7-4dd5-80da-cb7de0cd7bba',
    target: '/my-site/folder/'
});

log.info('New path: %s', content3._path); // '/my-site/folder/my-content-name'
```

```typescript
import {move} from '/lib/xp/content';

// Move and rename content.
const content4 = move({
    source: '/my-site/my-content-name',
    target: '/my-site/folder/new-name'
});

log.info('New path: %s', content4._path); // '/my-site/folder/new-name'
```

```typescript
import {move} from '/lib/xp/content';

// Handle error if target already exists.
try {
    const content5 = move({
        source: '/my-site/my-content-name',
        target: '/my-site/folder/existing-content'
    });

} catch (e) {
    if (e.code == 'contentAlreadyExists') {
        log.error('There is already a content in the target specified');
    } else {
        log.error('Unexpected error: %s', e.message);
    }
}
```

### publish

Publishes content to the master branch

**Parameters:**

`publish()` takes a single `PublishContentParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| keys | string[] | List of all content keys (path or id) that should be published. |
| schedule | [Schedule](#schedule) | **Optional.** Schedule publishing. |
| excludeDescendantsOf | string[] | **Optional.** List of content keys whose descendants should be excluded from publishing. |
| excludeChildrenIds | string[] | **Optional.** *Deprecated, use* `excludeDescendantsOf` *instead.* |
| includeDependencies | boolean | **Optional.** Whether all related content should be included when publishing content. Defaults to `true`. |
| message | string | **Optional.** Publish message. |

Returns

**object** : Status of the publish operation as JSON

Examples

```typescript
import {publish} from '/lib/xp/content';

// Publish content by path or key
const result = publish({
    keys: ['/mysite/somepage', '79e21db0-5b43-45ce-b58c-6e1c420b22bd'],
    schedule: {
        from: new Date().toISOString(),
        to: '2018-01-01T13:37:00.000Z'
    },
    includeDependencies: false
});

if (result) {
    log.info('Pushed %s content.', result.pushedContents.length);
    log.info('Content that failed operation: %s', result.failedContents.length);
} else {
    log.info('Operation failed.');
}
```

```typescript
// Content published.
const expected = {
    pushedContents: [
        "d7ad428b-eae2-4ff1-9427-e8e8a8a3ab23",
        "9f5b0db0-38f9-4e81-b92e-116f25476b1c",
        "e1f57280-d672-4cd8-b674-98e26e5b69ae"
    ],
    failedContents: [
        "79e21db0-5b43-45ce-b58c-6e1c420b22bd"
    ]
};
```

### query

Retrieves content using a query

**Parameters:**

`query()` takes a single `QueryContentParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| start | number | **Optional.** Start index (used for paging). Defaults to `0`. |
| count | number | **Optional.** Number of contents to fetch. Defaults to `10`. |
| query | string \| object | **Optional.** Query string or [DSL](docs/code/stable/storage/querying.md) expression. |
| filters | object \| object[] | **Optional.** Filters to apply to query result. |
| sort | string \| object \| object[] | **Optional.** Sorting string or [DSL](docs/code/stable/storage/querying.md#sort) expression. |
| aggregations | object | **Optional.** Aggregations expression. |
| contentTypes | string[] | **Optional.** Content types to filter on. |
| highlight | object | **Optional.** Highlight expression. |

Returns

**object** : Result of query

If `sort` was specified, results will contain system meta properties `_sort` and `_score: null`, otherwise `_score` will have a relevant value.

Examples

```typescript
import {query} from '/lib/xp/content';

// Query content using aggregations.
const result = query({
    start: 0,
    count: 2,
    sort: "modifiedTime DESC, geoDistance('data.location', '59.91,10.75', 'km')",
    query: "data.city = 'Oslo' AND fulltext('data.description', 'garden', 'AND') ",
    filters: {
        boolean: {
            must: [
                {
                    exists: {
                        field: "modifiedTime"
                    }
                },
                {
                    exists: {
                        field: "another"
                    }
                }
            ],
            mustNot: {
                hasValue: {
                    field: "myField",
                    values: [
                        "cheese",
                        "fish",
                        "onion"
                    ]
                }
            }
        },
        notExists: {
            field: "unwantedField"
        },
        ids: {
            values: ["id1", "id2"]
        }
    },
    contentTypes: [
        app.name + ":house",
        app.name + ":apartment"
    ],
    aggregations: {
        floors: {
            terms: {
                field: "data.number_floor",
                order: "_count asc"
            },
            aggregations: {
                prices: {
                    histogram: {
                        field: "data.price",
                        interval: 1000000,
                        extendedBoundMin: 1000000,
                        extendedBoundMax: 3000000,
                        minDocCount: 0,
                        order: "_key desc"
                    }
                }
            }
        },
        by_month: {
            dateHistogram: {
                field: "data.publish_date",
                interval: "1M",
                minDocCount: 0,
                format: "MM-yyyy"
            }
        },
        price_ranges: {
            range: {
                field: "data.price",
                ranges: [
                    {to: 2000000},
                    {from: 2000000, to: 3000000},
                    {from: 3000000}
                ]
            }
        },
        my_date_range: {
            dateRange: {
                field: "data.publish_date",
                format: "MM-yyyy",
                ranges: [
                    {to: "now-10M/M"},
                    {from: "now-10M/M"}
                ]
            }
        },
        price_stats: {
            stats: {
                field: "data.price"
            }
        }
    }
});

log.info('Found %s number of contents', result.total);

result.hits.forEach((content) => {
  log.info('Content %s found', content._name);
});
```

```typescript
// Result set returned.
const expected = {
    total: 20,
    count: 2,
    hits: [
        {
            _id: "id1",
            _name: "name1",
            _path: "/a/b/name1",
            _sort: ["1970-01-01T00:00:00Z", 9279.647306690395],
            _score: null,
            creator: "user:system:admin",
            modifier: "user:system:admin",
            createdTime: "1970-01-01T00:00:00Z",
            modifiedTime: "1970-01-01T00:00:00Z",
            type: "base:unstructured",
            displayName: "My Content 1",
            hasChildren: false,
            valid: false,
            data: {},
            x: {},
            page: {},
            attachments: {},
            publish: {}
        },
        {
            _id: "id2",
            _name: "name2",
            _path: "/a/b/name2",
            _sort: [ "1970-01-01T00:00:00Z", 15964.050071707446],
            _score: null,
            creator: "user:system:admin",
            modifier: "user:system:admin",
            createdTime: "1970-01-01T00:00:00Z",
            modifiedTime: "1970-01-01T00:00:00Z",
            type: "base:unstructured",
            displayName: "My Content 2",
            hasChildren: false,
            valid: false,
            data: {},
            x: {},
            page: {},
            attachments: {},
            publish: {}
        }
    ],
    aggregations: {
        genders: {
            buckets: [
                {
                    key: "male",
                    docCount: 10
                },
                {
                    key: "female",
                    docCount: 12
                }
            ]
        },
        by_month: {
            buckets: [
                {
                    key: "2014-01",
                    docCount: 8
                },
                {
                    key: "2014-02",
                    docCount: 10
                },
                {
                    key: "2014-03",
                    docCount: 12
                }
            ]
        },
        price_ranges: {
            buckets: [
                {
                    key: "a",
                    docCount: 2,
                    to: 50
                },
                {
                    key: "b",
                    docCount: 4,
                    from: 50,
                    to: 100
                },
                {
                    key: "c",
                    docCount: 4,
                    from: 100
                }
            ]
        },
        my_date_range: {
            buckets: [
                {
                    key: "date range bucket key",
                    docCount: 2,
                    from: "2014-09-01T00:00:00Z"
                },
                {
                    docCount: 5,
                    from: "2014-10-01T00:00:00Z",
                    to: "2014-09-01T00:00:00Z"
                },
                {
                    docCount: 7,
                    to: "2014-11-01T00:00:00Z"
                }
            ]
        },
        item_count: {
            count: 5,
            min: 1,
            max: 5,
            avg: 3,
            sum: 15
        }
    }
};
```

### removeAttachment

Removes an attachment from an existing content

**Parameters:**

`removeAttachment()` takes a single `RemoveAttachmentParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id to the content |
| name | string \| string[] | Attachment name, or array of names |

Examples

```typescript
import {removeAttachment} from '/lib/xp/content';

// Removes an attachment, by content path.
removeAttachment({key: '/mySite/mycontent', name: 'document'});
```

```typescript
import {removeAttachment} from '/lib/xp/content';

// Removes multiple attachments, by content id.
removeAttachment({key: '3381d720-993e-4576-b089-aaf67280a74c', name: ['document', 'image']});
```

### resetInheritance

Resets custom inheritance flags of a content item. For an item that was inherited from a parent content project/layer this action will reset specified changes made inside a specified layer.

**Parameters:**

`resetInheritance()` takes a single `ResetInheritanceParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id to the content |
| projectName | string | A unique id of a Content Layer in which the inherited content item should be reset |
| inherit | string[] | Array of inheritance flags (case-sensitive, all upper-case). Supported values are: `CONTENT` (resets any customized content data), `PARENT` (resets item moved under a different parent), `NAME` (resets renamed item), `SORT` (resets custom sorting). |

Examples

```typescript
import {resetInheritance} from '/lib/xp/content';

// Resets all custom changes made to inherited item '/mySite/mycontent' in the layer 'layer-no'
resetInheritance({key: '/mySite/mycontent', projectName: 'layer-no', inherit: ['CONTENT', 'PARENT', 'NAME', 'SORT']});
```

```typescript
import {resetInheritance} from '/lib/xp/content';

// Resets custom sorting of inherited item '/mySite/mycontent' in the layer 'layer-no', but preserves any other changes
resetInheritance({key: '/mySite/mycontent', projectName: 'layer-no', inherit: ['SORT']});
```

### restore

Restores a content from the archive

**Parameters:**

`restore()` takes a single `RestoreContentParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| content | string | Path or id of the content to be restored |
| path | string | **Optional.** Path of parent for restored content |

Returns

**string[]** : List with ids of the contents that were restored

Examples

```typescript
import {restore} from '/lib/xp/content';

// Restore content by path.
const result1 = restore({
    content: '/path/to/mycontent',
});

log.info('Restored content ids: %s', result1.join(','));

// Restore content by id.
const result2 = restore({
    content: 'my-content-id'
});

log.info('Restored content ids: %s', result2.join(','));

// Restore content by id to custom path.
const result3 = restore({
    content: 'my-content-id',
    path: '/custom-parent'
});

log.info('Restored content ids: %s', result3.join(','));
```

### applyPermissions

Applies permissions on a content.

> **Note:** If the content is published, the permissions will be applied to the published content as well without a need to republish it.

**Parameters:**

`applyPermissions()` takes a single `ApplyPermissionsParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id of the content. |
| permissions | [AccessControlEntry](#accesscontrolentry)[] | **Optional.** Array of permissions to overwrite current permissions. Cannot be used with `addPermissions` or `removePermissions`. |
| addPermissions | [AccessControlEntry](#accesscontrolentry)[] | **Optional.** Array of permissions to add. Cannot be used simultaneously with `permissions`. |
| removePermissions | [AccessControlEntry](#accesscontrolentry)[] | **Optional.** Array of permissions to remove. Cannot be used simultaneously with `permissions`. |
| scope | string (`SINGLE` \| `TREE` \| `SUBTREE`) | **Optional.** Scope of applying permissions. `SINGLE` applies permissions only to the content itself. `TREE` applies permissions to the content and its descendants. `SUBTREE` applies permissions only to the content’s descendants. Defaults to `SINGLE`. |

Returns

**object** : The map  indicating for each content id which permissions were applied

Examples

1) Applying permissions to a content by overwriting the current permissions.

```typescript
import {applyPermissions} from '/lib/xp/content';

applyPermissions({
    key: '/my-content',
    permissions: [
        {
            principal: 'role:system.everyone',
            allow: ['READ']
        },
        {
            principal: 'user:system:my-user',
            allow: ['READ', 'CREATE', 'MODIFY', 'DELETE']
        }
    ]
});
```

2) Adding permissions to a content.

```typescript
import {applyPermissions} from '/lib/xp/content';

applyPermissions({
    key: '/my-content',
    addPermissions: [
        {
            principal: 'role:system.everyone',
            allow: ['CREATE', 'MODIFY']  // 'READ' permission is already set and will be kept.
        },
        {
            principal: 'user:system:my-new-user',
            allow: ['READ', 'CREATE', 'MODIFY', 'DELETE'] // New user will have all permissions.
        }
    ]
});
```

3) Removing permissions from a content.

```typescript
import {applyPermissions} from '/lib/xp/content';

applyPermissions({
    key: '/my-content',
    removePermissions: [
        {
            principal: 'role:system.everyone',
            allow: ['CREATE', 'MODIFY']  // 'READ' permission will be kept.
        },
        {
            principal: 'user:system:my-user',
            allow: ['DELETE'] // 'DELETE' permission will be removed. All other permissions will be kept.
        },
        {
            principal: 'user:system:my-new-user' // All permissions for this principal will be removed.
        }
    ]
});
```

Applying permissions to a content and its descendants.

```typescript
import {applyPermissions} from '/lib/xp/content';

applyPermissions({
    key: '/my-content',
    permissions: [
        {
            principal: 'role:system.everyone',
            allow: ['READ']
        }
    ],
    scope: 'TREE'
});
```

Applying permissions to a content’s descendants only.

```typescript
import {applyPermissions} from '/lib/xp/content';

applyPermissions({
    key: '/my-content',
    permissions: [
        {
            principal: 'role:system.everyone',
            allow: ['READ']
        }
    ],
    scope: 'SUBTREE'
});
```

### unpublish

Unpublishes content that had been published to the master branch

**Parameters:**

`unpublish()` takes a single `UnpublishContentParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| keys | string[] | List of all content keys(path or id) that should be unpublished |

Returns

**string[]** : List with ids of the content that were unpublished

Examples

```typescript
import {unpublish} from '/lib/xp/content';

// Unpublish content by path or key
const result = unpublish({
    keys: ['/mysite/somepage', '79e21db0-5b43-45ce-b58c-6e1c420b22bd']
});

log.info('Unpublished content ids: %s', result.join(','));
```

```typescript
// Content unpublished.
const expected = [
    "d7ad428b-eae2-4ff1-9427-e8e8a8a3ab23",
    "9f5b0db0-38f9-4e81-b92e-116f25476b1c",
    "e1f57280-d672-4cd8-b674-98e26e5b69ae"
];
```

## Type Definitions

### ContentType

Properties

| Name | Type | Description |
| --- | --- | --- |
| name | string | Name of the content type. |
| title | string | Title of the content type. |
| description | string | Description of the content type. |
| superType | string | Name of the super type, or null if it has no super type. |
| abstract | boolean | Whether or not content of this type may be instantiated. |
| final | boolean | Whether or not it may be used as super type of other content types. |
| allowChildContent | boolean | Whether or not to allow creating child items on content of this type. |
| modifiedTime | string | Modified time of the content type. |
| icon | [Icon](#icon) | **Optional.** Icon of the content type. |
| form | [FormItem](docs/code/stable/fundamentals/types.md#form-item)[] | Form schema — an array of form items. |
| config | object | Custom schema configuration for the descriptor. |

### Icon

Properties

| Name | Type | Description |
| --- | --- | --- |
| data | [ByteSource](docs/code/stable/fundamentals/types.md#byte-source) | Stream with the binary data for the icon. Read it with `lib-io`. |
| mimeType | string | Mime type of the icon image. |
| modifiedTime | string | Modified time of the icon. May be used for caching. |

### Schedule

A publish schedule. Same shape as [PublishInfo](docs/code/stable/fundamentals/types.md#publish-info) without the `first` field.

Properties

| Name | Type | Description |
| --- | --- | --- |
| from | string | **Optional.** Time from which the content is considered published, as an ISO-8601 instant. Defaults to the time of publishing. |
| to | string | **Optional.** Time until which the content is considered published. ISO-8601 instant. |

### AccessControlEntry

A permission entry for a single principal.

Properties

| Name | Type | Description |
| --- | --- | --- |
| principal | [PrincipalKey](docs/code/stable/fundamentals/types.md#principal-key) | Principal the entry applies to (for example, `role:system.admin`, `user:system:su`). |
| allow | string[] | **Optional.** Permissions to grant. Each value is one of `READ`, `CREATE`, `MODIFY`, `DELETE`, `PUBLISH`, `READ_PERMISSIONS`, `WRITE_PERMISSIONS`. |
| deny | string[] | **Optional.** Permissions to deny. Same set of values as `allow`. |
