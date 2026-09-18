<!-- src:https://developer.enonic.com/docs/content-studio/stable/content-types/unstructured generated:2026-07-29T03:46:58Z format:llm-dense content-studio-stable -->
#DOC docs/content-studio/stable/content-types/unstructured.md

# Unstructured

The **Unstructured** content type stores free-form data without a fixed schema. Applications use it for runtime data they need to persist as content — for example, captured form submissions, app-specific state, or anything that doesn’t warrant its own content type.

The data is not editable through Content Studio: only display name, path, settings, and security are exposed in the editor. Application code reads and writes the underlying data through the content APIs.

## When to use it

Unstructured is the right choice when an application needs the standard content envelope (path, permissions, lifecycle, search indexing) but the payload is dynamic or evolving, and defining a fixed content type would be premature or awkward.

For data that has a known shape and is edited by humans, a custom content type is the better choice — see the [CMS content type reference](https://developer.enonic.com/docs/cms/stable/content/content-types).
