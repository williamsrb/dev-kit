---
name: google-translate
description: "Translate text with Google Cloud Translation API v2 (bundled CLI). Use to translate, detect language, list languages, or localize copy. Reads GOOGLE_TRANSLATE_API_KEY from ~/.google-cloud.env. | recommendedRole: deterministic | aliases: translate, google-cloud-translate, gtranslate, localize-text."
metadata:
  recommendedRole: deterministic
  aliases: translate, google-cloud-translate, gtranslate, localize-text
  cliDependencies:
    required: [python3]
---

# Google Translate (Cloud Translation Basic)

Translate, detect language, or list languages using Cloud Translation API **Basic (v2)** REST.

Docs: https://docs.cloud.google.com/translate/docs/reference/rest

## Auth

The script reads `~/.google-cloud.env` (KEY=VALUE lines). Put one of:

- `GOOGLE_TRANSLATE_API_KEY` (preferred)
- `GOOGLE_API_KEY` (fallback)

A process-environment value for the same name overrides the file. Do not put the
key in skill files, chat, or commit messages. If the key is missing, stop and
tell the user to set it in `~/.google-cloud.env`.

## When to use

- User asks to translate a string, paragraph, or file between languages
- Need language detection for unknown source text
- Need ISO language codes supported by Google Translate

## When not to use

- Humanizing / rewriting English prose (use humanize-text / write-as-human)
- Localizing Enonic `phrases.properties` with project-specific tone rules unless the user explicitly wants raw MT output
- Tasks that need a glossary, document batch, or Advanced (v3) features — this skill is Basic/API-key only

## Commands

Script path (shared pool):

```bash
python3 ~/.agents/skills/google-translate/scripts/translate.py
```

From the skill directory (when already there):

```bash
python3 scripts/translate.py
```

### Translate

```bash
python3 ~/.agents/skills/google-translate/scripts/translate.py translate \
  -t nb -- "Hello, world"
```

```bash
python3 ~/.agents/skills/google-translate/scripts/translate.py translate \
  -s en -t pt --format text -- "Save changes"
```

```bash
python3 ~/.agents/skills/google-translate/scripts/translate.py translate \
  -t es -f ./copy.txt
```

```bash
printf '%s' 'Bonjour' | python3 ~/.agents/skills/google-translate/scripts/translate.py translate -t en
```

Default stdout is plain translated text (one line/block per input). Use `--json` for the full API payload (includes `detectedSourceLanguage` when source was omitted).

| Flag | Purpose |
|------|---------|
| `-t` / `--target` | Target language code (required) |
| `-s` / `--source` | Source language; omit to auto-detect |
| `--format` | `text` (default) or `html` |
| `--model` | Optional `nmt` or Translation LLM resource name |
| `-f` / `--file` | UTF-8 input file |
| `--json` | Full JSON response |

### Detect language

```bash
python3 ~/.agents/skills/google-translate/scripts/translate.py detect -- "Hei verden"
```

Plain output: `language` and optional confidence (`lang\tconfidence`). `--json` for full response.

### List languages

```bash
python3 ~/.agents/skills/google-translate/scripts/translate.py languages -t en
```

## Agent rules

1. Read this skill, then **run the script** — do not reimplement the HTTP call.
2. Prefer `translate` over guessing when the user wants Google Translate output.
3. Quote or heredoc user text so shell metacharacters do not alter the payload.
4. On HTTP errors, report the API message; do not invent a translation.
5. Stdlib only (`urllib`); no pip packages.

## Notes

- Basic v2 endpoint: `https://translation.googleapis.com/language/translate/v2`
- Language codes follow Google’s Language Support list (e.g. `en`, `nb`, `pt`, `zh-CN`)
- Advanced (v3) project/OAuth flows are out of scope for this skill
