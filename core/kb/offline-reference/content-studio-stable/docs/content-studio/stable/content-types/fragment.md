<!-- src:https://developer.enonic.com/docs/content-studio/stable/content-types/fragment generated:2026-07-29T03:46:58Z format:llm-dense content-studio-stable -->
#DOC docs/content-studio/stable/content-types/fragment.md

# Fragment

The **Fragment** content type is a reusable page component saved as its own content item.

## Introduction

Parts and Layouts placed directly on a page are configured independently on every page that uses them, a Fragment is configured *once* — editing the fragment updates every page that references it.

Fragments live in the content tree like any other content item, with their own path, status, permissions, and version history.

## Editing a fragment

In the content form, a single part or layout appears at root of the component tree. Layout fragments may contain additional components, just like in a normal page structure. The components can be edited in place. Once updated, any page using the fragment will instantly reflect the changes in preview, and on the live site after publishing.

TODO: Screenshot of fragment content form, showing a part or layout at the root of the component tree, with the edit-in-place tools visible.

## Creating, inserting, detaching

Fragments are created indirectly from existing pages, and placed on pages either by direct insertion or by reference. The full workflow — save-as-fragment, insert, detach — is documented under the Page editor:

- [Page editor — Fragment](docs/content-studio/stable/editor/page-editor.md#_fragment)
