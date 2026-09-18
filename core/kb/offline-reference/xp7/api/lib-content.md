<!-- src:https://developer.enonic.com/docs/platform/7.x/api/lib-content generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC api/lib-content.md

# Content API

Functions to find and manipulate content.

## Usage

```groovy
dependencies {
  include "com.enonic.xp:lib-content:${xpVersion}"
}
```

Add the `import` statement to your controller:

```typescript
import contentLib from '/lib/xp/content';
```

## Constants

### CONTENT_ROOT_PATH

Variable of type NodePath describing content node root path.

Usage

```typescript
import {CONTENT_ROOT_PATH} from '/lib/xp/content';

const myRoot = CONTENT_ROOT_PATH; // NodePath.create( "/content" ).build()
```

### ARCHIVE_ROOT_PATH

Variable of type NodePath describing archive node root path.

Usage

```typescript
import {ARCHIVE_ROOT_PATH} from '/lib/xp/content';

const myRoot = ARCHIVE_ROOT_PATH; // NodePath.create( "/archive" ).build()
```

## Functions

### addAttachment

Adds an attachment to an existing content.

**Parameters:**

An object with the following keys and their values:

| Name | Type | Attributes | Description |
| --- | --- | --- | --- |
| key | string |  | Path or id to the content |
| name | string |  | Attachment name (unique within the content) |
| mimeType | string |  | Attachment content type |
| label | string | <optional> | Attachment label |
| data | object | <optional> | Stream with the binary data for the attachment |

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

XP 7.8.0

Archives a content

**Parameters:**

An object with the following keys and their values:

| Name | Type | Description |
| --- | --- | --- |
| сontent | string | Path or id of the content to be archived |

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

An object with the following keys and their values:

| Name | Type | Attributes | Default | Description |
| --- | --- | --- | --- | --- |
| name | string | <optional> |  | Name of content |
| parentPath | string |  |  | Path to place content under |
| displayName | string | <optional> |  | Display name. Default is same as name |
| requireValid | boolean | <optional> | true | The content has to be valid, according to the content type, to be created. If requireValid=true and the content is not strictly valid, an error will be thrown |
| refresh | boolean | <optional> | true | If refresh is true, the created content will to be searchable through queries immediately, else within 1 second. Since there is a performance penalty doing this refresh, refresh should be set to false for bulk operations |
| contentType | string |  |  | Content type to use |
| language | string | <optional> |  | The language tag representing the content’s locale |
| childOrder | string | <optional> |  | Default ordering of children when doing getChildren if no order is given in query |
| data | object |  |  | Actual content data |
| x | object | <optional> |  | eXtra data to use |
| workflow | object | <optional> |  | Workflow information to use. Default has state READY and empty check list. |

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

An object with the following keys and their values:

| Name | Type | Attributes | Default | Description |
| --- | --- | --- | --- | --- |
| name | string | <optional> |  | Name of content |
| parentPath | string | <optional> | / | Path to place content under |
| mimeType | string | <optional> |  | Mime-type of the data |
| focalX | number | <optional> |  | Focal point for X axis (if it’s an image) |
| focalY | number | <optional> |  | Focal point for Y axis (if it’s an image) |
| data |  |  |  | Data (as stream) to use |

Returns

**object** : Returns the created media content

Examples

```typescript
import {createMedia} from '/lib/xp/content';

// Creates a media.
const result = createMedia({
    name: 'mycontent',
    parentPath: '/a/b',
    mimeType: 'text/plain',
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

### modifyMedia

Modifies a media content

**Parameters:**

An object with the following keys and their values:

| Name | Type | Attributes | Default | Description |
| --- | --- | --- | --- | --- |
| key | string |  |  | Path or id of the media content |
| name | string |  |  | Name of the media content |
| data |  |  |  | Media data (as a stream) |
| mimeType | string | <optional> |  | Mime-type of the data |
| focalX | number | <optional> |  | Focal point for X axis (if content is an image) |
| focalY | number | <optional> |  | Focal point for Y axis (if content is an image) |
| caption | string | <optional> |  | Caption |
| artist | string \| string[] | <optional> |  | Artist |
| copyright | string | <optional> |  | Copyright |
| tags | string \| string[] | <optional> |  | Tags |
| workflowInfo | object | <optional> |  | Workflow state (default: READY). |

Returns

**object** : Returns the modified media content

Examples

```typescript
import {modifyMedia} from '/lib/xp/content';

// Modifies a media.
const result = modifyMedia({
    key: '/a/b/mycontent',
    name: 'mycontent',
    data: stream,
    artist: ['Artist 1', 'Artist 2'],
    caption: 'Caption',
    copyright: 'Copyright',
    mimeType: 'text/plan',
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
        mimeType: "text/plan",
        tags: [
            "tag1",
            "tag2"
        ]
    },
    x: {},
    page: {},
    attachments: {},
    publish: {},
    workflow: {
        state: "READY",
        checks: {}
    }
};
```

### delete

Deletes a content. A published content will be unpublished before deletion.

**Parameters:**

An object with the following keys and their values:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id to the content |

Returns

**boolean** : `true` if deleted, `false` otherwise

Examples

```typescript
import {delete as deleteContent} from '/lib/xp/content';

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

XP 7.12.0 Duplicates a content.

**Parameters:**

An object with the following keys and their values:

| Name | Type | Attributes | Default | Description |
| --- | --- | --- | --- | --- |
| contentId | string |  |  | Id of the content. |
| workflow | Object | <optional> | `{ state: "READY", checks: {} }` | Workflow state. |
| includeChildren | boolean | <optional> | true | Indicates that children contents must be duplicated, too. Ignored if `variant=true`. |
| variant | boolean | <optional> | false | Indicates that duplicated content is a variant. |
| parent | string | <optional> |  | Destination parent path. By default, a duplicated content will be added as a sibling of the source content. |
| name | string | <optional> |  | New content name. |

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

An object with the following keys and their values:

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

An object with the following keys and their values:

| Name | Type | Attributes | Description |
| --- | --- | --- | --- |
| key | string |  | Path or id to the parent content |
| versionId XP 7.2.0 | string | <optional> | Content version id |

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

### getAttachments

This function returns a content attachments

**Parameters:**

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id to the content |

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

An object with the following keys and their values:

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

An object with the following keys and their values:

| Name | Type | Attributes | Default | Description |
| --- | --- | --- | --- | --- |
| key | string |  |  | Path or id to the parent content |
| start | number | <optional> | 0 | Start index (used for paging) |
| count | number | <optional> | 10 | Number of contents to fetch |
| sort | string | <optional> |  | Sorting expression |

Returns

**object** : An array of child items (as JSON) fetched from the repository

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

XP 7.2.0

Returns the list of content items that are outbound dependencies of specified content.

**Parameters:**

An object with the following properties:

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

An object with the following keys and their values:

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
    inheritsPermissions: false,
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

An object with the following keys and their values:

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

An object with the following keys and their values:

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

| Name | Type | Description |
| --- | --- | --- |
| name | string | Name of the content type, as 'app:name' (e.g. 'com.enonic.myapp:article') |

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
    displayName: "Person",
    description: "Person content type",
    superType: "base:structured",
    abstract: false,
    final: true,
    allowChildContent: true,
    displayNameExpression: "${name}",
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
contentTypes.forEach(({displayName,name,superType}) => {
    if (superType === 'base:structured') {
        log.info('%s - %s', name, displayName);
    }
});
```

### modify

Modifies a content

> **Note:** Properties starting with `_` may not be modified using this function. To rename or move a content (ie to change the `_name` property), use the [move function](#move) instead.

**Parameters:**

An object with the following keys and their values:

| Name | Type | Attributes | Default | Description |
| --- | --- | --- | --- | --- |
| key | string |  |  | Path or id to the content |
| editor | function |  |  | Editor callback function |
| requireValid | boolean | <optional> | true | The content has to be valid (according to the content type) to be updated. If `requireValid=true` and the content is not strictly valid, an error will be thrown |

Returns

**object** : Modified content as JSON

Examples

```typescript
import {modify} from '/lib/xp/content';

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

// Modify content by path
const result = modify({
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

### move

Renames a content or moves it to a new path

**Parameters:**

An object with the following keys and their values:

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

An object with the following keys and their values:

| Name | Type | Attributes | Default | Description |
| --- | --- | --- | --- | --- |
| keys | string[] |  |  | List of all content keys(path or id) that should be published |
| schedule | [ScheduleParams](#scheduleparams) | <optional> |  | Schedule publishing |
| excludeChildrenIds | string[] | <optional> |  | List of content keys whose descendants should be excluded from publishing |
| includeDependencies | boolean | <optional> | true | Whether all related content should be included when publishing content |
| sourceBranch | string |  |  | *Not in use from* XP 7.12.0. The branch where the content to be published is stored. |
| targetBranch | string |  |  | *Not in use since* XP 7.12.0. The branch to which the content should be published. Technically, publishing is just a move from one branch to another, and publishing user content from master to draft is therefore also valid usage of this function, which may be practical if user input to a web-page is stored on master |

#### ScheduleParams

| Name | Type | Attributes | Description |
| --- | --- | --- | --- |
| from | string | <optional> | Time from which the content is considered published. Defaults to the time of publishing |
| to | string | <optional> | Time until which the content is considered published |

Returns

**object** : Status of the publish operation as JSON

Examples

```typescript
import {publish} from '/lib/xp/content';

// Publish content by path or key
const result = publish({
    keys: ['/mysite/somepage', '79e21db0-5b43-45ce-b58c-6e1c420b22bd'],
    sourceBranch: 'draft',
    targetBranch: 'master',
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

An object with the following keys and their values:

| Name | Type | Attributes | Default | Description |
| --- | --- | --- | --- | --- |
| start | number | <optional> | 0 | Start index (used for paging) |
| count | number | <optional> | 10 | Number of contents to fetch |
| query | string/object |  |  | Query string or [DSL](/docs/platform/7.x/storage/dsl) expression |
| filters | object | <optional> |  | Filters to apply to query result |
| sort | string/object | <optional> |  | Sorting string or [DSL](/docs/platform/7.x/storage/dsl#sort) expression |
| aggregations | string | <optional> |  | Aggregations expression |
| contentTypes | string[] | <optional> |  | Content types to filter on |

Returns

**object** : Result of query

XP 7.5.0 If `sort` was specified, results will contain system meta properties `_sort` and `_score: null`, otherwise `_score` will have a relevant value.

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

An object with the following keys and their values:

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

XP 7.6.0

Resets custom inheritance flags of a content item. For an item that was inherited from a parent content project/layer this action will reset specified changes made inside a specified layer.

**Parameters:**

An object with the following keys and their values:

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

XP 7.8.0

Restores a content from the archive

**Parameters:**

An object with the following keys and their values:

| Name | Type | Description |
| --- | --- | --- |
| content | string | Path or id of the content to be restored |
| path | string | Path of parent for restored content |

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

### setPermissions

Sets permissions on a content

**Parameters:**

An object with the following keys and their values:

| Name | Type | Attributes | Description |
| --- | --- | --- | --- |
| key | string |  | Path or id of the content |
| inheritPermissions | boolean | <optional> | Set to `true` if the content must inherit permissions. Default to false |
| overwriteChildPermissions | boolean | <optional> | Set to true to overwrite child permissions. Default to false |
| permissions | [PermissionsParams](#permissionsparams)[] | <optional> | Array of permissions |

#### PermissionsParams

| Name | Type | Description |
| --- | --- | --- |
| principal | string | Principal key |
| allow | string[] | Allowed permissions |
| deny | string[] | Denied permissions |

Returns

**boolean** : `true` if successful, `false` otherwise

Examples

```typescript
import {setPermissions} from '/lib/xp/content';

// Set permissions for content by path.
const flag = setPermissions({
    key: '/features/js-libraries/mycontent',
    inheritPermissions: false,
    overwriteChildPermissions: true,
    permissions: [{
        principal: 'user:system:anonymous',
        allow: ['READ'],
        deny: ['DELETE']
    }]
});

if (flag) {
    log.info('Permissions set');
} else {
    log.info('Content not found');
}
```

### unpublish

Unpublishes content that had been published to the master branch

**Parameters:**

An object with the following keys and their values:

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

## Objects

### ContentType

Fields

| Name | Type | Attributes | Description |
| --- | --- | --- | --- |
| name | string |  | Name of the content type |
| displayName | string |  | Display name of the content type |
| description | string |  | Description of the content type |
| superType | string |  | Name of the super type, or null if it has no super type |
| abstract | boolean |  | Whether or not content of this type may be instantiated |
| final | boolean |  | Whether or not it may be used as super type of other content types |
| allowChildContent | boolean |  | Whether or not allow creating child items on content of this type |
| displayNameExpression | string |  | ES6 string template for generating the content name based on values in the content form |
| icon | [IconType](#icontype) | <optional> | Icon of the content type |
| form | object[] |  | Form schema represented as an array of form items: Input, ItemSet, Layout, OptionSet |

### IconType

Fields

| Name | Type | Attributes | Description |
| --- | --- | --- | --- |
| data | object | <optional> | Stream with the binary data for the icon |
| mimeType | string | <optional> | Mime type of the icon image |
| modifiedTime | string | <optional> | Modified time of the icon. May be used for caching |
