<!-- src:https://developer.enonic.com/docs/cms/stable/schemas/forms generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/schemas/forms.md

# Forms

Forms are central to content modeling in Enonic.

## Concept

Schemas define the forms that can be seen and edited through an administrative interface, typically [Content Studio](https://developer.enonic.com/docs/content-studio).

More importantly, schemas also have a back-end equivalent that validates content, and can be used programmatically. Central parts of the Headless API are automatically generated from the schemas and in particular the form definitions.

All forms are essentially compositions of various [Form items](docs/cms/stable/schemas/form-items.md).

Once a form is populated and submitted, the end-result will be a property structure that matches 1-1 with the form definition. The property structure can then be persisted directly into the XP repository.

## Usage

Forms are declared statically in YAML, using a format that looks like this:

```yaml
form:
  - type: "TextLine"
    name: "firstname"
    label: "First Name"
  - type: "TextLine"
    name: "lastname"
    label: "Last Name"
```

The form implementation controls how the data is actually persisted. The persisted output from the above form might look something like this:

```JSON
{
  firstname: "Tom",
  lastname: "Cat"
}
```

## Beyond CMS

Enonic XP re-uses the form concept in other contexts than the CMS. For instance, identity providers and tasks also use schemas for their configuration. In these cases the form output will not be persisted as content, but rather stored in the respective context (e.g. identity provider configuration). However, the same form definition approach is used, and the same validation rules apply.

> **Note:** Only a generic subset of form items are supported in these contexts.
