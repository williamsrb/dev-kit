#!/usr/bin/env python3
"""Run NVIDIA SkillSpector and emit bounded JSON.

Default is static analysis only. --llm loads
~/.agents/.auth/nvidia-api-key.yaml into NVIDIA_INFERENCE_KEY.
Never print the API key.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

NVIDIA_TOKEN_PATH = Path.home() / ".agents" / ".auth" / "nvidia-api-key.yaml"
CACHE_DIR = Path.home() / ".agents" / ".cache" / "skillspector"
SECRET_RE = re.compile(r"nvapi-[A-Za-z0-9_-]+")
ISSUE_KEYS = (
    "id",
    "rule_id",
    "category",
    "severity",
    "confidence",
    "message",
    "explanation",
    "finding",
)
GATE = {
    "SAFE": "allow",
    "CAUTION": "warn",
    "DO_NOT_INSTALL": "block",
}


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))


def redact(text: str) -> str:
    return SECRET_RE.sub("nvapi-[REDACTED]", text)


def clip(value: Any, limit: int = 240) -> Any:
    if not isinstance(value, str):
        return value
    text = redact(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def load_yaml_map(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"invalid credential line in {path}")
        key, _, value = line.partition(":")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        data[key.strip()] = value
    return data


def nvidia_key(path: Path | None = None) -> str:
    env_key = os.environ.get("NVIDIA_INFERENCE_KEY", "").strip()
    if env_key:
        return env_key
    token_path = path or Path(
        os.environ.get("SKILLSPECTOR_NVIDIA_KEY_FILE", NVIDIA_TOKEN_PATH)
    )
    token_path = token_path.expanduser()
    if not token_path.is_file():
        raise FileNotFoundError(
            f"NVIDIA API key file not found: {token_path}. "
            "Expected api_key (or set NVIDIA_INFERENCE_KEY)."
        )
    raw = load_yaml_map(token_path)
    key = (
        raw.get("api_key")
        or raw.get("nvidia_inference_key")
        or raw.get("NVIDIA_INFERENCE_KEY")
        or ""
    ).strip()
    if not key:
        raise ValueError(f"{token_path} must contain api_key")
    return key


def resolve_target(raw: str) -> str:
    if raw.startswith(("http://", "https://", "file://", "git@")):
        return raw
    return str(Path(raw).expanduser().resolve())


def bound_issue(issue: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in ISSUE_KEYS:
        if key in issue:
            out[key] = clip(issue[key], 400 if key in {"explanation", "finding"} else 240)
    location = issue.get("location")
    if isinstance(location, dict):
        out["location"] = {
            "file": clip(location.get("file"), 240),
            "start_line": location.get("start_line"),
        }
    return out


def bound_report(report: dict[str, Any], *, max_issues: int) -> dict[str, Any]:
    issues = report.get("issues") or []
    risk = report.get("risk_assessment") or {}
    recommendation = risk.get("recommendation")
    metadata = report.get("metadata") or {}
    skill = report.get("skill") or {}
    return {
        "skill": {
            "name": skill.get("name"),
            "source": skill.get("source"),
            "scanned_at": skill.get("scanned_at"),
        },
        "risk_assessment": {
            "score": risk.get("score"),
            "severity": risk.get("severity"),
            "recommendation": recommendation,
            "max_issue_severity": risk.get("max_issue_severity"),
        },
        "gate": GATE.get(str(recommendation), "warn"),
        "safe_to_install": recommendation == "SAFE",
        "issue_count": len(issues),
        "issues": [bound_issue(item) for item in issues[:max_issues]],
        "issues_truncated": max(0, len(issues) - max_issues),
        "component_count": len(report.get("components") or []),
        "has_executable_scripts": metadata.get("has_executable_scripts"),
        "skillspector_version": metadata.get("skillspector_version"),
        "llm_requested": metadata.get("llm_requested"),
        "llm_available": metadata.get("llm_available"),
        "llm_error": metadata.get("llm_error"),
        "execution_successful": report.get("execution_successful"),
    }


def report_path_for(target: str, output: Path | None) -> Path:
    if output:
        return output.expanduser().resolve()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(target.rstrip("/")).name).strip("-") or "skill"
    return CACHE_DIR / f"{slug}-{stamp}.json"


def run_scan(args: argparse.Namespace) -> int:
    binary = shutil.which("skillspector")
    if not binary:
        emit({"status": "error", "error": "skillspector CLI is not on PATH"})
        return 2
    target = resolve_target(args.target)
    use_llm = bool(args.llm)
    previous_key = None
    previous_provider = None
    previous_model = None
    if use_llm:
        try:
            key = nvidia_key()
        except (OSError, ValueError) as exc:
            emit({"status": "error", "error": str(exc), "llm_requested": True})
            return 2
        previous_key = os.environ.get("NVIDIA_INFERENCE_KEY")
        previous_provider = os.environ.get("SKILLSPECTOR_PROVIDER")
        previous_model = os.environ.get("SKILLSPECTOR_MODEL")
        os.environ["NVIDIA_INFERENCE_KEY"] = key
        os.environ.setdefault("SKILLSPECTOR_PROVIDER", "nv_build")
        # Bundled nv_build default z-ai/glm-5.2 reached EOL 2026-08-21 (HTTP 410).
        os.environ.setdefault("SKILLSPECTOR_MODEL", "deepseek-ai/deepseek-v4-flash-0731")
    full_report = report_path_for(target, args.output)
    full_report.parent.mkdir(parents=True, exist_ok=True)
    command = [binary, "scan", target, "--format", "json", "--output", str(full_report)]
    if not use_llm:
        command.append("--no-llm")
    if args.recursive:
        command.append("--recursive")
    if args.baseline:
        command += ["--baseline", str(Path(args.baseline).expanduser().resolve())]
    try:
        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=args.timeout,
        )
    except subprocess.TimeoutExpired:
        emit({
            "status": "error",
            "error": f"skillspector timed out after {args.timeout}s",
            "target": target,
            "scan_mode": "llm" if use_llm else "static",
        })
        return 2
    finally:
        if use_llm:
            if previous_key is None:
                os.environ.pop("NVIDIA_INFERENCE_KEY", None)
            else:
                os.environ["NVIDIA_INFERENCE_KEY"] = previous_key
            if previous_provider is None:
                os.environ.pop("SKILLSPECTOR_PROVIDER", None)
            else:
                os.environ["SKILLSPECTOR_PROVIDER"] = previous_provider
            if previous_model is None:
                os.environ.pop("SKILLSPECTOR_MODEL", None)
            else:
                os.environ["SKILLSPECTOR_MODEL"] = previous_model
    stderr = redact(result.stderr or "")[:2000]
    if not full_report.is_file():
        emit({
            "status": "error",
            "error": "skillspector did not write a report",
            "exit_code": result.returncode,
            "stderr": stderr,
            "stdout": redact(result.stdout or "")[:2000],
            "target": target,
        })
        return 2
    try:
        raw = json.loads(full_report.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        emit({
            "status": "error",
            "error": f"report is not JSON: {exc}",
            "report_path": str(full_report),
            "exit_code": result.returncode,
        })
        return 2
    reports = raw if isinstance(raw, list) else [raw]
    bounded = [bound_report(item, max_issues=args.max_issues) for item in reports]
    payload: dict[str, Any] = {
        "status": "ok" if result.returncode in {0, 1} else "error",
        "target": target,
        "scan_mode": "llm" if use_llm else "static",
        "llm_used": bool(
            use_llm
            and any(item.get("llm_available") and not item.get("llm_error") for item in bounded)
        ),
        "report_path": str(full_report),
        "exit_code": result.returncode,
        "count": len(bounded),
        "reports": bounded,
        "stderr": stderr if stderr.strip() else "",
    }
    if len(bounded) == 1:
        payload.update(bounded[0])
    emit(payload)
    return result.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan an agent skill with NVIDIA SkillSpector.")
    parser.add_argument("target", help="Skill directory, SKILL.md, zip, or Git URL.")
    parser.add_argument("--llm", action="store_true", help="Enable NVIDIA semantic analysis.")
    parser.add_argument("--recursive", action="store_true", help="Scan immediate skill subdirectories.")
    parser.add_argument("--output", type=Path, help="Write the full JSON report here.")
    parser.add_argument("--baseline", type=Path, help="Suppression baseline YAML/JSON.")
    parser.add_argument("--max-issues", type=int, default=20, help="Maximum issues in the bounded payload.")
    parser.add_argument("--timeout", type=int, default=180, help="Seconds before aborting the scan.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return run_scan(args)


if __name__ == "__main__":
    raise SystemExit(main())
