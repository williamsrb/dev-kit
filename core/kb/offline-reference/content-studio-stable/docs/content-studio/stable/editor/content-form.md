<!-- src:https://developer.enonic.com/docs/content-studio/stable/editor/content-form generated:2026-07-29T03:46:58Z format:llm-dense content-studio-stable -->
#DOC docs/content-studio/stable/editor/content-form.md

# Content Form

This panel appears on the left side of the page after content is created or while being edited. It is here the form appears in which content data is entered. The structure and fields in the form are determined by the **content type** which is defined in the application code. The content editor panel can be collapsed to give the page editor more room by clicking the arrow icon on the top right of the panel.

## Header

The top of the content form has the content type icon, the Display Name, and the content path name. The default icon can be replaced with a thumbnail image by clicking on it and uploading an image file. When the Display Name is being changed, the path name will change accordingly, to a URL-friendly version. It is also possible for the Display Name to be generated dynamically from the values of other form fields, if the application’s content type defines a Display Name expression.

> **Note:** Value of the Path field must be unique and will be validated against existing content every time the field is changed.

> **Tip:** For a new content, Path will be auto-generated as you type into the Display Name field. International letters will be automatically transliterated into their english equivalents. It’s possible to turn off this behaviour in the Content Studio’s [config file](docs/content-studio/stable/config.md#disable_path_name_transliteration).

After a content has been published, the Path field gets locked and user must click the path to rename content in the dedicated modal dialog. These precautions aim to prevent accidental breaking of external hard-coded links.

## Form

Underneath the header is the toolbar with clickable navigation steps that correspond to different sections of the content form. The first one is always the content type name followed by optional **X-data** steps (if any). Clicking on an item in the toolbar will scroll the content form down to the corresponding section.

Clicking the "

> **Note:** For fragments and page templates the Page Components tree will be inside the first form step.
