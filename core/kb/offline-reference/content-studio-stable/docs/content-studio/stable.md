<!-- src:https://developer.enonic.com/docs/content-studio/stable generated:2026-07-29T03:46:58Z format:llm-dense content-studio-stable -->
#DOC docs/content-studio/stable.md

# Content Studio 6 documentation - WIP

Content Studio is Enonic XP’s content-management UI — the editor-facing application for creating, organising, and publishing content.

> **Important:** **Work in progress** We are still working to complete the documentation. Expect some outdated screenshots until we finish this work.

> **Tip:** A collection of short videos demonstrating Content Studio’s features and capabilities is available on the [Enonic site](https://www.enonic.com/resources/content-studio-videos).

**For content modelling** and schema references, go to the [Enonic CMS docs](https://developer.enonic.com/docs/cms).

## Installation

Content Studio is a standalone Enonic XP application that can be installed from [Enonic Market](https://market.enonic.com/vendors/enonic/content-studio).

## User interface

The [Workbench](docs/content-studio/stable/workbench.md) is the application shell: a project bar on top, a menu bar on the left, and a main panel filling the rest. The default menuitem is the [Navigator](docs/content-studio/stable/workbench/navigator.md) — the content tree, search, and per-content actions.

Autoring happesn in the [Content Editor](docs/content-studio/stable/editor.md), which launches in a separate browser tab (Google Docs style) and provides a consistent interface for editing and previewing.

## Concepts

A few recurring concepts surface everywhere in the UI — in dialogs, widgets, toolbars, and URLs.

### Projects and layers

Content lives in [projects](docs/content-studio/stable/projects.md). Each project has a repository with its own content tree, optional applications, and settings. [Layers](docs/content-studio/stable/projects/layers.md) inherit content for reuse or adaptation for other markets or languages.

### Content items and content types

A **content item** is a single piece of content — an article, image, page, or site. Every item has an identity (path, display name, id), a type, a set of field values, and a small envelope of metadata (security, schedule, workflow state).

A **content type** is the schema that defines an item’s fields. Most are defined in application code; a handful ship with XP and have special behaviour:

- **Folder** — a grouping container with no data fields beyond display name and path. See [Folder](docs/content-studio/stable/content-types/folder.md).

- **Shortcut** — a path that redirects to another content item. See [Shortcut](docs/content-studio/stable/content-types/shortcut.md).

- **Site** — the root of a website. Carries installed applications and gets a **Templates** folder as its first child. See [Site](docs/content-studio/stable/content-types/site.md).

- **Page template** — a reusable page definition. See [Page template](docs/content-studio/stable/content-types/page-template.md).

- **Media** — image, video, audio, and other binary uploads. See [Media](docs/content-studio/stable/content-types/media.md).

- **Image** — backed by an image file, with cropping and focal-point tools. See [Image](docs/content-studio/stable/content-types/image.md).

- **Unstructured** — formless content used by applications to store free-form data. See [Unstructured](docs/content-studio/stable/content-types/unstructured.md).

- **Fragment** — a reusable page component stored as a content item; edits propagate everywhere it’s referenced. See [Fragment](docs/content-studio/stable/content-types/fragment.md).

### Pages and rendering

Page rendering is driven by three collaborating concepts: the content item, the **page template** that describes how to render it, and the **page controller** (from an installed application) that supplies the HTML skeleton. Page building happens in the [Page editor](docs/content-studio/stable/editor/page-editor.md).

### Draft, master, and publishing

Content is always edited in the **draft** branch. Publishing copies the active draft version into the **master** branch, from which it becomes available to public consumers of the API.

**Workflow state** is the signal between editors that a draft is ready to publish — *In progress*, *Ready for publishing*, *Publish request*, *Published*, *Unpublished*. See [Workflow](docs/content-studio/stable/workflow.md) for the state machine and [Publish](docs/content-studio/stable/actions/publish.md) for the flow.

### Versions

Every save, publish, unpublish, rename, or permissions change creates a new **version**. Versions can be compared and reverted from the Version history widget — see [Versions](docs/content-studio/stable/workbench/contextpanel/versions.md).

### Dependencies

Content items reference each other — pages embed images, shortcuts target content, text fields link to other items. **Dependencies** are tracked in both directions (inbound: who uses this; outbound: what does this use). Publishing, archiving, and unpublishing all check dependencies — see [Dependencies](docs/content-studio/stable/workbench/contextpanel/dependencies.md).

### Permissions

Each content item has its own security settings: a list of **principals** (users, groups, roles) and the **permission flags** they have on that item (*Read*, *Create*, *Modify*, *Delete*, *Publish*, *Read/Write permissions*). Permissions are inherited from parent content by default and can be overridden per-item. See [Permissions](docs/content-studio/stable/workbench/permissions.md).

### Archive

Deleting content is destructive. **Archiving** is the non-destructive alternative — items are moved to a separate archive storage where they can be browsed, restored, or permanently deleted later. See [Archive](docs/content-studio/stable/workbench/archive.md).

### Applications and extensions

An **application** is an installable unit of XP code that can contribute content types, page controllers, parts, layouts, translations, and UI widgets. Applications are attached to a site via its Applications field; some (like Juke and Content Studio+) contribute UI across all sites.

**Extensions** are typically small UI surfaces contributed by an application. The main host is the [Context panel](docs/content-studio/stable/workbench/contextpanel.md); applications can also contribute [preview modes](docs/content-studio/stable/workbench/preview.md) and [menuitems](docs/content-studio/stable/workbench.md).

### Issues and publish requests

**Issues** are lightweight work items used to coordinate between editors — either a **task** (e.g. "spellcheck this article") or a **publish request** (review-and-publish handoff for users without publish permission, or for an approval flow). See [Issues](docs/content-studio/stable/issues.md) and [Publish request](docs/content-studio/stable/issues/publish-request.md).

## Content Studio+

Content Studio itself is free and open source. An Enonic subscription unlocks **Content Studio+**, a companion application distributed on [Enonic Market](https://market.enonic.com/vendors/enonic/content-studio-plus) that adds advanced editorial capabilities:

- [Archive browser](docs/content-studio/stable/workbench/archive.md) — the dedicated **Archive** menuitem for browsing, restoring, and permanently deleting archived content.

- [Content Variants](docs/content-studio/stable/workbench/contextpanel/variants.md) — create and manage variant copies of a content item for A/B testing.

- [AI translation](docs/content-studio/stable/projects/layers.md#ai_translation) — automatic translation of inherited content when localizing in a layer.

- [Layers widget](docs/content-studio/stable/projects/layers.md#layers_panel) — see the status of a content item across every layer in the system.

Without a valid license the Content Studio+ application can still be installed, but its UI contributions remain inactive. Pages that document a CS+ feature carry a **Content Studio+ feature** admonition at the top.

## Artificial Intelligence

Enonic offers a growing suite of AI-powered features to assist editors in their work. These features are available as for subscription customers under the [Juke AI](docs/content-studio/stable/ai.md) brand, and can be installed from [Enonic Market](https://market.enonic.com/vendors/enonic/ai-content-operator).

## Browser support

Content Studio works in all modern browsers. We are explicitly testing and supporting the latest versions of Google Chrome, Apple Safari, Mozilla Firefox, and Microsoft Edge.

## Release notes

Curious about what is new in this version? Check out the [release notes](docs/content-studio/stable/release.md).
