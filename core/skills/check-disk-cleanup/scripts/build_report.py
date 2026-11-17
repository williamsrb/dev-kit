#!/usr/bin/env python3
"""Build the HTML disk clean-up report from the agentctl disk cache (read-only, no scan)."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "assets" / "report-template.html"
DEFAULT_OUT = (
    Path.home() / ".local" / "state" / "agentctl-disk" / "disk-cleanup-report.html"
)
HOME = str(Path.home())

# agentctl rates these node_modules "safe", but they belong to installed apps and are not rebuilt.
APP_RUNTIME = ["/.local/portable/", "/.config/Lens/node_modules", "/.p2/pool/plugins/"]
# Large files in these places are installed software, toolchains, app data or git history.
INSTALLED = [
    "/usr/",
    "/opt/",
    "/boot/",
    "/var/lib/containerd",
    "/var/lib/docker",
    "/var/lib/apt/",
    "/root/.local/",
] + [
    HOME + p
    for p in [
        "/.nvm/",
        "/.codex/",
        "/.enonic/",
        "/.serena/",
        "/.rustup/",
        "/.jdks/",
        "/.local/jdk/",
        "/.local/bin/",
        "/.local/portable/",
        "/.local/state/",
        "/.gradle/wrapper/",
        "/.mozilla/",
        "/.thunderbird/",
        "/.agent-browser/",
        "/.wine/",
        "/.sonar/",
        "/.agents/graft/",
        "/.cargo/",
        "/.config/",
        "/.local/share/",
        "/.vscode/",
        "/.cursor/",
        "/.m2/",
        "/.p2/",
        "/.android/",
        "/snap/",
    ]
]
INSTALLED_PARTS = ["/.git/objects/", "/.gradle/nodejs/"]
LABELS = {"home": "/home (your files)", "root": "/ (system)"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render every finding of `agentctl disk report` for the given targets into one HTML page. "
        "Reads the scan cache only; deletes nothing.",
        epilog="Refresh: agentctl disk scan --all --background; agentctl disk status; then run this again.",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        default=["home", "root"],
        help="agentctl disk targets (default: home root).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"HTML file to write (default: {DEFAULT_OUT}).",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    data = {
        "home": HOME,
        "generated": datetime.now(UTC).isoformat(),
        "disks": [],
        "items": [],
        "refresh": refresh_commands(args),
    }
    for target in args.targets:
        report = agentctl_report(target)
        if report.get("status") != "ok":
            print(
                f"{target}: status {report.get('status')}; next: {report.get('next')}",
                file=sys.stderr,
            )
            return 1
        add_target(data, target, report)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    args.out.write_text(TEMPLATE.read_text().replace("/*DATA*/", payload))
    print(
        json.dumps(
            {
                "status": "ok",
                "out": str(args.out),
                "targets": args.targets,
                "findings": len(data["items"]),
                "refresh": [r["cmd"] for r in data["refresh"]],
            }
        )
    )
    return 0


def refresh_commands(args: argparse.Namespace) -> list[dict]:
    rebuild = ["python3", str(Path(__file__).resolve()), *args.targets]
    if args.out != DEFAULT_OUT:
        rebuild += ["--out", str(args.out.resolve())]
    return [
        {
            "why": "1. Rescan every disk in the background.",
            "cmd": "agentctl disk scan --all --background",
        },
        {
            "why": "2. Wait until every target shows state finished.",
            "cmd": "agentctl disk status",
        },
        {"why": "3. Rebuild this page from the new scan.", "cmd": shlex.join(rebuild)},
    ]


def agentctl_report(target: str) -> dict:
    proc = subprocess.run(
        [
            "agentctl",
            "disk",
            "report",
            target,
            "--limit",
            "1000",
            "--max-bytes",
            "50000000",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if not proc.stdout.strip():
        raise SystemExit(f"agentctl disk report {target} failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def add_target(data: dict, target: str, report: dict) -> None:
    summary = report["summary"]
    if report["truncated"]["shown"] < report["truncated"]["total"]:
        print(
            f"{target}: page shows {report['truncated']['shown']} of {report['truncated']['total']} findings",
            file=sys.stderr,
        )
    data["disks"].append(
        {
            "id": target,
            "mount": summary["mount"],
            "label": LABELS.get(target, summary["mount"]),
            "device": summary["device"],
            **summary["disk"],
            "scanned": summary["cache"]["scanned_at"],
            "danger": summary["reclaimable"].get("danger", 0),
        }
    )
    findings = report["findings"]
    # The reserved-blocks finding sits at the mount point, so it would count as the parent of everything.
    parents = [
        f["path"]
        for f in findings
        if f["category"] != "system" and f["path"].startswith("/")
    ]
    for f in findings:
        data["items"].append(
            {
                "id": f["id"],
                "disk": target,
                "cat": f["category"],
                "title": f["title"],
                "path": f["path"],
                "bytes": f["bytes"],
                "last": (f.get("last_used") or {}).get("at"),
                "risk": f["risk"],
                "bucket": verdict(f),
                "sudo": f["needs_sudo"],
                "reversible": f["reversible"],
                "cmd": f.get("suggested_command"),
                "verify": f.get("verify_command"),
                "evidence": f.get("evidence"),
                "inside": next(
                    (
                        p
                        for p in parents
                        if p != f["path"] and f["path"].startswith(p.rstrip("/") + "/")
                    ),
                    None,
                ),
            }
        )


def verdict(finding: dict) -> str:
    path = finding["path"]
    if any(s in path for s in APP_RUNTIME):
        return "leave"
    if finding["risk"] == "safe":
        return "safe"
    if finding["risk"] == "danger":
        return "leave"
    if finding["category"] == "big-files" and (
        any(path.startswith(p) for p in INSTALLED)
        or any(s in path for s in INSTALLED_PARTS)
    ):
        return "leave"
    return "decide"


if __name__ == "__main__":
    sys.exit(main())
