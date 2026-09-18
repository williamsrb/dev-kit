<!-- src:https://developer.enonic.com/docs/content-studio/stable/workflow generated:2026-07-29T03:46:58Z format:llm-dense content-studio-stable -->
#DOC docs/content-studio/stable/workflow.md

# Workflow

Workflow is the state machine a content item moves through on its way to being published. The state is shown as an icon next to the content-type icon throughout the UI (a red icon indicates the content is invalid — for example, required fields are missing).

The states:

- **[In progress](#_in_progress)** — default state for a new or modified content item. Cannot be published.

- **[Ready for publishing](#_ready_for_publishing)** — the editor has explicitly flagged the content as done.

- **[Publish request](#_publish_request)** — a review/approval has been requested from another user.

- **[Published](#_published)** — the active version in the `draft` branch matches what is live on `master`.

- **[Unpublished](#_unpublished)** — previously published content that has been taken offline.

Transitions are driven by four actions: **Mark as ready**, **[Publish](docs/content-studio/stable/actions/publish.md)**, **[Unpublish](docs/content-studio/stable/actions/unpublish.md)**, and **[Request publishing](docs/content-studio/stable/issues/publish-request.md)** (documented under Issues because a publish request is an issue type with assignees, comments, and a shared Open-Issues list).

## In progress

The default state of a new content item. Signals that the content is being worked on; it will stay in this state until the editor explicitly marks it as ready, or until a publisher overrides and publishes it directly.

In-progress content is **not eligible for publishing** — this is deliberate, to keep unfinished content from being published by accident. The [Publishing wizard](docs/content-studio/stable/actions/publish.md) will block the batch and highlight the offending items:

The default toolbar action for in-progress content is **Mark as ready**.

> **Note:** A user with publish permission can invoke **Publish…​** directly on in-progress content from the Content Editor — the item is automatically marked as ready first, on the assumption that invoking publish signals the work is finished.

## Ready for publishing

Set by the **Mark as ready** action from the Content Editor or Content Navigator. The yellow `!` icon is replaced with a green `✓`, and the item becomes eligible for publishing.

The default toolbar action changes to **[Publish](docs/content-studio/stable/actions/publish.md)** (if the user has publish permission) or **[Request publishing](docs/content-studio/stable/issues/publish-request.md)** (if not).

> **Tip:** Editors with publish permission may still use **Request publishing** when content needs sign-off or additional input from another user.

Any edit to a **Ready for publishing** item immediately resets it to **In progress** — the editor must mark it ready again once the edits are finished.

## Publish request

Set when another user has been asked to review and publish the item via the **Request publishing** action. The full wizard, the request dialog, and how requests are managed are documented on the [Publish request](docs/content-studio/stable/issues/publish-request.md) page.

## Published

Set when the active version has been pushed from `draft` to `master`. No icon is shown — published is the default, quiet state.

Editing a published item resets the workflow state to **In progress**; the `master` branch is unaffected until the item is published again.

## Unpublished

Set when a previously-published item is removed from `master` via the [Unpublish](docs/content-studio/stable/actions/unpublish.md) action. Unpublishing an item automatically unpublishes all of its descendants.
