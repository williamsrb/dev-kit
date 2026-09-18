---
name: find-skills
description: "Find and install agent skills from skills.sh (`npx skills`). Use when the user asks to find a skill, or a plan/run/test/validate step needs a capability that is not installed. | recommendedRole: follow."
metadata:
  recommendedRole: follow
  cliDependencies:
    required: [npx, npm]
    optional: [agentctl, skillspector]
---

# Find Skills

Discover and install skills from the open agent skills ecosystem (`npx skills`, https://skills.sh/). Commands: `npx skills find [query] [--owner <owner>]`, `npx skills add <owner/repo@skill> -g -y`, `npx skills update`.

## Nested / auxiliary use

Other workflow skills (`plan-implementation`, `plan-task-evidence`, `run-plan`, `validate-impl`, and their aliases) may call this skill **only when needed** — never as a mandatory step of every run.

### When a parent skill should call you

Call `find-skills` when **all** of the following are true:

1. A concrete action is blocked or would be poorly done without specialized guidance/tools.
2. No already-installed skill (or MCP / normal tools) covers it adequately.
3. A one-off session-only script would be disproportionate or fragile compared to a reusable skill.

Do **not** call `find-skills` for routine work the parent skill already knows how to do, or for tiny helpers that a few shell/Python lines can cover.

### Nested procedure

When invoked from a parent skill:

1. State in reasoning: `called_from: <parent-skill-name>` (e.g. `called_from: plan-implementation`).
2. Identify the **capability gap** in one line (domain + task), e.g. "read local `.fig` / Figma design file".
3. Follow Steps 1–4 below (understand need → leaderboard → search → quality verify).
4. Prefer an already-installed skill if search reveals you already have an equivalent (canonical pool `~/.agents/skills/`, projected into `~/.cursor/skills/` and `~/.claude/skills/`).
5. If a quality-verified skill exists and is not installed:
   - Briefly tell the user what you found and that you are installing it as an auxiliary skill for the parent run.
   - Scan first: `agentctl skills scan https://github.com/<owner>/<repo>` (or the local path). Do not install if `gate` is `block`.
   - Install with: `npx skills add <owner/repo@skill> -g -y`
   - Read the newly installed `SKILL.md` and follow it for the blocked action.
6. If nothing suitable is found (or quality bar fails): say so briefly, fall back to general capabilities or ask the user — then return control to the parent skill.
7. **Return control** to the parent skill so it can continue its workflow. Do not re-plan or re-run the parent from scratch.

Parent skills keep ownership of the overall run; this skill only closes the capability gap.

## How to Help Users Find Skills

### Step 1: Understand What They Need

When a user asks for help with something, identify:

1. The domain (e.g., React, testing, design, deployment)
2. The specific task (e.g., writing tests, creating animations, reviewing PRs)
3. Whether this is a common enough task that a skill likely exists

### Step 2: Check the Leaderboard First

Before running a CLI search, check the [skills.sh leaderboard](https://skills.sh/) to see if a well-known skill already exists for the domain. The leaderboard ranks skills by total installs, surfacing the most popular and battle-tested options.

For example, top skills for web development include:
- `vercel-labs/agent-skills` — React, Next.js, web design (100K+ installs each)
- `anthropics/skills` — Frontend design, document processing (100K+ installs)

### Step 3: Search for Skills

If the leaderboard doesn't cover the user's need, run the find command:

```bash
npx skills find [query] [--owner <owner>]
```

For example:

- User asks "how do I make my React app faster?" → `npx skills find react performance`
- User asks "can you help me with PR reviews?" → `npx skills find pr review`
- User asks "I need to create a changelog" → `npx skills find changelog`
- Parent skill needs a Figma reader → `npx skills find figma`

### Step 4: Verify Quality Before Recommending

**Do not recommend a skill based solely on search results.** Always verify:

1. **Install count** — Prefer skills with 1K+ installs. Be cautious with anything under 100.
2. **Source reputation** — Official sources (`vercel-labs`, `anthropics`, `microsoft`) are more trustworthy than unknown authors.
3. **GitHub stars** — Check the source repository. A skill from a repo with <100 stars should be treated with skepticism.

### Step 5: Present Options to the User

When you find relevant skills **in a user-initiated find** (not nested), present them to the user with:

1. The skill name and what it does
2. The install count and source
3. The install command they can run
4. A link to learn more at skills.sh

Example response:

```
I found a skill that might help! The "react-best-practices" skill provides
React and Next.js performance optimization guidelines from Vercel Engineering.
(185K installs)

To install it:
npx skills add vercel-labs/agent-skills@react-best-practices

Learn more: https://skills.sh/vercel-labs/agent-skills/react-best-practices
```

In **nested / auxiliary** mode, keep the announcement short (name + why + install), then install and continue — do not stall the parent workflow on a long menu unless quality is ambiguous or multiple peers tie.

### Step 6: Scan, then install

Before `npx skills add`, scan the source with SkillSpector (static, bounded JSON):

```bash
agentctl skills scan https://github.com/<owner>/<repo>
```

If the path is already local (cloned dir or `SKILL.md`):

```bash
agentctl skills scan /absolute/path/to/skill
```

Gate on `gate` / `risk_assessment.recommendation` (exit `0` is both `SAFE` and `CAUTION`):

| `recommendation` | Action |
|------------------|--------|
| `SAFE` | Install |
| `CAUTION` | User-initiated: tell the user and wait. Nested: continue with a one-line warning. |
| `DO_NOT_INSTALL` | Do not install. Report `report_path` and top issues. |

If `skillspector` is missing, say so and do not install an unknown third-party skill until it can be scanned (`uv tool install git+https://github.com/NVIDIA/skillspector.git`). Official sources (`anthropics`, `vercel-labs`) still get scanned when the CLI is present.

Then install with:

```bash
npx skills add <owner/repo@skill> -g -y
```

The `-g` flag installs globally (user-level) and `-y` skips confirmation prompts.

## Common Skill Categories

When searching, consider these common categories:

| Category        | Example Queries                          |
| --------------- | ---------------------------------------- |
| Web Development | react, nextjs, typescript, css, tailwind |
| Testing         | testing, jest, playwright, e2e           |
| DevOps          | deploy, docker, kubernetes, ci-cd        |
| Documentation   | docs, readme, changelog, api-docs        |
| Code Quality    | review, lint, refactor, best-practices   |
| Design          | ui, ux, design-system, accessibility, figma |
| Productivity    | workflow, automation, git                |

## Tips for Effective Searches

1. **Use specific keywords**: "react testing" is better than just "testing"
2. **Try alternative terms**: If "deploy" doesn't work, try "deployment" or "ci-cd"
3. **Check popular sources**: Many skills come from `vercel-labs/agent-skills` or `ComposioHQ/awesome-claude-skills`

## When No Skills Are Found

If no relevant skills exist:

1. Acknowledge that no existing skill was found
2. Offer to help with the task directly using your general capabilities (or return that outcome to the parent skill in nested mode)
3. Suggest the user could create their own skill with `npx skills init`

Example:

```
I searched for skills related to "xyz" but didn't find any matches.
I can still help you with this task directly! Would you like me to proceed?

If this is something you do often, you could create your own skill:
npx skills init my-xyz-skill
```
