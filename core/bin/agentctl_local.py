"""Local-model backend choice: Ollama when it can serve the model, else the ROLES.md `deterministic` Claude cell."""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import agentctl_bench
from agentctl_common import agents_home, run

DEFAULT_HOST = "http://localhost:11434"
TAGS_TIMEOUT_S = 3.0
PREVIEW_EDGE = 1280


def ollama_host() -> str:
    host = os.environ.get("OLLAMA_HOST") or DEFAULT_HOST
    return host if "://" in host else f"http://{host}"


def ollama_models() -> list[dict[str, str]]:
    ollama = shutil.which("ollama")
    if not ollama:
        return []
    result = run([ollama, "list"])
    models = []
    for line in result.stdout.splitlines()[1:]:
        parts = line.split()
        if parts:
            models.append({"name": parts[0], "id": parts[1] if len(parts) > 1 else ""})
    return models


def served_models() -> list[str] | None:
    """Model names the Ollama service reports, or None when it does not answer."""
    try:
        with urllib.request.urlopen(f"{ollama_host().rstrip('/')}/api/tags", timeout=TAGS_TIMEOUT_S) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return None
    return [str(m.get("name") or m.get("model") or "") for m in body.get("models") or []]


def ollama_status(model: str) -> tuple[bool, str | None]:
    """(available, reason). Reasons: ollama-missing, service-unreachable, model-not-pulled."""
    if not shutil.which("ollama"):
        return False, "ollama-missing"
    names = served_models()
    if names is None:
        return False, "service-unreachable"
    wanted = {model, f"{model}:latest"} if ":" not in model else {model}
    return (True, None) if wanted & set(names) else (False, "model-not-pulled")


def fallback_cell() -> dict[str, str]:
    """Model and effort of the ROLES.md `deterministic` role, Claude column."""
    cell = agentctl_bench.read_role_cells(agents_home() / "skills-vendor" / "ROLES.md").get(("deterministic", "claude"))
    parts = re.findall(r"`([^`]+)`", cell or "")
    if not parts:
        raise RuntimeError(f"ROLES.md has no readable deterministic/claude cell: {cell!r}")
    return {"model": parts[0], "effort": parts[1] if len(parts) > 1 else "medium"}


def claude_fallback(prompt: str, system: str, *, image_dir: Path | None = None, timeout: float = 180,
                    budget_usd: float = 0.25) -> dict[str, Any]:
    """One stripped headless call: no user settings, hooks, CLAUDE.md or MCP, which would leak the operator's
    reply format into the output and cost far more. Read is the only tool, and only for an image folder."""
    claude = shutil.which("claude")
    cell = fallback_cell()
    if not claude:
        return {"ok": False, "error": "claude CLI not on PATH", "model": cell["model"]}
    # The prompt goes right after -p: --tools and --add-dir take several values and would swallow a trailing one.
    argv = [claude, "-p", prompt, "--model", cell["model"], "--effort", cell["effort"], "--output-format", "json",
            "--setting-sources", "", "--strict-mcp-config", "--max-budget-usd", f"{budget_usd:.2f}",
            "--system-prompt", system]
    if image_dir is not None:
        argv += ["--tools", "Read", "--allowedTools", "Read", "--add-dir", str(image_dir)]
    else:
        argv += ["--tools", ""]
    result = run(argv, cwd=image_dir or Path(tempfile.gettempdir()), timeout=timeout)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "model": cell["model"], "error": (result.stderr or result.stdout).strip()[:500]}
    text = str(payload.get("result", ""))
    ok = result.returncode == 0 and not payload.get("is_error")
    return {"ok": ok, "text": text, "model": cell["model"], "effort": cell["effort"],
            "duration_ms": payload.get("duration_ms"), "cost_usd": payload.get("total_cost_usd"),
            "error": None if ok else text[:500]}


def preview(image: Path, folder: Path) -> Path:
    """Sidecar capped at PREVIEW_EDGE px on the long edge; the original when already small or no ImageMagick."""
    identify, convert = shutil.which("identify"), shutil.which("convert")
    if not (identify and convert):
        return image
    size = run([identify, "-format", "%w %h", f"{image}[0]"])
    if size.returncode != 0 or max(map(int, size.stdout.split())) <= PREVIEW_EDGE:
        return image
    sidecar = folder / f"{image.stem}.preview.png"
    run([convert, f"{image}[0]", "-resize", f"{PREVIEW_EDGE}x{PREVIEW_EDGE}>", str(sidecar)], check=True)
    return sidecar


def describer_prompt() -> str:
    """Body of the image-describer subagent, so the CLI fallback and the subagent share one prompt."""
    text = (agents_home() / "agents" / "image-describer.md").read_text(encoding="utf-8")
    return text.split("---", 2)[2].strip() if text.startswith("---") else text.strip()
