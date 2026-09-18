<!-- src:https://developer.enonic.com/docs/content-studio/stable/workbench/navigator generated:2026-07-29T03:46:58Z format:llm-dense content-studio-stable -->
#DOC docs/content-studio/stable/workbench/navigator.md

# Navigator

The **Navigator** is the default menuitem of Content Studio — what you see when you open the application. It is built around the project’s content tree and the actions you can perform on it.

The view consists of the [action toolbar](#toolbar) on top, followed by the main view divided in four vertical responsive panels, from left to right: [Search panel](#search_panel), [Content tree](#content_tree), [Preview panel](docs/content-studio/stable/workbench/preview.md) and [Context panel](docs/content-studio/stable/workbench/contextpanel.md).

## Toolbar

The toolbar in the Navigator has buttons for the following actions:

- **New:** Opens the [New content](docs/content-studio/stable/actions/new.md) dialog for creating new content;

- **Edit:** Opens the content for [editing](docs/content-studio/stable/actions/edit.md) in a new browser tab;

- **Delete:** Opens the [Delete](docs/content-studio/stable/actions/delete.md) dialog for the selected content. Deleted items are moved to the [Archive](docs/content-studio/stable/workbench/archive.md).

- **Duplicate:** Makes a [copy](docs/content-studio/stable/actions/duplicate.md) of the selected content;

- **Move:** Opens the [Move item(s) with children](docs/content-studio/stable/actions/move.md) dialog;

- **Sort:** Opens the [Sort items](docs/content-studio/stable/actions/sort.md) dialog where child items of the selected content can be sorted;

The dropdown action button on the right of the toolbar is context-dependent and will have a different main action preset, depending on if a content is selected, what state content has, current user permissions etc.:

- If selected content is not published: **Publish** (opens the [Publishing wizard](docs/content-studio/stable/actions/publish.md#publishing_wizard) dialog)

- If selected content is published: **Unpublish** (opens the [Unpublish Wizard](docs/content-studio/stable/actions/unpublish.md) dialog for taking the content offline)

- If selected content is published but has child items that are not published: **Publish Tree** (opens the [Publishing wizard](docs/content-studio/stable/actions/publish.md#publish_tree) dialog with selected content and all descendants)

- If selected content has workflow state "In progress": **Mark as Ready** (to mark selected content item(s) as ready for publishing)

- If selected content is not published and current user doesn’t have publishing permissions: **Request Publishing** (opens the [Publish Request](docs/content-studio/stable/issues/publish-request.md) wizard)

- If no content is selected: **Create Task** opens the [New Task](docs/content-studio/stable/issues.md#create_a_task) dialog

These options are also available in the context menu that appears when right-clicking on a content item in the tree grid panel.

### Accessibility

The toolbar supports keyboard navigation. When focused, the toolbar itself and its every interactable child element will be highlighted with a border. When the toolbar is focused, the following keys can be used to navigate and activate its elements:

- Arrow buttons to navigate between action buttons

- `Enter` or `Space` to activate the focused action button or expand the dropdown

Additionally, some action buttons have keyboard shortcuts that are displayed on cursor hover.

## Search panel

The search panel can be toggled with the icon at the far left of the menu bar. It contains a free-text search field and several parameters to filter the content list by:

- Free-text search (by content Id, display name or path)

- Content type

- Last modification date

- Last modifier

- Owner

- Language

> **Tip:** Search results can at any time (except for when there are no hits) be exported to a CSV file using the download icon underneath the free-text search field. The file will contain basic meta fields (id, display-name, path etc.), not custom input fields from the content type schema.

Search results are instantly updated in the tree grid as search parameters are changed. Children of matching content items will also be displayed in the tree grid but won’t be visible unless the parent node is expanded.

The number of hits will appear below the search field, along with a `Clear` button that will reset the filter.

Each content type that has at least one matching content will appear in the **Content type** filter list with the number of matches in brackets `()`. Checking the box next to a content type will hide the results that do not match that type. Multiple content types can be selected. By default, only the 5 most popular content types will be shown, followed by "Show more" link to expand the entire list.

The **Last Modified** list works in a similar manner. It is used to limit results to content that has been modified in the last month, week, day or hour. This list may not appear if other search parameters have limited results to content that was modified more than a month ago.

Filter aggregations for **Last modified by** and **Owner** are dropdowns with the list of users who last modified content or are content owners. To simplify search for the current user, there’s **Me** checkbox in both aggregations which serves as an alias for the current user. Selected users will be displayed as checkboxes above the dropdown.

> **Tip:** Search results remain in the tree grid when the search panel is collapsed. Don’t forget to clear the search when you are done with your search.

## Content tree

Content items can be organized and stored in a tree hierarchy with child items collapsed under parent content. Parent content will have a gray triangle to the left of the content icon that can be clicked to expand or collapse the list of its children.

The content tree can also be navigated with the keyboard arrow keys.

Content tree has its own toolbar with an icon to refresh the content list and a checkbox to select or deselect all the content items in the grid.

Information in the content list is displayed in four columns. The number of columns may vary, depending on the content tree width.

- The first column contains a content type icon, a display name and a path. A gray expand icon will appear to the left of the icon if the content has child content.

- The second column shows the icon, representing the current [sorting](docs/content-studio/stable/actions/sort.md) order of the content’s children.

- The third column shows status of the content: `New`, `Published`, `Unpublished` or `Modified`.

- The fourth column shows the date when content was last modified.

Checkboxes to the left of each content in the tree can be used to select more than one content. Group actions available in the menu bar will be performed on all the selected content. Some actions can only be performed on one content at a time.

Double-click on a content item will open it for [edit](docs/content-studio/stable/editor.md) in a new browser tab.

Right-click on a content item will expand its context menu.

## Preview and Context panels

The two right-hand panels — **Preview** and **Context panel** — are shared with the [Editor](docs/content-studio/stable/editor.md) and documented on their own pages: [Preview](docs/content-studio/stable/workbench/preview.md) and [Context panel](docs/content-studio/stable/workbench/contextpanel.md).
