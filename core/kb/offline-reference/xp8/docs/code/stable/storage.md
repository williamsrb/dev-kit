<!-- src:https://developer.enonic.com/docs/code/stable/storage generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/storage.md

# Storage

Reference material for writing applications that read, query, and persist data in Enonic XP’s NoSQL data store.

> **Tip:** This section assumes you understand the platform-level concepts — repositories, nodes, branches, and properties. If not, start [Storage overview documentation](docs/platform/stable/storage.md).

## Libraries

Most application code touches the data store through one of these libraries:

lib-node

Generic NoSQL access to any repository. Use this for non-content data, custom repositories, and low-level node operations.

lib-repo

Create, delete, and configure repositories and branches.

lib-content

Content-aware operations on the CMS repository. Adds content type validation, draft/master handling, and publishing on top of node operations.

lib-context

Run code in a chosen repository and branch.

See each library’s reference for the full API.

## Querying

The [Query DSL](docs/code/stable/storage/querying.md) is the recommended way to query node data — a JSON expression tree that is programmatically composable and covers the full feature set of the query engine.

Related capabilities:

- [Aggregations](docs/code/stable/storage/aggregations.md) — extract statistics from search results (terms, ranges, date histograms, metrics).

- [Highlighting](docs/code/stable/storage/highlighting.md) — return matched snippets from queried properties so the UI can show where the query hit.

## Writing

- [Editors](docs/code/stable/storage/editors.md) — XP’s write pattern. Rather than update statements, supply a function that transforms one node at a time. Typically paired with a query that selects which nodes to edit.

## Access control

- [Permissions](docs/code/stable/storage/permissions.md) — read, set, and apply node ACLs; query by permission; run elevated operations through `lib-context`.

## Legacy

These APIs predate the Query DSL and are kept for backward compatibility. Prefer the DSL in new code.

- [NoQL](docs/code/stable/storage/noql.md) — SQL-inspired string query language. Use the Query DSL instead.

- [Filters](docs/code/stable/storage/filters.md) — standalone post-query filters. Use DSL filters instead.

## Examples

JSON examples used throughout this section live under `code/` next to the chapter that references them.
