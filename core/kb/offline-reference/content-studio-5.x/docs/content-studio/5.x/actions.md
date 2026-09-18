<!-- src:https://developer.enonic.com/docs/content-studio/5.x/actions generated:2026-07-29T03:47:31Z format:llm-dense content-studio-5.x -->
#DOC docs/content-studio/5.x/actions.md

# Actions

Content can be created, edited, archived, deleted, duplicated, moved, sorted and published. Depending on permissions, users may perform those actions on selected content items.

## New

The `New` action will launch the **New Content** dialog.

There are three ways to open the **New Content** dialog in Content Studio:

- The first method is with the shortcut — `alt + n`;

- By clicking the `New` button in the toolbar;

- By clicking `New` in the context menu, which is accessible by right-clicking an item.

> **Note:** The **New Content** dialog will use the context of the selected content to create the new item. If no context is set, the item will be created on the root level.

### New by Type

The **New Content** dialog lets you choose from available content types, based on the context of the selected item.

- Select from the list of all content types;

- Select from the "Most Popular" list (most used content types in your current context);

- Select from the "Recently Used" list (based on users recent actions).

> **Tip:** To filter the list of items — simply start typing on your keyboard to filter the list of available content types.

Once a content type is selected, a new item is created, and the content editor is launched in a new tab.

### New by Uploading

Create file-based content aka "media" from the new content dialog by uploading. There are two ways to upload files:

- Click the upload icon placed in the top right of the dialog;

- Drag’n drop — also supports bulk uploading.

> **Note:** When uploading files, the underlying content type is automatically detected from the file type file uploaded.

## Edit

`Edit` action will open the **Content Wizard** for editing selected content items in a new tab. If multiple items are selected, then the action will open a browser tab for each one.

There are four ways to open content for edit in Content Studio:

- The first method is with the shortcut — `⌘ + e` (`ctrl + e` for Windows);

- By clicking the `Edit` button in the toolbar;

- By double-clicking the item in the grid;

- By clicking `Edit` in the context menu, which is accessible by right-clicking an item.

## Archive

`Archive` action will open the **Archive item(s)** dialog for selected content to move it to the "Archive".

There are three ways to open the **Archive item(s)** dialog in Content Studio:

- The first method is with the shortcut — `⌘ + del` (`ctrl + del` for Windows);

- By clicking the `Archive` button in the toolbar;

- By selecting `Archive` from the context menu, which is accessible by right-clicking an item.

> **Tip:** If you want to delete content rather than move it to archive, you can do that by selecting **Delete" from the button dropdown in the *Archive item(s)** dialog.

> **Important:** Online content will instantly go offline after archiving or deleting.

If any of the items in the dialog has an inbound dependency (is referenced by another content), a warning will be shown on top of the dialog and the action button will be disabled. User can either click "Ignore inbound references" link to ignore the warning and proceed with archiving/deletion, or click "Show references" link for every referenced item and remove the references (the dialog will be automatically refreshed).

## Duplicate

The `Duplicate` action will launch the **Duplicate content** dialog for the selected content.

There are two ways to open this dialog in Content Studio:

- By clicking the `Duplicate` button in the toolbar;

- By clicking `Duplicate` in the context menu, which is accessible by right-clicking an item.

In the dialog, you can choose whether child items of selected content(s) should also be duplicated or not by pressing the tree icon to the left of the content. Pressing the "Duplicate" button in the dialog will trigger the duplicate operation which will be visualized by a progress bar if the process is taking more than a few seconds. Duplicates will get a new id and path names will be postfixed with `-copy` or `-copy-*` with a number instead of an asterisk starting with `2` if it is not the first copy.

> **Note:** When the `Duplicate` button is clicked from inside the Content Wizard, only the current item will be selected in the dialog.

## Move

The `Move` action will launch the **Move item(s) with children** dialog for the selected content.

There are several ways to move content inside Content Studio:

- By selecting one or several content items in the Content Navigator and clicking the `Move` button in the toolbar;

- By selecting `Move` in the context menu, which is accessible by right-clicking an item in the Content Navigator;

- By clicking the "Move" button in the toolbar of the Content Wizard (only the current item will be moved then).

This action moves the selected item(s) with all children and current permissions to a different location in the content hierarchy. Type inside the modal dialog’s input to search for a new parent content, or use the dropdown arrow to find a new parent content where the selected item(s) will be moved under.

> **Tip:** There’s a special item at the top of the dropdown’s list called "Project root". Select it if you want to move the selected item(s) to the root of the content project.

> **Note:** Current parent of the selected item and the item itself will be disabled inside the Mode dialog’s dropdown.

Once the items are moved a notification will pop up at the bottom of the page. If the items were moved from the Content Navigator, this notification will contain the new parent’s path which can be clicked to locate and expand the new parent item in the Content Navigator to help the user quickly find the moved item(s) in their new location.

## Sort

The `Sort` action will launch the **Sort items** dialog for the selected content.

There are two ways to open this dialog in Content Studio:

- By clicking the `Sort` button in the toolbar;

- By clicking `Sort` in the context menu, which is accessible by right-clicking an item.

Child items of any content can be sorted in a number of ways through the **Sort items** dialog.

The default sorting is by the **Modified date** in descending order.

You can sort items in ascending or descending order by Modified date, Created date, Display name or Publish date. Children can also be manually sorted by simply dragging them in the **Sort items** dialog.

Once items are sorted, the parent content will have an arrow in the browse view tree grid pointed up or down to denote ascending or descending. If the content is manually sorted, an icon with three horizontal bars will appear.

Clicking the bars or arrow icon will open the **Sort items** dialog.

In the image below, `/Posts/Featured Image` is sorted by Display name in ascending order, `/Posts/Gotham Sure Is A Big Town` is sorted by Published date in ascending order, and `/Posts` has custom sorting.

## Preview

The `Preview` action will open and render a selected Site or Page in the new tab.

There are two ways to open this dialog in Content Studio:

- By clicking the `Preview` button in the toolbar;

- By clicking `Preview` in the context menu, which is accessible by right-clicking an item.

## Publish

Publishing is a simple but important concept for working with content in Enonic XP. The basic concept of publishing is that it makes content available online. Before a content item can be published, it has to be **marked as ready** for publishing.

The `Publish` action will open the **Publishing Wizard** dialog for the selected content.

There are three ways to open the **Publishing Wizard** dialog in Content Studio:

- Via keyboard shortcut — `⌘ + alt + p` (`ctrl + alt + p` for Windows)

- By using the `Publish` button in the toolbar

- By right-clicking an item in the Content Navigator and selecting `Publish` from the context menu

The Publish button in the toolbar has a dropdown menu with various actions for currently selected item(s).

- [**Mark as ready**](docs/content-studio/5.x/workflow.md#ready_for_publishing) (only for content in progress) will mark selected item(s) as ready. This action will automatically open the Publishing dialog.

- **Publish** will open the Publishing dialog for the selected item(s)

- [**Publish Tree**](#_publish-tree) will open the same dialog but will include all the selected items' children and dependencies

- [**Unpublish**](#_unpublish) (available only for published item(s)) will open the **Unpublish** dialog

- [**Request Publishing**](docs/content-studio/5.x/workflow.md#publish_request) (available only for unpublished item(s))

- [**Create Task**](#_create-issue) will open the **New Task** dialog.

> **Note:** Default action of the toolbar button is always the first available action from the dropdown menu.

### Draft and Master branches

Content created in Content Studio will originally be created in the **draft** branch with status `New` and workflow state `In progress`. This content in the **draft** branch can be edited and previewed until it is ready to be `Published`. Every time a content is saved with changes, a new version is created.

When a content is published, the active version is copied from the **draft** branch to the **master** branch. Only content in the **master** branch can be accessed by users outside of Content Studio, subject to the contents security settings.

### Content status

Published content will have the status `Published` while content that has not yet been published will show either as `New` (if it has never been published) or `Unpublished` (if it was published and then unpublished). When changes to a published content are saved, the new version becomes the active version in the `draft` branch, but the active version in the `master` branch remains unchanged. The status of the new active version will be `Modified` and this content will have to be published again for the changes to go online. In other words, each publishing operations overwrites the active version in the `master` branch with the active version from the `draft` branch.

A content can either be archived or instantly deleted in the [**Archive**](#archive) dialog. In both cases the content will be taken offline (deleted from the `master` branch), if it’s currently published. Upon instant deletion the content will be instantly removed from both the `draft` and the `master` branches, making it inaccessible online. Archived items will be moved under the special `/archive` node where they can be restored from.

### Publishing wizard

Content is published through the **Publishing Wizard** dialog. When a content is selected for publishing, its parents and all the related content will be published along with it. For example, in the image below, a content named "*March madness*" was selected for publishing. This post has two related **Category** content items (*/parent* and */parent/first-child-category*) and one related **Author** item (*/authors/michael-lazell*). Therefore, these two categories and the author are automatically included in the list of items to be published, and all the ascendants of the dependent items will also be included. Total number of items that will be published is displayed on the **Publish Now** button.

> **Tip:** The Calendar icon next to the "Publish Now" button enables [Scheduled Publishing](#_scheduled-publishing) of the selected content.

> **Note:** If current user is missing publishing permissions for selected item(s), the "**Publish All**" button will be replaced with "**Request Publishing**" (read more about publish requests [here](docs/content-studio/5.x/workflow.md#publish_request)).

### Dependencies

Child items of the content selected for publishing can be added to the publishing batch by clicking the tree icon to the left of the content.

Optional dependencies & child items can be excluded from the publishing batch using checkboxes in the dependency list. Confirm your changes by clicking the "Apply" button in the toolbar. Sometimes the checkbox is disabled, this means that the item cannot be excluded, either because it’s an inbound dependency required for publishing of the originally selected item(s), or it has its children in the list (and child items cannot be published without publishing all of their ascendants). In the latter case, exclude the children first, apply the changes and then parents will be automatically removed.

> **Tip:** If you want to add back dependent items excluded by mistake, click **Show excluded** link above the list and all excluded items will reappear in the list. Select the items you want to put back, and click "Apply".

> **Tip:** It’s possible to overrule the default behaviour of automatic inclusion of all the dependencies by using the Content Studio’s [config file](docs/content-studio/5.x/config.md#exclude_optional_dependencies). In this special mode only the mandatory dependencies will be auto-included, the optional ones will be auto-excluded and can be included manually.

### Validation

Content Studio has a built-in validation which ensures that items to be published are valid, ready for publishing and are allowed to be published by current user.

If the list of items to be published contains invalid items or items that are still in the "In progress" workflow state or items that current user is not allowed to publish, the warning section will be shown on top of the dialog, displaying all failed validation checks. The "Publish" button will then be disabled and "problematic" items will be shown on top of the list.

User can use links next to each validation check to exclude these items from the publication. All the validation checks will be re-run on every change of the publication contents.

> **Note:** Some items might be required for publication and cannot be excluded (like parent items, dependencies etc).

If all the checks have successfully passed, the "Publish" button will be enabled and the warning section will say that everything is ready for publishing.

> **Tip:** Use "Mark as ready" link up in the status bar to mark all in-progress items as ready for publishing.

### Scheduled publishing

The Calendar icon in the **Publishing Wizard** dialog will open a section on top of the dialog where you can schedule the period of time when the content should be online. "Publish Now" button will then change its label to "Schedule". By default, "Online from" is set to "Now" (content goes online immediately), and only "Online to" needs to be set.

> **Note:** Only offline items can be scheduled for publishing. If the item is already online, the new changes will be published immediately.

### Publishing from the Content Wizard

When the `Publish` button is clicked from inside the Content Wizard, only the currently opened item will be selected in the dialog.

## Unpublish

Currently published content can be taken offline with the "Unpublish" feature. All the content’s descendants will be listed and unpublished along with the selected content. The total number of content items that will be taken offline will appear on the red `Unpublish` button at the bottom of the dialog.

There are two ways to open this dialog in Content Studio:

- By clicking the `Unpublish` option button in the toolbar (it will replace the `Publish` button for the published content, otherwise it can be found in the publish menu dropdown, next to the `Publish` button);

- By selecting `Unpublish` from the context menu, which is accessible by right-clicking an item, where it will replace `Publish` option for the published content.

Unpublishing a published content that is marked for deletion will first take it offline and then delete it.

> **Note:** Just like with deletion, you will be asked to confirm the Unpublish action by entering the total number of items to be unpublished.

If any of the items in the dialog has a **published** inbound dependency (is referenced by another **published** content), a warning will be shown on top of the dialog and the action button will be disabled. User can either click "Ignore inbound references" link to ignore the warning and proceed with unpublishing, or click "Show references" link for every referenced item, remove the references and publish the changes.

## Create Issue

> **Note:** In-depth reference on the issues can be found in the separate [chapter](docs/content-studio/5.x/issues.md).

## Request Publishing

This action will replace "Publish" for a user that doesn’t have sufficient publishing permissions for a content item.

> **Note:** In-depth reference on the publish requests can be found [here](docs/content-studio/5.x/workflow.md#publish_request).
