---
name: codex-chat-export
description: Export a Codex CLI chat session (from ~/.codex/sessions/*.jsonl) into a Markdown transcript. Use when the user asks to export this chat/session/transcript to a .md file.
---

# Codex Chat Export

Export Codex sessions to Markdown by converting the local JSONL session logs in `~/.codex/sessions/`.

## Default Behavior

- Exports only `user` + `assistant` messages (no tool logs).
- Selects the current session via `CODEX_THREAD_ID` when available; otherwise falls back to the most recently modified `rollout-*.jsonl`.
- Writes to `specs/standup/` if it exists, otherwise `specs/`, otherwise the current directory.
- Prints the output path to stdout.

## Workflow

1. Export to Markdown:

```bash
python3 .agents/skills/codex-chat-export/scripts/export_codex_chat_to_md.py --ascii-only
```

2. Spot-check the output:

```bash
sed -n '1,80p' <exported-file>
```

3. Tell the user the output path, and recommend redacting sensitive content before sharing.

## Options

- `--thread-id <id>`: Choose a specific session/thread id (matches filenames under `~/.codex/sessions/`).
- `--session-jsonl <path>`: Export from an explicit JSONL file.
- `--out <path>`: Write to a specific Markdown file.
- `--include-developer`: Include `developer` role messages.
- `--ascii-only`: Force ASCII-only output (non-ASCII characters become `?`).

## Safety Notes

- Transcripts may include sensitive user-provided content; recommend redaction before sharing.
- Tool outputs can contain secrets and are excluded by default.
