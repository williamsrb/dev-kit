<!-- src:https://developer.enonic.com/docs/content-studio/5.x/issues generated:2026-07-29T03:47:31Z format:llm-dense content-studio-5.x -->
#DOC docs/content-studio/5.x/issues.md

# Issues

There are two types of issues in Content Studio: tasks and publish requests.

**Tasks** are used to assign general tasks, like spellcheck an article, or add new content to a site. **Publish Requests** are typically used when you have made some changes to a content which you want someone else to approve and publish.

## Issues list

"**Open Issues"** button in the Content Studio header opens the modal dialog with the list of issues (both tasks and publish requests). If there are no active issues, the button will say "**No Open Issues**".

The list by default shows all active issues. Use Open/Closed toggler to switch between Open and Closed issues.

> **Tip:** Tasks and Publish Requests are using different icons to make it easier to distinguish them.

By using the filter above the list you can narrow down the list to issues assigned to current user, created by current user, only Publish Requests or only task. By default, if you have any active issues assigned to you, the filter will be preset to show you only them.

To create a new task, click the [`New Task…`](#_create-a-task) button.

Clicking on an issue from the list will open the [issue details dialog](#_update-an-issue).

## Tasks

### Create a task

To create a new task, click "Create Task…​" button in the Content Studio toolbar.

If some content items are selected in the Content Navigator, you can expand the toolbar menu and select either "Create Task…​" or "Request Publishing…​". In this case selected items will be automatically added to a new issue you are about to create.

You can assign multiple users to work on an issue, using the **Assignees** selector, but you can’t assign yourself.

To add specific content to an issue, click on the `Add items` button. The **Items** selector will appear.

You can read about creating a new Publishing Request in a dedicated [workflow section](docs/content-studio/5.x/workflow.md#publish_request).

### Update an issue

To modify an issue, click on it in the [**Issue list**](#_issues-list) dialog. It will open the dialog with three tabs.

Click the title to edit it, then click anywhere outside of the text field to save the changes.

Under the title you will see the status of the current issue. It can be `Open` or `Close`. Click this button to change the issue status. Altenatively, you can use `Close Task` button (for an active issue) or `Reopen Task` (for a closed issue).

#### Comments

The first tab shows comments on the current issue. Comments can be added by clicking the `Comment` button.

> **Tip:** When you are in the comment field, "Close Task" button changes to "Comment & Close Task" to comment and close with one click.

To **edit** or **delete** a comment, click on the **kebab** icon to the right of the comment, that will show the menu with those two options. The number next to the tab title shows the total number of comments.

#### Items

On the second tab, you can update the list of content items in this issue. There can be multiple items or no content at all. Child/dependent items of the selected content can be toggled by clicking on the tree icon next to the content item.

If you are inside a **task** and click the `Publish…​` button, you will be taken to the Publishing Wizard where you can publish items immediately or schedule publishing. For a *Publish Request* you can publish items or schedule publish directly from this dialog.

The number next to the tab title shows the total number of content items inside the issue.

#### Assignees

On the third tab, assignees can be added and removed from this issue. The number next to the tab title shows the total number of assignees.
