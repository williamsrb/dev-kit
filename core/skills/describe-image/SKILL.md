---
name: describe-image
description: "Describe a local screenshot: local Ollama vision (gemma4:e4b) first, the ROLES.md deterministic Claude model when Ollama cannot serve it. Use when layout, UI, or text in an image needs semantics that pixel-diff or OCR cannot answer."
metadata:
  recommendedRole: explore
  aliases: ollama-vision, image-description, vision-describe, local-image-describe
  cliDependencies:
    required: [python3, agentctl]
    optional: [ollama, claude, identify, convert]
---

# Describe Image

Turn one local image into a short text description, so the main model spends tokens on the answer, not on the pixels.

## Local deterministic first

This is a model, not a deterministic tool: wording and detail vary run to run. Prefer these when they answer the question:

- Only need the words on screen? Use [ocr](../tesseract-cli/SKILL.md) (`tesseract`): exact text, no hallucination risk.
- Only need "how much is blank"? Use [blank-space](../blank-space/SKILL.md): exact pixel ratio.
- Only need "did anything change"? Use [diff-image](../diff-image/SKILL.md): exact pixel diff.

Reach for `describe-image` when the question is semantic ("does this layout look broken", "which UI elements are present").

## Backends

`agentctl image describe` picks the backend per call and reports it in `backend`:

| Backend | When | Speed and cost |
|---------|------|----------------|
| `ollama` | `ollama` is installed, the service answers on `$OLLAMA_HOST` (default `http://localhost:11434`), and `--model` is pulled | Free; no GPU on this host, so `gemma4:e4b` measured ~140 s warm per screenshot, more on a cold load |
| `claude` | Any of those fails (`fallback_reason`: `ollama-missing`, `service-unreachable`, `model-not-pulled`) | The ROLES.md `deterministic` Claude cell (`agentctl local models` shows it), about 6 s and under $0.001 per screenshot |

The fallback reads a 1280 px preview (`03-vendor-vision-image-preview.md`) and runs with no user settings, hooks or MCP. The original stays on disk.

## Privacy

The `claude` backend sends the image to Anthropic. Pass `--local-only` when the screenshot shows personal data, customer records or credentials. The command then fails the way the Ollama path fails instead of falling back. Crop to the region in question when only part of the screen matters.

## Inside a Claude Code session

Run `agentctl image describe` first: Ollama may serve it for free. When the result already says `backend: "claude"`, use it; do not also spawn the subagent.

To skip Ollama on purpose (for example several images where ~140 s each is too slow), spawn the `image-describer` subagent with the absolute path and the question, one subagent per image in the same message:

```text
Agent(subagent_type: "image-describer", prompt: "Image: /abs/path/in.preview.png\nQuestion: Is the hero title clipped on the right?")
```

Make the preview first when the long edge is over 1280 px: `convert in.png -resize '1280x1280>' in.preview.png`.

## When not to use

- Anything decisive for a security decision, destructive action, or a Jira evidence pass/fail gate. Those need deterministic checks and vendor-model or human judgment (`02-local-first-deterministic-tools.md`).
- Text-only extraction: OCR is faster, exact, and free of hallucination.
- Pixel-exact comparison: use `diff-image`.

## Command

```bash
agentctl image describe /absolute/path/screenshot.png --prompt "List every visible button label"
```

| Flag | Default | Purpose |
|------|---------|---------|
| `--prompt` | general layout/text/UI/issues description | Ask something specific and factual. |
| `--model` | `gemma4:e4b` | Ollama vision model (`ollama show <model>` lists `vision` under Capabilities). Not used by the fallback. |
| `--timeout` | `300` seconds | Ollama inference wait. The fallback uses at most 180 s. |
| `--max-chars` | `4000` | Bounds the returned description. |
| `--local-only` | off | Never leave the machine: fail instead of falling back. |

`python3 ~/.agents/skills/describe-image/scripts/describe.py <image> [--host URL]` is the Ollama backend alone, with no fallback.

## Output

Bounded JSON: `status`, `description`, `truncated`, `model`, `backend`, and `fallback_reason` when Ollama was not used. The Ollama path adds `eval_count` and `total_duration_ms`; the fallback adds `preview`, `duration_ms` and `cost_usd`. On an Ollama failure (`--local-only`) the JSON carries a `hint`.

## Failures

| Situation | Action |
|-----------|--------|
| `backend: "claude"` but you wanted local | Pull the model (`ollama pull gemma4:e4b`) or start the service (`systemctl status ollama`), then rerun. |
| `claude CLI not on PATH` | Install Claude Code, or pull the Ollama model. |
| Timeout | First Ollama inference after a model load is slow; retry once with a larger `--timeout`. |
| Description looks wrong | Treat it as a hint. Crop to the region and ask a narrower question, or look at the preview yourself. |
