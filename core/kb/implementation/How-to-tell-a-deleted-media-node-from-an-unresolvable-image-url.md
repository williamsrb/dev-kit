---
id: how-to-tell-a-deleted-media-node-from-an-unresolvable-image-url
when_skills: [run-plan, validate-impl]
inputs: [lib/modules/extension/portal myImageUrl]
outputs: [a guard that omits a dead URL without killing the attachment fallback]
read: section
prose: caveman-lite
---

# How to tell a deleted media node from an unresolvable image URL

**Scope:** client XP apps whose `lib/modules/extension/portal` exposes `myImageUrl`
(jotron, acme). Verified on jotron `lib/modules/extension/portal/index.ts:144-184`,
JOT-270 round 2.

## The gotcha

`myImageUrl` returns `false` from **three** different branches:

- no `imageId` passed;
- `get({ key: imageId })` is null — the media node is **deleted**;
- `imageUrl()` produced no string, or one containing `error/404` / `error/500` — the
  common case being a **vector** the image service will not render.

Its success branch always carries a `link`, so there is no "resolved but linkless" result.
Any review comment or plan that says "`false` means the media node is gone" is therefore
half right, and the obvious guard is wrong:

```ts
// WRONG: also fires for the vector case, killing the attachment fallback
if (image === false) return undefined
return (image && image.link) || myAttachmentURL(logoId) || undefined
```

A deleted node must omit the URL (an attachment URL for it 404s). A vector must still fall
through to `myAttachmentURL`, which is the only reason that fallback exists.

## Procedure

Gate on the thing that actually differs — whether the content node exists — before calling
`myImageUrl`:

```ts
if (!getContent({ key: logoId })) return undefined

const image = myImageUrl(logoId, 'width(600)')
return (image && image.link) || myAttachmentURL(logoId) || undefined
```

`get as getContent` from `/lib/xp/content` is usually already imported in these modules.

## Pitfalls

- Do not add a `try/catch` around it; `get` returns null rather than throwing for a missing
  key.
- The extra `get` is a second node read on a path that already reads the node inside
  `myImageUrl`. Acceptable for a once-per-page call (a header logo); reconsider inside a
  list loop.
- Related: `How-to-pick-a-myImageUrl-scale-param.md` — the `scaleParam` union rejects
  `square(w,h)`.
