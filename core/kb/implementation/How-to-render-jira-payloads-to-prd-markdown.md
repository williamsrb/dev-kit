---
id: how-to-render-jira-payloads-to-prd-markdown
when_skills: [download-jira-task, run-plan]
inputs: [saved getJiraIssue payload JSON]
outputs: [~/.agents/prds/<KEY>.md]
stop_if: [payload is not a Jira issue object]
read: section
prose: caveman-lite
---

# Render Jira payloads to PRD markdown

`~/.agents/skills/download-jira-task/scripts/render_issue.py` is the single
renderer. It handles all three body shapes the Atlassian MCP tools return.

## Three payload formats, one endpoint choice decides which

| Tool | `description` shape | Detection |
|------|--------------------|-----------|
| `mcp__plugin_atlassian_atlassian__getJiraIssue` | ADF node tree (`dict`) | `isinstance(value, dict)` |
| `mcp__atlassian-rovo-preview__getJiraIssue` | HTML string | `appliedContentFormat: "html"`, or tag sniff |
| either, with `responseContentFormat: "markdown"` | markdown string | no tags |

Both endpoints are usually configured at once. **`rovo-preview` is the one that
answers by default and it returns HTML.**

## Procedure

```bash
# single
render_issue.py <payload.json> --output ~/.agents/prds/<KEY>.md --json
# many
render_issue.py --batch a.json b.json --outdir ~/.agents/prds --json
```

`--json` reports `format` (adf/html/markdown), `comments`, `attachments`, `skipped_bot_comments`.

`render_issue.py <payload.json> --list-attachments --json` prints `{key, dir, attachments[]}` with `id` and absolute `outputPath`. That listing has no download URL. `download-jira-task` mints each URL via MCP, then runs the collected `downloadCommand`s in one `run_download_commands.py` pass before writing the PRD. The markdown `## Attachments` section lists the same names; it does not prove the curl succeeded.

## Pitfalls

- **Never let a bare string into an ADF walker.** The pre-2026-08 version began
  `if isinstance(node, str): return node`, so an HTML description was copied into
  the PRD with its tags intact — no error, no warning. 7 of 288 cached PRDs are
  corrupted this way (`RFD-676.md` is 39 lines of raw markup). The walker now
  raises `TypeError` instead; classify with `detect_format()` first.
  Audit: `grep -lE '<(p|div|h[1-6]|strong|ul|li|table)\b' ~/.agents/prds/*.md`,
  then discount hits inside ``` fences (those are legitimate sample markup).
- **Order matters for blob stripping.** After HTML→MD, `<img src="blob:...">` is
  already `![](blob:...)`. Substituting the bare URL yields
  `![]((image attachment — see ## Attachments))`. Strip the whole image wrapper first.
- **`markdownify` is an optional import**, with a stdlib `HTMLParser` fallback,
  because the skill must run where no third-party package is installed. Test the
  fallback by shadowing the module:
  `PYTHONPATH=<dir with markdownify.py that raises ImportError> render_issue.py ...`
- **Jira wraps list-item text in `<p>`.** A naive HTML parser emits the bullet,
  then a blank line, splitting every item. Suppress the paragraph break directly
  inside `<li>`.
- **Bot filtering is two-tier.** Default skips only `Solutions Jira x GitLab`
  (what SKILL.md mandates). The broad regex `bot|gitlab|github|jenkins|bamboo|
  automation` is behind `--strict-bots` — as a default it silently drops comments
  from humans whose display name contains those substrings.
- **The script's output template is SKILL.md's**, not a leaner variant. If they
  drift, the skill stops being able to reproduce its own `~/.agents/prds/` cache.

## Placement

Stays in the skill's `scripts/`, not `~/.agents/bin`: one consumer, invoked by
relative path from `SKILL.md`, and `sync-bin-projections.sh` never touches the
skills tree. `~/.claude/skills/download-jira-task` is a symlink into
`~/.agents/skills/`, so the skill tree is already vendor-neutral — nothing here
is Claude-specific. See `How-to-keep-harness-scripts-in-bin-and-bin-vendor.md`.
