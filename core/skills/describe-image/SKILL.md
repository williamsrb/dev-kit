---
name: describe-image
description: "Describe a local screenshot with local Ollama vision (gemma4:e4b), not remote LLM vision. Use when layout, UI, or text in an image needs semantics that pixel-diff or OCR cannot answer. | recommendedRole: explore | aliases: ollama-vision, image-description, vision-describe, local-image-describe."
metadata:
  recommendedRole: explore
  aliases: ollama-vision, image-description, vision-describe, local-image-describe
  cliDependencies:
    required: [python3]
    optional: [agentctl]
    services:
      required: [ollama serving on localhost:11434 with a vision-capable model pulled]
---

# Describe Image

Send a local image to a locally-running Ollama vision model and get back a text description, without spending remote LLM subscription tokens. Runs entirely on-machine over the Ollama HTTP API (`/api/generate`).

## Local deterministic first

This is **not** deterministic — it's a real (small, local) vision model, so wording and detail vary run to run. Prefer these when they can answer the question instead:

- Only need the words on screen? Use [ocr](../tesseract-cli/SKILL.md) (`tesseract`) — exact text, no hallucination risk.
- Only need "how much is blank"? Use [blank-space](../blank-space/SKILL.md) — exact pixel ratio.
- Only need "did anything change"? Use [diff-image](../diff-image/SKILL.md) — exact pixel diff.

Reach for `describe-image` when the question is genuinely semantic ("what does this look like", "does this layout look broken", "what UI elements are present") and those tools can't answer it — but don't spend a remote LLM vision call ($$$, subscription tokens) to get there.

## Performance

This host has no GPU — `gemma4:e4b` runs on CPU and one screenshot description measured **~140s warm** (model already loaded), more on a cold load. It's still free of remote-token cost, but it is not fast. Don't reach for it inside a tight loop over many screenshots without warning the user about wall-clock time; batch or prioritize instead.

## When to use

- Evidence screenshot review where a semantic read is needed but doesn't warrant a full remote-model turn.
- Quick "what's on this screen" sanity check before deciding whether deeper (remote-model) review is warranted.
- Batch-describing many screenshots cheaply, reserving remote-model attention for ambiguous ones.

## When not to use

- Anything load-bearing for a security decision, destructive action, or a Jira evidence pass/fail gate — those need deterministic checks and vendor-model or human judgment (per this repo's local-first-deterministic-tools rule).
- Text-only extraction — OCR is faster, exact, and free of hallucination.
- Pixel-exact comparison — use `diff-image`.

## Command

Prefer `agentctl` — the shared entry point for local image primitives:

```bash
agentctl image describe /absolute/path/screenshot.png
```

Equivalent direct call (adds `--host` for a non-default Ollama endpoint, not exposed via `agentctl`):

```bash
python3 ~/.agents/skills/describe-image/scripts/describe.py /absolute/path/screenshot.png
```

Options (identical on both forms except `--host`, direct-script only):

| Flag | Default | Purpose |
|------|---------|---------|
| `--prompt` | general layout/text/UI/issues description | Override to ask something specific, e.g. `"List every visible button label"` or `"Does the hero image overlap the title?"`. Keep it factual and scoped — this is a small local model, not a reasoning model. |
| `--model` | `gemma4:e4b` | Must be a vision-capable local Ollama model (`ollama show <model>` lists `vision` under Capabilities). |
| `--host` | `http://localhost:11434` | Override only for a non-default Ollama endpoint. |
| `--timeout` | `300` seconds | CPU-only inference (no GPU on this box) on the 8B `gemma4:e4b` model measured ~140s *warm* for one screenshot; a cold model load (nothing in `ollama ps`) adds more on top. Raise further for large images or when `ollama ps` shows no model loaded. |
| `--max-chars` | `4000` | Bounds the returned description so it doesn't blow up context. |

## Output

Bounded JSON on stdout: `description` (the model's text), `truncated` (bool), `eval_count`, `total_duration_ms`, and `model`. On failure (`status: "error"`), the JSON includes a `hint` — e.g. pull the model or check `ollama serve` is running.

## Failures

| Situation | Action |
|-----------|--------|
| `cannot reach ollama` | Check `systemctl status ollama` / `ollama serve` is running. Do not fall back to a remote vision API without telling the user. |
| HTTP error mentioning the model | Model isn't pulled — `ollama pull <model>`, or use one of the other local vision-capable models (`ollama list`). |
| Timeout | First inference after model load is slow; retry once with a larger `--timeout`, or re-run (model stays warm in memory for a while after). |
| Description looks wrong/hallucinated | This is a small local model — treat it as a hint, not ground truth. Verify visually or escalate to vendor-model judgment before treating the description as evidence. |

## Example

```bash
agentctl image describe \
  ${HOME}/.agents/prds/PROJ-388/evidence/01-article-content-form.png \
  --prompt "Is this an article content form? List the visible form fields and any empty-looking sections."
```
