Screenshots intended for Jira (evidence comment, analyst comment, attachments, immediate upload) must be validated, then stamped, before flatten/upload/post:

1. **Correct element** — the intended UI/target from the plan step, not a wrong panel, modal, or sibling.
2. **Correct zoom** — crop/viewport scale matches the step; the element is readable and dominant as planned.
3. **Correct example page** — URL/content matches the planned example (right env, path, locale, sample content).
4. **Pixel-size stamp** — after the local image gate (whitespace + OCR + Read), stamp every Jira-bound PNG, then refuse upload if the stamp is missing:

```bash
agentctl image stamp /abs/path.png [/abs/other.png ...]
agentctl image stamp --check /abs/path.png [/abs/other.png ...]
```

`--check` exit 1 = do not upload or embed. Pass **file paths**. A directory argument only auto-stamps `NN-*.png` (skips `*.viewport.png` unless named). Do not run raw `mogrify … *.png` — that skips the tag. Do not mention the stamp in the Jira comment. Equivalent script: `python3 ~/.agents/skills/plan-task-evidence/scripts/annotate-evidence-resolution.py`.

How (1–3): after each capture (or before upload), open a **vision preview** of the image (see vendor-vision-image-preview) and check all three against the plan step. The canonical file stays on disk for stamp/upload. On failure, retake — do not stamp/upload/post a failed shot.

Storage-only screenshots (not for immediate Jira evidence) do not require this.
