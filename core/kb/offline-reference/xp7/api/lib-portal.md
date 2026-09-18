<!-- src:https://developer.enonic.com/docs/platform/7.x/api/lib-portal generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC api/lib-portal.md

# Portal API

API to access functions related to rendering.

## Usage

```groovy
dependencies {
  include "com.enonic.xp:lib-portal:${xpVersion}"
}
```

Add the `import` statement to your controller:

```typescript
import portalLib from '/lib/xp/portal';
```

## Functions

### assetUrl

Starting from XP 7.15.0 `assetUrl` is deprecated and will be removed in future versions. [`lib-asset`](https://developer.enonic.com/docs/lib-asset) and [`lib-static`](https://developer.enonic.com/docs/lib-static) are introduced as a replacement.

Generates URL to a static file.

Parameters

| Name | Type | Description |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- |
| params | object | Input parameters as JSON      Properties                    Name | Type | Attributes | Default | Description |
| path | string |  |  | Path to the asset |  |  |
| application | string | <optional> |  | Other application to reference to. Defaults to current application |  |  |
| type | string | <optional> | server | URL type. Either `server` (server-relative URL) or `absolute` |  |  |
| params | object | <optional> |  | Custom parameters to append to the url |  |  |

Returns

**string** : The generated URL.

Example

```typescript
import {assetUrl} from '/lib/xp/portal';

const url = assetUrl({
  path: 'styles/main.css'
});
```

### attachmentUrl

Generates URL to an attachment.

If `name` is provided, XP will try to find an attachment by the unique name and give an exception if it’s not found. If `name` is empty but `label` is provided, XP will try to find an attachment with the provided label (will return the first one if several were found, or give an exception if none were found). If both `name` and `label` are empty, XP will generate attachment url only for a binary content with an attachment.

Parameters

| Name | Type | Description |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- |
| params | object | Input parameters as JSON      Properties                    Name | Type | Attributes | Default | Description |
| id | string | <optional> |  | Id of the content with the attachment. |  |  |
| path | string | <optional> |  | Path to the content with the attachment. |  |  |
| name | string | <optional> |  | Unique name of the attachment. |  |  |
| label | string | <optional> | source | Label of the attachment. |  |  |
| download | boolean | <optional> | false | Set to `true` if the disposition header should be set to attachment. |  |  |
| type | string | <optional> | server | URL type. Either `server` (server-relative URL) or `absolute`. |  |  |
| params | object | <optional> |  | Custom parameters to append to the url. |  |  |

Returns

**string** : The generated URL.

Example

Obtains list of active tasks:

```typescript
import {attachmentUrl} from '/lib/xp/portal';

const url = attachmentUrl({
  id: '1234',
  download: true
});
```

### componentUrl

Generates URL to a page component.

Parameters

| Name | Type | Description |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- |
| params | object | Input parameters as JSON      Properties                    Name | Type | Attributes | Default | Description |
| id | string | <optional> |  | Id to the page. |  |  |
| path | string | <optional> |  | Path to the page. |  |  |
| component | string | <optional> |  | Path to the component. If not set, the current path is set. |  |  |
| type | string | <optional> | server | URL type. Either `server` (server-relative URL) or `absolute`. |  |  |
| params | object | <optional> |  | Custom parameters to append to the url. |  |  |

Returns

**string** : The generated URL.

Example

Obtains list of active tasks:

```typescript
import {componentUrl} from '/lib/xp/portal';

const url = componentUrl({
  component: 'main/0'
});
```

Return value:

```typescript
const expected = 'ComponentUrlParams{type=server, params={}, component=main/0}'
```

### getComponent

Returns component in the current execution context. It is meant to be called from a layout or a part controller.

Returns

**object** : The current component as JSON.

Example

Returns component in the current context:

```typescript
import {getComponent} from '/lib/xp/portal';

const result = getComponent();
log.info('Current component name = %s', result.name);
```

Return value:

```typescript
const expected = {
  path: "/main/0",
  type: "layout",
  descriptor: "myapplication:mylayout",
  config: {
    a: "1"
  },
  regions: {
    bottom: {
      components: [
        {
          path: "/main/0/bottom/0",
          type: "part",
          descriptor: "myapplication:mypart",
          config: {
            a: "1"
          }
        }
      ],
      name: "bottom"
    }
  }
};
```

### getContent

Returns content in the current execution context. It is meant to be called from a page, a layout or a part controller.

Returns

**object** : The current content as JSON.

Example

Get content and log the result:

```typescript
import {getContent} from '/lib/xp/portal';

const result = getContent();
log.info('Current content path = %s', result._path);
```

Return value:

```typescript
const expected = {
  _id: "123456",
  _name: "mycontent",
  _path: "/a/b/mycontent",
  creator: "user:system:admin",
  modifier: "user:system:admin",
  createdTime: "1970-01-01T00:00:00Z",
  modifiedTime: "1970-01-01T00:00:00Z",
  type: "base:unstructured",
  displayName: "My Content",
  hasChildren: false,
  language: "en",
  valid: false,
  data: {
    a: "1"
  },
  x: {},
  page: {},
  attachments: {},
  publish: {}
};
```

### getIdProviderKey

Returns the key of ID provider in the current execution context.

Returns

**object** : The current ID provider as JSON.

Example

Returns the current ID provider:

```typescript
import {getIdProviderKey} from '/lib/xp/portal';

const idProviderKey = getIdProviderKey();

if (idProviderKey) {
    log.info('Id provider key: %s', idProviderKey);
}
```

Return value:

```typescript
const expected = "myidprovider";
```

### getMultipartForm

Returns a JSON containing multipart items. If not a multipart request, then this function returns `undefined`.

Returns

**object** : The multipart form items.

Example

Get the form and log the result:

```typescript
import {getMultipartForm} from '/lib/xp/portal';

const result = getMultipartForm();
log.info('Multipart form %s', result);
```

Return value:

```typescript
const expected = {
  item1: {
    name: "item1",
    fileName: "item1.jpg",
    contentType: "image/png",
    size: 10
  },
  item2: [
    {
      name: "item2",
      fileName: "image1.png",
      contentType: "image/png",
      size: 123
    },
    {
      name: "item2",
      fileName: "image2.jpg",
      contentType: "image/jpeg",
      size: 456
    }
  ]
};
```

### getMultipartItem

Returns a JSON containing a named multipart item. If the item does not exist, it returns `undefined`.

Parameters

| Name | Type | Attributes | Description |
| --- | --- | --- | --- |
| name | string |  | Name of the multipart item |
| index | number | <optional> | Optional zero-based index. It should be specified if there are multiple items with the same name |

Returns

**object** : The named multipart form item.

Example

Get item and log the result:

```typescript
import {getMultipartItem} from '/lib/xp/portal';

const result = getMultipartItem('item1');
log.info('Multipart item %s', result);
```

Return value:

```typescript
const expected = {
  name: "item1",
  fileName: "item1.jpg",
  contentType: "image/png",
  size: 10
};
```

### getMultipartStream

Returns a data stream for a named multipart item.

Parameters

| Name | Type | Attributes | Description |
| --- | --- | --- | --- |
| name | string |  | Name of the multipart item |
| index | number | <optional> | Optional zero-based index. It should be specified if there are multiple items with the same name |

Returns

**object** : Stream of multipart item data.

Example

```typescript
import {getMultipartStream} from '/lib/xp/portal';

const stream1 = getMultipartStream('item2');
const stream2 = getMultipartStream('item2', 1);
```

### getMultipartText

Returns the multipart item data as text.

Parameters

| Name | Type | Attributes | Description |
| --- | --- | --- | --- |
| name | string |  | Name of the multipart item |
| index | number | <optional> | Optional zero-based index. It should be specified if there are multiple items with the same name |

Returns

**string** : Text for multipart item data.

Example

```typescript
import {getMultipartText} from '/lib/xp/portal';

const text = getMultipartText('item1');
```

### getSite

Returns the parent site of a content in the current execution context. It is meant to be called from a page, a layout or a part controller.

Returns

**object** : The current site as JSON.

Example

Get site and log the result:

```typescript
import {getSite} from '/lib/xp/portal';

const result = getSite();
log.info('Current site name = %s', result._name);
```

Return value:

```typescript
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

Returns configuration of the parent site for a content in the current execution context. It is meant to be called from a page, a layout or a part controller.

Returns

**object** : The site configuration for current application as JSON.

Example

Get site and log the result:

```typescript
import {getSiteConfig} from '/lib/xp/portal';

const result = getSiteConfig();
log.info('Field value for the current site config = %s', result.Field);
```

Return value:

```typescript
const expected = {
  Field: 42
};
```

### idProviderUrl

Generates URL to an ID provider.

Parameters

| Name | Type | Attributes | Description |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- |
| params | object | <optional> | Input parameters as JSON      Properties                    Name | Type | Attributes | Default | Description |
| idProvider | string | <optional> |  | Key of an ID provider. If idProvider is not set, then the id provider corresponding to the current execution context will be used. |  |  |  |
| contextPath | string | <optional> | vhost | Context path. Either vhost (using vhost target path) or relative to the current path. |  |  |  |
| type | string | <optional> | server | URL type. Either `server` (server-relative URL) or `absolute`. |  |  |  |
| params | object | <optional> |  | Custom parameters to append to the url. |  |  |  |

Returns

**string** : The generated URL.

### imagePlaceholder

Generates URL of an image placeholder with a specified size.

Parameters

| Name | Type | Description |  |  |
| --- | --- | --- | --- | --- |
| params | object | Input parameters as JSON      Properties                Name | Type | Description |
| width | number | Width of the image in pixels. |  |  |
| height | number | Height of the image in pixels. |  |  |

Returns

**string** : Placeholder image URL.

Example

Obtains image encoded to base64:

```typescript
import {imagePlaceholder} from '/lib/xp/portal';

const url = imagePlaceholder({
  width: 32,
  height: 24
});
```

Return value:

```typescript
const expected = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAYCAYAAACbU/80AAAAGUlEQVR42u3BAQEAAACCIP+vbkhAAQAA7wYMGAAB93LuRQAAAABJRU5ErkJggg==';
```

### imageUrl

Generates URL to an image.

Parameters

| Name | Type | Description |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- |
| params | object | Input parameters as JSON      Properties                    Name | Type | Attributes | Default | Description |
| id | string |  |  | ID of the image content. |  |  |
| path | string |  |  | Path to the image. If id is specified, this parameter is not used. |  |  |
| scale | string |  |  | Required. Options are width(px), height(px), block(width, height) and square(px). |  |  |
| quality | number | <optional> | 85 | Quality for JPEG images, ranges from 0 (max compression) to 100 (min compression). |  |  |
| background | string | <optional> |  | Background color. |  |  |
| format | string | <optional> |  | Format of the image. |  |  |
| filter | string | <optional> |  | A number of filters are available to alter the image appearance, for example, blur(3), grayscale(), rounded(5), etc. |  |  |
| type | string | <optional> | server | URL type. Either `server` (server-relative URL) or `absolute`. |  |  |
| params | object | <optional> |  | Custom parameters to append to the url. |  |  |

Returns

**string** : The generated URL.

Example

Obtains image url:

```typescript
import {imageUrl} from '/lib/xp/portal';

const url = imageUrl({
  id: '1234',
  scale: 'block(1024,768)',
  filter: 'rounded(5);sharpen()'
});
```

### loginUrl

Generates URL to the login endpoint of an ID provider.

Parameters

| Name | Type | Attributes | Description |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- |
| params | object | <optional> | Input parameters as JSON      Properties                    Name | Type | Attributes | Default | Description |
| idProvider | string | <optional> |  | Id provider key. If idProvider is not set, then the id provider corresponding to the current execution context will be used. |  |  |  |
| redirect | string | <optional> |  | The URL to redirect to after the login. |  |  |  |
| contextPath | string | <optional> | vhost | Context path. Either vhost (using vhost target path) or relative to the current path. |  |  |  |
| type | string | <optional> | server | URL type. Either `server` (server-relative URL) or `absolute`. |  |  |  |
| params | object | <optional> |  | Custom parameters to append to the url. |  |  |  |

Returns

**string** : The generated URL.

### logoutUrl

Generates URL to the logout endpoint of ID provider in the current context.

Parameters

| Name | Type | Attributes | Description |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- |
| params | object | <optional> | Input parameters as JSON      Properties                    Name | Type | Attributes | Default | Description |
| redirect | string | <optional> |  | The URL to redirect to after the logout. |  |  |  |
| contextPath | string | <optional> | vhost | Context path. Either vhost (using vhost target path) or relative to the current path. |  |  |  |
| type | string | <optional> | server | URL type. Either `server` (server-relative URL) or `absolute`. |  |  |  |
| params | object | <optional> |  | Custom parameters to append to the url. |  |  |  |

Returns

**string** : The generated URL.

### pageUrl

Generates URL to a content page.

Parameters

| Name | Type | Description |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- |
| params | object | Input parameters as JSON      Properties                    Name | Type | Attributes | Default | Description |
| id | string | <optional> |  | Id of a content. If id is set, then path is not used. |  |  |
| path | string | <optional> |  | Path of a content. Relative paths are resolved based on the current context. |  |  |
| type | string | <optional> | server | URL type. Either `server` (server-relative URL) or `absolute`. |  |  |
| params | object | <optional> |  | Custom parameters to append to the url. |  |  |

Returns

**string** : The generated URL.

Example

Obtains page url:

```typescript
import {pageUrl} from '/lib/xp/portal';

const url = pageUrl({
  path: '/my/page',
  params: {
    a: 1,
    b: [1, 2]
  }
});
```

### processHtml

Resolves internal links to images and internal content items contained in an HTML text and replaces them with correct URLs. It will also process embedded macros.

> **Tip:** When outputting processed HTML in Thymeleaf, use attribute `data-th-utext="${processedHtml}"`.

Parameters

| Name | Type | Description |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- |
| params | object | Input parameters as JSON      Properties                    Name | Type | Attributes | Default | Description |
| value | string |  |  | Html value string to process. |  |  |
| type | string | <optional> | server | URL type. Either `server` (server-relative URL) or `absolute`. |  |  |
| XP 7.7.0 imageWidths | number[] | <optional> |  | A comma-separated list of image widths. If this parameter is provided, all `<img>` tags will have an additional `srcset` attribute with image URLs generated for specified widths. |  |  |
| XP 7.8.0 imageSizes | string | <optional> |  | Specifies the width for an image depending on browser dimensions. The value has the following format: `(media-condition) width`. Multiple sizes are comma-separated. |  |  |

Returns

**string** : The processed HTML.

Example

Process HTML:

```typescript
import {processHtml} from '/lib/xp/portal';

const html = processHtml({
  value: '<a href="content://123" target="">Content</a>' +
         '<a href="media://inline/123" target="">Inline</a>' +
         '<a href="media://download/123" target="">Download</a>' +
         '<img src="image://123"/>',
  imageWidths: [32, 480, 800]
});
```

### sanitizeHtml

Sanitizes an HTML string by stripping all potentially unsafe tags and attributes.

> **Tip:** HTML sanitization can be used to protect against cross-site scripting (XSS) attacks by sanitizing any HTML code submitted by a user.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| html | string | HTML string value to process |

Returns

**string** : The sanitized HTML.

Example

Sanitizes unsafe HTML:

```typescript
import {sanitizeHtml} from '/lib/xp/portal';

const unsafeHtml = '<p><a href="https://example.com/" onclick="stealCookies()">Link</a></p>' +
                 '<iframe src="javascript:alert(\'XSS\');"></iframe>';
const sanitizedHtml = sanitizeHtml(unsafeHtml);
```

Return value:

```typescript
const expected = '<p><a href="https://example.com/">Link</a></p>';
```

### serviceUrl

Generates URL to a service.

Parameters

| Name | Type | Description |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- |
| params | object | Input parameters as JSON      Properties                    Name | Type | Attributes | Default | Description |
| service | string |  |  | Name of the service. |  |  |
| application | string | <optional> |  | Other application to reference to. Default is current application. |  |  |
| type | string | <optional> | server | URL type. Either `server` (server-relative URL) or `absolute` or `websocket. |  |  |
| params | object | <optional> |  | Custom parameters to append to the url. |  |  |

Returns

**string** : The generated URL.

Example

```typescript
import {serviceUrl} from '/lib/xp/portal';

const url = serviceUrl({
  service: 'myservice',
  params: {
    a: 1,
    b: 2
  }
});
```

### url

Generates URL to a resource.

Parameters

| Name | Type | Description |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- |
| params | object | Input parameters as JSON      Properties                    Name | Type | Attributes | Default | Description |
| path | string |  |  | Path of the resource. |  |  |
| type | string | <optional> | server | URL type. Either `server` (server-relative URL) or `absolute` or `websocket`. |  |  |
| params | object | <optional> |  | Custom parameters to append to the url. |  |  |

Returns

**string** : The generated URL.

Example

```typescript
import {url as buildUrl} from '/lib/xp/portal';

const url = buildUrl({
  path: '/site/master/mysite',
  params: {
    a: 1,
    b: 2
  }
});
```
