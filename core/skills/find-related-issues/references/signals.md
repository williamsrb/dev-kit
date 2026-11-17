# Signals, ranking and output

Read this when you need to explain a rank, tune a threshold, or parse `related.json`.

## Where candidates come from

| Signal | How it is found | `relations` value |
|--------|-----------------|-------------------|
| Unreleased work on our files | Local and remote branches not merged into base, minus the task's own branch. For each, commits since the merge-base that touch the task's files. Keys come from the commit subject and body, else from the branch name. | `parallel-unreleased` |
| Released history on our files | `git log <base> --since=<window>` on the task's files (24 months, 400 commits). Keys from subject and body. | `history-released` |
| Parent | Jira `parent` of the task | `parent` |
| Children | Jira `parent = <task>` | `child` |
| Siblings | Jira `parent = <task's parent> AND key != <task>` | `sibling` |
| Links | Jira `issuelinks` of the task. Label is the link wording (`blocks`, `is blocked by`, `duplicates`, `relates to`). | `linked:<label>`, `duplicate:<label>` |
| Chain | A candidate's parent or links hit the task's parent or a linked key | `via:<KEY>` |
| PRD mention | Keys in `~/.agents/prds/<TASK-ID>.md`, most frequent first, 15 at most | `mentioned-in-prd` |

The task's files are, in order: `--files`, the diff `base...HEAD`, the repo files the plan folder names, the repo files the PRD names. A named path counts only when it is in `git ls-files`. `files.source` says which one was used (`args`, `diff`, `plan`, `prd`, `none`). At most 60. Matching is by exact path. A renamed file hides its history: pass the old path in `--files`.

A key that Jira does not know (a branch called `step-2`) is dropped when the tracker answered. With the tracker down it stays, `confirmed: false`.

## Tiers and score

Tier is the first that holds: `parallel` (unreleased commits touching our files), `tracker` (any tracker relation), `history` (released commits only). Score orders inside the report:

| Part | Points |
|------|--------|
| Unreleased commits on our files | 50 + 5 per shared file, at most 6 files |
| Released commits only | 10 + 3 per shared file, at most 5 files |
| `parent` / `sibling` / `child` | 20 / 25 / 25 |
| `linked` / `duplicate` | 35 / 40 |
| `via` / `mentioned-in-prd` | 15 / 15 |
| Status not Done | 5 |

The score is a reading order, not a verdict. A `tracker` candidate with no code and no activity is context, not a risk.

## `<TASK-ID>.related.json`

Summary first: `task_id`, `generated_at`, `repo`, `base`, `head` (`branch`, `sha`), `files` (`source`: `args|diff|plan|prd|none`, `count`, `list`), `refs_fetched_at`, `tracker` (`status`: `ok|skipped|unavailable`, `own`), `counts`, `warnings`. Then `candidates[]`: `key`, `tier`, `score`, `confirmed`, `summary`, `status`, `type`, `assignee`, `relations`, `code_state` (`unreleased|released|none`), `overlap_files`, `branches`, `commit_counts`, `last_activity`, `recent[]` (15 in the file, 2 on stdout). Then `unkeyed_branches[]`: `ref`, `files`, `commits[]`.

## Caps and limits

- Jira enrichment covers 80 keys, highest score first; the rest are dropped when the tracker answered.
- `brief` reads at most 40 commits per branch, 20 released commits, 80 files, 300 diff lines per branch, 5 comments of 600 characters, and a 1500-character description.
- Redaction is a pattern (`password`, `secret`, `token`, `api_key` followed by `:` or `=`). It is a safety net, not a scrubber.

## Pitfalls

- Remote refs are as old as the last fetch. `refs_fetched_at` and the stale warning say how old. The skill does not fetch.
- Commits squashed into base lose their branch but keep the key in the message, so they show as `history`, not `parallel`.
- An integration branch (`develop`, a review branch) is unreleased: it brings every key whose commit touched our files. That is intended.
- A mass rename or formatter commit touches every file and lights up as overlap. Judge it `unrelated` from the diffstat.
- Work in another repository, or a review request (MR/PR) from a fork, has no ref here and is not found.
