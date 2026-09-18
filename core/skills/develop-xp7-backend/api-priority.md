# API Priority (Backend First)

Use this order when selecting Enonic XP APIs:

1. **Request and app context**
   - `lib-context`, `lib-app`, `lib-portal`
2. **Auth and identity**
   - `lib-auth`, IAM docs (ID providers, users/groups, roles)
3. **Content and storage**
   - `lib-content`, `lib-node`, `lib-repo`, `lib-schema`, `lib-project`
4. **Cross-cutting runtime**
   - `lib-event`, `lib-task`, `lib-scheduler`, `lib-vhost`, `lib-cluster`
5. **Operational/support APIs**
   - `lib-admin`, `lib-common`, `lib-io`, `lib-mail`, `lib-value`, `lib-websocket`, `lib-auditlog`, `lib-export`, `lib-grid`

## Selection rules

- Prefer `lib-content` for CMS-managed content behavior; drop to `lib-node` only when lower-level node control is required.
- Use `lib-context` explicitly when switching repository, branch, or principal assumptions.
- Avoid mixing query styles in the same module unless needed; keep NoQL/DSL usage consistent per codepath.
- For long-running work, prefer task/scheduler APIs over blocking request handlers.

## Full API catalog (stable)

- APIs root: <https://developer.enonic.com/docs/xp/stable/api>
- Admin API: <https://developer.enonic.com/docs/xp/stable/api/lib-admin>
- Application API: <https://developer.enonic.com/docs/xp/stable/api/lib-app>
- Auditlog API: <https://developer.enonic.com/docs/xp/stable/api/lib-auditlog>
- Auth API: <https://developer.enonic.com/docs/xp/stable/api/lib-auth>
- Cluster API: <https://developer.enonic.com/docs/xp/stable/api/lib-cluster>
- Common API: <https://developer.enonic.com/docs/xp/stable/api/lib-common>
- Content API: <https://developer.enonic.com/docs/xp/stable/api/lib-content>
- Context API: <https://developer.enonic.com/docs/xp/stable/api/lib-context>
- Event API: <https://developer.enonic.com/docs/xp/stable/api/lib-event>
- Export API: <https://developer.enonic.com/docs/xp/stable/api/lib-export>
- Grid API: <https://developer.enonic.com/docs/xp/stable/api/lib-grid>
- I18N API: <https://developer.enonic.com/docs/xp/stable/api/lib-i18n>
- IO API: <https://developer.enonic.com/docs/xp/stable/api/lib-io>
- Mail API: <https://developer.enonic.com/docs/xp/stable/api/lib-mail>
- Node API: <https://developer.enonic.com/docs/xp/stable/api/lib-node>
- Portal API: <https://developer.enonic.com/docs/xp/stable/api/lib-portal>
- Project API: <https://developer.enonic.com/docs/xp/stable/api/lib-project>
- Repo API: <https://developer.enonic.com/docs/xp/stable/api/lib-repo>
- Scheduler API: <https://developer.enonic.com/docs/xp/stable/api/lib-scheduler>
- Schema API: <https://developer.enonic.com/docs/xp/stable/api/lib-schema>
- Tasks API: <https://developer.enonic.com/docs/xp/stable/api/lib-task>
- Value API: <https://developer.enonic.com/docs/xp/stable/api/lib-value>
- VHost API: <https://developer.enonic.com/docs/xp/stable/api/lib-vhost>
- Websocket API: <https://developer.enonic.com/docs/xp/stable/api/lib-websocket>
