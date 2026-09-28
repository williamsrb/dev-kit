# How to add a tracker connector in Morpheus

## Scope

Compile-time tracker registry under `morpheus/packages/harness/src/connectors/`. Use when adding a second ticket-system connector, or when changing how work sources resolve `trackers.current` / `spec.connector`.

## Prerequisites

- Morpheus checkout with the vendor-neutral ingest split already landed (`connectors/types.ts`, `connectors/registry.ts`, Jira as the sole installed connector).
- Do **not** load connector JS from the vault.

## Procedure

1. Add `packages/harness/src/connectors/<id>.ts` implementing `TrackerConnector` / `TrackerClient` from `types.ts`. Keep vendor query language, pickup rules, and enqueue-var aliases inside that file.
2. Register it in `connectors/registry.ts` `CONNECTORS` (stable order; first entry is the omit-default when `trackers.current` is empty).
3. Keep core `packages/harness/src/sources.ts` free of vendor client imports and of `jql` / `JQL` tokens (FR-11 grep gate).
4. Extend `ConfigSchema` refusal copy only if the installed-list wording needs updating; unknown `trackers.current` already fails via `unknownTrackerMessage`.
5. WorkSource YAML: optional `spec.connector`; omit → `resolveCurrentTracker(config)`. Do not inject `connector: <id>` on load and do not infer connector from connector-specific blocks.
6. Enqueue: write vendor-neutral vars (`issueKey`, …) **and** any legacy aliases the seeded playbooks still interpolate.
7. Docs: name the vendor only in connector-local sentences; `docs/configuration.md` documents `trackers.current`. Do not invent a `morpheus tracker` CLI unless a ticket asks for it.

## Pitfalls

- Putting JQL (or equivalent) on `PollTickResult` or passing it from `sources.ts` into the client breaks the FR-11 gate.
- Calling `postRestrictedComment` (or any outbound comment API) from the poll tick violates the control-plane-does-not-post rule.
- Renaming seeded playbook id `jira-to-commit` or approval channels `jira_comment` / `jira_worklog` is out of scope unless a ticket says otherwise.

## Sample data

```yaml
# config.yaml
trackers:
  current: jira   # or omit

# sources/example.yaml — connector omitted; resolves to trackers.current
apiVersion: morpheus/v1
kind: WorkSource
metadata:
  id: example
spec:
  jira:
    baseUrl: https://example.atlassian.net
    pickup: status
    statuses: ["To Do"]
  playbook: jira-to-commit
```
