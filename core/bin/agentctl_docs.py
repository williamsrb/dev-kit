"""Local Ollama inference and Markdown FTS for agentctl."""

from __future__ import annotations

import argparse
import re
import shutil
import sqlite3
import sys
from pathlib import Path

from agentctl_common import argsafe_limit, emit, run


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


def cmd_local_models(args: argparse.Namespace) -> int:
    models = ollama_models()
    emit({"available": bool(shutil.which("ollama")), "models": models})
    return 0


def cmd_local_run(args: argparse.Namespace) -> int:
    ollama = shutil.which("ollama")
    if not ollama:
        emit({"status": "ollama-missing"})
        return 2
    if args.file:
        content = args.file.read_text(encoding="utf-8", errors="replace")
    elif args.text is not None:
        content = args.text
    else:
        content = sys.stdin.read()
    content = content[: argsafe_limit(args.max_chars)]
    prompt = f"{args.instruction.strip()}\n\nINPUT:\n{content}"
    result = run([ollama, "run", args.model], input_text=prompt)
    clean_stderr = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", result.stderr)
    emit({"status": "ok" if result.returncode == 0 else "error", "model": args.model,
          "input_chars": len(content), "output": result.stdout[: argsafe_limit(args.max_output_chars)],
          "stderr": clean_stderr[:1000] if result.returncode else "", "exit_code": result.returncode})
    return result.returncode


def cmd_docs_index(args: argparse.Namespace) -> int:
    database = args.db.expanduser().resolve()
    database.parent.mkdir(parents=True, exist_ok=True)
    roots = [path.expanduser().resolve() for path in args.root]
    documents: list[tuple[str, str, str]] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            if path.name == "llm-index.md":
                continue
            body = path.read_text(encoding="utf-8", errors="replace")
            title = next(
                (line.lstrip("#").strip() for line in body.splitlines() if line.startswith("#")),
                path.stem,
            )
            documents.append((str(path), title, body))
    connection = sqlite3.connect(database)
    try:
        connection.execute("DROP TABLE IF EXISTS docs")
        connection.execute(
            "CREATE VIRTUAL TABLE docs USING fts5("
            "path UNINDEXED, title, body, tokenize='unicode61 remove_diacritics 2')"
        )
        connection.executemany("INSERT INTO docs(path, title, body) VALUES (?, ?, ?)", documents)
        connection.commit()
        optimize_error = None
        try:
            connection.execute("INSERT INTO docs(docs) VALUES ('optimize')")
        except sqlite3.DatabaseError as exc:
            optimize_error = str(exc)
    finally:
        connection.close()
    emit({"status": "indexed", "database": str(database), "roots": [str(path) for path in roots],
          "documents": len(documents), "optimize_error": optimize_error})
    return 0


def cmd_docs_search(args: argparse.Namespace) -> int:
    database = args.db.expanduser().resolve()
    if not database.is_file():
        emit({"status": "missing-index", "database": str(database)})
        return 2
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    tokens = re.findall(r"[\w.]+", args.query, re.UNICODE)
    fts_query = args.query if args.raw_fts else " ".join(f'"{token}"' for token in tokens)
    if not fts_query:
        emit({"status": "query-error", "database": str(database), "error": "empty query"})
        return 2
    try:
        rows = connection.execute(
            "SELECT path, title, snippet(docs, 2, '[', ']', ' … ', 24) AS snippet, "
            "bm25(docs, 0.0, 2.0, 1.0) AS score FROM docs WHERE docs MATCH ? "
            "ORDER BY score LIMIT ?",
            (fts_query, args.limit),
        ).fetchall()
    except sqlite3.DatabaseError as exc:
        emit({"status": "query-error", "database": str(database), "error": str(exc)})
        return 2
    finally:
        connection.close()
    emit({"status": "ok", "database": str(database), "query": args.query,
          "fts_query": fts_query,
          "count": len(rows), "results": [dict(row) for row in rows]})
    return 0


def add_local_parsers(group) -> None:
    models = group.add_parser(
        "models",
        help="List installed Ollama models.",
        description="Return installed local model names and sizes without running inference.",
    )
    models.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    models.set_defaults(func=cmd_local_models)
    local_run = group.add_parser(
        "run",
        help="Run bounded low-risk local inference.",
        description=(
            "Send bounded text—not images or authoritative decisions—to a local Ollama model. "
            "Use only for low-risk clustering, classification, or summarization."
        ),
    )
    local_run.add_argument("--model", default="granite3-moe:3b", help="Installed Ollama model.")
    local_run.add_argument("--instruction", required=True, help="Focused operation to perform.")
    local_run.add_argument("--file", type=Path, help="Read input text from this file.")
    local_run.add_argument("--text", help="Inline input text; mutually exclusive with --file.")
    local_run.add_argument("--max-chars", type=int, default=24000, help="Maximum input characters.")
    local_run.add_argument(
        "--max-output-chars", type=int, default=8000, help="Maximum returned output characters."
    )
    local_run.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    local_run.set_defaults(func=cmd_local_run)


def add_docs_parsers(group) -> None:
    docs_index = group.add_parser(
        "index",
        help="Build or refresh an offline documentation index.",
        description="Index Markdown files from one or more roots into a local SQLite FTS database.",
    )
    docs_index.add_argument(
        "--root", type=Path, action="append", required=True, help="Documentation root; repeatable."
    )
    docs_index.add_argument("--db", type=Path, required=True, help="SQLite database path.")
    docs_index.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    docs_index.set_defaults(func=cmd_docs_index)
    docs_search = group.add_parser(
        "search",
        help="Search an offline documentation index.",
        description="Return ranked source paths and bounded matching snippets from SQLite FTS.",
    )
    docs_search.add_argument("query", help="Words or phrase to search for.")
    docs_search.add_argument("--db", type=Path, required=True, help="SQLite database path.")
    docs_search.add_argument("--limit", type=int, default=8, help="Maximum results.")
    docs_search.add_argument("--raw-fts", action="store_true", help="Treat query as SQLite FTS syntax.")
    docs_search.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    docs_search.set_defaults(func=cmd_docs_search)
