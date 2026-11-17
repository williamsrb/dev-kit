# Providers

Claude Code and Cursor have no image, audio or 3D generator of their own, so assets come from external services through an MCP server, a REST API or an official SDK. Pick per media type, keep one provider for the whole batch.

## Choosing

1. **What the design needs.** Pixel art or isometric → a pixel-art specialist. Many assets of one character → subject or character reference. Many assets in one look → style reference image or a custom style. Sprites and tiles → transparent background. Flat icons → vector output or an exact palette.
2. **What is configured.** `keys.py status --json` (`configured` only) and the MCP tools this session lists.
3. **Access path, in order:** an MCP tool already connected for that provider; the official SDK run under `keys.py run`; the REST API run under `keys.py run`.

Record the choice and the reason in `design-log.md`. A provider that lacks a needed feature is allowed only as a stated fallback ("no reference images: consistency rests on seed and prompt; expect more rejects").

## Calling with a key

`keys.py run <provider> -- <command>` exports the provider's env var into that one child process. The key never appears in the command you type, in a file, or in output.

- SDKs read the env var themselves: `$K run openai -- python3 <lake>/assets/gen.py` with a small script you write next to the assets.
- Shell tools must expand the variable **inside** the child, so quote the whole command: `$K run openai -- sh -c 'curl -sS https://… -H "Authorization: Bearer $OPENAI_API_KEY" -d @req.json -o out.json'`. Unquoted, your own shell expands an empty variable first.
- Never run `env`, `printenv`, `set -x` or anything that echoes the variable.
- Async APIs (job id, then poll): poll from the script with a bounded loop (fixed interval, a timeout), not from repeated agent tool calls.
- Downloaded results go to `assets/raw/`; keep the provider's job id in `design-log.md`.

Missing key: `keys.py run` exits 2 and names the file. Report it; do not ask for the key in chat and do not write it yourself.

## Native generators

| Harness | Native | Use |
|---|---|---|
| Claude Code | none | external provider only |
| Codex CLI | built-in `$imagegen` skill (OpenAI image model, counts against Codex usage) | fallback when no key is configured; no documented seed or palette control |
| Cursor (2.4+) | native image generation (Nano Banana Pro), saves under `assets/` | same fallback; move outputs into `<lake>/assets/raw/` |

A native generator still goes through `normalize`, `check` and review. It lacks reference and seed controls, so prefer a configured provider whenever the design has more than a handful of assets.

## Catalog

Researched 2026-10-30 from each provider's docs (URLs below). Model ids change often: read the provider's docs page for the current id at D1 and pin it in the lock; do not reuse ids from memory. `keys.py` id = file `~/.agents/.auth/<id>-api-key.yaml`.

| `keys.py` id | Media | Best for | MCP (official) | REST | SDK (Py / JS) | Env var |
|---|---|---|---|---|---|---|
| `pixellab` | pixel art | sprites, 4/8-direction characters, isometric tiles, tilesets | `https://api.pixellab.ai/mcp` (Bearer) | `https://api.pixellab.ai/v2` (async jobs) | `pixellab` / `@pixellab-code/pixellab` | `PIXELLAB_SECRET` |
| `retro-diffusion` | pixel art, low-poly 3D | isometric assets, tilesets, palette-bound pixel art | `https://mcp.retrodiffusion.ai/mcp` (Bearer) | `https://api.retrodiffusion.ai/v2/inferences` (async) | none (HTTP) | `RD_API_KEY` (header `X-RD-Token`) |
| `recraft` | raster, SVG | custom style from 1–10 refs (`style_id`), flat icons, vector | `https://mcp.recraft.ai/mcp` (OAuth, subscription credits) | `https://external.api.recraft.ai/v1/images/generations` | OpenAI SDK with `base_url` | `RECRAFT_API_TOKEN` |
| `scenario` | image, 3D, audio, video | trained custom models (LoRA) on your anchors: strongest batch consistency | `https://mcp.scenario.com/mcp` (OAuth or Basic) | `https://api.cloud.scenario.com/v1/...` (jobs) | `scenario-sdk` / `@scenario-labs/sdk` | `SCENARIO_API_KEY` + `SCENARIO_API_SECRET` (Basic) |
| `bfl` | image | many references per call, seed, hex colors, exact size (FLUX.2) | `https://mcp.bfl.ai` (OAuth) | `https://api.bfl.ai/v1/{model}` (async, `polling_url`) | none | `BFL_API_KEY` (header `x-key`) |
| `openai` | image | multi-reference edits, masks, transparent PNG/WebP | none | `https://api.openai.com/v1/images/generations`, `/images/edits` | `openai` / `openai` | `OPENAI_API_KEY` |
| `gemini` | image | character and style references (up to 14), multi-turn edits | none | Gemini API `generativelanguage.googleapis.com` | `google-genai` / `@google/genai` | `GEMINI_API_KEY` |
| `replicate` | many models | one key for open models, FLUX fine-tunes | remote MCP (URL unverified); npm `replicate-mcp` | `https://api.replicate.com/v1/predictions` | `replicate` / `replicate` | `REPLICATE_API_TOKEN` |
| `fal` | many models | one key for open models, fast queue | `https://mcp.fal.ai/mcp-relay` (OAuth) | `https://queue.fal.run/{model_id}` | `fal-client` / `@fal-ai/client` | `FAL_KEY` (`Authorization: Key …`) |
| `stability` | image, audio, 3D | Style Guide with `fidelity`, seed returned in a header, Stable Audio | none | `https://api.stability.ai/v2beta/...` | none current | `STABILITY_API_KEY` |
| `meshy` | 3D | target polycount, PBR, retexture, rig and animate | npm `@meshy-ai/meshy-mcp-server` | `https://api.meshy.ai/openapi/v2/text-to-3d` (preview, then refine) | none | `MESHY_API_KEY` |
| `tripo` | 3D | image/model/texture seed values, face limit, smart low-poly | `tripo-mcp` (Blender bridge, alpha) | `https://openapi.tripo3d.ai/v3/...` | `tripo3d` / none | `TRIPO_API_KEY` |
| `higgsfield` | image, video | cinematic video from approved anchors (trailers, cutscenes), photoreal people; not pixel art or isometric | `https://mcp.higgsfield.ai/mcp` (OAuth) | `https://api.higgsfield.ai` (async: `request_id`, poll `status_url` or webhook) | `higgsfield-client` / `@higgsfield/client` | `HF_API_KEY_ID` + `HF_API_KEY_SECRET` (`Authorization: Key id:secret`); SDKs read `HF_KEY` (Py) / `HF_CREDENTIALS` (JS) as `id:secret` |
| `elevenlabs` | SFX, music | SFX with `loop`, music with `seed` | `elevenlabs-mcp` (uvx) | `https://api.elevenlabs.io/v1/sound-generation`, `/v1/music` | `elevenlabs` / `@elevenlabs/elevenlabs-js` | `ELEVENLABS_API_KEY` (header `xi-api-key`) |

Remote MCP servers that use OAuth or a key header are connected in the operator's MCP configuration; this skill never edits MCP configuration. When one is connected, its tools appear in the session and take precedence.

### Pitfalls per provider

- **PixelLab, Retro Diffusion, BFL, Scenario, Meshy, Tripo, Stable Audio 3:** async. Submit, keep the job id, poll from a script. Retro Diffusion wants an `Idempotency-Key` header so a retried POST does not bill twice.
- **BFL:** result URLs expire after 10 minutes; download right after the job is `Ready`. FLUX 3 rejects `seed`; use FLUX.2 when the lock pins a seed.
- **Recraft:** inpaint, outpaint and background operations work only on `recraftv3*` models. The MCP bills subscription credits, not API units.
- **OpenAI, Gemini:** no documented seed. Consistency rests on reference images; pass the anchor on every call.
- **ElevenLabs:** sound effects have no seed; keep one prompt prefix and duration per family of sounds.
- **Tripo:** the v2 API shuts down on 2026-10-31; use v3 paths only.
- **Higgsfield:** model ids (for example `higgsfield-ai/soul/v2/standard`) and their parameters live in the console's per-model reference, not the docs index; check seed and reference-image support there before relying on them. The docs index does not cover Soul characters (trained characters), which the MCP exposes, so treat them as MCP-only until the model reference shows otherwise. MCP generations always spend credits at standard rates, even on plans with unlimited web use; the API bills per request. `keys.py run higgsfield` exports all four variables.
- **Gemini:** Imagen is shut down in the Gemini API; use the Gemini image models.

### Not usable here

- **Midjourney:** no public API; its guidelines prohibit automation.
- **Ollama image generation:** experimental, macOS first; not available on this Linux host as of 2026-10-30.
- **ComfyUI:** no key; usable when the operator runs it locally (`POST /prompt`, `GET /history/{id}`, `GET /view`) or connects `comfy-mcp`. Full control (seed, LoRA, nodes) but the operator owns the workflow file.

### Sources

PixelLab `https://api.pixellab.ai/v2/llms.txt` · Retro Diffusion `https://github.com/Retro-Diffusion/api-examples` · Recraft `https://www.recraft.ai/docs/api-reference/agents.md` · Scenario `https://docs.scenario.com`, `https://mcp.scenario.com/docs` · BFL `https://docs.bfl.ml/api_integration/integration_guidelines.md` · OpenAI `https://developers.openai.com/api/docs/guides/image-generation.md` · Gemini `https://ai.google.dev/gemini-api/docs/image-generation.md.txt` · Replicate `https://replicate.com/docs/reference/mcp` · fal `https://fal.ai/docs/documentation/model-apis/mcp.md` · Stability `https://docs.stability.ai/api-reference/index.md` · Meshy `https://docs.meshy.ai/api/ai.md` · Tripo `https://github.com/VAST-AI-Research/tripo-python-sdk` · Higgsfield `https://docs.higgsfield.ai/docs/authentication.md`, `https://docs.higgsfield.ai/docs/how-to/sdk.md`, `https://higgsfield.ai/creator-hub/help-center/mcp-cli/what-is-higgsfield-mcp` · ElevenLabs `https://elevenlabs.io/docs/api-reference/text-to-sound-effects/convert.md` · Codex `https://learn.chatgpt.com/docs/image-generation.md` · Cursor `https://cursor.com/changelog/2-4` · Ollama `https://ollama.com/blog/image-generation` · ComfyUI `https://docs.comfy.org/development/comfyui-server/comms_routes.md`
