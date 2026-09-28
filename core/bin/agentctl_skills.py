"""Skill metadata audit and SkillSpector scan for agentctl."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
from pathlib import Path
from typing import Any

from agentctl_common import agents_home, emit, run_skill_script
from agentctl_jira import load_yaml_map

TOP_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*:")
EXISTING_DESC_SUFFIX = re.compile(
    r"\s*\|\s*(?:recommendedRole:\s*[a-z0-9-]+(?:\s*\|\s*aliases:\s*[^|]+)?|"
    r"aliases:\s*[^|]+)\.?\s*$"
)


def metadata_description_suffix(role: str | None, aliases: str | None) -> str:
    parts = []
    if role:
        parts.append(f"recommendedRole: {role}")
    if aliases:
        parts.append(f"aliases: {aliases}")
    if not parts:
        return ""
    return " | " + " | ".join(parts) + "."


def extract_description(fm_lines: list[str]) -> str:
    for index, line in enumerate(fm_lines):
        if not line.startswith("description:"):
            continue
        rest = line.split(":", 1)[1].strip()
        if rest in {">", ">-", "|", "|-"}:
            collected = []
            for nxt in fm_lines[index + 1 :]:
                if TOP_KEY.match(nxt) and not nxt.startswith((" ", "\t")):
                    break
                collected.append(nxt.strip())
            return " ".join(item for item in collected if item)
        if len(rest) >= 2 and rest[0] == rest[-1] and rest[0] in {'"', "'"}:
            return rest[1:-1]
        return rest
    return ""


def parse_frontmatter(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return {}
    result: dict[str, Any] = {}
    metadata_lines: list[str] = []
    fm_lines: list[str] = []
    in_metadata = False
    for line in lines[1:]:
        if line == "---":
            break
        fm_lines.append(line)
        if re.match(r"^[A-Za-z][A-Za-z0-9_-]*:", line):
            in_metadata = line.startswith("metadata:")
            key, value = line.split(":", 1)
            result[key] = value.strip().strip("'\"")
        elif in_metadata:
            metadata_lines.append(line)
            stripped = line.strip()
            if stripped.startswith("recommendedRole:"):
                result["recommendedRole"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("aliases:"):
                result["aliases"] = stripped.split(":", 1)[1].strip()
    result["metadata_text"] = "\n".join(metadata_lines)
    result["description"] = extract_description(fm_lines)
    return result


def is_alias_bound_symlink(entry: Path) -> bool:
    if not entry.is_symlink():
        return False
    skill = entry / "SKILL.md"
    if not skill.exists():
        return False
    name = parse_frontmatter(skill).get("name")
    return bool(name) and name != entry.name


def alias_bound_symlinks(root: Path) -> list[str]:
    if not root.is_dir():
        return []
    return sorted(entry.name for entry in root.iterdir() if is_alias_bound_symlink(entry))


def description_suffix_ok(data: dict[str, Any]) -> bool:
    role = data.get("recommendedRole") or None
    aliases = data.get("aliases") or None
    expected = metadata_description_suffix(role, aliases)
    description = (data.get("description") or "").rstrip()
    if not expected:
        return EXISTING_DESC_SUFFIX.search(description) is None
    return description.endswith(expected)


def public_nvidia_auth(path: Path) -> dict[str, Any]:
    raw = load_yaml_map(path)
    key = (
        raw.get("api_key")
        or raw.get("nvidia_inference_key")
        or raw.get("NVIDIA_INFERENCE_KEY")
        or ""
    ).strip()
    expires = raw.get("expires_at") or ""
    expired = False
    if expires:
        try:
            expired = dt.date.fromisoformat(expires[:10]) < dt.datetime.now(dt.timezone.utc).date()
        except ValueError:
            expired = False
    return {
        "path": str(path),
        "user": raw.get("user") or None,
        "key_name": raw.get("key_name") or None,
        "created_at": raw.get("created_at") or None,
        "expires_at": expires or None,
        "expired": expired,
        "key_present": bool(key),
        "world_readable": oct(path.stat().st_mode & 0o777) in {"0o644", "0o664", "0o666", "0o755"},
    }


def cmd_skills_scan(args: argparse.Namespace) -> int:
    script = agents_home() / "skills" / "skillspector" / "scripts" / "scan.py"
    timeout = args.timeout or (600 if args.llm else 180)
    script_args = [args.target, "--max-issues", str(args.max_issues), "--timeout", str(timeout)]
    if args.llm:
        script_args.append("--llm")
    if args.recursive:
        script_args.append("--recursive")
    if args.output:
        script_args += ["--output", str(args.output.expanduser().resolve())]
    if args.baseline:
        script_args += ["--baseline", str(args.baseline.expanduser().resolve())]
    return run_skill_script(script, script_args, timeout=timeout + 30)


def cmd_skills_audit(args: argparse.Namespace) -> int:
    roots = [path.resolve() for path in args.root]
    unique: dict[str, dict[str, Any]] = {}
    leftover_aliases: list[str] = []
    for root in roots:
        leftover_aliases.extend(f"{root}/{name}" for name in alias_bound_symlinks(root))
        if not root.is_dir():
            continue
        for path in root.glob("*/SKILL.md"):
            real = path.resolve()
            key = str(real)
            if key in unique:
                unique[key]["entries"].append(str(path))
                continue
            data = parse_frontmatter(real)
            metadata_text = data.get("metadata_text", "")
            required_match = re.search(r"required:\s*\[([^]]*)\]", metadata_text)
            required_dependencies = []
            if required_match:
                required_dependencies = [
                    value.strip().strip("'\"")
                    for value in required_match.group(1).split(",")
                    if value.strip()
                ]
            unique[key] = {
                "name": data.get("name"),
                "path": key,
                "entries": [str(path)],
                "recommended_role": data.get("recommendedRole") or None,
                "aliases": data.get("aliases") or None,
                "description_suffix_ok": description_suffix_ok(data),
                "disable_model_invocation": data.get("disable-model-invocation") == "true",
                "has_dependency_metadata": "cliDependencies:" in metadata_text,
                "required_dependencies": required_dependencies,
                "missing_required_dependencies": [
                    value for value in required_dependencies if not shutil.which(value)
                ],
                "codex_policy": None,
            }
            policy = real.parent / "agents" / "openai.yaml"
            if policy.is_file():
                policy_text = policy.read_text(encoding="utf-8")
                unique[key]["codex_policy"] = "allow_implicit_invocation: false" in policy_text
    vendor_status: dict[str, Any] = {}
    for vendor in args.vendor:
        vendor_root = vendor.resolve()
        leftover_aliases.extend(
            f"{vendor_root}/{name}" for name in alias_bound_symlinks(vendor_root)
        )
        missing = []
        divergent = []
        suffix_mismatches = []
        for path in vendor_root.glob("*/SKILL.md") if vendor_root.is_dir() else []:
            data = parse_frontmatter(path.resolve())
            if not description_suffix_ok(data):
                suffix_mismatches.append(data.get("name") or path.parent.name)
        for item in unique.values():
            name = item["name"]
            candidate = vendor_root / str(name) / "SKILL.md"
            if not candidate.exists():
                missing.append(name)
            elif candidate.resolve() != Path(item["path"]):
                divergent.append(name)
        vendor_status[str(vendor_root)] = {
            "missing": sorted(missing),
            "divergent": sorted(divergent),
            "description_suffix_mismatches": sorted(set(suffix_mismatches)),
        }
    items = sorted(unique.values(), key=lambda item: str(item["name"]))
    suffix_mismatches = sorted(
        str(item["name"]) for item in items if not item["description_suffix_ok"]
    )
    declared_aliases = sum(
        len([part for part in (item["aliases"] or "").split(",") if part.strip()])
        for item in items
    )
    leftover_aliases = sorted(set(leftover_aliases))
    emit({
        "unique_skills": len(items),
        "alias_entries": len(leftover_aliases),
        "alias_bound_symlinks": leftover_aliases,
        "declared_aliases": declared_aliases,
        "description_suffix_mismatches": suffix_mismatches,
        "manual_only_frontmatter": sum(1 for item in items if item["disable_model_invocation"]),
        "manual_only_codex": sum(1 for item in items if item["codex_policy"]),
        "with_dependency_metadata": sum(1 for item in items if item["has_dependency_metadata"]),
        "missing_required_dependencies": sorted({
            value for item in items for value in item["missing_required_dependencies"]
        }),
        "vendors": vendor_status,
        "skills": items,
    })
    return 2 if leftover_aliases or suffix_mismatches else 0


def add_skills_parsers(group) -> None:
    skill_scan = group.add_parser(
        "scan",
        help="Scan a skill with NVIDIA SkillSpector (static by default).",
        description=(
            "Run NVIDIA SkillSpector and return a bounded JSON verdict. "
            "Default is static analysis only. Pass --llm to add NVIDIA semantic "
            "analysis using ~/.agents/.auth/nvidia-api-key.yaml."
        ),
    )
    skill_scan.add_argument(
        "target",
        help="Skill directory, SKILL.md, zip, or Git URL.",
    )
    skill_scan.add_argument(
        "--llm",
        action="store_true",
        help="Enable NVIDIA semantic analysis.",
    )
    skill_scan.add_argument(
        "--recursive",
        action="store_true",
        help="Scan immediate subdirectories that each contain SKILL.md.",
    )
    skill_scan.add_argument(
        "--output",
        type=Path,
        help="Write the full SkillSpector JSON report here.",
    )
    skill_scan.add_argument(
        "--baseline",
        type=Path,
        help="Suppression baseline YAML or JSON.",
    )
    skill_scan.add_argument(
        "--max-issues",
        type=int,
        default=20,
        help="Maximum issues in the bounded payload.",
    )
    skill_scan.add_argument(
        "--timeout",
        type=int,
        default=0,
        help="Seconds. 0 = 180 static / 600 with --llm.",
    )
    skill_scan.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    skill_scan.set_defaults(func=cmd_skills_scan)
    skill_audit = group.add_parser(
        "audit",
        help="Audit canonical skills and vendor copies.",
        description=(
            "Check that recommendedRole/aliases are pipe-appended on description, "
            "reject leftover alias-bound symlinks, and compare optional vendor skill directories."
        ),
    )
    skill_audit.add_argument(
        "--root", type=Path, action="append", required=True, help="Canonical skill root; repeatable."
    )
    skill_audit.add_argument(
        "--vendor", type=Path, action="append", default=[], help="Vendor skill root to compare; repeatable."
    )
    skill_audit.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    skill_audit.set_defaults(func=cmd_skills_audit)

