<!-- src:https://developer.enonic.com/docs/content-studio/stable/projects generated:2026-07-29T03:46:58Z format:llm-dense content-studio-stable -->
#DOC docs/content-studio/stable/projects.md

# Content Projects

Content Studio allows you to organize your content in multiple independent repositories aka projects.

## What is a project?

Each project provides a dedicated repository for content, with its own access control, project roles, features, and language settings. Content in one project is managed independently of other projects.

Each project’s repository also contains its own *draft* and *master* branches, meaning content is edited and published independently per project — see [Publish](docs/content-studio/stable/actions/publish.md) for how content moves between the branches.

Each project has a unique **identifier**, which is set when the project is created and cannot be changed later.

Privileged users can create and manage projects via [Content Studio settings](docs/content-studio/stable/workbench/settings.md).

> **Note:** Content items cannot be moved or copied between projects. For reusing content across projects, see [content layering](docs/content-studio/stable/projects/layers.md).

## Access mode

A project’s access mode controls the default READ permission for content items inside the project — in practice, whether the role *Everyone* is granted READ access:

- **Public** — the *Everyone* role is granted READ access by default, making published items visible to anyone, including users that are not logged in.

- **Private** — no READ access for *Everyone*. Only principals with [project roles](#project-roles) or administrators can access the content.

- **Custom** — like Private, but READ access is additionally granted to specific principals in the system. This is useful if you want to give users from other projects READ access to content inside this project.

> **Note:** Principals that are given Custom access will be added to a special project role called "*Viewer*".

> **Important:** The access mode only affects **published** content (the *master* branch). Regardless of access mode, the *draft* branch is only accessible to users with a [project role](#project-roles) — a public project never exposes unpublished work. See [Permissions](docs/content-studio/stable/workbench/permissions.md) for the full permission model.

## Project roles

Every project has a fixed set of roles that can be used to assign different levels of permissions inside a project to users or groups. A principal must have at least one of these roles to be able to access the project in Content Studio:

- **Contributor** — has access to the project in Content Studio, but can only view the content inside.

- **Author** — same as **Contributor** + create, modify and delete content. **Author** is not allowed to publish content, create sites or change their configuration.

- **Editor** — same as **Author** + publish content and modify content permissions.

- **Owner** — same as **Editor** + create and configure sites, and modify project settings.

> **Note:** Project roles set the **default** permissions that every new content item in the project inherits. Per-item overrides are managed through the **Edit Permissions** dialog opened from the [Details widget](docs/content-studio/stable/workbench/contextpanel/details.md) in the Context panel. See [Permissions](docs/content-studio/stable/workbench/permissions.md) for the full model.

## Applications

Applications may be assigned to a project. This enables usage of content types and controller mappings defined in the assigned applications when creating or rendering content outside of sites. This is especially useful for management of headless content, as opposed to a site-oriented approach.

Application assignment follows these rules:

- Only applications containing CMS features can be assigned to a project — the application must include a `cms.yaml` descriptor.

- Project applications do not apply to sites or content items within a site. To use an application for the contents of a site, assign it directly to the site.

- A layer always inherits the applications of its parent project. Inherited apps cannot be removed from the layer, but additional apps may be assigned.

## Getting started

A fresh Enonic installation contains no projects, meaning you will have to create a project before you can start authoring.

You should see the following dialog when starting Content Studio for the first time:

Clicking **Start Project wizard** will launch the [project wizard](#project-wizard), which will guide you through the steps of creating a new project.

## Project wizard

New projects are created with the project wizard. It launches from the first-run dialog above, or from the **New** button in the [Settings section](docs/content-studio/stable/workbench/settings.md). You can click the **Previous** button at any time to review or change your choices, and the X icon to exit without creating a project.

- Language and content layering

Optionally select a **parent project** — this makes the new project a [layer](docs/content-studio/stable/projects/layers.md), inheriting content from the parent. Then select the **default language**, which will be applied to new content created in the root of the project.

> **Important:** The parent project cannot be changed after the project is created. The default language can.

- Name your project

Give the project a **display name**. The **identifier** is auto-generated from the display name, but can be overridden. Only alphanumeric characters and "-" are allowed, the value is validated for uniqueness, and it cannot be changed later. Optionally, add a description.

> **Note:** When creating a layer, the wizard will suggest display name and description based on the parent project and the selected language.

- Public or private

Select the [access mode](#access-mode) — the default READ permissions for content in the project.

- Grant project roles

Give users or groups access to the project by assigning [project roles](#project-roles).

- Project scope applications

Select the [applications](#project-applications) that should be available for the project’s content.

- Summary

Verify the settings of the project you are about to create, then click **Create Project**.

> **Note:** If you created a layer, a synchronization job will kick in and inherit content from the parent project.

## Managing projects

Existing projects are managed from the [Settings section](docs/content-studio/stable/workbench/settings.md): select one or more projects and click **Edit** in the toolbar, or simply double-click a project. Most of the wizard’s settings can also be changed on an existing project. Things to be aware of:

- **Icon** — click the project thumbnail to upload a custom icon. This can only be done after creation, as the wizard has no icon step.

- **Default language** — changing it only affects new items created after the project is saved; existing content items keep their language.

- **Access mode** — changing to or from **Public** must be confirmed, since it updates permissions on every single content item inside the project.

- The **identifier** and **parent project** can never be changed.

To delete a project, select it in the Settings grid and click **Delete** in the toolbar.

> **Caution:** Deleting a project will delete its repository and all the data inside. This action has to be confirmed and cannot be undone.

## Project layering

Content Studio also offers an advanced feature for reusing and augmenting content across multiple projects. This is called [content layering](docs/content-studio/stable/projects/layers.md).
