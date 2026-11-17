---
id: how-to-leave-a-restricted-comment-on-the-tracker
when_skills: [run-plan, find-related-issues]
inputs: [.agentctl, agentctl jira]
outputs: [a tracker comment only a named group can read]
stop_if: [the read-back shows no visibility, the group does not exist]
read: whole
prose: caveman-lite
---

# Leave a restricted (hidden, closed) comment on the tracker

Use when a note must reach the team but not the client or the reporter: for the factory, the "related issue has no branch yet" notice. Words people use: hidden comment, closed comment, restricted comment, internal comment, comment visible to a group.

## Jira

1. Group check: `agentctl jira request GET '/rest/api/3/groups/picker?query=leanon'` must list a group named exactly `leanon`.
2. Post: `agentctl jira comment KEY --body "<text>" --visibility group:leanon --confirm-issue KEY`. The `--visibility` value is `.agentctl [tracker.jira] restricted_comment_visibility` (default `group:leanon`). `--visibility role:NAME` restricts to a project role instead.
3. Read back, always: `agentctl jira request GET '/rest/api/3/issue/KEY/comment/<id>'` and require `visibility.value == "leanon"` and `visibility.type == "group"`. A comment without `visibility` is public: stop and tell the operator at once.
4. Never edit a posted comment without the backup first (`rules/jira-comment-edit-backup.mdc`); post a new one instead, or skip when a comment with the same marker line already exists.
5. Direct Atlassian MCP comment tools are denied by `hooks/jira-write-guard.py`; `agentctl jira comment` is the only path.

## Verified 2026-10-27

Comment `541112` on `INFRA-142` (operator's test sub-task) posted with `--visibility group:leanon`; the read-back returned `visibility: {type: group, value: leanon, identifier: 70e164bc-...}`; the comment list shows it with value `leanon`. It is left in place on purpose. The group picker also returns `leanon-notify-all-events`; match the exact name.

## Other trackers

A tracker without comment visibility has no safe equivalent: park and ask, do not post publicly.
