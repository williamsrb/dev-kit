When creating or rewriting a helper/auxiliary script for a skill (anything under a skill's `scripts/` dir, or a standalone automation the agent adds), default to **`python3`** over `bash`/`sh`.

- Target Python 3.12, **standard library only** — no pip installs unless the user approves.
- Use `pathlib`, `shutil`, `argparse`, `subprocess`, `datetime`, `tempfile` instead of `find`, `sed -i`, `command -v`, `date -d`, heredocs, `mktemp`. Removes fragile BSD-vs-GNU hacks.
- External CLIs (`git`, `enonic`, `npm`, …) are still fine via `subprocess`. Porting moves the **orchestration** to Python; it does not reimplement the CLI.

Shell is still fine for: trivial one-line wrappers around a real `.py`; genuine shell-native tools with no clean Python substitute (e.g. ImageMagick pipelines); container entrypoints/runtime scripts that must run where `python3` may be absent (e.g. a Docker `launcher.sh` shipped into generated projects).
