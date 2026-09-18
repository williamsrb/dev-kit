<!-- src:https://developer.enonic.com/docs/platform/stable/security generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/platform/stable/security.md

# Security, Identity and Access Management

Enonic XP ships with a complete and pluggable concept for authentication, authorization and auditing - commonly referred to as IAM.

## ID providers

ID providers represent a pluggable abstraction layer for user authentication. To authenticate - or even create users in XP - you will need an [ID provider](docs/platform/stable/security/idproviders.md).

XP ships with a built-in System ID provider to get you started quickly. Choose from a range of standard ID providers on [Enonic Market](https://market.enonic.com), or build your own for a fully customized approach.

## Principals

Principals are the actors of XP’s security model. XP provides three basic principals: [users](docs/platform/stable/security/principals.md#users), [groups](docs/platform/stable/security/principals.md#groups) and [roles](docs/platform/stable/security/principals.md#roles). Combined with ID providers, these form the essence of Enonic IAM.

## Service accounts

[Service accounts](docs/platform/stable/security/service-accounts.md) enable secure, token-based authentication for machine-to-machine communication - for example when accessing the [Management API](docs/platform/stable/endpoints/management.md) from remote clients or CI/CD pipelines.

## Permissions

In addition to role-based access control, the CMS (and underlying [NoSQL storage](docs/platform/stable/storage.md)) supports fine-grained [access control](docs/platform/stable/storage/permissions.md) - down to a single item.

## Audit logs

XP automatically registers completed actions affecting repositories, content, applications, principals and ID providers in a dedicated repository. Visit [Audit logs](docs/platform/stable/security/audit-logs.md) for details on the available events and how to enable or disable logging.

## Management

Principals, ID providers and service accounts can be managed through the [Users admin tool](docs/platform/stable/admin/users.md), or programmatically via APIs.
