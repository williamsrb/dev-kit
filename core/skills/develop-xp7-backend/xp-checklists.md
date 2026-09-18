# XP Checklists (Modeling to Runtime)

## CMS and modeling checklist

- Content types align with page/components and controller expectations.
- Schemas use the correct field type semantics (required, occurrences, localization).
- Mixins/x-data are consistent across content types that share behavior.
- Page templates, regions, parts, and layouts match rendering logic.

Docs:
- CMS root: <https://developer.enonic.com/docs/xp/stable/cms>
- Content types: <https://developer.enonic.com/docs/xp/stable/cms/content-types>
- Pages/components: <https://developer.enonic.com/docs/xp/stable/cms/pages>
- Schemas: <https://developer.enonic.com/docs/xp/stable/cms/schemas>

## IAM and security checklist

- Required roles are documented for each privileged operation.
- ID provider assumptions are explicit (system IDP vs custom IDP).
- User/group lookup and authorization checks are done at boundaries.

Docs:
- IAM root: <https://developer.enonic.com/docs/xp/stable/iam>
- ID providers: <https://developer.enonic.com/docs/xp/stable/iam/idproviders>
- Roles: <https://developer.enonic.com/docs/xp/stable/iam/roles>

## Storage and query checklist

- Repository/branch are explicit for read/write operations.
- Index expectations are documented when adding/renaming fields.
- Query behavior validated for NoQL or DSL, including filters/aggregations.

Docs:
- Storage root: <https://developer.enonic.com/docs/xp/stable/storage>
- NoQL: <https://developer.enonic.com/docs/xp/stable/storage/noql>
- DSL: <https://developer.enonic.com/docs/xp/stable/storage/dsl>
- Indexing: <https://developer.enonic.com/docs/xp/stable/storage/indexing>

## Runtime and deployment checklist

- Engine assumptions are explicit (site/admin/webapp/http/idprovider).
- Config/vhost requirements are recorded for each environment.
- Task engine and clustering implications are considered when scaling.
- Upgrade notes reviewed for version-sensitive behavior.

Docs:
- Runtime root: <https://developer.enonic.com/docs/xp/stable/runtime>
- Hosting/deployment: <https://developer.enonic.com/docs/xp/stable/deployment>
- Release notes: <https://developer.enonic.com/docs/xp/stable/release>
