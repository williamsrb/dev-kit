"""Local security scan/summarize for agentctl."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from agentctl_common import argsafe_limit, emit, repo_root, run

# Local parity for the group/ci-templates application security baseline (INT-238).
# Tool choice, flags, severity defaults, and skip rules follow
# security-skills/SETTINGS.md; the exclusion list mirrors DS_EXCLUDED_PATHS in
# ci-templates general/gitlab-security-baseline.yml.

SECURITY_OUTPUT_DIR = ".security-local"
SECURITY_SEVERITIES = ("UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL")
SECURITY_CHECKS = ("secrets", "deps", "sast", "iac")
# sast and iac are slow and noisy on first run; they stay opt-in via --check.
SECURITY_DEFAULT_CHECKS = ("secrets", "deps")

DEPENDENCY_LOCKFILES = (
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb",
    "composer.lock", "Gemfile.lock", "go.mod", "Cargo.lock", "poetry.lock",
    "Pipfile.lock", "requirements.txt", "gradle.lockfile",
)

SECURITY_EXCLUDED_DIRS = (
    "vendor", "node_modules", ".gradle", "build", "dist", "test", "tests",
    "spec", "tmp", ".git", SECURITY_OUTPUT_DIR,
)

SOURCE_SUFFIXES = {
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".es6", ".php", ".py",
    ".java", ".kt", ".rb", ".go", ".cs", ".rs", ".scala",
}

# Enonic layouts first (SETTINGS.md): scan sources, never compiled output.
SAST_ROOT_CANDIDATES = ("xp/src", "xp/assets/src", "src", "app", "lib", "packages")
IAC_DIR_CANDIDATES = ("environments", "charts", "chart", "k8s", "kubernetes", "deploy", "terraform", "docker")
IAC_FILE_GLOBS = ("Chart.yaml", "docker-compose*.yml", "docker-compose*.yaml",
                  "compose.yaml", "compose.yml", "*.tf")

SEVERITY_ALIASES = {
    "ERROR": "HIGH", "WARNING": "MEDIUM", "WARN": "MEDIUM", "INFO": "LOW",
    "MODERATE": "MEDIUM", "IMPORTANT": "HIGH", "NONE": "UNKNOWN", "": "UNKNOWN",
}


def normalize_severity(value: Any) -> str:
    text = str(value or "").strip().upper()
    text = SEVERITY_ALIASES.get(text, text)
    return text if text in SECURITY_SEVERITIES else "UNKNOWN"


def severity_from_score(score: Any) -> str:
    try:
        number = float(score)
    except (TypeError, ValueError):
        return "UNKNOWN"
    if number >= 9.0:
        return "CRITICAL"
    if number >= 7.0:
        return "HIGH"
    if number >= 4.0:
        return "MEDIUM"
    return "LOW" if number > 0 else "UNKNOWN"


def security_excluded(root: Path, path: Path) -> bool:
    return any(part in SECURITY_EXCLUDED_DIRS for part in path.relative_to(root).parts)


def dependency_lockfiles(root: Path) -> list[str]:
    found: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or security_excluded(root, path):
            continue
        if path.name in DEPENDENCY_LOCKFILES:
            found.append(str(path.relative_to(root)))
        if len(found) >= 50:
            break
    return sorted(found)


def sast_roots(root: Path) -> list[str]:
    roots = [name for name in SAST_ROOT_CANDIDATES if (root / name).is_dir()]
    if roots:
        return roots
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in SOURCE_SUFFIXES and not security_excluded(root, path):
            return ["."]
    return []


def iac_targets(root: Path) -> list[str]:
    targets = {name for name in IAC_DIR_CANDIDATES if (root / name).is_dir()}
    for pattern in IAC_FILE_GLOBS:
        targets.update(str(path.relative_to(root)) for path in root.glob(pattern))
        targets.update(
            str(path.relative_to(root)) for path in root.glob(f"*/{pattern}")
            if not security_excluded(root, path)
        )
    return sorted(targets)


def security_applicability(root: Path) -> dict[str, dict[str, Any]]:
    lockfiles = dependency_lockfiles(root)
    roots = sast_roots(root)
    iac = iac_targets(root)
    return {
        "secrets": {"applies": True, "targets": ["."], "reason": "always applicable"},
        "deps": {
            "applies": bool(lockfiles), "targets": lockfiles[:20],
            "reason": "lockfile or manifest present" if lockfiles else "no dependency lockfile found",
        },
        "sast": {
            "applies": bool(roots), "targets": roots,
            "reason": "source roots present" if roots else "no scannable source files",
        },
        "iac": {
            "applies": bool(iac), "targets": iac,
            "reason": "deploy or infrastructure definitions present" if iac else "no IaC or deploy files",
        },
    }


def security_plan(check: str, root: Path, out_dir: Path, targets: list[str]) -> dict[str, Any] | None:
    """Tool invocation for one check, or None when no tool is installed."""
    rel_out = out_dir.relative_to(root)
    all_severities = ",".join(SECURITY_SEVERITIES)
    skip_dirs = [arg for name in SECURITY_EXCLUDED_DIRS for arg in ("--skip-dirs", name)]
    if check == "secrets":
        artifact = rel_out / "gitleaks.json"
        # --no-git scans the working tree, which is what SETTINGS.md specifies and the
        # only mode that sees uncommitted changes or a directory that is not a repo.
        # Commit-range scanning (--log-opts) stays a separate pre-push step.
        # --exit-code 0 keeps "found leaks" distinct from "gitleaks crashed".
        return {"tool": "gitleaks", "artifact": artifact, "args": [
            "detect", "--source", ".", "--no-git", "--no-banner", "--redact",
            "--exit-code", "0", "--report-format", "json", "--report-path", str(artifact),
        ]}
    if check == "deps":
        if shutil.which("trivy"):
            artifact = rel_out / "trivy-deps.json"
            return {"tool": "trivy", "artifact": artifact, "args": [
                "fs", "--scanners", "vuln,license", "--severity", all_severities,
                "--format", "json", "--output", str(artifact), *skip_dirs, ".",
            ]}
        artifact = rel_out / "osv-scanner.json"
        return {"tool": "osv-scanner", "artifact": artifact, "args": [
            "scan", "source", "--recursive", "--format", "json",
            "--output-file", str(artifact), ".",
        ]}
    if check == "sast":
        artifact = rel_out / "semgrep.json"
        excludes = [arg for name in SECURITY_EXCLUDED_DIRS for arg in ("--exclude", name)]
        return {"tool": "semgrep", "artifact": artifact, "args": [
            "scan", "--config", "p/ci", "--metrics", "off", "--quiet",
            "--json", "--output", str(artifact), *excludes, *targets,
        ]}
    if check == "iac":
        artifact = rel_out / "trivy-config.json"
        # trivy config takes one target; scan the root and exclude noise instead.
        # Rendered-manifest scanning (helm template) stays a manual step per SETTINGS.md.
        return {"tool": "trivy", "artifact": artifact, "args": [
            "config", "--severity", all_severities, "--format", "json",
            "--output", str(artifact), *skip_dirs, ".",
        ]}
    return None


def findings_from_gitleaks(data: Any) -> list[dict[str, Any]]:
    # Gitleaks reports no severity; a committed secret is treated as HIGH.
    return [{
        "severity": "HIGH",
        "id": item.get("RuleID"),
        "title": item.get("Description"),
        "location": f"{item.get('File')}:{item.get('StartLine')}",
    } for item in (data or []) if isinstance(item, dict)]


def findings_from_trivy(data: Any) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for result in (data or {}).get("Results") or []:
        target = result.get("Target") or ""
        for vuln in result.get("Vulnerabilities") or []:
            findings.append({
                "severity": normalize_severity(vuln.get("Severity")),
                "id": vuln.get("VulnerabilityID"),
                "title": f"{vuln.get('PkgName')} {vuln.get('InstalledVersion')}".strip(),
                "location": target,
            })
        for miscfg in result.get("Misconfigurations") or []:
            findings.append({
                "severity": normalize_severity(miscfg.get("Severity")),
                "id": miscfg.get("ID"),
                "title": miscfg.get("Title"),
                "location": f"{target}:{(miscfg.get('CauseMetadata') or {}).get('StartLine', '')}".rstrip(":"),
            })
    return findings


def findings_from_osv(data: Any) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for result in (data or {}).get("results") or []:
        source = (result.get("source") or {}).get("path") or ""
        for package in result.get("packages") or []:
            name = (package.get("package") or {}).get("name") or ""
            scores: dict[str, str] = {}
            for group in package.get("groups") or []:
                bucket = severity_from_score(group.get("max_severity"))
                for identifier in group.get("ids") or []:
                    scores[identifier] = bucket
            for vuln in package.get("vulnerabilities") or []:
                identifier = vuln.get("id")
                severity = normalize_severity((vuln.get("database_specific") or {}).get("severity"))
                if severity == "UNKNOWN":
                    severity = scores.get(identifier, "UNKNOWN")
                findings.append({
                    "severity": severity,
                    "id": identifier,
                    "title": (vuln.get("summary") or name)[:200],
                    "location": f"{source}:{name}".rstrip(":"),
                })
    return findings


def findings_from_semgrep(data: Any) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for item in (data or {}).get("results") or []:
        extra = item.get("extra") or {}
        findings.append({
            "severity": normalize_severity(extra.get("severity")),
            "id": item.get("check_id"),
            "title": (extra.get("message") or "").strip()[:200],
            "location": f"{item.get('path')}:{(item.get('start') or {}).get('line')}",
        })
    return findings


def sniff_report_tool(data: Any) -> str | None:
    if isinstance(data, list):
        return "gitleaks" if not data or "RuleID" in (data[0] or {}) else None
    if not isinstance(data, dict):
        return None
    if "Results" in data:
        return "trivy"
    results = data.get("results")
    if isinstance(results, list):
        if any("check_id" in item for item in results if isinstance(item, dict)):
            return "semgrep"
        if any("source" in item for item in results if isinstance(item, dict)):
            return "osv-scanner"
        return "semgrep" if "paths" in data else "osv-scanner"
    return None


def relative_location(location: str, root: Path | None) -> str:
    if not root or not location:
        return location
    prefix = f"{root}/"
    return location.removeprefix(prefix)


def read_findings(path: Path, root: Path | None = None) -> tuple[str | None, list[dict[str, Any]]]:
    if not path.is_file() or not path.stat().st_size:
        return None, []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None, []
    tool = sniff_report_tool(data)
    readers = {
        "gitleaks": findings_from_gitleaks,
        "trivy": findings_from_trivy,
        "osv-scanner": findings_from_osv,
        "semgrep": findings_from_semgrep,
    }
    reader = readers.get(tool or "")
    if not reader:
        return tool, []
    findings = reader(data)
    for item in findings:
        item["location"] = relative_location(item["location"], root)
    return tool, findings


def summarize_findings(findings: list[dict[str, Any]], top: int) -> dict[str, Any]:
    counts = {name: 0 for name in SECURITY_SEVERITIES}
    for item in findings:
        counts[item["severity"]] = counts.get(item["severity"], 0) + 1
    ranked = sorted(findings, key=lambda item: -SECURITY_SEVERITIES.index(item["severity"]))
    return {"total": len(findings), "by_severity": counts, "top": ranked[:argsafe_limit(top)]}


def gate_tripped(counts: dict[str, int], fail_on: str | None) -> bool:
    if not fail_on:
        return False
    threshold = SECURITY_SEVERITIES.index(normalize_severity(fail_on))
    return any(
        count > 0 for name, count in counts.items()
        if SECURITY_SEVERITIES.index(name) >= threshold
    )


def cmd_security_detect(args: argparse.Namespace) -> int:
    cwd = args.cwd.resolve()
    root = repo_root(cwd) or cwd
    applicability = security_applicability(root)
    emit({
        "root": str(root),
        "default_checks": list(SECURITY_DEFAULT_CHECKS),
        "opt_in_checks": [name for name in SECURITY_CHECKS if name not in SECURITY_DEFAULT_CHECKS],
        "applicable": [name for name, item in applicability.items() if item["applies"]],
        "checks": applicability,
    })
    return 0


def cmd_security_scan(args: argparse.Namespace) -> int:
    cwd = args.cwd.resolve()
    root = repo_root(cwd) or cwd
    requested = [name.strip() for name in args.check.split(",") if name.strip()]
    unknown = [name for name in requested if name not in SECURITY_CHECKS]
    if unknown:
        emit({"status": "error", "error": f"unknown checks: {', '.join(unknown)}",
              "valid": list(SECURITY_CHECKS)})
        return 1
    out_dir = root / SECURITY_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    applicability = security_applicability(root)
    totals = {name: 0 for name in SECURITY_SEVERITIES}
    checks: list[dict[str, Any]] = []
    for name in requested:
        applies = applicability[name]
        if not applies["applies"]:
            checks.append({"check": name, "status": "skipped", "reason": applies["reason"]})
            continue
        plan = security_plan(name, root, out_dir, applies["targets"])
        executable = shutil.which(plan["tool"])
        if not executable:
            checks.append({"check": name, "status": "unavailable", "tool": plan["tool"]})
            continue
        artifact = root / plan["artifact"]
        artifact.unlink(missing_ok=True)
        result = run([executable, *plan["args"]], cwd=root, timeout=args.timeout)
        tool, findings = read_findings(artifact, root)
        summary = summarize_findings(findings, args.top)
        for severity, count in summary["by_severity"].items():
            totals[severity] += count
        produced = artifact.is_file() and artifact.stat().st_size > 0
        entry = {
            "check": name,
            "status": "completed" if produced else "error",
            "tool": tool or plan["tool"],
            "exit_code": result.returncode,
            "artifact": str(artifact),
            "targets": applies["targets"][:20],
            **summary,
        }
        if not produced:
            stderr = (result.stderr or result.stdout or "").strip()
            entry["error"] = stderr[: argsafe_limit(args.max_output_chars)] or "no report produced"
        checks.append(entry)
    errored = [item["check"] for item in checks if item["status"] == "error"]
    tripped = gate_tripped(totals, args.fail_on)
    emit({
        "root": str(root),
        "output_dir": str(out_dir),
        "gitignored": SECURITY_OUTPUT_DIR in (root / ".gitignore").read_text(encoding="utf-8")
        if (root / ".gitignore").is_file() else False,
        "requested": requested,
        "totals": totals,
        "fail_on": args.fail_on,
        "gate_tripped": tripped,
        "errored": errored,
        "checks": checks,
    })
    return 2 if tripped or errored else 0


def cmd_security_summarize(args: argparse.Namespace) -> int:
    tool, findings = read_findings(args.report.resolve())
    if tool is None:
        emit({"status": "error", "report": str(args.report),
              "error": "unrecognized or empty report; expected gitleaks, trivy, osv-scanner, or semgrep JSON"})
        return 1
    summary = summarize_findings(findings, args.top)
    tripped = gate_tripped(summary["by_severity"], args.fail_on)
    emit({"report": str(args.report), "tool": tool, "fail_on": args.fail_on,
          "gate_tripped": tripped, **summary})
    return 2 if tripped else 0


def add_security_parsers(group) -> None:
    sec_detect = group.add_parser(
        "detect",
        help="Report which security checks apply to this repository.",
        description=(
            "Detect applicable security checks from repository contents: lockfiles "
            "for dependency scanning, source roots for SAST, deploy and chart files "
            "for IaC. Returns the skip reason for every check that does not apply."
        ),
    )
    sec_detect.add_argument("--cwd", type=Path, default=Path.cwd(), help="Repository directory.")
    sec_detect.set_defaults(func=cmd_security_detect)

    sec_scan = group.add_parser(
        "scan",
        help="Run selected security scans and return bounded findings.",
        description=(
            "Run local scans, keep raw tool reports in .security-local/, and return "
            "severity counts plus the highest-severity findings. Secrets and "
            "dependency scanning run by default; sast and iac are slower and noisier "
            "and only run when named in --check. A missing tool reports "
            "'unavailable' rather than failing the run."
        ),
    )
    sec_scan.add_argument("--cwd", type=Path, default=Path.cwd(), help="Repository directory.")
    sec_scan.add_argument(
        "--check", default=",".join(SECURITY_DEFAULT_CHECKS),
        help="Comma-separated checks to run: " + ", ".join(SECURITY_CHECKS) + ".",
    )
    sec_scan.add_argument(
        "--fail-on", choices=SECURITY_SEVERITIES, default=None,
        help="Exit 2 when a finding at or above this severity exists.",
    )
    sec_scan.add_argument("--top", type=int, default=10, help="Findings returned per check.")
    sec_scan.add_argument("--timeout", type=float, default=900.0, help="Per-tool timeout in seconds.")
    sec_scan.add_argument(
        "--max-output-chars", type=int, default=4000, help="Maximum captured error output per check."
    )
    sec_scan.set_defaults(func=cmd_security_scan)

    sec_summarize = group.add_parser(
        "summarize",
        help="Normalize a gitleaks, trivy, osv-scanner, or semgrep JSON report.",
        description=(
            "Read a raw scanner report and return severity counts plus the "
            "highest-severity findings, so a full multi-megabyte report never "
            "has to enter the model context."
        ),
    )
    sec_summarize.add_argument("report", type=Path, help="Path to the scanner JSON report.")
    sec_summarize.add_argument("--top", type=int, default=20, help="Findings returned.")
    sec_summarize.add_argument(
        "--fail-on", choices=SECURITY_SEVERITIES, default=None,
        help="Exit 2 when a finding at or above this severity exists.",
    )
    sec_summarize.set_defaults(func=cmd_security_summarize)

