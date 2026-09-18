<!-- src:https://developer.enonic.com/docs/content-studio/stable/content-types/shortcut generated:2026-07-29T03:46:58Z format:llm-dense content-studio-stable -->
#DOC docs/content-studio/stable/content-types/shortcut.md

# Shortcut

A **Shortcut** is a content item whose only purpose is to redirect to another path. It is the intended way to expose a short, stable URL that points at deeply-nested content, or to alias one content item under another path.

## Fields

- **Target** (required) — the content item or URL to redirect to.

- **Parameters** (optional) — a list of name-value pairs appended to the redirect URL as query-string parameters.

## Behaviour

Shortcuts cannot use page templates — the redirect fires even if a matching template exists. The shortcut’s target is resolved at request time; if the target is missing or unpublished, the redirect will produce a broken response.
