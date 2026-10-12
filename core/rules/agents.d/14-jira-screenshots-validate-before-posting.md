Jira-bound screenshots (evidence or analyst comment, attachments, immediate upload) are validated, then stamped, before flatten/upload/post. Storage-only screenshots are exempt.

1. **Correct element**: the plan step's target, not a wrong panel, modal, or sibling.
2. **Correct zoom**: crop/viewport matches the step; the element is readable and dominant.
3. **Correct example page**: right env, path, locale, and sample content.
4. **Pixel-size stamp**, after the local image gate (whitespace + OCR + Read):

```bash
agentctl image stamp /abs/path.png [/abs/other.png ...]
agentctl image stamp --check /abs/path.png [/abs/other.png ...]
```

`--check` exit 1 = do not upload or embed. Pass **file paths**; a directory only auto-stamps `NN-*.png` (skips `*.viewport.png` unless named). No raw `mogrify … *.png` (skips the tag). Never mention the stamp in the comment. Equivalent: `python3 ~/.agents/skills/plan-task-evidence/scripts/annotate-evidence-resolution.py`.

Check 1–3 on a **vision preview** (vendor-vision-image-preview) after each capture or before upload; the canonical file stays for stamp/upload. Failure → retake; never stamp/upload/post a failed shot.
