---
id: how-to-switch-the-git-host-flavor
when_skills: [run-plan, plan-implementation]
inputs: [.agentctl, mcp/catalog.json]
outputs: [.agentctl git_host table, MCP server entry for the new host]
stop_if: [a rule, skill or script names a host where it should read .agentctl]
read: whole
prose: caveman-lite
---

# Switch the git host flavor

GitLab is one flavor of `[git_host]` in `.agentctl`, GitHub another. Rules, skills, hooks and scripts say "review request" (MR / PR / merge request / pull request: a commit or branch that waits for approval) and read the host's own words, paths, CLI and CI file from the active table. Flipping the host is a config change plus the MCP wiring below.

## Procedure

1. In `.agentctl` set `[git_host] kind = "github"` (or add a `[git_host.<kind>]` table with the same keys as `gitlab`: `review_request`, `review_request_short`, `web_blob_path`, `web_commit_path`, `web_review_request_path`, `ci_file`, `cli`, `mcp_server`, `mcp_binary`, `mcp_release_repo`, `bot_author_re`). Keep `review_request_terms` complete: the operator's MR, PR, merge request and pull request all mean the same thing.
2. Add the host's MCP server to `mcp/catalog.json` and install it (`python3 mcp/install.py install <server> --vendors cursor,claude,codex`). That rewrites `~/.claude/.claude.json`, `~/.codex/config.toml` and `~/.cursor/mcp.json`; do not hand-edit them.
3. Put the host's token under `$AGENTS_HOME/.auth/` and a wrapper in `bin/` the way `bin/gitlab-mcp` does. The wrapper, not `mcp.json`, holds the secret.
4. Run `python3 -m unittest tests.test_agentctl_config`: it proves the CI signals, bot filter and tools audit follow `kind`.
5. Check `.agentctl [git.factory] protected_branches` and `base_branches` for the new host's default branches.

## What reads `[git_host]`

`agentctl_config.git_host()` and `bot_author_pattern()`; `classify-ticket-autonomy` (CI file and host-name signals); `render_issue.py` and `agentctl jira` (host integration bot comments); `agentctl tools audit` (the MCP release binary); `plan-task-evidence` prose (blob path template). BASE §3 *Review requests* defines the vocabulary for every session.

## Still GitLab-specific on purpose (flavor implementations, replace with the new host's equivalents)

- `bin/gitlab-mcp`, `bin/gitlab-mcp.py`, `mcp/catalog.json` entries `gitlab` and `gitlab-mcp-server`, `mcp/install.py` `fetch_gitlab`, `mcp/env.example`, `mcp/README.md`.
- KB pages about GitLab itself: `kb/testing/_shared/How-to-capture-a-gitlab-commit-diff-as-evidence.md`, `How-to-list-gitlab-pipelines-when-mcp-returns-array.md`, `How-to-prove-a-review-deploy-carries-a-merge.md`, and client pages that mention pipelines.
- `skills/set-up-enonic-react4xp` scaffolds a `.gitlab-ci.yml` for GitLab-hosted client projects (a project template, not a harness setting).
- `bin/agentctl_security.py` cites the GitLab CI security baseline as the source of its exclusion list (provenance, not behavior).
- The Jira integration author `Solutions Jira x GitLab` in `.agentctl [tracker.jira] skip_comment_authors` is the Jira app's own name.

## Pitfalls

- Never write a host name into a rule, skill, hook or script: grep for it first (`grep -rniI gitlab rules skills hooks bin`) and read `.agentctl` instead.
- A host's web paths differ (`/-/blob/` on GitLab, `/blob/` on GitHub); take them from `web_blob_path`, never from prose.
