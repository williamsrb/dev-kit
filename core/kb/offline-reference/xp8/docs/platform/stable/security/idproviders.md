<!-- src:https://developer.enonic.com/docs/platform/stable/security/idproviders generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/platform/stable/security/idproviders.md

# ID providers (IDP)

ID providers provide a pluggable abstraction layer for user authentication and access management in XP.

## Introduction

The main purpose of IDproviders is to provde pluggable authentication and authorization to XP. With an ID provider configured, your may associate it with a [web service](docs/platform/stable/endpoints/web.md) of your choice via [virtual host](docs/platform/stable/config/vhosts.md) configuration.

## System ID provider

To get started quickly, Enonic XP ships with a built-in `system` ID provider. This is most commonly used by developers, or for administrative purposes. When accessing the XP admin console for the first time in a fresh installation, you will see the login screen of System ID provider.

You may also create service accounts in the System ID provider, and use them to authenticate against the Management Endpoint, or other APIs as described in [Service accounts](docs/platform/stable/security/service-accounts.md).

> **Tip:** Avoid adding human users to the System ID provider, but rather create custom ID providers for this purpose.

### System users

The System ID provider is also the home of two special users:

**system:su** The `Super User` exists in order to perform priveliged actions, and to allow you to start using XP before you have created any users. The Super User has the **system.admin** role, and thus unrestricted access.

**system:anonymous** - XP expects a user in every request. As such, the `Anonymous` user steps in to cover for users that have not authenticated.

## Custom ID providers

ID providers can be created and managed in the Users app, or via the API. An ID provider essentially consist of the following:

- A unique name (cannot be changed later)

- ID provider application, with optional configuration settings.

> **Tip:** You may choose from a range of standard ID providers on [Enonic Market](https://market.enonic.com), or build your own for a fully customized approach.

- Permissions - specifies who can manage and access the ID provider

For a walkthrough of creating and configuring an ID provider from the UI, see the [Users admin tool](docs/platform/stable/admin/users.md#id-providers).

Once your ID provider is created, you may start working with users and groups within it.

> **Note:** Often, ID providers are simply proxies against 3rd party systems such as Google Auth, or Microsoft Entra, In this case, you will not be able to manage the users locally - they will typically appear in XP once they sign in the first time.
