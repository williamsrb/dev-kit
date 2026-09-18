---
name: develop-xp7-backend
description: "Enonic XP 7 backend: controllers, services, schemas, CMS, IAM, queries, deploy. Use for XP7, lib-content, lib-node, content types, NoQL/DSL, or Enonic app development. | recommendedRole: implement | aliases: enonic-xp7-backend-development, xp7-backend, enonic-backend, xp-backend-dev."
metadata:
  recommendedRole: implement
  aliases: enonic-xp7-backend-development, xp7-backend, enonic-backend, xp-backend-dev
  cliDependencies:
    required: [agentctl, rg, python3, enonic]
    optional: [npm, docker]
---
## Local documentation search first

Run `agentctl docs search '<focused query>' --db ~/.agents/.cache/offline-docs.sqlite --json`. Open only the best matching source path; fall back to the routing index when no result is relevant.

# Enonic XP 7 Backend Development

## Use this skill when

- Building or debugging Enonic XP 7 apps.
- Working with server-side code, APIs, or request handling.
- Designing content types/schemas that backend code depends on.
- Reviewing IAM, storage, runtime, or deployment behavior in XP projects.

## Backend-first defaults

1. Start from the runtime path: request -> controller -> service/lib calls -> content/node/repo access.
2. Prefer stable XP APIs and explicit context handling before custom abstractions.
3. Keep schema and content model changes aligned with query/index usage.
4. Validate permissions/roles early when auth-sensitive endpoints are involved.

## Recommended workflow

Copy this checklist and keep it updated while working:

```markdown
Task Progress:
- [ ] 1) Identify request entrypoint and engine (site/admin/webapp/http/idprovider)
- [ ] 2) Confirm required API libs and context/auth assumptions
- [ ] 3) Implement or adjust backend logic
- [ ] 4) Verify schema/index/query compatibility
- [ ] 5) Validate runtime/deployment implications
- [ ] 6) Summarize risks, tests, and follow-ups
```

### 1) Identify entrypoint

- Determine whether flow starts in controller, filter, processor, task, websocket, or main controller.
- Confirm applicable engine and mapping configuration.

### 2) Confirm APIs and context

- Pick the smallest API surface that solves the task.
- Verify principal/role expectations and repository/branch context.
- Explicitly account for project/layer behavior in CMS-backed solutions.

### 3) Implement backend logic

- Keep handlers thin; move domain logic into reusable modules.
- Make error handling explicit and predictable for XP response flows.
- Keep i18n keys and templating usage consistent if response rendering is involved.

### 4) Verify schema/index/query compatibility

- Ensure content type/x-data/schema changes support existing queries.
- For storage-heavy changes, check query syntax (NoQL/DSL), filters, aggregations, and highlighting assumptions.

### 5) Validate runtime/deployment implications

- Check impact on vhosts/config, task engine behavior, and clustering assumptions where relevant.
- Call out configuration requirements for local, sandbox, and hosted environments.

## Response format for coding tasks

When this skill is active, structure responses as:

1. **Approach**: entrypoint, API libs, and context model.
2. **Implementation**: concrete code/file changes.
3. **Validation**: runtime checks, query/index checks, and auth checks.
4. **Risk notes**: backward compatibility and deployment considerations.

## Documentation map

Use the official **XP 7.x** docs as source of truth (`/docs/platform/7.x/`, not `stable`):

- Core guides: Admin, IAM, CMS, Applications, Development, Runtime, Storage, Hosting, Audit Logs, Release Notes.
- Framework areas: controllers, filters, tasks, mappings, components, processors, websocket, templating, error handling, Java bridge.
- API areas: `lib-admin`, `lib-app`, `lib-auth`, `lib-content`, `lib-context`, `lib-node`, `lib-portal`, `lib-project`, `lib-repo`, `lib-schema`, `lib-task`, `lib-value`, `lib-vhost`, `lib-websocket`.

For compact references in this skill:

- API focus and selection: [api-priority.md](api-priority.md)
- Modeling, storage, runtime, and deployment checks: [xp-checklists.md](xp-checklists.md)
- CMS schema input types quick map: [schema-input-types.md](schema-input-types.md)
- Development + framework lookup strategy: [development-framework-priority.md](development-framework-priority.md)

## Optimized doc usage strategy

When solving XP backend tasks, consult docs in this order:

1. **Development root + Code/Build/Config/TypeScript**
   - Validate project setup, toolchain, build mode, and runtime config assumptions first.
2. **Framework page matching the entrypoint**
   - Controller/filter/processor/task/websocket/main logic should use corresponding framework docs before API deep-dives.
3. **Minimal API surface**
   - Choose API libs by capability boundaries (`content` vs `node`, `task` vs blocking request, `auth` + `context` for privileged flows).
4. **Storage/query details**
   - Re-check indexing and query semantics before changing schema or query code.

## Offline docs support

Prefer offline LLM-dense snapshots for repeated XP **7.x** lookups (docs are **not** under this skill):

1. Route via `~/.agents/kb/offline-reference/xp7/llm-index.md` (chooser: `api` / `development` / `framework`).
2. Open the matching subtree `llm-index.md`, then the page under `~/.agents/kb/offline-reference/xp7/{development,framework,api}/`.
3. Online source of truth for this skill is **7.x** (`https://developer.enonic.com/docs/platform/7.x/...`), not `stable` (XP 8).

Refresh (from this skill directory; default output is the KB path above):

```bash
python3 scripts/sync-xp-docs.py
```

Docs and tooling:
- Offline docs guide: `~/.agents/kb/offline-reference/xp7/README.md`
- Sync script: `scripts/sync-xp-docs.py`
- Catalog root: `~/.agents/kb/offline-reference/README.md`
