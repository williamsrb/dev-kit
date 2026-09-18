<!-- src:https://developer.enonic.com/docs/content-studio/stable/actions generated:2026-07-29T03:46:58Z format:llm-dense content-studio-stable -->
#DOC docs/content-studio/stable/actions.md

# Actions

Actions are the verbs editors use day-to-day on content — creating, editing, moving, publishing, and so on. They are available from three consistent places:

- The **toolbar** at the top of the [Navigator](docs/content-studio/stable/workbench/navigator.md) and the [Editor](docs/content-studio/stable/editor.md).

- The **context menu** that appears when right-clicking an item in the Navigator.

- **Keyboard shortcuts** — see the [Keyboard shortcuts](docs/content-studio/stable/keyboard-shortcuts.md) reference for the full list.

Whether a given action is shown, enabled, or disabled depends on two things: the selection (what content is currently selected) and the user’s [permissions](docs/content-studio/stable/workbench/permissions.md) on that content.

## In this chapter

New

Create a new content item via the **New Content** dialog — either by picking a content type or by uploading a file.

Edit

Open one or more selected items in the Content Editor.

Duplicate

Make a copy of the selected content (optionally including its children).

Move

Relocate content to a different parent in the tree, preserving children and permissions.

Sort

Configure how child items of the selected content are ordered in the Navigator and on rendered pages.

Preview

Open the rendered page for a site or page content in a new browser tab.

Publish

Push content from the *draft* branch to *master* so it becomes available online. Covers the publishing wizard, scheduled publishing, and publishing with dependencies.

Unpublish

Remove published content from *master*. Descendants are unpublished along with the selection.

Delete

Remove content from the active tree. Deleted items are moved to the [Archive](docs/content-studio/stable/workbench/archive.md), preserving descendants and version history so they can be restored.

## Related reference

**Mark as ready** and the publishing state machine are documented under [Workflow](docs/content-studio/stable/workflow.md). **Request publishing** (the review/approval handoff variant of Publish) is a kind of issue — see [Publish request](docs/content-studio/stable/issues/publish-request.md). **Permanent delete** (from the archive) and restoring archived items are on the [Archive](docs/content-studio/stable/workbench/archive.md) page. The **Create task** entry point is documented under [Issues](docs/content-studio/stable/issues.md).
