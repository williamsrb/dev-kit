---
name: check-disk-cleanup
description: "Find disk clean-up opportunities on a disk, the system root or the user home with `agentctl disk`. Read-only: ranks big files, stale items, caches, Trash, Downloads, docker, apt, flatpak and snap leftovers with size and age filters. Use for 'check clean-up opportunities on disk X', 'system root', 'my user home', 'bigger than 5 GB', 'older than 2025-01-01'."
metadata:
  recommendedRole: deterministic
  aliases: disk-cleanup, cleanup-opportunities, free-disk-space
  cliDependencies:
    required: [python3, agentctl]
    optional: [docker, flatpak, dpkg, apt-get, snap, journalctl]
---

## Local deterministic first

Run `agentctl disk report <target>` and read its JSON. It answers from a SQLite cache that cron refreshes, so it never walks the disk and returns in about a second. Do not run `du`, `find` or `docker system df` to answer the same question.

# Check disk clean-up opportunities

`agentctl disk` only reports. It never deletes, moves or edits anything. Every finding carries a `suggested_command` string for the operator to approve.

## Prompt to command

| The operator says | Run |
|---|---|
| "check clean-up opportunities on disk X" | `agentctl disk targets`, then `agentctl disk report <mount point or device>` |
| "system root" | `agentctl disk report root` |
| "my user home" | `agentctl disk report home` |
| "bigger than 5 GB" | `--min-size 5GB` (accepts `500M`, `2GB`, `2GiB`) |
| "older than 2025-01-01", "older than 6 months" | `--older-than 2025-01-01` or `--older-than 6m` (`90d`, `6m`, `1y`, ISO date) |
| "only docker", "only caches" | `--category docker` (`caches`, `home-regenerable`, `home-stale`, `trash`, `downloads`, `big-files`, `system`, `docker`, `apps`) |
| "include risky items" | `--max-risk danger` (default `review` hides `danger`) |
| "oldest first" | `--sort age` |
| "show more" | the `next` command that ends with `--offset N` |

Filters combine. `summary.filters` echoes what was applied. Default page is 25 findings under 16 KB; raise `--limit` or `--max-bytes` only when asked.

## Read the summary first

- `summary.disk`: size, used and available of the disk.
- `summary.cache.stale`: true means the scan is older than `--max-age` (default 36h). Say so, and offer `agentctl disk scan <target> --background` from `next`.
- `summary.coverage.mode`: `partial` means some directories were unreadable. For `root` the `next` list carries the one-time install command; the operator runs it with sudo.
- `summary.reclaimable`: bytes per risk. `safe` is regenerable, `review` needs a human decision, `danger` is informational and has no command.
- `summary.excluded_unknown_age`: items hidden by `--older-than` because their age is unknown.
- `unavailable`: a collector that could not run (for example `snap not installed`). The report is still valid.
- Status other than `ok`: `no_cache` and `schema_mismatch` come with the scan or install command in `next`. Run `agentctl disk scan <target> --background`, then `agentctl disk status`.

## Findings

Each finding has `id`, `category`, `path`, `bytes`, `last_used` with its source, `risk`, `reversible`, `regenerable`, `needs_sudo` and `suggested_command`. `agentctl disk explain <id>` returns the evidence, the risk reasoning and the exact command, and executes nothing. `size_drift: true` means the item changed after the scan.

## HTML report

After answering, offer the HTML report in one line. Build it on the operator's yes, or at once when they ask for a report, a page, a table or a chart:

```bash
python3 <this skill>/scripts/build_report.py [targets ...] [--out FILE]
```

Targets default to `home root`; `--out` defaults to `~/.local/state/agentctl-disk/disk-cleanup-report.html`. The script reads every finding from the cache, fills `assets/report-template.html` and prints JSON with `out` and `refresh`. Do not hand-write the page or edit the template for one report.

The page holds a headline sentence, a bar per disk (used, safe to clear, your call, reserved for root, free), a bar per category, a filterable table of every finding with copy buttons, and a "Refresh this report" section. It sorts each finding into one verdict:

- **Safe to clear**: `risk: safe`, except app runtimes that agentctl misrates (`node_modules` under `~/.local/portable`, `~/.config/Lens`, `~/.p2/pool/plugins`).
- **Leave alone**: `risk: danger`, those app runtimes, and big files that are installed software, toolchains, app data or git history (`/usr`, `/opt`, `~/.nvm`, `.git/objects` and similar).
- **Your call**: everything else.

Open the file in a browser, or publish it where the harness publishes pages. End the reply with the refresh commands from the script's `refresh` output, so the operator can refresh without asking:

```bash
agentctl disk scan --all --background
agentctl disk status
python3 <this skill>/scripts/build_report.py home root
```

## Rules

- Read-only. Never run a `suggested_command` yourself. Present the finding, its risk and its command, and wait for the operator's approval.
- When the operator approves a batch (for example "everything safe to clear"), first check what holds each path (`ps`, `lsof +D`). Skip caches of running apps, such as the desktop app hosting this session, an open browser, or a `uvx` server running from `~/.cache/uv`, and name them with the reason. Run the rest from one script, not one tool call per item.
- `needs_sudo: true` items go to the operator: show the command, do not run `sudo`.
- Trash and docker volumes are permanent when removed; say so. Protected docker volumes (under `/home/volumes`) have `risk: danger` and no command.
- For a stale project, run the finding's `verify_command` (a read-only `git status` and `git log`) before suggesting removal.
- The root-level scan is installed by the operator: `python3 ~/.agents/bin/agentctl-disk-root-install.py` is the dry run, `sudo ... --apply` performs it.
