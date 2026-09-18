---
name: skillspector
description: "Scan an agent skill for prompt injection, exfil, and supply-chain risks with NVIDIA SkillSpector before install. Default is static --no-llm. | recommendedRole: deterministic | aliases: skill-inspector, scan-skill, nvidia-skillspector."
metadata:
  recommendedRole: deterministic
  aliases: skill-inspector, scan-skill, nvidia-skillspector
  cliDependencies:
    required: [skillspector]
    optional: [agentctl]
allowed-tools: Bash, Read, Write, Env
---

# SkillSpector

NVIDIA SkillSpector static-scans a skill (directory, markdown file, zip, or Git URL) and returns a bounded JSON verdict. Default is deterministic (`--no-llm`). Optional `--llm` sends analyzer-eligible file contents to NVIDIA (`nv_build`) using `~/.agents/.auth/nvidia-api-key.yaml`.

## When to use

- Before installing a third-party skill
- Auditing a local skill directory you did not author
- Rechecking a skill after it grew scripts or network calls

## When not to use

- Authoring or rewriting a skill — this only scores existing content
- Treating a static `SAFE` as a sandbox: SkillSpector does not execute or isolate the skill
- Jira evidence pass/fail, destructive actions, or security sign-off from `--llm` wording alone

## Command

Prefer `agentctl` (bounded JSON; full report stays on disk):

```bash
agentctl skills scan /absolute/path/to/skill
```

```bash
agentctl skills scan https://github.com/owner/repo
```

Equivalent direct call:

```bash
python3 ~/.agents/skills/skillspector/scripts/scan.py /absolute/path/to/skill
```

| Flag | Default | Purpose |
|------|---------|---------|
| `--llm` | off | NVIDIA semantic pass. Loads `api_key` from `~/.agents/.auth/nvidia-api-key.yaml` (or `NVIDIA_INFERENCE_KEY`). Provider `nv_build`, model `deepseek-ai/deepseek-v4-flash-0731` unless already set. Sends file contents to NVIDIA. |
| `--recursive` | off | Scan immediate subdirectories that each contain a skill markdown file. |
| `--output` | `~/.agents/.cache/skillspector/<slug>-<utc>.json` | Full SkillSpector JSON. Bounded summary still goes to stdout. |
| `--baseline` | — | Suppression file from `skillspector baseline`. |
| `--max-issues` | `20` | Cap issues in the bounded payload. |
| `--timeout` | `180` static / `600` with `--llm` on `agentctl` | Abort hung scans. |

## Gate

Read `gate` / `risk_assessment.recommendation`, not only the process exit code (`0` is both `SAFE` and `CAUTION`):

| `recommendation` | `gate` | Action |
|------------------|--------|--------|
| `SAFE` | `allow` | Install |
| `CAUTION` | `warn` | Tell the user; nested installs may continue with a one-line warning |
| `DO_NOT_INSTALL` | `block` | Do not install |

SC4 still queries OSV.dev with dependency names on static scans. `--llm` additionally sends file contents to NVIDIA (`nv_build`, model `deepseek-ai/deepseek-v4-flash-0731` unless `SKILLSPECTOR_MODEL` is already set). A partial LLM failure (`llm_error` set) is fail-closed: treat it as static-only and read `gate`. Never paste the NVIDIA key into chat, commits, or the JSON payload.

## Failures

| Situation | Action |
|-----------|--------|
| `skillspector CLI is not on PATH` | Install NVIDIA SkillSpector with uv from the GitHub repo `NVIDIA/skillspector` |
| `--llm` and missing key file | Stop. Do not fall back to another vendor. Static scan still works without `--llm`. |
| `DO_NOT_INSTALL` | Report `report_path` + top issues. Do not install. |
| Timeout / exit 2 | Report `error` and `stderr` from the JSON. Do not invent a verdict. |
