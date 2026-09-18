<!-- src:https://developer.enonic.com/docs/content-studio/stable/content-types generated:2026-07-29T03:46:58Z format:llm-dense content-studio-stable -->
#DOC docs/content-studio/stable/content-types.md

# Built-in and custom Content Types

Every content item in Enonic XP has a content type — it defines the item’s form and behavior

## Overview

Content types come from two sources: a set of **built-in** types that ship with Enonic XP, and **custom** types defined by the applications available in your project.

Custom types simply render the form their application defines. The built-in types, however, have special behaviour and dedicated tooling in Content Studio — those are documented in this chapter:

- [Folder](docs/content-studio/stable/content-types/folder.md) — grouping container with no data fields.

- [Shortcut](docs/content-studio/stable/content-types/shortcut.md) — redirect to another path.

- [Site](docs/content-studio/stable/content-types/site.md) — the root of a website; carries installed applications.

- [Page template](docs/content-studio/stable/content-types/page-template.md) — reusable page definition pairing a page controller with one or more content types.

- [Media](docs/content-studio/stable/content-types/media.md) — images, video, audio, documents, and other binary uploads.

- [Image](docs/content-studio/stable/content-types/image.md) — image-specific tools (cropping, focal point).

- [Fragment](docs/content-studio/stable/content-types/fragment.md) — reusable page component stored as a content item; edits propagate everywhere referenced.

- [Unstructured](docs/content-studio/stable/content-types/unstructured.md) — formless content used by applications to store free-form data.

> **Tip:** For defining your own content types and content modelling in general, see the [Enonic CMS docs](https://developer.enonic.com/docs/cms/stable/content/content-types).
