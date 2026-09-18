<!-- src:https://developer.enonic.com/docs/content-studio/stable/ai generated:2026-07-29T03:46:58Z format:llm-dense content-studio-stable -->
#DOC docs/content-studio/stable/ai.md

# Juke - AI Content Operator

> **Note:** **Content Studio+ feature.** The AI Assistant is part of the [Content Studio+](https://market.enonic.com/vendors/enonic/content-studio-plus) subscription. It also requires the [Juke AI Content Operator](https://market.enonic.com/vendors/enonic/ai-content-operator) application.

Juke AI brings artificial intelligence to Content Studio. Over time, Juke will evolve to help out with a range of daily content management chores.

> **Note:** Juke AI is in early development stages. Errors may occur, and responses will improve over time. See [Known issues](#known_issues) for more details.

## Interface

To launch the Juke chat interface, you may either click the Juke icon in the Content Editor’s toolbar, or the Juke icon appearing next to an active form field.

This will open a modal chat interface where you can communicate with Juke.

## Field context

It may often be useful to focus Juke’s attention on a specific field. Clicking or focusing on a supported form field will instantly trigger Juke’s attention by setting the field in the chat context.

To clear the context, simply click the `x` to the right.

> **Note:** Juke is currently limited to work with TextLine, TextArea and HtmlArea fields in the main content type form. More will follow soon.

## Mentions

Fields may also be mentioned directly in the chat. Pressing `@` inside the chat’s input will list all available fields in the scope of the current context. Select a field from the list to make it a part of your prompt.

> **Note:** If no context is set, you may mention fields at the root level of your content

**Sample prompts:**

- Expand the list in `@Article body` from 3 to 5 items and turn it into a numbered list

- Create `@Display Name` based on `@Article body`

## Retry

If you are not satisfied with the response provided by Juke or the request fails, use the «retry» icon to make Juke reprocess the instruction.

## Insert

Juke may provide field value responses. Simply click the `Insert` icon next to value in order to update the form directly.

If Juke provides multiple field values, you may use the `Insert all` icon to insert all values into the form with a single click.

Finally, the `Copy to buffer` icon will copy the text to your clipboard, allowing you to paste it manually later.

## Variants

On demand, Juke may provide multiple variants for a single field. Use the arrow icons next to the response which you can use to navigate through the suggestions, and insert values as required.

Sample prompts:

- Give 3 variants of `@Teaser` and `@Display Name`

- Make 2 suggestions for `@Abstract`

## General instructions

You may provide a standard prompt for Juke. These instructions may be specified at a project or site level.

For instance, you may want Juke to use a consistent tone of voice or provide other relevant details about the content you are working on. This helps Juke produce more relevant responses every time.

By adding the `Juke AI Content Operator` application to your project or site, you may provide `custom instructions` as desired

> **Note:** Working with application settings requires the [Owner](docs/content-studio/stable/projects.md#project-roles) project role or higher.

## Known issues

Known limitations in current version

- Not optimized for general chat

- Only works with text-based fields

- Single Item-/OptionSet occurences may not be a context

- Only works with fields in the main content type form

- Only availabe in "Edit" context

- Initial greeting is hardcoded (not AI generated)

- [AI localization](docs/content-studio/stable/projects/layers.md) can’t be invoked from chat
