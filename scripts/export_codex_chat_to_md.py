#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional, TypedDict


THREAD_ID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)

# Normalize common "smart punctuation" to ASCII. (We keep other Unicode by default.)
PUNCT_TRANSLATE = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2026": "...",
        "\u00a0": " ",
    }
)


class Msg(TypedDict):
    timestamp: Optional[str]
    role: str
    text: str


def _normalize(text: str, *, ascii_only: bool) -> str:
    text = text.translate(PUNCT_TRANSLATE)
    if not ascii_only:
        return text
    return text.encode("ascii", "replace").decode("ascii")


def _fence_for(text: str) -> str:
    # Choose a fence longer than any backtick run in the message content.
    max_run = 0
    for m in re.finditer(r"`+", text):
        max_run = max(max_run, len(m.group(0)))
    return "`" * (max_run + 3)


def _extract_thread_id(path: Path) -> Optional[str]:
    matches = THREAD_ID_RE.findall(path.name)
    return matches[-1] if matches else None


def _find_session_jsonl(*, thread_id: Optional[str]) -> Path:
    sessions_dir = Path.home() / ".codex" / "sessions"
    if not sessions_dir.exists():
        raise FileNotFoundError(f"Codex sessions directory not found: {sessions_dir}")

    candidates: list[Path] = []
    if thread_id:
        for p in sessions_dir.rglob("rollout-*.jsonl"):
            if thread_id in p.name:
                candidates.append(p)
    else:
        candidates = list(sessions_dir.rglob("rollout-*.jsonl"))

    if not candidates:
        suffix = f" for thread_id={thread_id}" if thread_id else ""
        raise FileNotFoundError(f"No Codex session files found under {sessions_dir}{suffix}")

    # Pick the most recently modified candidate.
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _default_out_path(*, thread_id: Optional[str]) -> Path:
    date = datetime.now().strftime("%Y-%m-%d")
    safe_id = thread_id or "unknown"
    filename = f"{date}-codex-chat-export-{safe_id}.md"

    cwd = Path.cwd()
    for rel in ("specs/standup", "specs"):
        d = cwd / rel
        if d.is_dir():
            return d / filename
    return cwd / filename


def _iter_messages(
    session_jsonl: Path,
    *,
    include_developer: bool,
) -> Iterator[Msg]:
    allowed_roles = {"user", "assistant"}
    if include_developer:
        allowed_roles.add("developer")

    with session_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                # If the file is actively being written, the last line can be partial.
                continue

            if obj.get("type") != "response_item":
                continue

            payload = obj.get("payload") or {}
            role = payload.get("role")
            if role not in allowed_roles:
                continue

            parts: list[str] = []
            for c in payload.get("content") or []:
                if not isinstance(c, dict):
                    continue
                t = c.get("text")
                if isinstance(t, str) and t.strip():
                    parts.append(t)

            if not parts:
                continue

            yield {
                "timestamp": obj.get("timestamp"),
                "role": role,
                "text": "".join(parts),
            }


def export_to_markdown(
    *,
    session_jsonl: Path,
    out_path: Path,
    include_developer: bool,
    ascii_only: bool,
) -> Path:
    thread_id = _extract_thread_id(session_jsonl)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as out:
        out.write("# Codex Chat Export\n\n")
        out.write(f"- Exported at: {datetime.now().isoformat(timespec='seconds')}\n")
        out.write(f"- Source JSONL: {session_jsonl}\n")
        if thread_id:
            out.write(f"- Thread id: {thread_id}\n")
        out.write("\n")

        for msg in _iter_messages(session_jsonl, include_developer=include_developer):
            role_title = msg["role"].capitalize()
            ts = msg.get("timestamp")

            out.write(f"## {role_title}")
            if isinstance(ts, str) and ts:
                out.write(f" ({_normalize(ts, ascii_only=ascii_only)})")
            out.write("\n\n")

            body = _normalize(msg["text"], ascii_only=ascii_only).rstrip() + "\n"
            fence = _fence_for(body)
            out.write(f"{fence}md\n")
            out.write(body)
            out.write(f"{fence}\n\n")

    return out_path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Export a Codex session JSONL into a Markdown transcript (user+assistant messages)."
    )
    parser.add_argument(
        "--session-jsonl",
        type=Path,
        help="Path to a Codex session JSONL file (rollout-*.jsonl).",
    )
    parser.add_argument(
        "--thread-id",
        help="Codex thread id to match in ~/.codex/sessions/**/rollout-*.jsonl (defaults to $CODEX_THREAD_ID).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Output Markdown path (defaults to specs/standup/ or specs/ if present, else CWD).",
    )
    parser.add_argument(
        "--include-developer",
        action="store_true",
        help="Include developer-role messages in the transcript.",
    )
    parser.add_argument(
        "--ascii-only",
        action="store_true",
        help="Force ASCII-only output (non-ASCII characters become '?').",
    )
    args = parser.parse_args(argv)

    session_jsonl: Path
    if args.session_jsonl:
        session_jsonl = args.session_jsonl.expanduser().resolve()
    else:
        thread_id = args.thread_id or os.environ.get("CODEX_THREAD_ID")
        session_jsonl = _find_session_jsonl(thread_id=thread_id)

    if not session_jsonl.exists():
        raise FileNotFoundError(f"Session JSONL not found: {session_jsonl}")

    out_path = (
        args.out.expanduser()
        if args.out
        else _default_out_path(thread_id=_extract_thread_id(session_jsonl))
    ).resolve()
    exported = export_to_markdown(
        session_jsonl=session_jsonl,
        out_path=out_path,
        include_developer=args.include_developer,
        ascii_only=args.ascii_only,
    )
    print(str(exported))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
