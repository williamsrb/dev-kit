"""Benchmark collection for the orchestration role table.

Fetches leaderboards, keeps the raw response under $AGENTS_HOME/.cache/benchmarks,
writes one normalized YAML per source under $AGENTS_HOME/benchmarks/<YYYY-MM>/,
and merges them into $AGENTS_HOME/benchmarks/latest.yaml with one column per source.
`place` converts those columns to one scale to propose the ROLES.md table; `status`
reports how old the collected data is. bin/agentctl only registers the group.
"""

from __future__ import annotations

import argparse
import calendar
import json
import math
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentctl_common import emit
from agentctl_jira import agents_home, load_yaml_map

SCHEMA_VERSION = 2
USER_AGENT = "agentctl-bench/1"
EFFORTS = ("max", "xhigh", "high", "medium", "low")
AA_KEY_PATH = Path(".auth") / "artificial-analysis-api-key.yaml"
ROLES_PATH = Path("skills-vendor") / "ROLES.md"
ROW_KEYS = ("vendor", "model", "effort", "score", "cost_usd")


class BenchError(Exception):
    """User-facing bench command failure."""


def add_bench_parsers(group) -> None:
    collect = group.add_parser(
        "collect",
        help="Fetch benchmark sources and rebuild benchmarks/latest.yaml.",
        description=(
            "Fetch each source, save the raw response under .cache/benchmarks, write "
            "benchmarks/<YYYY-MM>/<source>.yaml, then merge every month's newest "
            "source file plus benchmarks/overrides.yaml into benchmarks/latest.yaml."
        ),
    )
    collect.add_argument(
        "--source",
        action="append",
        choices=[*SOURCES, "all"],
        help="Source to fetch; repeatable (default all). Unfetched sources keep their last file.",
    )
    collect.add_argument("--root", type=Path, help="Harness root (default $AGENTS_HOME).")
    collect.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    collect.set_defaults(func=cmd_collect)

    gaps = group.add_parser(
        "gaps",
        help="Compare ROLES.md models with benchmarks/latest.yaml.",
        description=(
            "List ROLES.md models and which sources cover them, then models from our "
            "vendors that ROLES.md does not name, best score first."
        ),
    )
    gaps.add_argument("--limit", type=int, default=15, help="Max unlisted models (default 15).")
    gaps.add_argument("--root", type=Path, help="Harness root (default $AGENTS_HOME).")
    gaps.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    gaps.set_defaults(func=cmd_gaps)

    status = group.add_parser(
        "status",
        help="Report benchmark age; stale after one calendar month. Never fails.",
        description=(
            "Read generated_at from benchmarks/latest.yaml. stale is true when it is "
            "more than one calendar month old or missing. Always exits 0 so callers "
            "such as orchestrate can warn without blocking."
        ),
    )
    status.add_argument("--root", type=Path, help="Harness root (default $AGENTS_HOME).")
    status.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    status.set_defaults(func=cmd_status)

    place = group.add_parser(
        "place",
        help="Propose the ROLES.md table from consolidated scores and bands.yaml.",
        description=(
            "Convert every source to Terminal-Bench points via shared models, combine "
            "them weighted by confidence, then give each vendor/role the cheapest "
            "harness.yaml config at or above the role's band. Writes "
            "benchmarks/placement.yaml; never edits ROLES.md."
        ),
    )
    place.add_argument("--markdown", action="store_true", help="Print the Roles table and the diff vs ROLES.md.")
    place.add_argument("--root", type=Path, help="Harness root (default $AGENTS_HOME).")
    place.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    place.set_defaults(func=cmd_place)


def cmd_collect(args: argparse.Namespace) -> int:
    root = (args.root or agents_home()).expanduser()
    wanted = list(SOURCES) if not args.source or "all" in args.source else args.source
    aliases = load_aliases(root)
    now = datetime.now(timezone.utc)
    results: dict[str, Any] = {}
    failed = False
    for name in wanted:
        try:
            results[name] = collect_source(root, name, aliases, now)
        except (BenchError, OSError, ValueError) as exc:
            failed = True
            results[name] = {"status": "error", "error": str(exc)}
    latest = write_latest(root, now)
    emit({"status": "error" if failed else "ok", "sources": results, "latest": latest})
    return 1 if failed else 0


def cmd_gaps(args: argparse.Namespace) -> int:
    root = (args.root or agents_home()).expanduser()
    latest_path = root / "benchmarks" / "latest.yaml"
    if not latest_path.is_file():
        raise BenchError(f"{latest_path} missing. Run 'agentctl bench collect' first.")
    rows = load_rows_yaml(latest_path)
    aliases = load_aliases(root)
    emit(role_gaps(read_role_models(root / ROLES_PATH, aliases), rows, args.limit))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = (args.root or agents_home()).expanduser()
    emit(benchmark_status(root / "benchmarks" / "latest.yaml", datetime.now(timezone.utc)))
    return 0


REFRESH_HINT = "agentctl bench collect && agentctl bench place --markdown"


def benchmark_status(latest: Path, now: datetime) -> dict[str, Any]:
    """Age of the oldest source fetch behind latest.yaml; any read problem counts as stale."""
    try:
        collected = _header_value(latest, "collected_at") or _header_value(latest, "generated_at")
        when = datetime.fromisoformat(collected)
    except (OSError, TypeError, ValueError):
        return {"status": "ok", "stale": True, "collected_at": None,
                "warning": f"No readable benchmark data at {latest}. Run: {REFRESH_HINT}"}
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    stale = now > _add_month(when)
    age = (now - when).days
    result = {"status": "ok", "stale": stale, "collected_at": collected, "age_days": age}
    if stale:
        result["warning"] = (
            f"Benchmarks are {age} days old (last collect {when.date().isoformat()}). "
            f"Refresh: {REFRESH_HINT}"
        )
    return result


def _add_month(when: datetime) -> datetime:
    year, month = (when.year + 1, 1) if when.month == 12 else (when.year, when.month + 1)
    return when.replace(year=year, month=month, day=min(when.day, calendar.monthrange(year, month)[1]))


def _header_value(path: Path, key: str) -> Any:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{key}:"):
            return _parse_scalar(line.partition(":")[2].strip())
        if line.startswith("rows:"):
            break
    return None


def cmd_place(args: argparse.Namespace) -> int:
    root = (args.root or agents_home()).expanduser()
    bench = root / "benchmarks"
    for name in ("latest.yaml", "harness.yaml", "bands.yaml"):
        if not (bench / name).is_file():
            raise BenchError(f"{bench / name} missing")
    rows = load_rows_yaml(bench / "latest.yaml")
    fits = fit_families(rows)
    scored = consolidate(rows, fits)
    harness = expand_harness(load_rows_yaml(bench / "harness.yaml", ("vendor", "model", "efforts", "slug")))
    bands = load_yaml_map(bench / "bands.yaml")
    placement = place_roles(scored, harness, bands)
    out = bench / "placement.yaml"
    header = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scale": "Terminal-Bench 4.0 points",
        "frontier": placement["frontier"],
        "fits": {name: f"{fit['transform']} n={fit['n']} loo_rmse={fit['loo_rmse']}" for name, fit in fits.items()},
    }
    write_rows_yaml(out, header, placement["cells"])
    current = read_role_cells(root / ROLES_PATH)
    result: dict[str, Any] = {
        "status": "ok",
        "file": str(out),
        "frontier": placement["frontier"],
        "fits": fits,
        "cells": placement["cells"],
        "changed": [
            {"role": c["role"], "vendor": c["vendor"], "from": current.get((c["role"], c["vendor"])), "to": c["cell"]}
            for c in placement["cells"]
            if current.get((c["role"], c["vendor"])) != c["cell"]
        ],
    }
    if args.markdown:
        emit(render_roles_table(placement["cells"]), as_json=False)
        emit(result["changed"])
        return 0
    emit(result)
    return 0


# Orchestration


def collect_source(root: Path, name: str, aliases: dict[str, str], now: datetime) -> dict[str, Any]:
    source = SOURCES[name]
    raw = source["fetch"](root)
    stamp = now.strftime("%Y-%m-%d")
    raw_path = root / ".cache" / "benchmarks" / f"{stamp}-{name}.{source['ext']}"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(raw, encoding="utf-8")

    parsed = source["parse"](raw)
    rows, skipped = [], []
    for item in parsed:
        model = canonical_model(item["model"], aliases)
        vendor = vendor_of(model)
        if vendor is None:
            skipped.append(model)
            continue
        rows.append({"vendor": vendor, "model": model, **{k: v for k, v in item.items() if k != "model"}})
    rows.sort(key=lambda r: (-(r["score"] if r["score"] is not None else -1), r["model"], r["effort"]))

    out_path = root / "benchmarks" / now.strftime("%Y-%m") / f"{name}.yaml"
    header = {
        "schema_version": SCHEMA_VERSION,
        "benchmark": name,
        "score": source["score"],
        "cost_usd": source["cost"],
        "source": source["url"],
        "fetched_at": now.isoformat(timespec="seconds"),
        "raw": str(raw_path),
    }
    write_rows_yaml(out_path, header, rows)
    return {
        "status": "ok",
        "file": str(out_path),
        "raw": str(raw_path),
        "rows": len(rows),
        "skipped_other_vendors": len(set(skipped)),
    }


def write_latest(root: Path, now: datetime) -> dict[str, Any]:
    bench = root / "benchmarks"
    newest: dict[str, Path] = {}
    for path in sorted(bench.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]/*.yaml")):
        newest[path.stem] = path
    merged: dict[tuple[str, str, str], dict[str, Any]] = {}
    for name, path in sorted(newest.items()):
        for row in load_rows_yaml(path):
            merge_row(merged, row, name)
    overrides = bench / "overrides.yaml"
    if overrides.is_file():
        for row in load_rows_yaml(overrides):
            merge_row(merged, row, "guess")
    rows = sorted(merged.values(), key=lambda r: (r["vendor"], r["model"], effort_rank(r["effort"])))
    fetched = [_header_value(path, "fetched_at") for path in newest.values()]
    header = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now.isoformat(timespec="seconds"),
        "collected_at": min((f for f in fetched if f), default=None),
        "note": "Columns are <source>_score / <source>_cost_usd. Benchmarks differ; compare within a column.",
        "sources": {name: str(path.relative_to(root)) for name, path in sorted(newest.items())},
    }
    out = bench / "latest.yaml"
    write_rows_yaml(out, header, rows)
    return {"file": str(out), "rows": len(rows), "sources": sorted(newest)}


def merge_row(merged: dict, row: dict[str, Any], column: str) -> None:
    """Several harnesses can run one model/effort; the column keeps the best score."""
    key = (row["vendor"], row["model"], row["effort"])
    target = merged.setdefault(key, {"vendor": key[0], "model": key[1], "effort": key[2]})
    score, held = row.get("score"), target.get(f"{column}_score")
    if f"{column}_score" in target and (score is None or (held is not None and held >= score)):
        return
    target[f"{column}_score"] = score
    target[f"{column}_cost_usd"] = row.get("cost_usd")
    for extra in SOURCES.get(column, {}).get("merge_extra", ()):
        target[f"{column}_{extra}"] = row.get(extra)


# Sources


def fetch_deepswe(_root: Path) -> str:
    return http_get(SOURCES["deepswe"]["url"])


def parse_deepswe(raw: str) -> list[dict[str, Any]]:
    data = json.loads(raw)
    rows = data.get("rows")
    if not isinstance(rows, list):
        raise BenchError("deepswe: payload has no 'rows' list")
    out = []
    for row in rows:
        require(row, ("model", "reasoning_effort", "pass_rate", "mean_cost_usd"), "deepswe")
        out.append({
            "model": row["model"],
            "effort": effort_label(row["reasoning_effort"]),
            "score": pct(row["pass_rate"]),
            "cost_usd": money(row["mean_cost_usd"]),
            "harness": row.get("harness"),
            "ci_half": pct(row.get("ci_half")),
            "n": row.get("n_attempted"),
        })
    return out


def fetch_tbench(_root: Path) -> str:
    return http_get(SOURCES["tbench"]["url"])


TBENCH_ROWS_RE = re.compile(r'\\"rows\\":\[')


def parse_tbench(raw: str) -> list[dict[str, Any]]:
    """Rows live in the Next.js flight payload as an escaped JSON array."""
    match = TBENCH_ROWS_RE.search(raw)
    if not match:
        raise BenchError("tbench: leaderboard rows not found in page; layout changed")
    rows = json.loads(_escaped_json_array(raw, match.end() - 1))
    out = []
    for row in rows:
        meta, metrics = row.get("metadata") or {}, row.get("metrics") or {}
        require(metrics, ("accuracy", "total_cost_usd", "n_trials"), "tbench")
        model = (meta.get("model_display") or {}).get("label")
        if not model:
            raise BenchError("tbench: row without model_display.label")
        trials = metrics["n_trials"] or 0
        cost = metrics["total_cost_usd"]
        out.append({
            "model": model,
            "effort": effort_label(meta.get("reasoning_effort")),
            "score": round(float(metrics["accuracy"]), 2),
            "cost_usd": money(cost / trials) if cost and trials else None,
            "harness": (meta.get("agent_display") or {}).get("label"),
            "ci_half": metrics.get("accuracy_ci95_half_width"),
            "n": trials,
            "date": meta.get("date"),
        })
    return out


def _escaped_json_array(text: str, start: int) -> str:
    """Return the JSON text of the escaped array opening at text[start]."""
    depth, in_string, i = 0, False, start
    while i < len(text):
        if text[i] == "\\":
            if text[i + 1 : i + 2] == '"':
                in_string = not in_string
            i += 2
            continue
        if not in_string and text[i] in "[]":
            depth += 1 if text[i] == "[" else -1
            if depth == 0:
                return json.loads(f'"{text[start : i + 1]}"')
        i += 1
    raise BenchError("tbench: unterminated rows array")


def fetch_aa(root: Path) -> str:
    key_path = root / AA_KEY_PATH
    if not key_path.is_file():
        raise BenchError(f"aa: key file {key_path} missing (expects 'token:')")
    token = load_yaml_map(key_path).get("token", "")
    if not token:
        raise BenchError(f"aa: {key_path} has no 'token' value")
    return http_get(SOURCES["aa"]["url"], {"x-api-key": token})


AA_EFFORT_SUFFIX_RE = re.compile(r"-(?:max|xhigh|high|medium|low|non-reasoning|reasoning)$")


def parse_aa(raw: str) -> list[dict[str, Any]]:
    data = json.loads(raw).get("data")
    if not isinstance(data, list):
        raise BenchError("aa: payload has no 'data' list")
    out = []
    for row in data:
        require(row, ("slug", "name", "evaluations"), "aa")
        evals = row["evaluations"] or {}
        coding = evals.get("artificial_analysis_coding_index")
        intel = evals.get("artificial_analysis_intelligence_index")
        tb4 = evals.get("terminalbench_v4_0")
        if coding is None and intel is None and tb4 is None:
            continue
        out.append({
            "model": AA_EFFORT_SUFFIX_RE.sub("", row["slug"]),
            "effort": aa_effort(row["name"]),
            "score": coding,
            "cost_usd": None,
            "intelligence_index": intel,
            "terminalbench_v4_0": pct(tb4),
            "price_1m_blended": (row.get("pricing") or {}).get("price_1m_blended_3_to_1"),
            "release_date": row.get("release_date"),
        })
    return out


SOURCES: dict[str, dict[str, Any]] = {
    "deepswe": {
        "url": "https://deepswe.datacurve.ai/artifacts/v1.1/leaderboard-live.json",
        "ext": "json",
        "score": "pass_rate * 100 (mini-swe-agent, 113 tasks)",
        "cost": "mean_cost_usd per attempt",
        "merge_extra": ("ci_half",),
        "fetch": fetch_deepswe,
        "parse": parse_deepswe,
    },
    "tbench": {
        "url": "https://www.tbench.ai/leaderboard",
        "ext": "html",
        "score": "Terminal-Bench 4.0 accuracy % (vendor harness: Claude Code, Codex, Grok Build)",
        "cost": "total_cost_usd / n_trials",
        "merge_extra": ("ci_half",),
        "fetch": fetch_tbench,
        "parse": parse_tbench,
    },
    "aa": {
        "url": "https://artificialanalysis.ai/api/v2/data/llms/models",
        "ext": "json",
        "score": "Artificial Analysis Coding Index (attribution: https://artificialanalysis.ai/)",
        "cost": "not published per task; see price_1m_blended",
        "merge_extra": ("terminalbench_v4_0", "intelligence_index", "price_1m_blended"),
        "fetch": fetch_aa,
        "parse": parse_aa,
    },
}


# Model and effort naming


def load_aliases(root: Path) -> dict[str, str]:
    path = root / "benchmarks" / "models.yaml"
    return {k.lower(): v for k, v in load_yaml_map(path).items()} if path.is_file() else {}


CLAUDE_FAMILIES = ("opus", "sonnet", "fable", "haiku")


def canonical_model(name: str, aliases: dict[str, str]) -> str:
    """'Opus 5.5', 'claude-opus-5-5' and 'Claude Opus 5.5 (Max)' all become 'claude-opus-5.5'."""
    key = re.sub(r"\s*\(.*\)\s*$", "", name).strip().lower()
    if key in aliases:
        return aliases[key]
    tokens = [t for t in re.split(r"[\s_-]+", key) if t]
    merged: list[str] = []
    for token in tokens:
        if merged and token.isdigit() and len(token) <= 2 and re.fullmatch(r"\d+(?:\.\d+)*", merged[-1]):
            merged[-1] += f".{token}"
        else:
            merged.append(token)
    if merged and merged[0] in CLAUDE_FAMILIES:
        merged.insert(0, "claude")
    model = "-".join(merged)
    return aliases.get(model, model)


def vendor_of(model: str) -> str | None:
    if model.startswith("claude-"):
        return "claude"
    if model.startswith("gpt-"):
        return "codex"
    if model.startswith(("grok-", "composer-")):
        return "cursor"
    return None


def effort_label(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in EFFORTS:
        return text.upper()
    if text in ("none", "non-reasoning", "minimal"):
        return "NONE"
    return "DEFAULT"


def aa_effort(name: str) -> str:
    inner = re.search(r"\(([^)]*)\)\s*$", name)
    if not inner:
        return "DEFAULT"
    parts = [p.strip().lower() for p in inner.group(1).split(",")]
    if "non-reasoning" in parts:
        return "NONE"
    for part in parts:
        if part in EFFORTS:
            return part.upper()
    return "DEFAULT"


def effort_rank(effort: str) -> int:
    order = ("MAX", "XHIGH", "HIGH", "MEDIUM", "LOW", "DEFAULT", "NONE")
    return order.index(effort) if effort in order else len(order)


# ROLES.md comparison


EFFORT_SUFFIX_RE = re.compile(r"-(max|xhigh|high|medium|low)$")
# Scales differ, so rank by one column at a time: vendor-harness runs first.
GAPS_SORT = ("tbench", "deepswe", "aa")


def read_role_models(path: Path, aliases: dict[str, str]) -> list[str]:
    """Model slugs from the Roles table, e.g. `cursor-grok-4.7-medium` -> grok-4.7."""
    if not path.is_file():
        raise BenchError(f"{path} missing")
    models: list[str] = []
    for cell in read_role_cells(path).values():
        slug = re.match(r"`([^`]+)`", cell)
        if not slug or slug.group(1) == "auto":
            continue
        model = canonical_model(EFFORT_SUFFIX_RE.sub("", slug.group(1)), aliases)
        if model not in models:
            models.append(model)
    return models


def role_gaps(role_models: list[str], rows: list[dict[str, Any]], limit: int) -> dict[str, Any]:
    columns = sorted({k[: -len("_score")] for r in rows for k in r if k.endswith("_score")})
    by_model: dict[str, dict[str, float]] = {}
    for row in rows:
        best = by_model.setdefault(row["model"], {})
        for col in columns:
            value = row.get(f"{col}_score")
            if value is not None and value > best.get(col, -1):
                best[col] = value
    listed = [
        {"model": m, "vendor": vendor_of(m), "best": by_model.get(m, {}),
         "missing": [c for c in columns if c != "guess" and c not in by_model.get(m, {})]}
        for m in role_models
    ]
    unlisted = [
        {"model": m, "vendor": vendor_of(m), "best": best}
        for m, best in by_model.items()
        if m not in role_models and set(best) - {"guess"}
    ]
    unlisted.sort(key=lambda r: [-r["best"].get(c, -1) for c in GAPS_SORT])
    return {
        "status": "ok",
        "columns": columns,
        "roles_models": listed,
        "unlisted_models": unlisted[: max(limit, 0)],
        "unlisted_total": len(unlisted),
    }


# Placement: one quality scale, absolute bands, cheapest config per vendor


REFERENCE = "tbench_score"
# Independent evidence groups: latest.yaml columns in preference order, first present wins.
# AA's own Terminal-Bench column only stands in when the real one is missing.
FAMILIES = {
    "tbench": ("tbench_score", "aa_terminalbench_v4_0"),
    "deepswe": ("deepswe_score", "guess_score"),
    "aa": ("aa_intelligence_index",),
}
# guess_score is a hand estimate on the DeepSWE scale; it converts with DeepSWE's fit.
FIT_SOURCE = {"guess_score": "deepswe_score"}
MIN_BRIDGE = 8
DEFAULT_REF_SE = 1.6
ROLE_ORDER = (
    "deterministic", "explore", "follow", "plan", "build", "impl-review", "plan-review", "task-owner", "quality-gate",
)
VENDOR_COLUMNS = ("codex", "claude", "cursor")


def fit_families(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Fit every non-reference column onto Terminal-Bench points over shared configs."""
    fits: dict[str, dict[str, Any]] = {}
    for columns in FAMILIES.values():
        for column in columns:
            if column == REFERENCE or column in FIT_SOURCE:
                continue
            pairs = [(r[column], r[REFERENCE]) for r in rows if r.get(column) is not None and r.get(REFERENCE) is not None]
            if len(pairs) < MIN_BRIDGE:
                continue
            best = min((_fit(pairs, t) for t in TRANSFORMS), key=lambda f: f["loo_rmse"])
            fits[column] = best
    return fits


def consolidate(rows: list[dict[str, Any]], fits: dict[str, dict[str, Any]]) -> dict[tuple, dict[str, Any]]:
    costs = estimate_costs(rows)
    out: dict[tuple, dict[str, Any]] = {}
    for row in rows:
        estimates: dict[str, tuple[float, float]] = {}
        used: dict[str, str] = {}
        guessed = False
        for family, columns in FAMILIES.items():
            for column in columns:
                value = row.get(column)
                if value is None:
                    continue
                if column == REFERENCE:
                    ci = row.get("tbench_ci_half")
                    estimates[family] = (value, ci / 1.96 if ci else DEFAULT_REF_SE)
                else:
                    fit = fits.get(FIT_SOURCE.get(column, column))
                    if fit is None:
                        continue
                    ci = row.get("deepswe_ci_half") if column == "deepswe_score" else None
                    slope = _predict(fit, value + 0.5) - _predict(fit, value - 0.5)
                    se = (fit["loo_rmse"] ** 2 + (slope * (ci or 0) / 1.96) ** 2) ** 0.5
                    estimates[family] = (_predict(fit, value), se)
                    guessed = guessed or column == "guess_score"
                used[family] = column
                break
        if used.get("tbench") == "aa_terminalbench_v4_0" and "aa" in estimates:
            # Both stand-ins are AA measurements; keep the tighter one, not both.
            drop = "aa" if estimates["aa"][1] >= estimates["tbench"][1] else "tbench"
            estimates.pop(drop)
            used.pop(drop)
        if not estimates:
            continue
        weights = {f: 1 / se**2 for f, (_, se) in estimates.items()}
        total = sum(weights.values())
        score = sum(weights[f] * q for f, (q, _) in estimates.items()) / total
        disagree = any(
            abs(a[0] - b[0]) > 2 * (a[1] ** 2 + b[1] ** 2) ** 0.5
            for i, a in enumerate(estimates.values()) for b in list(estimates.values())[i + 1 :]
        )
        key = (row["vendor"], row["model"], row["effort"])
        cost, cost_basis = costs.get(key, (None, None))
        out[key] = {
            "score": round(score, 2),
            "se": round(total ** -0.5, 2),
            "cost_usd": cost,
            "cost_basis": cost_basis,
            "families": sorted(estimates),
            "sources": sorted({column.split("_", 1)[0] for column in used.values()}),
            "guessed": guessed,
            "disagree": disagree,
        }
    return out


def place_roles(scored: dict[tuple, dict[str, Any]], harness: list[dict[str, Any]], bands: dict[str, str]) -> dict[str, Any]:
    measured = [v for v in scored.values() if not v["guessed"]]
    if not measured:
        raise BenchError("no measured scores to set the frontier")
    top = max(measured, key=lambda v: v["score"])
    tie_sigma = float(bands.get("tie_sigma", 2))
    cells = []
    for role in ROLE_ORDER:
        band = bands.get(role)
        if band is None:
            raise BenchError(f"bands.yaml has no '{role}'")
        for vendor in VENDOR_COLUMNS:
            options = []
            for config in (h for h in harness if h["vendor"] == vendor):
                found = scored.get((vendor, config["model"], config["effort"]))
                if found is None:
                    continue
                # The conservative score (one SE below) must clear the floor, so a wide
                # estimate cannot ride its own uncertainty into a band.
                floor = top["score"] - tie_sigma * top["se"] if band == "tie" else float(band) * top["score"]
                options.append((config, found, found["score"] - found["se"] >= floor, floor))
            cells.append(_pick_cell(role, vendor, options))
    return {"frontier": top["score"], "cells": cells}


def _pick_cell(role: str, vendor: str, options: list[tuple]) -> dict[str, Any]:
    cell: dict[str, Any] = {"role": role, "vendor": vendor}
    passing = [o for o in options if o[2]]
    if passing:
        config, found, _, floor = min(
            passing, key=lambda o: (o[1]["cost_usd"] is None, o[1]["cost_usd"] or 0, -o[1]["score"])
        )
        status = "provisional" if found["guessed"] or len(found["sources"]) == 1 else "ok"
    elif options:
        config, found, _, floor = max(options, key=lambda o: o[1]["score"])
        status = "below band"
    else:
        cell.update({"status": "no data", "cell": None})
        return cell
    cell.update({
        "status": status,
        "cell": render_cell(config),
        "model": config["model"],
        "effort": config["effort"],
        "score": found["score"],
        "se": found["se"],
        "floor": round(floor, 2),
        "cost_usd": found["cost_usd"],
        "cost_basis": found["cost_basis"],
        "sources": " ".join(found["sources"]),
        "disagree": found["disagree"],
    })
    return cell


def expand_harness(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """`efforts: "LOW MAX"` becomes one config per effort; `{effort}` fills the slug."""
    out = []
    for row in rows:
        for effort in str(row["efforts"]).split():
            out.append({**row, "effort": effort.upper()})
    return out


def render_cell(config: dict[str, Any]) -> str:
    effort = config["effort"].lower()
    slug = config["slug"]
    if "{effort}" in slug:
        return f"`{slug.replace('{effort}', effort)}`"
    return f"`{slug}` default" if effort == "default" else f"`{slug}` `{effort}`"


def render_roles_table(cells: list[dict[str, Any]]) -> str:
    by_key = {(c["role"], c["vendor"]): c for c in cells}
    lines = ["| Role | Codex | Claude | Cursor |", "|---|---|---|---|"]
    for role in ROLE_ORDER:
        parts = []
        for vendor in VENDOR_COLUMNS:
            c = by_key[(role, vendor)]
            mark = STATUS_MARK.get(c["status"], "")
            parts.append((c["cell"] or "no data") + mark)
        lines.append(f"| `{role}` | " + " | ".join(parts) + " |")
    lines.append("")
    lines.append("† Provisional: one evidence source (mostly Artificial Analysis) or an estimated cost.")
    lines.append("‡ Below band: the vendor has no config at the role's floor; this is its best one.")
    return "\n".join(lines)


STATUS_MARK = {"ok": "", "provisional": " †", "below band": " ‡"}


def read_role_cells(path: Path) -> dict[tuple[str, str], str]:
    """Current ROLES.md cells, without the † / ‡ status marks."""
    cells: dict[tuple[str, str], str] = {}
    if not path.is_file():
        return cells
    in_roles = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            in_roles = line.strip() == "## Roles"
        role = re.match(r"^\|\s*`([a-z-]+)`\s*\|", line)
        if not in_roles or not role or role.group(1) not in ROLE_ORDER:
            continue
        values = [v.strip() for v in line.strip().strip("|").split("|")[1:]]
        for vendor, value in zip(VENDOR_COLUMNS, values):
            cells[(role.group(1), vendor)] = value.removesuffix(" †").removesuffix(" ‡")
    return cells


def _logit(x: float) -> float:
    p = min(max(x / 100, 0.005), 0.995)
    return math.log(p / (1 - p))


def _sigmoid(x: float) -> float:
    return 100 / (1 + math.exp(-x))


TRANSFORMS = {
    "linear": (lambda x: x, lambda y: y, lambda y: y),
    "logit": (_logit, _logit, _sigmoid),
}


def _ols(points: list[tuple[float, float]]) -> tuple[float, float]:
    n = len(points)
    mx = sum(x for x, _ in points) / n
    my = sum(y for _, y in points) / n
    sxx = sum((x - mx) ** 2 for x, _ in points)
    slope = sum((x - mx) * (y - my) for x, y in points) / sxx if sxx else 0.0
    return my - slope * mx, slope


def _fit(pairs: list[tuple[float, float]], transform: str) -> dict[str, Any]:
    fx, fy, inv = TRANSFORMS[transform]
    points = [(fx(x), fy(y)) for x, y in pairs]
    errors = []
    for i in range(len(points)):
        a, b = _ols(points[:i] + points[i + 1 :])
        errors.append(inv(a + b * points[i][0]) - pairs[i][1])
    a, b = _ols(points)
    return {
        "transform": transform,
        "intercept": round(a, 4),
        "slope": round(b, 4),
        "n": len(pairs),
        "loo_rmse": round((sum(e * e for e in errors) / len(errors)) ** 0.5, 2),
    }


def _predict(fit: dict[str, Any], x: float) -> float:
    fx, _, inv = TRANSFORMS[fit["transform"]]
    return min(max(inv(fit["intercept"] + fit["slope"] * fx(x)), 0.0), 100.0)


def _median_cost_ratio(rows: list[dict[str, Any]]) -> float | None:
    ratios = [
        r["tbench_cost_usd"] / r["deepswe_cost_usd"]
        for r in rows
        if r.get("tbench_cost_usd") and r.get("deepswe_cost_usd")
    ]
    return _median(ratios) if len(ratios) >= MIN_BRIDGE else None


def estimate_costs(rows: list[dict[str, Any]]) -> dict[tuple, tuple[float, str]]:
    """Cost per task on the Terminal-Bench scale, most direct basis first.

    measured: Terminal-Bench. converted: DeepSWE or a guess times the median
    Terminal-Bench/DeepSWE ratio. ladder: another effort of the same model times the
    median cost ratio between those efforts. price: AA blended token price times the
    median cost per price unit at that effort.
    """
    ratio = _median_cost_ratio(rows)
    costs: dict[tuple, tuple[float, str]] = {}
    for row in rows:
        key = (row["vendor"], row["model"], row["effort"])
        if row.get("tbench_cost_usd"):
            costs[key] = (round(row["tbench_cost_usd"], 4), "measured")
            continue
        for column in ("deepswe_cost_usd", "guess_cost_usd"):
            if row.get(column) and ratio:
                costs[key] = (round(row[column] * ratio, 4), "converted")
                break
    ladder = _effort_ladder(rows)
    by_model: dict[tuple, dict[str, float]] = {}
    for (vendor, model, effort), (cost, _) in costs.items():
        by_model.setdefault((vendor, model), {})[effort] = cost
    per_price = _median_per_effort(
        (row["effort"], costs[k][0] / row["aa_price_1m_blended"])
        for row in rows
        if (k := (row["vendor"], row["model"], row["effort"])) in costs and row.get("aa_price_1m_blended")
    )
    for row in rows:
        key = (row["vendor"], row["model"], row["effort"])
        if key in costs:
            continue
        known = by_model.get((row["vendor"], row["model"]), {})
        anchors = [e for e in known if e in ladder and row["effort"] in ladder]
        if anchors:
            anchor = min(anchors, key=lambda e: abs(effort_rank(e) - effort_rank(row["effort"])))
            costs[key] = (round(known[anchor] * ladder[row["effort"]] / ladder[anchor], 4), "ladder")
        elif row.get("aa_price_1m_blended") and row["effort"] in per_price:
            costs[key] = (round(row["aa_price_1m_blended"] * per_price[row["effort"]], 4), "price")
    return costs


def _effort_ladder(rows: list[dict[str, Any]]) -> dict[str, float]:
    """Median DeepSWE cost of each effort relative to the same model at MAX."""
    max_cost = {
        (r["vendor"], r["model"]): r["deepswe_cost_usd"]
        for r in rows
        if r["effort"] == "MAX" and r.get("deepswe_cost_usd")
    }
    return _median_per_effort(
        (r["effort"], r["deepswe_cost_usd"] / max_cost[(r["vendor"], r["model"])])
        for r in rows
        if r.get("deepswe_cost_usd") and (r["vendor"], r["model"]) in max_cost
    )


def _median_per_effort(pairs) -> dict[str, float]:
    grouped: dict[str, list[float]] = {}
    for effort, value in pairs:
        grouped.setdefault(effort, []).append(value)
    return {e: _median(v) for e, v in grouped.items() if len(v) >= 3}


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


# YAML subset: a header of scalars / flat maps, then `rows:` as a list of flat maps.


def write_rows_yaml(path: Path, header: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    lines = ["# Generated by `agentctl bench`. Do not edit; edit the source or overrides.yaml."]
    for key, value in header.items():
        if isinstance(value, dict):
            lines.append(f"{key}:")
            lines.extend(f"  {k}: {_scalar(v)}" for k, v in value.items())
        else:
            lines.append(f"{key}: {_scalar(value)}")
    lines.append("rows:" if rows else "rows: []")
    for row in rows:
        ordered = [k for k in ROW_KEYS if k in row] + [k for k in row if k not in ROW_KEYS]
        for i, key in enumerate(ordered):
            lines.append(f"{'- ' if i == 0 else '  '}{key}: {_scalar(row[key])}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_rows_yaml(path: Path, required: tuple[str, ...] = ("vendor", "model", "effort")) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    in_rows = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if not line.startswith((" ", "-")):
            in_rows = line.startswith("rows:")
            continue
        if not in_rows:
            continue
        if line.startswith("- "):
            rows.append({})
            line = line[2:]
        key, _, value = line.strip().partition(":")
        if not rows or not key:
            raise BenchError(f"{path}: cannot parse line {raw!r}")
        rows[-1][key.strip()] = _parse_scalar(value.strip())
    for row in rows:
        missing = [k for k in required if k not in row]
        if missing:
            raise BenchError(f"{path}: row {row} lacks {missing}")
    return rows


def _scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    return json.dumps(str(value), ensure_ascii=False)


def _parse_scalar(text: str) -> Any:
    if text in ("", "null", "~"):
        return None
    if text in ("true", "false"):
        return text == "true"
    if text[0] in "\"'":
        return json.loads(text) if text[0] == '"' else text[1:-1]
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


# Infrastructure


def http_get(url: str, headers: dict[str, str] | None = None) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8")


def require(row: dict, keys: tuple[str, ...], source: str) -> None:
    missing = [k for k in keys if k not in row]
    if missing:
        raise BenchError(f"{source}: row missing {missing}; schema changed")


def pct(value: Any) -> float | None:
    return None if value is None else round(float(value) * 100, 2)


def money(value: Any) -> float | None:
    return None if value is None else round(float(value), 4)
