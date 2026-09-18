<!-- src:https://developer.enonic.com/docs/code/stable/libraries/lib-portal generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries/lib-portal.md

# Portal library

API to access functions related to rendering.

## Usage

```groovy
dependencies {
  include xplibs.portal
}
```

```typescript
import portalLib from '/lib/xp/portal';
```

## Functions

### apiUrl

Generates a URL pointing to a [Universal API](docs/code/stable/web/apis.md). Picks the right URL form based on the calling context — a service-point under the active service when called from a site, webapp, or admin tool, and `/api/` otherwise.

Parameters

`apiUrl()` takes a single `ApiUrlParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| api | string | Descriptor key in `<app>:<api>` form. |
| type | string | **Optional.** URL type. Either `server` (server-relative), `absolute`, or `websocket`. Defaults to `server`. |
| path | string \| string[] | **Optional.** Path appended after the API segment. Accepts a string or a string array. |
| params | object | **Optional.** Custom query parameters to append to the URL. |
| baseUrl | string | **Optional.** Override the resolved base URL. |

Returns

**string** : The generated URL.

Example

```typescript
import {apiUrl} from '/lib/xp/portal';

const url = apiUrl({
  api: 'com.example.myapp:myapi',
  path: '/items',
  params: {
    id: '42'
  }
});
```

### assetUrl

`assetUrl` is deprecated and will be removed in future versions. [`lib-asset`](https://developer.enonic.com/docs/lib-asset) and [`lib-static`](https://developer.enonic.com/docs/lib-static) are introduced as a replacement.

Generates URL to a static file.

Parameters

`assetUrl()` takes a single `AssetUrlParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| path | string | Path to the asset. |
| application | string | **Optional.** Other application to reference to. Defaults to current application. |
| type | string | **Optional.** URL type. Either `server` (server-relative URL) or `absolute`. Default is `server`. |
| params | object | **Optional.** Custom query parameters to append to the URL. |

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

`attachmentUrl()` takes a single `AttachmentUrlParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| id | string | **Optional.** Id of the content with the attachment. |
| path | string | **Optional.** Path to the content with the attachment. |
| name | string | **Optional.** Unique name of the attachment. |
| label | string | **Optional.** Label of the attachment. Default is `source`. |
| download | boolean | **Optional.** Set to `true` if the disposition header should be set to attachment. Default is `false`. |
| type | string | **Optional.** URL type. Either `server` (server-relative URL) or `absolute`. Default is `server`. |
| project | string | **Optional.** Name of the project. |
| branch | string | **Optional.** Name of the branch. |
| baseUrl | string | **Optional.** Custom baseUrl. |
| params | object | **Optional.** Custom query parameters to append to the URL. |

Returns

**string** : The generated URL.

Example

```typescript
import {attachmentUrl} from '/lib/xp/portal';

const url = attachmentUrl({
  id: '1234',
  download: true
});
```

### baseUrl

Generates a base URL.

Parameters

`baseUrl()` takes a single `BaseUrlParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| type | string | **Optional.** URL type. Either `server` (server-relative URL) or `absolute` or `websocket`. Default is `server`. |
| id | string | **Optional.** ID of the content. |
| path | string | **Optional.** Path to the content. |
| project | string | **Optional.** Name of the project to use for resolving the URL. |
| branch | string | **Optional.** Name of the branch to use for resolving the URL. |

Returns

**string** : The generated URL.

Example

```typescript
import {baseUrl} from '/lib/xp/portal';

const url = baseUrl({
  type: 'server',
  path: '/path',
  project: 'explicit-project',
  branch: 'explicit-branch'
});
```

### componentUrl

Generates URL to a page component.

Parameters

`componentUrl()` takes a single `ComponentUrlParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| id | string | **Optional.** Id to the page. |
| path | string | **Optional.** Path to the page. |
| component | string | **Optional.** Path to the component. If not set, the current path is set. |
| type | string | **Optional.** URL type. Either `server` (server-relative URL) or `absolute`. Default is `server`. |
| params | object | **Optional.** Custom query parameters to append to the URL. |

Returns

**string** : The generated URL.

Example

```typescript
import {componentUrl} from '/lib/xp/portal';

const url = componentUrl({
  component: 'main/0'
});
```

### getComponent

Returns the component in the current execution context. Meant to be called from a layout or part. Takes no arguments.

Returns

*object* : (>) The current component, or `null` if there is no component in the current context.

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

Returns the content in the current execution context. Meant to be called from a page, layout, or part. Takes no arguments.

Returns

*object* : (>) The current content, or `null` if there is no content in the current context.

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

Returns the key of ID provider in the current execution context. Takes no arguments.

Returns

**string|null** : The current ID provider key, or `null` if no ID provider is bound to the current context.

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

Returns a JSON containing multipart items. If the request is not multipart, an empty object is returned. Takes no arguments.

Returns

*object* : (>) The multipart form items.

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

Returns a JSON containing a named multipart item. If the item does not exist, it returns `null`.

Parameters

`getMultipartItem()` takes the `name` of the multipart item (string) and an optional zero-based `index` (number) — specify the index when several items share the same name.

Returns

*object* : (>) The named multipart form item, or `null` if it does not exist.

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

Returns a data stream for a named multipart item. If the item does not exist, it returns `null`.

Parameters

`getMultipartStream()` takes the `name` of the multipart item (string) and an optional zero-based `index` (number) — specify the index when several items share the same name.

Returns

*object* : (>) Stream of multipart item data, or `null` if the item does not exist.

Example

```typescript
import {getMultipartStream} from '/lib/xp/portal';

const stream1 = getMultipartStream('item2');
const stream2 = getMultipartStream('item2', 1);
```

### getMultipartText

Returns the multipart item data as text. If the item does not exist, it returns `null`.

Parameters

`getMultipartText()` takes the `name` of the multipart item (string) and an optional zero-based `index` (number) — specify the index when several items share the same name.

Returns

**string|null** : Text for multipart item data, or `null` if the item does not exist.

Example

```typescript
import {getMultipartText} from '/lib/xp/portal';

const text = getMultipartText('item1');
```

### getSite

Returns the parent site of the content in the current execution context. Meant to be called from a page, layout, or part. Takes no arguments.

Returns

*object* : (>) The current site, or `null` if the content has no parent site.

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

Returns the configuration of the parent site for the content in the current execution context. Meant to be called from a page, layout, or part. Takes no arguments.

Returns

**object|null** : The site configuration for the current application, or `null` if the content has no parent site.

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

`idProviderUrl()` takes a single, optional `IdProviderUrlParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| idProvider | string | **Optional.** Key of an ID provider. If idProvider is not set, then the id provider corresponding to the current execution context will be used. |
| type | string | **Optional.** URL type. Either `server` (server-relative URL) or `absolute`. Default is `server`. |
| params | object | **Optional.** Custom query parameters to append to the URL. |

Returns

**string** : The generated URL.

### imagePlaceholder

Generates URL of an image placeholder with a specified size.

Parameters

`imagePlaceholder()` takes a single `ImagePlaceholderParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| width | number | **Optional.** Width of the image in pixels. |
| height | number | **Optional.** Height of the image in pixels. |

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

`imageUrl()` takes a single `ImageUrlParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| id | string | **Optional.** ID of the image content. Either `id` or `path` is required. |
| path | string | **Optional.** Path to the image. If `id` is specified, this parameter is not used. |
| scale | string | Options are `width(px)`, `height(px)`, `block(width,height)`, `square(px)`, `max(px)`, `wide(width,height)` and `full`. |
| quality | number | **Optional.** Quality for JPEG images, ranges from 0 (max compression) to 100 (min compression). Default is `85`. |
| background | string | **Optional.** Background color. |
| format | string | **Optional.** Format of the image. |
| filter | string | **Optional.** A number of filters are available to alter the image appearance, for example, blur(3), grayscale(), rounded(5), etc. |
| type | string | **Optional.** URL type. Either `server` (server-relative URL) or `absolute`. Default is `server`. |
| project | string | **Optional.** Name of the project. |
| branch | string | **Optional.** Name of the branch. |
| baseUrl | string | **Optional.** Custom baseUrl. |
| params | object | **Optional.** Custom query parameters to append to the URL. |

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

`loginUrl()` takes a single, optional `LoginUrlParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| idProvider | string | **Optional.** Id provider key. If idProvider is not set, then the id provider corresponding to the current execution context will be used. |
| redirect | string | **Optional.** The URL to redirect to after the login. |
| type | string | **Optional.** URL type. Either `server` (server-relative URL) or `absolute`. Default is `server`. |
| params | object | **Optional.** Custom query parameters to append to the URL. |

Returns

**string** : The generated URL.

### logoutUrl

Generates URL to the logout endpoint of ID provider in the current context.

Parameters

`logoutUrl()` takes a single, optional `LogoutUrlParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| redirect | string | **Optional.** The URL to redirect to after the logout. |
| type | string | **Optional.** URL type. Either `server` (server-relative URL) or `absolute`. Default is `server`. |
| params | object | **Optional.** Custom query parameters to append to the URL. |

Returns

**string** : The generated URL.

### pageUrl

Generates URL to a content page.

Parameters

`pageUrl()` takes a single `PageUrlParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| id | string | **Optional.** Id of a content. If id is set, then path is not used. |
| path | string | **Optional.** Path of a content. Relative paths are resolved based on the current context. |
| type | string | **Optional.** URL type. Either `server` (server-relative URL) or `absolute` or `websocket`. Default is `server`. |
| project | string | **Optional.** Project of the context. |
| branch | string | **Optional.** Branch of the project for context. |
| params | object | **Optional.** Custom query parameters to append to the URL. |

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

`processHtml()` takes a single `ProcessHtmlParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| value | string | Html value string to process. |
| type | string | **Optional.** URL type. Either `server` (server-relative URL) or `absolute`. Default is `server`. |
| imageWidths | number[] | **Optional.** A comma-separated list of image widths. If this parameter is provided, all `<img>` tags will have an additional `srcset` attribute with image URLs generated for specified widths. |
| imageSizes | string | **Optional.** Specifies the width for an image depending on browser dimensions. The value has the following format: `(media-condition) width`. Multiple sizes are comma-separated. |

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

`sanitizeHtml()` takes the `html` string value to process.

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

> **Warning:** HTTP services are deprecated in XP 8 in favor of [Universal APIs](docs/code/stable/web/apis.md). Use [apiUrl](#apiurl) for new code; `serviceUrl()` is retained for backward compatibility with legacy services in `src/main/resources/services/`.

Generates URL to a service.

Parameters

`serviceUrl()` takes a single `ServiceUrlParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| service | string | Name of the service. |
| application | string | **Optional.** Other application to reference to. Default is current application. |
| type | string | **Optional.** URL type. Either `server` (server-relative URL) or `absolute` or `websocket`. Default is `server`. |
| params | object | **Optional.** Custom query parameters to append to the URL. |

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

`url()` takes a single `UrlParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| path | string \| string[] | Path to the resource. If a string is provided, it is treated as a full path. If an array of strings is provided, each element is treated as a path segment and will be joined using `/`. |
| type | string | **Optional.** URL type. Either `server` (server-relative URL) or `absolute` or `websocket`. Default is `server`. |
| params | object | **Optional.** Custom query parameters to append to the URL. |

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

## Type Definitions

### Site

A site is a specialized [`Content`](docs/code/stable/fundamentals/types.md#content) of type `portal:site`. In addition to the standard content properties, its `data` carries the site’s app configurations.

| Name | Type | Description |
| --- | --- | --- |
| description | string | **Optional.** Site description. |
| siteConfig | [SiteConfig](#site-config) \| [SiteConfig](#site-config)[] | Configuration for one or more applications enabled on the site. A single object when one application is configured, otherwise an array. |

### SiteConfig

Configuration entry for a single application enabled on a site.

| Name | Type | Description |
| --- | --- | --- |
| applicationKey | string | Key of the application this configuration applies to. |
| config | object | The application’s site configuration, shaped by its site descriptor form. |

### MultipartForm

A JSON object keyed by item name, where each value is a [MultipartItem](#multipart-item) or an array of them when several items share the same name.

### MultipartItem

| Name | Type | Description |
| --- | --- | --- |
| name | string | Name of the multipart item. |
| fileName | string | Original file name of the uploaded item. |
| contentType | string | MIME content type of the item. |
| size | number | Size of the item in bytes. |
