#!/usr/bin/env python3
"""Write the default `.agentctl` when it is absent.

The file is the one place agentctl settings live (see bin/agentctl_config.py), and the reader has no
built-in defaults, so a harness or profile without the file needs this script once:

    python3 bin/agentctl_defaults.py            # $AGENTS_HOME/.agentctl, else ~/.agents/.agentctl
    python3 bin/agentctl_defaults.py --path P   # somewhere else
    python3 bin/agentctl_defaults.py --print    # show the defaults, write nothing

An existing file is never touched (exit 0, "left untouched"); `--force` is the only way to replace one.
The first line of the written file says where the values came from. The text below is the single source
of the defaults: change a default here, not in a copy of the file.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

FILE_NAME = ".agentctl"

DEFAULTS_TOML = r"""# Default values written by bin/agentctl_defaults.py (run it again only when this file is absent; it never overwrites).
# agentctl settings: the one place agentctl-related defaults live (factory, tracker, git policy, hooks).
# TOML, read with the standard library. A profile may carry its own copy at $AGENTS_HOME/.agentctl,
# which wins over this one. $AGENTCTL_CONFIG overrides both (tests, experiments).
schema_version = 1

# --- issue tracker -----------------------------------------------------------------------------
# The factory talks to a tracker only through this table. Jira is one flavor; another flavor adds a
# [tracker.<kind>] table with the same keys and sets `kind`. `kind = "none"` runs local tasks only.
[tracker]
kind = "jira"

[tracker.jira]
key_regex = '^[A-Z][A-Z0-9]+-\d+$'          # a task id matching this is a tracker task, anything else is local
key_pattern = '(?<![A-Za-z0-9_])([A-Z][A-Z0-9]+-\d+)(?![A-Za-z0-9])'   # the same key found inside free text (group 1)
site = "https://example.atlassian.net"           # used when the token file names no site
token_file = ".auth/jira-api-token.yaml"       # API token YAML, relative to the harness root
browse_path = "/browse"                        # issue URL = site + browse_path + "/" + key
skip_comment_authors = ["Solutions Jira x GitLab"]   # bot authors download-jira-task leaves out of the PRD
restricted_comment_visibility = "group:leanon"   # who may read a factory notice: `--visibility` value of `agentctl jira comment`
bot_author_re = "bot|jenkins|bamboo|automation"      # with the git host's bot_author_re: the "also drop bots" filter
closed_statuses = ["Closed", "In Production", "Released", "Discarded", "Backlog"]   # released or discarded: never a sync candidate or a release member (a done status category counts too)
issue_fields = [                               # fields `agentctl jira get|fetch` ask for by default
  "summary", "description", "status", "issuetype", "priority", "assignee", "reporter", "created", "updated",
  "project", "comment", "attachment",
]
download_skill = "download-jira-task"        # step 0 of the tracker pipeline
# Bash patterns the post step may use. Only `post-evidence` gets them; no other step writes to the tracker.
post_tools = [
  "Bash(agentctl jira comment:*)", "Bash(agentctl jira attach:*)", "Bash(agentctl jira get:*)",
  "Bash(agentctl jira request:*)", "Bash(agentctl image:*)",
]
# A denied command matching this is a forbidden tracker write: the run parks instead of noting it.
write_command_re = '(?:\S*/)?agentctl\s+jira\s+(?:comment|attach)\b'
# MCP tool names the tracker write guard denies (writes go through `agentctl jira comment|attach`).
write_tools = ["addOrEditJiraIssueComment", "addCommentToJiraIssue", "uploadAttachmentToJiraIssue", "jira_add_comment", "jira_update_comment", "jira_prepare_upload"]
write_tool_re = 'addCommentToJira|addOrEditJiraIssueComment|uploadAttachment|executeWrite|jira_add_comment|jira_update_comment|jira_prepare_upload'
write_guard_hint = "Jira comment and attachment writes go through `agentctl jira comment|attach` (--confirm-issue <KEY>; evidence comments also --evidence-progress <file>). Use that command instead of the MCP tool."

# --- git host ----------------------------------------------------------------------------------
# Where branches are reviewed and merged. GitLab is one flavor, GitHub another; flipping `kind` is the
# whole switch. Prose and code say "review request" for the host's own merge request / pull request.
[git_host]
kind = "gitlab"
# Every word the operator may use for a commit (branch) that waits for approval before it lands. They all
# mean the same thing; write with the host's own term (`review_request` below).
review_request_terms = ["MR", "merge request", "PR", "pull request", "review request", "code review"]

[git_host.gitlab]
review_request = "merge request"
review_request_short = "MR"
web_blob_path = "/-/blob/{ref}/{path}"         # file view on the web UI, appended to the host URL + /<group>/<repo>
web_commit_path = "/-/commit/{sha}"
web_review_request_path = "/-/merge_requests/{id}"
ci_file = ".gitlab-ci.yml"
cli = "glab"
mcp_server = "gitlab"                    # name of the MCP server entry in the vendor configs
mcp_binary = "gitlab-mcp-server"               # release binary `agentctl tools audit` checks
mcp_release_repo = "jmrplens/gitlab-mcp-server"
bot_author_re = "gitlab"                       # comments from this host's integrations are noise
api_path = "/api/v4"                           # REST root under gitlab_url; the sync adapter calls it
token_name = "factory_token"                   # entry of the $AGENTS_HOME/.auth token file the sync uses (scope api)

[git_host.github]
review_request = "pull request"
review_request_short = "PR"
web_blob_path = "/blob/{ref}/{path}"
web_commit_path = "/commit/{sha}"
web_review_request_path = "/pull/{id}"
ci_file = ".github/workflows"
cli = "gh"
mcp_server = "github"
mcp_binary = "github-mcp-server"
mcp_release_repo = "github/github-mcp-server"
bot_author_re = "github"
api_path = ""                                  # no GitHub sync adapter yet: the sync stops with a clear error
token_name = ""
auth_files = []

# --- parallel-issue sync (plan factory-sync) --------------------------------------------------
# Factories coordinate through the git host and the tracker only. Review requests carry a marker block;
# a related issue with no branch gets a restricted tracker comment instead.
[sync]
enabled = true
marker_label = "factory-proposal"              # label on every proposal review request
marker_block = "agentctl-proposal"             # fenced block with the JSON marker in the description
proposal_branch = "proposal/{src}-into-{dst}"  # one branch, one open request per source/target pair
max_open_per_pair = 1
max_proposals_per_run = 3
ladder = ["notice", "ordering", "proposal"]    # cheapest first; a contradiction never reaches a proposal

# --- git policy --------------------------------------------------------------------------------
[git]
base_branches = ["origin/master", "origin/main", "master", "main"]   # first one that exists is the integration base
protected_branches = ["master", "main", "develop", "release"]        # never a push target for the factory
fast_forward = false                                                 # merges never fast-forward, for everyone

[git.factory]
commit = true                 # the factory may commit (stage + commit with the drafted message)
push = true                   # the factory may push the task branch
force_push = false
merge_strategy = "no-ff"      # integrate = merge the base into the branch with --no-ff, resolve conflicts, commit, push
worker_git_writes = false     # false: the engine owns git writes; headless workers still get them denied
signature = "Automated by: agentctl factory"   # last line of every factory commit and review request description, after a blank line
never_stage = [".env", ".env.*", "*.pem", "*.key", "id_rsa*", "credentials*", "*.p12"]
deploy_review = true          # deploy-review = merge the task branch into the repo's [review_env] branch with --no-ff and push it

# --- review environments -----------------------------------------------------------------------
# One table per git host project (origin's `group/repo`) whose review environment deploys from an integration
# branch, not from the task branch. deploy-review merges the task branch into `branch` and pushes it; await-review
# waits until the host's `environment` reports a successful deployment that contains the task head.
# A repo without a table skips both steps.
[review_env."group/as"]
branch = "review"
environment = "review"
timeout_min = 45
poll_s = 30
# kind = "install" (default "branch") for a repo whose review environment takes a built artifact installed by hand.
# The factory never installs. deploy-review checks that `verify` prints the artifact's sha256 (a read-only probe,
# never a service endpoint that starts a task); when it does not, the run parks operator_install with the commands.
# [review_env."group/repo"]
# kind = "install"
# artifact = "build/libs/*.jar"                    # glob relative to the repo; exactly one match
# backup = "review-backup/export.json"             # relative to the repo, or absolute; must exist before install
# install = "<command that installs the artifact>"
# restore = "<command that restores the backup>"
# verify = ["<read-only command>", "--print-sha256"]

# --- release integration -----------------------------------------------------------------------
# Test commands and test environments of `agentctl release open|merge|check|audit` (RC1). Commented sample:
# the same tables go in `<repo>/.agentctl` (only [release] is read there; the project file wins per `name`).
# `run` is split with shlex and run without a shell; a command that needs a pipe declares `bash -c` itself.
# An environment name or a host label must be one of review, staging, dev, test, qa, sandbox, preview.
# [[release.repos."group/repo".tests]]
# name = "unit"
# kind = "unit"                 # unit | integration | e2e | lint | smoke
# run = "python3 -m unittest"
# cwd = "."                     # repo-relative
# paths = ["tests/**"]          # where the tests of this kind live (the bug closing search)
# timeout_min = 30
# env = false                   # true: needs a deployed test environment (gets RELEASE_BASE_URL)
# [[release.repos."group/repo".envs]]
# name = "review"
# base_url = "https://review.example.com"
# deploy = ""                   # optional command; gets RELEASE_SHA, RELEASE_BRANCH, RELEASE_ENV, RELEASE_BASE_URL
# version_url = ""              # optional URL whose body carries the deployed commit
# default = true

# --- factory -----------------------------------------------------------------------------------
[factory]
env = "AGENTCTL_FACTORY"      # set on every worker process; hooks read it to know they run headless
state_dir = "factory"         # under the harness root; $AGENTS_FACTORY_DIR overrides
vendor = "claude"
supervisor_role = "follow"
route_step = "route"
pipelines = ["tracker-standard", "brainstorm", "sync", "release-replay", "release-review"]   # sync: re-run the related scan and the sync steps on a finished task; release-*: agentctl release

[factory.limits]              # uncalibrated defaults; pipeline files may override a key
uncalibrated = true
summary_chars = 1200
handoff_summaries = 3
handoff_bytes = 3072
excerpt_bytes = 4096
supervisor_bytes = 6144
attempts = 3
transient_retries = 2
gate_retries = 2
review_loops = 2
backoff_s = [30, 120, 300]
run_usd = 40.0
run_hours = 6.0
step_timeout_min = 90
dual_rewrite_ratio = 0.4

[factory.limits.budget_usd]
follow = 2
explore = 2
plan = 8
build = 8
impl-review = 6
plan-review = 6
task-owner = 12
quality-gate = 6

# Extra worker tools for one repo, keyed by origin's `group/repo`. Added to [factory.worker] allowed_tools for that
# repo's pipeline steps only; other repos get none of them. Each pattern still needs a real need in the repo's build.
# [factory.repo_tools."group/repo"]
# allowed_tools = ["Bash(npx eslint:*)", "Bash(./gradlew build:*)", "Bash(npx tsc:*)"]

[factory.worker]
permission_mode = "acceptEdits"
allowed_tools = [
  "Read", "Edit", "Write", "Skill", "Glob", "Grep", "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)",
  "Bash(agentctl:*)", "Bash(python3:*)", "Bash(ls:*)", "Bash(cat:*)", "Bash(rg:*)", "Bash(mkdir:*)", "Bash(echo:*)",
  "Bash(grep:*)", "Bash(head:*)", "Bash(tail:*)", "Bash(wc:*)", "Bash(find:*)", "Bash(sort:*)", "Bash(diff:*)",
  "Bash(test:*)", "Bash(pwd:*)", "Bash(date:*)", "Bash(which:*)", "Bash(touch:*)", "Bash(cp:*)", "Bash(sed:*)",
  "Bash(git branch:*)", "Bash(git rev-parse:*)", "Bash(git show:*)", "Bash(git ls-files:*)", "Bash(git remote:*)",
  "Bash(env:*)", "Bash(ruff check:*)",
  "mcp__serena__initial_instructions", "mcp__serena__find_symbol", "mcp__serena__get_symbols_overview",
  "mcp__serena__find_referencing_symbols", "mcp__serena__find_declaration", "mcp__serena__find_implementations",
  "mcp__serena__get_diagnostics_for_file", "mcp__serena__list_memories", "mcp__serena__read_memory",
]
# Always denied to workers. Git writes are added from [git.factory] when worker_git_writes is false.
disallowed_tools = []

# --- hooks -------------------------------------------------------------------------------------
[hooks]
# Reply formatting is for the operator's chat; headless factory workers are exempt.
response_format_skip_factory = true
# Under the factory env an `ask` verdict becomes `deny`: nobody can answer a prompt.
ask_becomes_deny_in_factory = true
"""


def default_path() -> Path:
    raw = os.environ.get("AGENTS_HOME")
    root = Path(raw).expanduser() if raw else Path.home() / ".agents"
    return root / FILE_NAME


def write_defaults(path: Path, *, force: bool = False) -> bool:
    """Write DEFAULTS_TOML to `path`. False when the file exists and `force` is off (nothing is touched)."""
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(DEFAULTS_TOML)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the default .agentctl when it is absent.")
    parser.add_argument("--path", type=Path, help="Target file (default: $AGENTS_HOME/.agentctl, else ~/.agents/.agentctl).")
    parser.add_argument("--force", action="store_true", help="Replace an existing file with the defaults.")
    parser.add_argument("--print", action="store_true", dest="show", help="Print the defaults and write nothing.")
    args = parser.parse_args(argv)
    if args.show:
        sys.stdout.write(DEFAULTS_TOML)
        return 0
    path = (args.path or default_path()).expanduser()
    if write_defaults(path, force=args.force):
        print(f"wrote defaults to {path}")
    else:
        print(f"{path} exists; left untouched (use --force to replace it)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
