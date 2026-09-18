---
id: how-to-list-gitlab-pipelines-when-mcp-returns-array
when_skills: [run-plan, plan-task-evidence]
read: section
prose: caveman-lite
---

# How to list GitLab pipelines via gitlab MCP

**Scope:** `_shared`
**Applies to:** any project on `git.example.com` via `user-gitlab`
**Related:** [acme-group/How-to-verify-review-environment.md](../acme-group/How-to-verify-review-environment.md)

List tools (`gitlab_pipeline_list`, `gitlab_job_list`, `gitlab_project_search`, `gitlab_ci_variable_list`, `gitlab_package_list`) return a **record**:

```
{"items": [ ... ]}
```

A root JSON array used to fail Cursor/Claude/Codex with `structuredContent: expected record, received array`. The server wraps lists as of the `items` change in `~/Workspace/Personal/gitlab-mcp`. Object tools (`gitlab_pipeline_get`, `gitlab_job_log`) are unchanged.

If that schema error still appears, the vendor is running a stale stdio process. Reload the `gitlab` MCP (or restart the vendor). Do not treat it as GitLab being down.

## Prerequisites

- Project path as GitLab encodes it, e.g. `group/acme-group`.

## Procedure

1. `gitlab_pipeline_list` with `project`, optional `ref` / `status` / `limit`. Read `items`.
2. `gitlab_job_list` with `project` and `pipeline_id` (and `scope='failed'` when diagnosing). Read `items`.
3. `gitlab_job_log` with `project`, `job_id`, optional `tail_lines`. Returns a record (`log`, `total_lines`, `returned_lines`).

REST only if MCP is unavailable (server not running, 401/403, or a still-stale process after reload):

```
GET https://git.example.com/api/v4/projects/<urlencoded-path>/pipelines?ref=<branch>&per_page=8
Header: PRIVATE-TOKEN: <token>
```

## Pitfalls

- Never paste the token into chat, plans, or KB sample rows.
- After a server-side wrap change, a live Cursor/Claude session keeps the old process until MCP reload.

## Sample data (minimal)

| Field | Example |
|-------|---------|
| Project | `group/acme-group` |
| Ref | `review` |
| Shape | `{"items":[{"id":87563,"status":"failed","ref":"review",...}]}` |
