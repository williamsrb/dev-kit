<!-- src:https://developer.enonic.com/docs/content-studio/5.x/navigator generated:2026-07-29T03:47:31Z format:llm-dense content-studio-5.x -->
#DOC docs/content-studio/5.x/navigator.md

# Content navigator

Content navigator is the default page of **Content Studio**. It consists of the [action toolbar](#toolbar) on top, followed by the main view divided in four vertical responsive panels, from left to right: [Search panel](#search_panel), [Content tree](#content_tree), [Preview panel](#preview_panel) and [Context panel](#context_panel).

## Toolbar

The Menu Toolbar in the Content Navigator has buttons for the following actions:

- **New:** Opens the [New content](docs/content-studio/5.x/actions.md#new) dialog for creating new content;

- **Edit:** Opens the content for [editing](docs/content-studio/5.x/editor.md) in a new browser tab;

- **Archive:** Opens the [Archive item(s)](docs/content-studio/5.x/actions.md#archive) dialog for the selected content.

- **Duplicate:** Makes a [copy](docs/content-studio/5.x/actions.md#duplicate) of the selected content;

- **Move:** Opens the [Move item(s) with children](docs/content-studio/5.x/actions.md#move) dialog;

- **Sort:** Opens the [Sort items](docs/content-studio/5.x/actions.md#sort) dialog where child items of the selected content can be sorted;

Dropdown action button on the right of the Toolbar is context-dependent and will have a different main action preset, depending on if a content is selected, what state content has, current user permissions etc.:

- If selected content is not published: **Publish** (opens the [Publishing wizard](docs/content-studio/5.x/actions.md#publishing_wizard) dialog)

- If selected content is published: **Unpublish** (opens the [Unpublish Wizard](docs/content-studio/5.x/actions.md#unpublish) dialog for taking the content offline)

- If selected content is published but has child items that are not published: **Publish Tree** (opens the [Publishing wizard](docs/content-studio/5.x/actions.md#publishing_wizard)) dialog with selected content and all descendants

- If selected content has workflow state "In progress": **Mark as Ready** (to mark selected content item(s) as ready for publishing)

- If selected content is not published and current user doesn’t have publishing permissions: **Request Publishing:** (opens the [Unpublish Wizard](docs/content-studio/5.x/actions.md#unpublish) dialog for taking the item offline)

- If no content is selected: **Create Issue**, opens the [New Task](docs/content-studio/5.x/issues.md#create_a_task) dialog

These options are also available in the context menu that appears when right-clicking on a content item in the tree grid panel.

### Accessibility

The toolbar supports keyboard navigation. When focused, the toolbar itself and its every interactable child element will be highlighted with a border. When the toolbar is focused, the following keys can be used to navigate and activate its elements: * Arrow buttons to navigate between action buttons * `Enter` or `Space` to activate the focused action button or expand the dropdown

Additionally, some action buttons have keyboard shortcuts that are displayed on cursor hover.

## Search Panel

The search panel can be toggled with the icon at the far left of the menu bar. It contains a free-text search field and several parameters to filter the content list by:

- Free-text search (by content Id, display name or path)

- [Content Types](docs/content-studio/5.x/content-types.md)

- Last modification date

- Last modifier

- Owner

- Language

> **Tip:** Search results can at any time (except for when there are no hits) be exported to a CSV file using the download icon underneath the free-text search field. The file will contain basic meta fields (id, display-name, path etc.), not custom input fields from the content type schema.

Search results are instantly updated in the tree grid as search parameters are changed. Children of matching content items will also be displayed in the tree grid but won’t be visible unless the parent node is expanded.

The number of hits will appear below the search field, along with a `Clear` button that will reset the filter.

Each content type that has at least one matching content will appear in the [Content Types](docs/content-studio/5.x/content-types.md) filter list with the number of matches in brackets `()`. Checking the box next to a content type will hide the results that do not match that type. Multiple content types can be selected. By default, only the 5 most popular content types will be shown, followed by "Show more" link to expand the entire list.

The **Last Modified** list works in a similar manner. It is used to limit results to content that has been modified in the last month, week, day or hour. This list may not appear if other search parameters have limited results to content that was modified more than a month ago.

Filter aggregations for **Last modified by** and **Owner** are dropdowns with the list of users who last modified content or are content owners. To simplify search for the current user, there’s **Me** checkbox in both aggregations which serves as an alias for the current user. Selected users will be displayed as checkboxes above the dropdown.

> **Tip:** Search results remain in the tree grid when the search panel is collapsed. Don’t forget to clear the search when you are done with your search.

## Content Tree

Content items can be organized and stored in a tree hierarchy with child items collapsed under parent content. Parent content will have a gray triangle to the left of the content icon that can be clicked to expand or collapse the list of its children.

The content tree can also be navigated with the keyboard arrow keys.

Content tree has its own toolbar with an icon to refresh the content list and a checkbox to select or deselect all the content items in the grid.

Information in the content list is displayed in four columns. The number of columns may vary, depending on the content tree width.

- The first column contains a content type icon, a display name and a path. A gray expand icon will appear to the left of the icon if the content has child content.

- The second column shows the icon, representing the current [sorting](docs/content-studio/5.x/actions.md#sort) order of the content’s children.

- The third column shows status of the content: `New`, `Published`, `Unpublished` or `Modified`.

- The fourth column shows the date when content was last modified.

Checkboxes to the left of each content in the tree can be used to select more than one content. Group actions available in the menu bar will be performed on all the selected content. Some actions can only be performed on one content at a time.

Double-click on a content item will open it for [edit](docs/content-studio/5.x/editor.md) in a new browser tab.

Right-click on a content item will expand its context menu.

## Preview panel

A preview of the selected content appears inside a panel to the right of the Content Tree. The preview is dynamic, so clicking a link will navigate you to the target page, both inside the preview panel and the Content Tree.

Toolbar of the preview panel contains the following:

- Current status of the selected content item (f.ex. `New`, `Published`, `Unpublished`, `Modified`). For items that have been published and then modified there will be an icon () to compare current version with the published version.

- Emulator dropdown to emulate screen resolutions of various device types (monitor, tablet, mobile) for the preview.

- Current preview mode. The default mode is "**Automatic**" which will automatically find and use the first mode that supports preview of the current content. You can explicitly select a mode from the dropdown list. Select "**Media**" to preview media content (if supported by browsers), "**Enonic rendering**" to use Enonic’s Site Engine and "JSON" to display current content in JSON format.

> **Note:** Even though any content can be displayed in the JSON format, this mode is not used as a fallback in the "Automatic" mode.

- button will open the content preview in a new browser tab. Note that the currently selected preview mode will be used in the new tab.

If currently selected content cannot be rendered by any of the available preview modes, the preview panel will display an error message.

> **Note:** Only the **Draft** version of content is visible in the preview panel.

## Context panel

Context panel for the selected content can be expanded with the icon next to the Action menu button in the top-right corner.

This panel displays the list of contextual widgets which can be used to work with the selected content. Widgets are applications that expand the functionality of Content Studio. There are several built-in widgets (described in the [Widgets section](docs/content-studio/5.x/widgets.md)), the rest is coming from installed applications.

In the screenshot above, the top 3 widgets are built into Content Studio and the bottom 2 are coming from two external applications installed in the system.
