<!-- src:https://developer.enonic.com/docs/cms/stable/apis/attachment generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/apis/attachment.md

# Attachment API

The Attachment API provides direct access to Content Attachments without processing.

## Location

By default, the API is available at:

```
8080:/api/media:attachment/
```

The exact public URL can differ per environment based on virtual host configuration, which is commonly used to expose the API on a friendlier path — for example `[https://api.example.com/graphql](https://api.example.com/graphql)`.

## Attachment URL structure

The attachment URL consists of the following components:

- Base

`:8080/api/media:attachment/`

- Media Locator with an optional (branch)

`(:)/`

`master` is the default branch (referring to published content). Specifying `master` branch is an error - to avoid cache pollution. Since we only have `master` and `draft` there are only two options: `//` and `/:draft/`

- (Optional) fingerprint

`:` - the fingerprint of the attachment.

If fingerprint is not supplied the response will not contain "immutable" `Cache-Control` header.

- Attachment name

`` is not the Content Name, but the name of the attachment stored within the content.

- (Optional) download parameter

`?download` - the response will set the `Content-Disposition` header, if specified.

Example of an attachment URL on the root of a live site behind a [Virtual Host](docs/platform/stable/config/vhosts.md#virtual-hosts):

```
/_/media:attachment/media-project/c82262a6-77d6-4276-b0e7-fe82f4eb57b8:ec25d6e4126c7064f82aaab8b34693fc/attachment.png?download
```

## Media scope

You may limit which projects and branches are accessible by mounting the API in a Virtual Host context.

Use the setting `endpoint.media.scope = , ` in the [Virtual Host Context](docs/platform/stable/config/vhosts.md#virtual-host-context).

## Response

A successful response streams the attachment binary in the body. The API accepts `GET`, `HEAD`, and `OPTIONS` — any other method returns `405 Method Not Allowed`.

### Headers

Content-Type

Set to the attachment’s MIME type. SVG attachments (`.svg`, `.svgz`) are always served as `image/svg+xml`.

Content-Length

Size of the attarchment, in bytes.

Accept-Ranges

Always set to `bytes`, signalling that the API supports partial downloads via the `Range` request header (see [Range requests](#range-requests)).

Cache-Control

Set only when the URL includes a fingerprint that matches the current binary hash. The value is taken from `media.public.cacheControl` for content publicly readable on the `master` branch, and from `media.private.cacheControl` otherwise. Requests without a fingerprint, or with a stale one, receive no `Cache-Control` header and are therefore treated as non-cacheable by intermediaries.

Content-Security-Policy

Set when configured via the `media.contentSecurityPolicy` portal config option. SVG responses use the separate `media.contentSecurityPolicy.svg` setting, which lets you tighten policy specifically for the inline-script-capable image format.

Content-Disposition

Set to `attachment; filename=""` only when the `?download` query parameter is present, prompting browsers to save the file rather than render it inline.

Content-Encoding

The platform-wide gzip filter is disabled by default (`gzip.enabled = false`), so attachments are served uncompressed unless an operator opts in. This default keeps the API edge-cache and CDN friendly — so that services like Fastly can perform their own conditional compression and chunking without conflicting with an upstream `Content-Encoding`.

### Range requests

The API honours `Range: bytes=…​` request headers, allowing clients to resume interrupted downloads or stream large media progressively.

- Single range → `206 Partial Content` with `Content-Range: bytes -/` and a body containing the requested slice.

- Multiple ranges → `206 Partial Content` with `Content-Type: multipart/byteranges; boundary=…​`; the body is a multipart payload with each range as a separate part.

- Out-of-bounds range → `416 Requested Range Not Satisfiable` with `Content-Range: bytes */` and an empty body.

Example: fetch the first 1 MB of an attachment

```http
GET /api/media:attachment/myproject/abc123:fp/large-video.mp4 HTTP/1.1
Range: bytes=0-1048575
```

```http
HTTP/1.1 206 Partial Content
Content-Type: video/mp4
Content-Length: 1048576
Content-Range: bytes 0-1048575/52428800
Accept-Ranges: bytes
```

## Configuration

The Attachment API is driven by two configuration files in your XP installation.

CMS configuration

Controls media-serving behaviour: `media.public.cacheControl`, `media.private.cacheControl`, `media.contentSecurityPolicy`, `media.contentSecurityPolicy.svg`, and the per-virtual-host `endpoint.media.scope` attribute.

System configuration

Controls platform-wide HTTP behaviour, including the Jetty gzip filter (`gzip.enabled`, `gzip.minSize`) referenced in the headers section above.
