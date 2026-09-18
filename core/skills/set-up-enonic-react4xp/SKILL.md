---
name: set-up-enonic-react4xp
description: "Bootstrap a new Enonic React4XP project with the standard architecture, CLAUDE.md, and scripts. | recommendedRole: task-owner | aliases: enonic-react4xp-setup, react4xp-enonic-setup."
disable-model-invocation: true
metadata:
  recommendedRole: task-owner
  aliases: enonic-react4xp-setup, react4xp-enonic-setup
  cliDependencies:
    required: [python3, enonic, npm]
    optional: [docker]
---
## Cursor IDE

Adapted from [git.example.com/group/enonic-skills](https://git.example.com/group/enonic-skills). Skill root: `.` (this skill directory).

| Claude Code | Cursor |
|-------------|--------|
| Bash | Shell |
| AskUserQuestion | AskQuestion (one option set per message) |
| Edit / Write | StrReplace / Write |

Replace `<skill-path>` below with `.` (this skill directory).

# Enonic React4xp Setup

## Knowledge base (How)

This skill owns the interactive wizard and bootstrap invocation.

Sets up a new React4XP project with a standard architecture: React4XP starter, docker structure, gitlab ci/cd. Generates a complete CLAUDE.md, operational scripts using Makefile, and a project structure ready for AI-assisted development.

## Workflow

**CRITICAL: Execute this workflow as an interactive step-by-step conversation. Ask ONE question at a time, wait for the user's answer, validate it, and only then proceed to the next question. NEVER ask multiple questions in a single message.**

### Step 1 — Project Display Name

Ask the user:

> What is the **display name** for your new project?
> _(Example: "My Awesome Website", "Client Portal 2025")_

- Wait for the user's response.
- Store the answer as `<project-display-name>`.

### Step 2 — Project Short Name

Ask the user:

> What is the **short name** for the project?
> _(Only alphanumeric characters, no spaces or special characters. Used for docker containers, config files, CI/CD environments, etc.)_
> _(Example: "myawesomewebsite", "clientportal2025")_

- Wait for the user's response.
- **Validate**: If the short name contains non-alphanumeric characters, tell the user it is invalid and ask again. Do NOT proceed until a valid short name is provided.
- Store the answer as `<project-short-name>`.

### Step 3 — Starter SHA Commit (optional)

Ask the user:

> Do you want to use a **specific starter SHA commit**?
> - Type the SHA commit hash to use a specific version.
> - Press Enter or type "no" to use the **latest** version from the main branch.

- Wait for the user's response.
- If the user provides a SHA, store it as `<starter-sha-commit>`.
- If the user says "no", leaves it empty, or presses Enter, leave `<starter-sha-commit>` empty.

### Step 4 — Confirm and Execute

Present a summary of all collected values and ask for confirmation:

> Here is your project configuration:
> - **Display Name**: `<project-display-name>`
> - **Short Name**: `<project-short-name>`
> - **Starter SHA**: `<starter-sha-commit>` _(or "latest")_
>
> Shall I proceed with the setup? (yes/no)

- Wait for the user's confirmation.
- If the user says "no", ask which value they want to change and go back to that specific step.
- If the user says "yes", proceed to run the bootstrap script.

### Step 5 — Run Bootstrap Script

Run the bootstrap script with the gathered info:

```bash
python3 <skill-path>/scripts/bootstrap.py "<project-display-name>" "<project-short-name>" "<starter-sha-commit>"
```

The script will:
- Install Enonic CLI if not already installed.
- Create an Enonic React4XP app (if /xp directory is empty or doesn't exist) using the variables collected during the workflow.
- Copy the template files with some default files used in every project, such as:
  - Docker structure for development.
  - CLAUDE.md with a project description, architecture overview, and instructions for development and deployment.
  - Makefile with operational scripts for common tasks (start, stop, build, deploy).
  - Gitlab CI/CD configuration file (.gitlab-ci.yml) with stages for build, test, and deploy.
  - Some default libraries.
  - A collection of skills to develop new tasks from Jira specifications, and to develop any Enonic React4XP code following the project patterns.

All templates live in `<skill-path>/template/` as plain, editable files. The script replaces `{PROJECT_DISPLAY_NAME}` and `{PROJECT_SHORT_NAME}` placeholders in the templates with the actual values provided by the user.

### Step 6 — Post-Bootstrap Modifications

After the bootstrap script completes successfully, use versions for npm deps from `<skill-path>/template/prototype/package.json`.

### Step 7 — Report Results

Tell the user:
1. Run `make up`, `make copyComponents` and `make deploy` to start the development environment with Docker.
2. The CLAUDE.md is ready — Cursor will follow the project patterns when assisting in that repo.

### General Rules
- **One question per message.** Never combine multiple questions in a single response.
- If the bootstrap script detects an existing /xp directory with files in it, stop and report an error. The setup can only be executed in a clean repository.
- When `<starter-sha-commit>` is empty, do not include this parameter in the command.
- If the user provides a Starter SHA commit that doesn't exist, report the error and stop.
- If the user provides a Project Short Name with non-alphanumeric characters, reject it immediately and ask again.
