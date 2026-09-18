#!/usr/bin/env python3
"""Shared harness hooks: log every Agent chat prompt and result to ~/.agents/history/."""

from __future__ import annotations

import fcntl
import json
import os
import sys
import tempfile
import traceback
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HISTORY_ROOT = Path.home() / '.agents' / 'history'
STATE_DIR = HISTORY_ROOT / '.state'
STATE_FILE = STATE_DIR / 'pending.json'
STATE_LOCK_FILE = STATE_DIR / 'pending.lock'
ERROR_LOG = STATE_DIR / 'hook-errors.log'

# Settled entries older than this are dropped; unresolved ones get a longer grace.
RETENTION_DAYS = 7
STALE_PENDING_DAYS = 30


def log_error(message: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    with ERROR_LOG.open('a', encoding='utf-8') as fh:
        fh.write(f'[{stamp}] {message}\n')


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_datetime(dt: datetime) -> str:
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def path_slug(iso_dt: str) -> str:
    return iso_dt.replace(':', '-')


def parse_iso(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def unique_slug(base_slug: str, day_dir: Path) -> str:
    slug = base_slug
    counter = 1
    while (day_dir / f'{slug}_prompt.md').exists():
        slug = f'{base_slug}_{counter}'
        counter += 1
    return slug


def empty_state() -> dict[str, Any]:
    return {'by_generation': {}, 'conversation_stack': {}}


@contextmanager
def state_lock():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with STATE_LOCK_FILE.open('a', encoding='utf-8') as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def quarantine_state_file(reason: str) -> None:
    """Move an unreadable state file aside so in-flight entries stay recoverable."""
    if not STATE_FILE.exists():
        return
    stamp = utc_now().strftime('%Y%m%dT%H%M%SZ')
    target = STATE_DIR / f'pending.corrupt.{stamp}.json'
    counter = 1
    while target.exists():
        target = STATE_DIR / f'pending.corrupt.{stamp}.{counter}.json'
        counter += 1
    try:
        os.replace(STATE_FILE, target)
        log_error(f'quarantined unreadable state -> {target.name} ({reason})')
    except OSError as exc:
        log_error(f'quarantine failed ({exc}); unreadable state left in place ({reason})')


def load_state_unlocked() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return empty_state()
    try:
        data = json.loads(STATE_FILE.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            quarantine_state_file(f'top-level value is {type(data).__name__}, expected object')
            return empty_state()
        data.setdefault('by_generation', {})
        data.setdefault('conversation_stack', {})
        return data
    except Exception as exc:
        log_error(f'load_state failed: {exc}')
        quarantine_state_file(str(exc))
        return empty_state()


def load_state() -> dict[str, Any]:
    with state_lock():
        return load_state_unlocked()


def save_state_unlocked(state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f'{STATE_FILE.name}.',
        suffix='.tmp',
        dir=str(STATE_DIR),
    )
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fd = -1
            json.dump(state, fh, indent=2, sort_keys=True)
            fh.write('\n')
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, STATE_FILE)
    finally:
        if fd != -1:
            os.close(fd)
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def save_state(state: dict[str, Any]) -> None:
    with state_lock():
        save_state_unlocked(state)


def prune_state(state: dict[str, Any], now: datetime) -> int:
    """Drop entries too old to ever be resolved, so the state file stays flat.

    An entry with an unparseable timestamp is already invisible to resolve_entry's
    ordering, so it counts as infinitely old.
    """
    by_generation = state['by_generation']
    keep: dict[str, Any] = {}
    for generation_id, entry in by_generation.items():
        stamp = parse_iso(str(entry.get('iso_datetime') or ''))
        age_days = float('inf') if stamp is None else (now - stamp).total_seconds() / 86400.0
        limit = STALE_PENDING_DAYS if entry.get('pending') else RETENTION_DAYS
        if age_days <= limit:
            keep[generation_id] = entry

    state['by_generation'] = keep
    state['conversation_stack'] = {
        conversation_id: live
        for conversation_id, generation_ids in state['conversation_stack'].items()
        if (live := [g for g in generation_ids if g in keep])
    }
    return len(by_generation) - len(keep)

def format_attachments(attachments: Any) -> str:
    if not attachments:
        return '_None_'
    lines: list[str] = []
    if isinstance(attachments, list):
        for item in attachments:
            if not isinstance(item, dict):
                lines.append(f'- {item!r}')
                continue
            kind = item.get('type', 'unknown')
            path = item.get('file_path') or item.get('path') or ''
            lines.append(f'- **{kind}**: `{path}`')
    else:
        lines.append(f'- {attachments!r}')
    return '\n'.join(lines) if lines else '_None_'


def format_workspace_roots(roots: Any) -> str:
    if not roots:
        return '_None_'
    if isinstance(roots, list):
        return '\n'.join(f'- `{r}`' for r in roots)
    return f'- `{roots}`'


def write_prompt_file(path: Path, payload: dict[str, Any], iso_dt: str, slug: str) -> None:
    prompt = payload.get('prompt', '')
    body = (
        '---\n'
        f'kind: prompt\n'
        f'iso_datetime: {iso_dt}\n'
        f'path_slug: {slug}\n'
        f'conversation_id: {payload.get("conversation_id", "")}\n'
        f'generation_id: {payload.get("generation_id", "")}\n'
        f'hook_event_name: {payload.get("hook_event_name", "beforeSubmitPrompt")}\n'
        '---\n\n'
        '# Prompt\n\n'
        f'{prompt}\n\n'
        '## Workspace roots\n\n'
        f'{format_workspace_roots(payload.get("workspace_roots"))}\n\n'
        '## Attachments\n\n'
        f'{format_attachments(payload.get("attachments"))}\n'
    )
    path.write_text(body, encoding='utf-8')


def write_result_file(path: Path, text: str, entry: dict[str, Any], payload: dict[str, Any]) -> None:
    body = (
        '---\n'
        f'kind: result\n'
        f'iso_datetime: {entry.get("iso_datetime", "")}\n'
        f'path_slug: {entry.get("slug", "")}\n'
        f'conversation_id: {entry.get("conversation_id", "")}\n'
        f'generation_id: {payload.get("generation_id", entry.get("generation_id", ""))}\n'
        f'hook_event_name: {payload.get("hook_event_name", "")}\n'
        f'status: {payload.get("status", "completed")}\n'
        '---\n\n'
        '# Result\n\n'
        f'{text if text else "_(empty response)_"}\n'
    )
    path.write_text(body, encoding='utf-8')


def register_prompt(payload: dict[str, Any]) -> None:
    with state_lock():
        now = utc_now()
        iso_dt = iso_datetime(now)
        iso_date = now.strftime('%Y-%m-%d')
        base_slug = path_slug(iso_dt)

        day_dir = HISTORY_ROOT / iso_date
        day_dir.mkdir(parents=True, exist_ok=True)

        slug = unique_slug(base_slug, day_dir)
        prompt_path = day_dir / f'{slug}_prompt.md'
        result_path = day_dir / f'{slug}_result.md'

        write_prompt_file(prompt_path, payload, iso_dt, slug)

        generation_id = str(payload.get('generation_id') or '').strip()
        conversation_id = str(payload.get('conversation_id') or '').strip()
        if not generation_id:
            generation_id = f'no-generation-{slug}'

        entry = {
            'slug': slug,
            'iso_datetime': iso_dt,
            'iso_date': iso_date,
            'prompt_path': str(prompt_path),
            'result_path': str(result_path),
            'conversation_id': conversation_id,
            'generation_id': generation_id,
            'pending': True,
        }

        state = load_state_unlocked()
        prune_state(state, now)
        state['by_generation'][generation_id] = entry
        if conversation_id:
            stack = state['conversation_stack'].setdefault(conversation_id, [])
            stack.append(generation_id)
        save_state_unlocked(state)

def resolve_entry(payload: dict[str, Any]) -> dict[str, Any] | None:
    with state_lock():
        state = load_state_unlocked()
        generation_id = str(payload.get('generation_id') or '').strip()
        conversation_id = str(payload.get('conversation_id') or '').strip()

        if generation_id and generation_id in state['by_generation']:
            return state['by_generation'][generation_id]

        if conversation_id:
            stack = state['conversation_stack'].get(conversation_id) or []
            for gid in reversed(stack):
                entry = state['by_generation'].get(gid)
                if entry and entry.get('pending'):
                    return entry

        pending = [
            entry for entry in state['by_generation'].values()
            if entry.get('pending')
        ]
        if len(pending) == 1:
            return pending[0]
        if pending:
            pending.sort(key=lambda e: e.get('iso_datetime', ''))
            return pending[-1]
        return None

def mark_complete(generation_id: str | None) -> None:
    if not generation_id:
        return
    with state_lock():
        state = load_state_unlocked()
        entry = state['by_generation'].get(generation_id)
        if entry:
            entry['pending'] = False
            save_state_unlocked(state)

def handle_response(payload: dict[str, Any]) -> None:
    entry = resolve_entry(payload)
    if not entry:
        log_error(f'handle_response: no pending entry for payload keys={list(payload.keys())}')
        return

    text = payload.get('text') or ''
    result_path = Path(entry['result_path'])
    write_result_file(result_path, text, entry, payload)
    mark_complete(str(payload.get('generation_id') or entry.get('generation_id') or ''))


def handle_stop(payload: dict[str, Any]) -> None:
    entry = resolve_entry(payload)
    if not entry:
        return

    result_path = Path(entry['result_path'])
    if result_path.exists() and result_path.stat().st_size > 0:
        mark_complete(str(payload.get('generation_id') or entry.get('generation_id') or ''))
        return

    status = payload.get('status', 'unknown')
    fallback = (
        f'_No assistant text was captured by `afterAgentResponse`. '
        f'Agent loop ended with status `{status}`._'
    )
    write_result_file(result_path, fallback, entry, payload)
    mark_complete(str(payload.get('generation_id') or entry.get('generation_id') or ''))


def main() -> int:
    mode = (sys.argv[1] if len(sys.argv) > 1 else '').strip()
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        if not isinstance(payload, dict):
            payload = {}

        if mode == 'prompt':
            register_prompt(payload)
            sys.stdout.write('{"continue": true}\n')
        elif mode == 'response':
            handle_response(payload)
            sys.stdout.write('{}\n')
        elif mode == 'stop':
            handle_stop(payload)
            sys.stdout.write('{}\n')
        else:
            log_error(f'unknown mode: {mode!r}')
            sys.stdout.write('{}\n')
        return 0
    except Exception:
        log_error(traceback.format_exc())
        if mode == 'prompt':
            sys.stdout.write('{"continue": true}\n')
        else:
            sys.stdout.write('{}\n')
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
