<!-- src:https://developer.enonic.com/docs/content-studio/stable/workbench/contextpanel/versions generated:2026-07-29T03:46:58Z format:llm-dense content-studio-stable -->
#DOC docs/content-studio/stable/workbench/contextpanel/versions.md

# Versions

Every save, publish, unpublish, rename, or permissions change on a content item creates a new **version**. The full history is available via the **Version history** widget in the [Context panel](docs/content-studio/stable/workbench/contextpanel.md): you can see every change, compare any two versions, and revert to an older one.

The current workflow status is shown in the widget header. Versions created by publish and unpublish events are listed alongside content versions so the full audit trail is visible in one place.

## Reverting to a version

Click a version box to expand it, then click **Revert**. The current (active) version cannot be reverted to itself, so it does not expand. Publish and unpublish markers are also non-expandable.

> **Note:** Some versions cannot be reverted — typically those created by permissions updates, renames, or moves. The widget disables the action for these.

## Comparing versions

Click the icon on any version to open the **Compare versions** dialog. The two dropdowns at the top select the pair of versions being compared: the left one is *older*, the right one *newer*.

By default the dialog shows only the differences between the two versions. Toggle **Show entire content** to see the full content JSON side-by-side.

Both dropdowns have aliases at the top of the list — *previous*, *next*, *published*, *current* — so you can compare against those without scrolling through the full version list.

The kebab menu on the right of each dropdown has one option, **Revert**, which reverts to the version currently selected in that dropdown.
