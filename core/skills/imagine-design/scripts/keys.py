#!/usr/bin/env python3
"""Provider credentials for the imagine-design skill: status, run, init.

Keys live in ~/.agents/.auth/<provider>-api-key.yaml (mode 600). This script
reports which providers are usable and runs a command with a provider's key in
its environment. It never prints a key. Exit codes: 0 ok, 2 bad input or no key;
`run` returns the command's own exit code.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

PLACEHOLDER = "REPLACE_ME"

# env: file field -> environment variable the provider's docs use
# derived: extra variable built from the fields (SDKs that want "id:secret" in one variable)
PROVIDERS: dict[str, dict] = {
    "bfl": {"name": "Black Forest Labs (FLUX)", "env": {"api_key": "BFL_API_KEY"},
            "docs": "https://docs.bfl.ml"},
    "cloudflare": {"name": "Cloudflare Workers AI", "env": {"account_id": "CLOUDFLARE_ACCOUNT_ID", "api_token": "CLOUDFLARE_API_TOKEN"},
                   "docs": "https://developers.cloudflare.com/workers-ai/get-started/rest-api/"},
    "elevenlabs": {"name": "ElevenLabs", "env": {"api_key": "ELEVENLABS_API_KEY"},
                   "docs": "https://elevenlabs.io/docs"},
    "fal": {"name": "fal.ai", "env": {"api_key": "FAL_KEY"},
            "docs": "https://fal.ai/docs/documentation/quickstart"},
    "gemini": {"name": "Google Gemini API", "env": {"api_key": "GEMINI_API_KEY"},
               "docs": "https://ai.google.dev/gemini-api/docs/image-generation"},
    "higgsfield": {"name": "Higgsfield", "env": {"api_key_id": "HF_API_KEY_ID", "api_key_secret": "HF_API_KEY_SECRET"},
                   "derived": {"HF_KEY": "{api_key_id}:{api_key_secret}", "HF_CREDENTIALS": "{api_key_id}:{api_key_secret}"},
                   "docs": "https://docs.higgsfield.ai/docs/authentication.md"},
    "meshy": {"name": "Meshy", "env": {"api_key": "MESHY_API_KEY"},
              "docs": "https://docs.meshy.ai"},
    "openai": {"name": "OpenAI", "env": {"api_key": "OPENAI_API_KEY"},
               "docs": "https://developers.openai.com/api/docs/guides/image-generation"},
    "pixellab": {"name": "PixelLab", "env": {"api_key": "PIXELLAB_SECRET"},
                 "docs": "https://api.pixellab.ai/v2/llms.txt"},
    "recraft": {"name": "Recraft", "env": {"api_key": "RECRAFT_API_TOKEN"},
                "docs": "https://www.recraft.ai/docs/api-reference/agents"},
    "replicate": {"name": "Replicate", "env": {"api_key": "REPLICATE_API_TOKEN"},
                  "docs": "https://replicate.com/docs"},
    "retro-diffusion": {"name": "Retro Diffusion", "env": {"api_key": "RD_API_KEY"},
                        "docs": "https://github.com/Retro-Diffusion/api-examples"},
    "scenario": {"name": "Scenario", "env": {"api_key": "SCENARIO_API_KEY", "api_secret": "SCENARIO_API_SECRET"},
                 "docs": "https://docs.scenario.com"},
    "stability": {"name": "Stability AI", "env": {"api_key": "STABILITY_API_KEY"},
                  "docs": "https://docs.stability.ai"},
    "tripo": {"name": "Tripo", "env": {"api_key": "TRIPO_API_KEY"},
              "docs": "https://github.com/VAST-AI-Research/tripo-python-sdk"},
}


class BadInput(Exception):
    pass


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except BadInput as exc:
        print(f"keys: {exc}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="keys.py", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(required=False)

    status = sub.add_parser("status", help="Which providers have a key, a placeholder, or nothing.")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)

    run = sub.add_parser("run", help="Run a command with the provider's key exported (usage: run <provider> -- cmd ...).")
    run.add_argument("provider", choices=sorted(PROVIDERS))
    run.add_argument("command", nargs=argparse.REMAINDER)
    run.set_defaults(func=cmd_run)

    init = sub.add_parser("init", help="Create missing placeholder files (mode 600); never overwrite.")
    init.add_argument("--provider", action="append", choices=sorted(PROVIDERS), help="default: all")
    init.set_defaults(func=cmd_init)
    return parser


def cmd_status(args: argparse.Namespace) -> int:
    rows = [provider_status(pid) for pid in sorted(PROVIDERS)]
    if args.json:
        print(json.dumps({"auth_dir": str(auth_dir()), "providers": rows}, indent=2))
    else:
        for row in rows:
            warn = "" if row["mode_ok"] in (True, None) else "  (mode is not 600)"
            print(f"{row['provider']:<16}{row['state']:<13}{row['file']}{warn}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        raise BadInput("nothing to run; usage: run <provider> -- cmd ...")
    row = provider_status(args.provider)
    if row["state"] != "configured":
        raise BadInput(f"{args.provider} is {row['state']}: fill {row['file']} (how to get a key: {PROVIDERS[args.provider]['docs']})")
    values = read_fields(auth_file(args.provider))
    env = dict(os.environ)
    for field, var in PROVIDERS[args.provider]["env"].items():
        env[var] = values[field]
    for var, template in PROVIDERS[args.provider].get("derived", {}).items():
        env[var] = template.format(**values)
    return subprocess.run(command, env=env, check=False).returncode


def cmd_init(args: argparse.Namespace) -> int:
    folder = auth_dir()
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    created, kept = [], []
    for pid in args.provider or sorted(PROVIDERS):
        path = auth_file(pid)
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            kept.append(str(path))
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(placeholder_text(pid))
        created.append(str(path))
    print(json.dumps({"created": created, "kept": kept}, indent=2))
    return 0


def provider_status(pid: str) -> dict:
    path = auth_file(pid)
    row = {"provider": pid, "file": str(path), "env": list(PROVIDERS[pid]["env"].values()), "mode_ok": None}
    if not path.is_file():
        return {**row, "state": "missing"}
    row["mode_ok"] = stat.S_IMODE(path.stat().st_mode) == 0o600
    values = read_fields(path)
    filled = all(values.get(field, "") not in ("", PLACEHOLDER) for field in PROVIDERS[pid]["env"])
    return {**row, "state": "configured" if filled else "placeholder"}


def placeholder_text(pid: str) -> str:
    spec = PROVIDERS[pid]
    lines = [
        f"# imagine-design: {spec['name']} credentials. How to get a key: {spec['docs']}",
        f"# Replace {PLACEHOLDER}; keep this file mode 600. Read by keys.py, never by an agent.",
    ]
    lines += [f"{field}: {PLACEHOLDER}" for field in spec["env"]]
    return "\n".join(lines) + "\n"


def read_fields(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def auth_dir() -> Path:
    raw = os.environ.get("AGENTS_HOME")
    return (Path(raw).expanduser() if raw else Path.home() / ".agents") / ".auth"


def auth_file(pid: str) -> Path:
    return auth_dir() / f"{pid}-api-key.yaml"


if __name__ == "__main__":
    sys.exit(main())
